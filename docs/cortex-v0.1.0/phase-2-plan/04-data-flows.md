# Phase 2 — Data Flow Diagrams

**Date:** 2026-04-10
**Project:** OneAI-Cortex

---

## Flow 1: Create an Agent

```
Client → POST /api/v1/agents (AgentCreate: name, model, system_prompt, tools, ...)
  │  Header: Authorization: Bearer <jwt_from_oneai_auth>
  │
  ├─ get_current_user() dependency: decode JWT locally (shared HS256 secret) → extract user_id from `sub`
  │
  └─ Router (agents.py):
       │  Parse & validate AgentCreate schema
       │
       └─ AgentService.create_agent(user_id, data):
            │
            ├─ FrameworkAdapter.validate_config(config)
            │     └─ Verify model is supported
            │     └─ Verify tools exist in registry
            │     └─ Return ValidationResult (errors/warnings)
            │     └─ RAISE if invalid
            │
            ├─ AgentRepository.create({name, user_id, framework, status=draft, ...})
            │     └─ INSERT INTO agents → return Agent
            │
            ├─ AgentRepository.create_version(agent_id, config_snapshot)
            │     └─ INSERT INTO agent_versions (version=1, config=JSON) → return AgentVersion
            │
            └─ Return Agent
       │
       └─ Return AgentResponse (201)
```

---

## Flow 2: Run an Agent (SSE Streaming)

```
Client → POST /api/v1/agents/{id}/run (RunRequest: message, session_id?)
  │  Header: Authorization: Bearer <jwt> OR ApiKey <cortex_api_key>
  │
  ├─ get_current_user(): JWT decoded locally OR API key looked up in Cortex DB → user_id
  │
  └─ Router (runner.py):
       │  Parse RunRequest
       │  Return StreamingResponse (SSE)
       │
       └─ RunnerService.run_agent(user_id, agent_id, request):
            │
            ├─ AgentRepository.get_by_id(agent_id)
            │     └─ Verify agent exists and belongs to user
            │
            ├─ AgentRepository.get_latest_version(agent_id)
            │     └─ Load config snapshot (JSONB dict)
            │
            ├─ _build_agent_config(config_dict, agent.name, encryption)
            │     └─ Hydrate full AgentConfig (all 17 fields) from stored dict
            │     └─ _normalize_model(): str/dict → "provider:model_id"
            │     └─ MiddlewareConfig, BackendConfig from nested dicts (or defaults)
            │     └─ _parse_subagents(): sync/async detection, async header decryption
            │     └─ _parse_interrupt_on(): bool/InterruptConfig per tool
            │     └─ Decrypt user_api_keys separately (passed to create_runtime)
            │
            ├─ IF session_id: SessionRepository.get(session_id)
            │     └─ Load existing messages for context
            │  ELSE: SessionRepository.create(agent_id, user_id)
            │     └─ New session
            │
            ├─ SessionRepository.add_message(session_id, "user", request.message)
            │
            ├─ FrameworkAdapter.create_runtime(agent_config, user_api_keys)
            │     └─ DeepAgents: create_deep_agent(model, tools, system_prompt, ...)
            │     └─ Returns AgentRuntime wrapping CompiledStateGraph
            │
            ├─ FrameworkAdapter.execute(runtime, messages, session_id)
            │     └─ DeepAgents: agent.stream({"messages": [...]})
            │     └─ YIELD AgentEvent per stream chunk:
            │           ├─ type="message"     → assistant text chunk
            │           ├─ type="tool_call"   → tool invocation
            │           ├─ type="tool_result" → tool response
            │           └─ type="done"        → execution complete
            │
            ├─ SessionRepository.add_message(session_id, "assistant", full_response)
            │
            └─ YIELD final AgentEvent(type="done", metadata={session_id, tokens_used, ...})
```

**SSE Wire Format:**
```
event: message
data: {"type": "message", "content": "Here's what I found...", "timestamp": "..."}

event: tool_call
data: {"type": "tool_call", "content": "Searching for...", "metadata": {"tool": "web_search"}}

event: done
data: {"type": "done", "metadata": {"session_id": "uuid", "tokens_used": 1234}}
```

---

## Flow 2b: Run Agent with MCP Tools

> When an agent has MCP servers assigned, the Runner loads their configs
> and passes them to the framework adapter before execution.

```
RunnerService.run_agent (continuation of Flow 2, after loading agent config):
  │
  ├─ MCPRepository.get_agent_servers(agent_id)
  │     └─ Load all assigned MCP server configs
  │     └─ Filter: only status='healthy' servers (warn on unhealthy)
  │
  ├─ For each MCP server: build MCPServerConfig from DB record
  │     └─ Decrypt env_vars (API keys) from encrypted JSONB
  │
  ├─ FrameworkAdapter.create_runtime(config, user_api_keys)
  │
  ├─ FrameworkAdapter.attach_mcp_servers(runtime, mcp_configs)
  │     └─ DeepAgents: writes mcp.json to temp dir, adds to agent config
  │     └─ Agent now has access to MCP tools (GitHub, Slack, DB, etc.)
  │
  └─ FrameworkAdapter.execute(runtime, messages, session_id)
        └─ Agent can invoke MCP tools alongside built-in tools
        └─ MCP tool calls appear as AgentEvent(type="tool_call", metadata={"source": "mcp"})
```

