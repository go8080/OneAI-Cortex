# Phase 2 — Dependencies & Risk Register

**Date:** 2026-04-10
**Project:** OneAI-Cortex

---

## Dependency Map

| Dependency | Type | Status | Blocks |
|-----------|------|--------|--------|
| Python 3.13+ | Runtime | Available | Everything |
| uv | Tooling | Available (standalone installer) | Project setup, dependency management, venv, lockfile |
| FastAPI + Uvicorn | Library | Available (uv) | API layer |
| **OneAI-Auth service** | **External service (HARD DEP)** | **Available (separate repo)** | **App startup, all authenticated endpoints** |
| PostgreSQL 15+ | Infrastructure | Needs Docker setup | All repositories |
| SQLAlchemy 2.0 (async) | Library | Available (uv) | Repository layer |
| Alembic | Library | Available (uv) | Migrations |
| Pydantic v2 + pydantic-settings | Library | Available (uv) | Config, schemas |
| DeepAgents SDK | Library | Available (uv, from source) | Framework adapter |
| LangChain + LangGraph | Library | Transitive via DeepAgents | Agent execution |
| Redis | Infrastructure | Needs Docker setup | Task queue (eval runs) |
| python-jose | Library | Available (uv) | JWT decode/validate (no signing) |
| httpx | Library | Available (uv) | Auth API client, MCP HTTP transport |
| sse-starlette | Library | Available (uv) | SSE streaming |
| mcp (Python SDK) | Library | Available (uv) | MCP client for stdio/SSE/HTTP transports |
| Docker + Docker Compose | Infrastructure | Assumed available | Dev environment |
| pytest + pytest-asyncio | Library | Available (uv) | Testing |
| Ruff | Library | Available (uv) | Linting/formatting |
| cryptography (Fernet) | Library | Available (uv, transitive via python-jose) | Field-level encryption for secrets at rest |
| packaging | Library | Available (uv) | Semver parsing for adapter compatibility |
| aiosqlite | Library | Available (uv) | AsyncSqliteSaver for LangGraph checkpointing |
| langgraph-checkpoint-sqlite | Library | Available (uv) | LangGraph checkpoint persistence |

---

## Risk Register

### Risk 1: OneAI-Auth service unavailable
**Likelihood:** Low | **Impact:** Critical | **Decision:** IMPLEMENT BEST PRACTICE

**Mitigation strategy (layered):**

1. **Startup gate (HARD):** Lifespan hook calls `GET {AUTH_SERVICE_URL}/ready` during startup. If it fails after 3 retries (2s backoff) → Cortex **refuses to start** with clear error: `"FATAL: OneAI-Auth unreachable at {url}. Cortex requires Auth service to be running."`

2. **Runtime resilience:** JWT validation is **local** (shared HS256 secret, no HTTP call) — so existing authenticated users continue working even if Auth goes down at runtime. Only profile lookups (`GET /users/profile`) need Auth API.

3. **Profile lookup degradation:** If Auth API is unreachable at runtime, profile lookups return `user_id` only (no name/avatar). Cached profiles served from Redis with 5-min TTL. Logged as WARNING, not error.

4. **Health check:** `GET /api/v1/health/ready` includes `"auth": "ok"|"degraded"|"unreachable"`. Monitoring alerts on anything other than `"ok"`.

5. **Docker Compose:** OneAI-Auth listed with `depends_on` + `condition: service_healthy` so Cortex doesn't start before Auth is ready.

---

### Risk 2: JWT_SECRET_KEY desync between Auth and Cortex
**Likelihood:** Low | **Impact:** Critical | **Decision:** SINGLE `.env` FILE

**Implementation:**
- One `.env` file at the project root level, shared by both services via Docker Compose `env_file` directive
- Both `OneAI-Auth` and `OneAI-Cortex` read `JWT_SECRET_KEY` from the same `.env`
- Startup validation: Cortex decodes a known test payload with the configured secret — if decode fails, startup aborts with `"FATAL: JWT_SECRET_KEY validation failed. Check .env is shared with OneAI-Auth."`
- `.env.example` documents this clearly: `# SHARED between OneAI-Auth and OneAI-Cortex — must be identical`

---

### Risk 3: `create_deep_agent()` not designed for multi-tenant server use
**Likelihood:** Medium | **Impact:** High | **Decision:** DEFERRED TO NEXT PHASE

For v0.1: each request creates a fresh agent instance via `create_deep_agent()`. No instance reuse across requests. This is safe enough for initial launch.

Multi-tenant isolation (process sandboxing, resource limits, memory cleanup) will be addressed when scaling patterns emerge from real usage.

