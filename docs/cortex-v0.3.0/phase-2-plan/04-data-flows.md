# Phase 2 — Data Flows

**Date:** 2026-04-13
**Project:** OneAI-Cortex v0.3.0
**Feature:** Agent Configuration Pipeline — Frontend Integration Support

---

## Flow 1: Agent Creation — API Key Encryption

```
Frontend → POST /api/v1/agents
  Body: {
    name: "Assistant", framework: "deepagents",
    config: { model: "anthropic:claude-sonnet-4-6", user_api_keys: { ANTHROPIC_API_KEY: "sk-ant-..." } }
  }

  → Router: validate body (AgentCreate schema), authenticate user (JWT)
    → AgentService.create_agent(user_id, name, description, framework, config)
      → self._adapters.get("deepagents")  ← validate framework exists
      → self._encrypt_config_secrets(config)
        → config["user_api_keys"] detected, non-empty
        → self._encryption.encrypt_dict_values({"ANTHROPIC_API_KEY": "sk-ant-..."})
        ← Returns: {"ANTHROPIC_API_KEY": "gAAAAABm...<fernet-token>..."}
      ← config now has encrypted user_api_keys
      → self._repo.create({user_id, name, description, framework, current_version: 1})
      ← Returns Agent model
      → self._repo.create_version({agent_id, version: 1, config: encrypted_config, change_summary: "Initial version"})
    ← Returns Agent
  ← Return 201: AgentResponse
```

---

## Flow 2: Version Retrieval — Encrypted Keys Returned

```
Frontend → GET /api/v1/agents/{agent_id}/versions/{version}

  → Router: authenticate user (JWT), parse path params
    → AgentService.get_version(agent_id, user_id, version)
      → self.get_agent(agent_id, user_id)  ← verify ownership
      → self._repo.get_version(agent_id, version)
      ← Returns AgentVersion with config JSONB
    ← Returns AgentVersion
  ← Return 200: AgentVersionResponse
    {
      config: {
        model: "anthropic:claude-sonnet-4-6",
        system_prompt: "...",
        user_api_keys: { ANTHROPIC_API_KEY: "gAAAAABm..." }  ← ENCRYPTED
      }
    }

  Frontend receives response:
    → Detects user_api_keys has entries → shows "Key configured" indicator
    → Does NOT attempt to decrypt or display the value
```

---

## Flow 3: Agent Execution — Key Decryption & Injection

```
Frontend → POST /api/v1/run/sessions/{session_id}/chat
  Body: { message: "Hello" }

  → Router: authenticate, validate
    → RunnerService.run_session(session_id, user_id, message)
      → Load session, agent, version
      → config_dict = version.config

      → Decrypt API keys:
        config_dict.get("user_api_keys") → {"ANTHROPIC_API_KEY": "gAAAAABm..."}
        self._encryption.decrypt_dict_values(encrypted_keys)
        ← user_api_keys = {"ANTHROPIC_API_KEY": "sk-ant-..."}  ← PLAINTEXT

      → Build AgentConfig from config_dict
      → adapter = self._adapters.get("deepagents")
      → runtime = await adapter.create_runtime(agent_config, user_api_keys)
        → Backup existing env vars
        → os.environ["ANTHROPIC_API_KEY"] = "sk-ant-..."
        → resolve_model("anthropic:claude-sonnet-4-6") → creates ChatAnthropic client
        → create_deep_agent(model=model, ...) → builds LangGraph
        ← Returns AgentRuntime
        → Restore env vars in finally block

      → Store user message in DB
      → Build message history
      → async for event in adapter.execute(runtime, messages, session_id):
          yield AgentEvent(type=MESSAGE, content="Hello! How can I help?")
      → Store assistant response in DB
    ← SSE stream: event: message\ndata: {...}\n\n
```

---

## Flow 4: Execution Failure — Missing API Keys

```
Frontend → POST /api/v1/run/sessions/{session_id}/chat
  Body: { message: "Hello" }

  → RunnerService.run_session()
    → config_dict.get("user_api_keys") → None or {}
    → user_api_keys = {}  ← EMPTY

    → adapter.create_runtime(agent_config, {})
      → env_backup = {} (nothing to set)
      → resolve_model("anthropic:claude-sonnet-4-6")
        → ChatAnthropic() — no ANTHROPIC_API_KEY in environment
        ← RAISES: AuthenticationError("Invalid API key")
      ← RAISES: AdapterError("Failed to create agent runtime: AuthenticationError: Invalid API key")

    → Error caught by runner endpoint
    ← SSE stream: event: error\ndata: {"type":"error","content":"Failed to create agent runtime: ..."}\n\n

  Frontend receives error:
    → Pattern match: /api.?key|authentication/i → true
    → Show: "This agent needs an API key. Configure it in Settings."
    → Link: /agents/edit/{agentId}
```

---

## Flow Summary

| # | Flow | Data State | Key Status |
|---|------|-----------|------------|
| 1 | Create agent | Plaintext → Encrypted | Keys stored encrypted in JSONB |
| 2 | Get version | Encrypted → Frontend | Frontend sees encrypted blobs |
| 3 | Execute (success) | Encrypted → Decrypted → Env var | Keys injected, then cleaned up |
| 4 | Execute (failure) | Empty → No env var → Error | Provider returns auth error |