---

## Flow 6: Register and Test MCP Server

```
Client → POST /api/v1/mcp-servers (MCPServerCreate: name, transport, url, env_vars, ...)
  │
  ├─ get_current_user() → user_id
  │
  └─ Router (mcp_servers.py):
       └─ MCPService.register_server(user_id, data):
            ├─ Encrypt sensitive env_vars (API keys)
            ├─ MCPRepository.create({name, transport, url, ..., status='untested'})
            └─ Return MCPServer
       └─ Return MCPServerResponse (201)

Client → POST /api/v1/mcp-servers/{id}/test
  │
  └─ Router:
       └─ MCPService.test_server(server_id):
            ├─ Load server config from DB
            ├─ Decrypt env_vars
            ├─ MCPClient.connect(transport, url/command, env_vars)
            │     ├─ stdio: spawn process, init MCP handshake
            │     ├─ sse: connect to SSE endpoint
            │     └─ http: send HTTP request
            ├─ MCPClient.list_tools()
            │     └─ Discover available tools via MCP protocol
            ├─ Update server: status='healthy', tools_discovered=[...], last_tested_at=now()
            │  OR: status='unhealthy' if connection/auth failed
            └─ Return MCPTestResult(reachable, tools_discovered, error, latency_ms)
       └─ Return MCPTestResult (200)
```

---

## Flow 2c: Human-in-the-Loop (HITL) Interrupt/Resume

> When an agent has `interrupt_on` configured for specific tools, execution pauses
> before those tool calls and waits for user approval via SSE + resume endpoint.

```
RunnerService.run_agent (continuation of Flow 2, during execution):
  │
  ├─ FrameworkAdapter.execute(runtime, messages, session_id)
  │     └─ Agent decides to call tool "edit_file" (which is in interrupt_on config)
  │     └─ HumanInTheLoopMiddleware intercepts the tool call
  │     └─ LangGraph pauses execution (interrupt_before)
  │
  ├─ YIELD AgentEvent(type="interrupt"):
  │     data: {
  │       "type": "interrupt",
  │       "content": "Agent wants to edit file: config.py",
  │       "metadata": {
  │         "tool_name": "edit_file",
  │         "tool_args": {"path": "config.py", "content": "..."},
  │         "interrupt_message": "Approve file edit?",
  │         "session_id": "uuid",
  │         "checkpoint_id": "cp-uuid"
  │       }
  │     }
  │
  └─ SSE stream stays open (keepalive pings every 15s) OR closes
       Client shows approval UI to user

─── User decides ───

Client → POST /api/v1/sessions/{session_id}/resume
  │  Body: {"approved": true, "modified_args": null}  ← or false to skip tool
  │
  ├─ get_current_user() → user_id
  │
  └─ RunnerService.resume_session(user_id, session_id, approved, modified_args):
       │
       ├─ Load session, agent, and version from DB
       │
       ├─ _build_agent_config(config_dict, agent.name, encryption)
       │     └─ Reconstruct identical AgentConfig as run_session (all 17 fields)
       │     └─ Ensures HITL resume uses same config as original execution
       │
       ├─ FrameworkAdapter.create_runtime(agent_config, user_api_keys)
       │
       ├─ Load checkpoint from AsyncSqliteSaver for session_id
       │
       ├─ IF approved:
       │     FrameworkAdapter.resume_after_interrupt(runtime, session_id, approved=True, modified_args)
       │     └─ LangGraph resumes from checkpoint, executes the tool call
       │     └─ Continue streaming remaining AgentEvents
       │
       ├─ IF rejected:
       │     FrameworkAdapter.resume_after_interrupt(runtime, session_id, approved=False)
       │     └─ Tool call skipped, LLM receives "Tool call was rejected by user"
       │     └─ LLM continues without the tool result
       │
       └─ YIELD remaining AgentEvents via SSE stream
```

**SSE Wire Format for Interrupt:**
```
id: 15
event: interrupt
data: {"type": "interrupt", "content": "Agent wants to execute: rm -rf /tmp/cache", "metadata": {"tool_name": "execute", "tool_args": {"command": "rm -rf /tmp/cache"}, "interrupt_message": "Approve shell command?", "session_id": "uuid"}}

:keepalive

id: 16
event: message
data: {"type": "message", "content": "I've cleaned up the cache.", "timestamp": "..."}
```

---

## Flow 2d: Checkpointed Session Continuity

> Checkpointing enables conversation resume after server restart or client reconnection.
> Uses LangGraph's AsyncSqliteSaver to persist graph state per session.