---

### Risk 4: SSE streaming drops connection mid-execution
**Likelihood:** Medium | **Impact:** Medium | **Decision:** MUST IMPLEMENT RECONNECTION

**Implementation:**
1. **Event IDs:** Every SSE event includes an incrementing `id` field:
   ```
   id: 42
   event: message
   data: {"type": "message", "content": "...", "event_id": 42}
   ```

2. **Persist partial results:** Every event is written to the `messages` table as it streams (not just the final response). Session stores last `event_id`.

3. **Reconnection via `Last-Event-ID`:** When client reconnects with `Last-Event-ID: 42` header, Runner replays events from event 43 onward from the session message log.

4. **Agent execution continuity:** If the agent is still running when client reconnects, stream resumes from live execution. If agent finished, replay from stored events.

5. **Timeout on stale connections:** Server closes SSE after 30s of no events (keepalive pings every 15s to detect dead connections).

---

### Risk 5: Agent execution hangs indefinitely (LLM timeout)
**Likelihood:** Medium | **Impact:** Medium | **Decision:** IMPLEMENT

**Implementation:**
- Wrap agent execution in `asyncio.wait_for(execute(), timeout=settings.agent_execution_timeout)`
- Default timeout: 120 seconds (configurable via `AGENT_EXECUTION_TIMEOUT_SECONDS` env var)
- On timeout: cancel the task, send `AgentEvent(type="error", content="Agent execution timed out after 120s. The LLM may be overloaded or the task too complex. Try again or simplify your request.")` via SSE
- Log timeout with structured context: `agent_id`, `session_id`, `elapsed_seconds`, `last_event_type`

---

### Risk 6: JSONB config schema drift across versions
**Likelihood:** Low | **Impact:** Medium

Config versioning in `agent_versions` table; migration scripts for old config formats if schema changes.

---

### Risk 7: Evaluation runs overload the system
**Likelihood:** High | **Impact:** Medium

Queue-based execution via Redis; limit concurrent eval runs per user; progress tracking via SSE.

---

### Risk 8: SDK package generation produces broken packages
**Likelihood:** Medium | **Impact:** Low

Integration test that generates SDK, installs it in a fresh `uv venv`, and runs the agent end-to-end.

---

### Risk 9: Users supply invalid LLM API keys
**Likelihood:** High | **Impact:** Medium | **Decision:** IMPLEMENT

**Implementation:**
- On first agent run, validate key with a lightweight API call (e.g., list models)
- Cache validation result per key hash with 10-min TTL in Redis
- On failure, return clear SSE event: `AgentEvent(type="error", content="Invalid API key for {provider}. Please check your {provider} API key and ensure it has sufficient quota.")`
- Distinguish: "invalid key" vs "rate limited" vs "insufficient quota" vs "network error"
- **Never log or persist raw API keys** — log only key prefix (first 8 chars) for debugging

---

### Risk 10: Tools/MCP servers with invalid API keys or auth
**Likelihood:** High | **Impact:** Medium | **Decision:** LLM RESPONDS WITH PROPER ERROR + STRUCTURED LOGGING

**Implementation:**
- `POST /mcp-servers/{id}/test` and `POST /tools/{id}/test` validate auth before assignment
- If tool/MCP auth fails **during agent execution**:
  1. Framework adapter catches the auth error
  2. Converts to `AgentEvent(type="tool_result", content="Tool '{tool_name}' authentication failed: {specific_error}. Please verify the API key configured for this tool.", metadata={"error": true, "tool": tool_name})`
  3. The LLM receives this as a tool result and **responds to the user explaining the issue** — e.g., "I tried to search GitHub but the configured API key is invalid. Please update the MCP server credentials."
  4. **Structured log:** `logger.warning("tool_auth_failure", tool_name=..., mcp_server_id=..., error_type=..., request_id=..., agent_id=..., session_id=...)`
- Agent does NOT crash — it gracefully handles the failed tool and continues with available tools

---

### Risk 11: MCP server becomes unreachable during agent execution
**Likelihood:** Medium | **Impact:** Medium | **Decision:** LLM RESPONDS WITH PROPER ERROR + STRUCTURED LOGGING

**Implementation:**
- Same pattern as Risk 10:
  1. MCP client catches connection error (timeout, refused, DNS failure)
  2. Returns as tool result: `"MCP server '{server_name}' is currently unreachable: {error}. I'll continue without this tool."`
  3. LLM receives this and **tells the user** — e.g., "The GitHub integration is currently unavailable. I can help with other tools, or you can try again later."
  4. **Structured log:** `logger.error("mcp_connection_failure", server_name=..., server_id=..., transport=..., error=..., request_id=..., agent_id=...)`