```
First request — new session:
  │
  ├─ RunnerService creates new session in DB
  ├─ CheckpointerFactory.get_or_create(session_id)
  │     └─ AsyncSqliteSaver(db_path="data/checkpoints/{session_id}.db")
  ├─ FrameworkAdapter.create_runtime(config, user_api_keys, checkpointer=saver)
  ├─ Execute with thread_id = session_id → state checkpointed after each step
  └─ Done

Second request — same session_id:
  │
  ├─ RunnerService loads existing session from DB
  ├─ CheckpointerFactory.get_or_create(session_id) → reuses same SQLite file
  ├─ FrameworkAdapter.create_runtime(config, user_api_keys, checkpointer=saver)
  ├─ Execute with thread_id = session_id → LangGraph loads prior state from checkpoint
  │     └─ Agent has full conversation context from previous turns
  └─ New messages appended, checkpoint updated
```

**Checkpointing is transparent to the user** — they just pass `session_id` in RunRequest.
Under the hood, LangGraph's checkpointer handles state serialization/deserialization.

---

## Flow 3: Evaluate an Agent

```
Client → POST /api/v1/test-suites/{id}/run (EvalRunRequest: agent_version?)
  │
  ├─ get_current_user() → user_id
  │
  └─ Router (evaluator.py):
       │
       └─ EvaluatorService.run_evaluation(test_suite_id, request):
            │
            ├─ EvaluationRepository.get_by_id(test_suite_id)
            │     └─ Load test suite with test cases
            │
            ├─ AgentRepository.get_version(agent_id, version)
            │     └─ Load agent config for specific version
            │
            ├─ EvaluationRepository.create_eval_run(test_suite_id, version)
            │     └─ INSERT eval_runs (status=running)
            │
            ├─ FOR EACH test_case in test_suite.cases:
            │     │
            │     ├─ FrameworkAdapter.create_runtime(config, keys)
            │     ├─ Collect all events from FrameworkAdapter.execute(runtime, [test_case.input])
            │     ├─ Score response:
            │     │     ├─ exact_match: output == expected
            │     │     ├─ contains: expected in output
            │     │     ├─ llm_judge: use LLM to grade (optional)
            │     │     ├─ latency_ms: execution time
            │     │     └─ token_count: total tokens used
            │     │
            │     └─ EvaluationRepository.add_eval_result(run_id, {
            │           test_case_id, actual_output, score, latency_ms, tokens
            │        })
            │
            ├─ Compute aggregate metrics:
            │     ├─ pass_rate = passed / total
            │     ├─ avg_latency_ms
            │     ├─ avg_tokens
            │     └─ total_cost_estimate
            │
            ├─ Update eval_run: status=completed, metrics=aggregates
            │
            └─ Return EvalRun with results
       │
       └─ Return EvalRunResponse (201)
```

---

## Flow 4: Deploy an Agent (Hosted)

```
Client → POST /api/v1/agents/{id}/deploy (DeployRequest: type="hosted", version?)
  │
  ├─ get_current_user() → user_id
  │
  └─ Router (deployer.py):
       │
       └─ DeployerService.deploy_agent(user_id, agent_id, request):
            │
            ├─ AgentRepository.get_version(agent_id, version)
            │     └─ Load specific version config
            │
            ├─ FrameworkAdapter.validate_config(config)
            │     └─ Verify config is still valid
            │
            ├─ Generate deployment_id (UUID)
            │
            ├─ DeploymentRepository.create({
            │     agent_id, version, type="hosted",
            │     endpoint="/api/v1/hosted/{deployment_id}/chat",
            │     status="active"
            │  })
            │
            └─ Return Deployment
       │
       └─ Return DeploymentResponse (201) with endpoint URL
```

**Hosted agent receives traffic at:**
```
Client → POST /api/v1/hosted/{deployment_id}/chat (ChatRequest: message, api_key)
  │
  └─ Router: load deployment → load agent config → RunnerService.run_agent()
       └─ Same execution flow as Flow 2 (SSE streaming)
```

---

## Flow 5: Download SDK

```
Client → GET /api/v1/agents/{id}/sdk?version=3
  │
  ├─ get_current_user() → user_id
  │
  └─ Router (deployer.py):
       │
       └─ DeployerService.generate_sdk(agent_id, version):
            │
            ├─ AgentRepository.get_version(agent_id, 3)
            │     └─ Load config snapshot
            │
            ├─ FrameworkAdapter.generate_sdk_package(config)
            │     └─ DeepAgents adapter generates:
            │           ├─ my_agent/
            │           │   ├─ __init__.py          (create_deep_agent() with baked config)
            │           │   ├─ agent.py              (agent runner with CLI)
            │           │   ├─ config.py             (agent configuration)
            │           │   └─ deepagents.toml        (native DeepAgents config)
            │           ├─ pyproject.toml              (uv-compatible, pinned deepagents + provider deps)
            │           ├─ README.md                  (setup: `uv sync` + usage instructions)
            │           └─ .env.example               (required API keys)
            │
            └─ Return SDKPackage(filename, zip_bytes, ...)
       │
       └─ Return StreamingResponse (application/zip)
```