- After 3 consecutive failures for the same MCP server in a session, stop retrying and inform LLM: `"MCP server '{name}' has failed multiple times this session. Skipping for remaining requests."`
- Background: update `mcp_servers.status = 'unhealthy'` and `last_tested_at = now()`

---

### Risk 12: PostgreSQL connection pool exhaustion under load
**Likelihood:** Low | **Impact:** High | **Decision:** IMPLEMENT

**Implementation:**
- Configure `pool_size`, `max_overflow`, `pool_timeout` via env vars
- Health check endpoint monitors pool stats: `"db_pool": {"size": 10, "checked_out": 3, "overflow": 0}`
- Readiness probe fails if pool is exhausted
- Connection leak detection in integration tests

---

### Risk 13: Framework adapter abstraction too leaky
**Likelihood:** Medium | **Impact:** Medium | **Decision:** IMPLEMENT

Code review gate: adapter protocol uses only framework-agnostic types. No LangGraph/LangChain types in service layer. Adapter version metadata enforces explicit SDK compatibility ranges.

---

### Risk 14: ENCRYPTION_KEY loss = all encrypted secrets unrecoverable
**Likelihood:** Low | **Impact:** Critical

**Mitigation:**
- `.env` file included in secure backup strategy (not in git — `.gitignore`)
- `.env.example` documents that `ENCRYPTION_KEY` must be backed up
- Docker Compose mounts `.env` as read-only
- Future: key rotation support with `key_id` prefix on ciphertext

---

### Risk 15: Framework SDK version mismatch
**Likelihood:** Medium | **Impact:** High

Each adapter declares `sdk_compatibility` (PEP 440). At startup, registry checks installed version. If incompatible → adapter not registered + warning. `GET /frameworks` exposes status.

---

### Risk 16: HITL interrupt state lost if server restarts
**Likelihood:** Low | **Impact:** Medium | **Decision:** IMPLEMENT

**Mitigation:**
- Checkpoint state is persisted in SQLite via AsyncSqliteSaver — survives server restarts
- Interrupt metadata (tool_name, tool_args) stored in checkpoint, not in-memory
- On resume, RunnerService loads checkpoint from disk and resumes graph execution
- If checkpoint file is corrupted/missing → clear error: `"Session interrupted state could not be restored. Please retry the agent execution."`

---

### Risk 17: Checkpoint SQLite files accumulate indefinitely
**Likelihood:** High | **Impact:** Low | **Decision:** IMPLEMENT

**Mitigation:**
- Cleanup job: delete checkpoint files for sessions older than 7 days (configurable `CHECKPOINT_RETENTION_DAYS`)
- Triggered on session delete and via periodic background task
- Monitor `data/checkpoints/` directory size in health endpoint

---

### Risk 18: Middleware ordering misconfiguration breaks agent
**Likelihood:** Low | **Impact:** Medium

DeepAgents enforces a strict middleware order (base stack → user middleware → tail stack). Cortex exposes only enable/disable toggles, not reordering. The adapter handles ordering internally. Custom middleware authoring deferred to v0.2 reduces this risk further.

---

## Error Handling Philosophy

> **Principle:** When a tool or MCP server fails, the **LLM tells the user what happened** in natural language.
> The platform converts errors into tool results that the LLM can understand and explain.
> All errors are also logged with structured context (`request_id`, `agent_id`, `session_id`, `tool_name`)
> for debugging. The user sees a helpful message; the operator sees a traceable log.

```
Error in tool/MCP → AgentEvent(type="tool_result", error=true, content="human-readable error")
                   → LLM reads this and explains to user in conversation
                   → Structured log emitted with full context for debugging
```

---

## Critical Path

```
1. Project scaffolding (app factory, config, DB, Docker) ─────────┐
2. Database models + Alembic migrations ──────────────────────────┤
3. Auth integration (JWT validation + API keys + Auth client) ────┤  ← HARD DEP on OneAI-Auth
4. Framework adapter protocol (versioned) + DeepAgents adapter ───┤
5. Tool Registry + MCP Server Manager ───────────────────────────┤  ← can be parallel with 4
6. Agent Builder (CRUD + versioning + MCP assignment) ────────────┤
7. Agent Runner (execution + SSE reconnection + sessions + MCP) ──┤
8. Agent Evaluator (test suites + scoring + tool/MCP testing) ────┤
9. Agent Deployer (hosted endpoints + SDK generation) ────────────┘
```
