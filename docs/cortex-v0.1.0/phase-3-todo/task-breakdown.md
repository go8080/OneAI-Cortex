# Phase 3 — Task Breakdown

**Date:** 2026-04-10
**Project:** OneAI-Cortex v0.1.0
**Input:** Phase 2 Plan (locked 2026-04-10)
**Status:** COMPLETE — 38 core tasks + 6 post-Phase-3 fixes implemented and verified 2026-04-10

---

## Completion Summary

| Stage | Tasks | Status |
|-------|-------|--------|
| 1. Foundation | T1-T5 | All DONE |
| 2. Data Layer | T6-T9 | All DONE |
| 3. Auth Integration | T10-T14 | All DONE |
| 4. Framework Adapter | T15-T20 | All DONE |
| 5. Tools & MCP | T21-T24 | All DONE |
| 6. Agent Builder | T25-T27 | All DONE |
| 7. Agent Runner | T28-T31 | All DONE |
| 8. Evaluator + Deployer | T32-T35 | All DONE |
| 9. Wiring & Health | T36-T38 | All DONE |
| **Total** | **38/38** | **COMPLETE** |
| Post-Phase 3 Fixes | T39-T44 | All DONE |

**Verification:** `uv run python -c "from app.main import app"` — 39 API routes registered, all imports clean.
**Test suite:** 189 tests passing (148 unit + 41 integration).

---

## Overview

38 tasks organized into 9 stages following the critical path.
Each task is sized S-L (no XL). Dependencies enforce layer ordering.

```
Stage 1: Foundation ──────────────────────┐
Stage 2: Data Layer ──────────────────────┤ (blocked by Stage 1)
Stage 3: Auth Integration ────────────────┤ (blocked by Stage 2)
Stage 4: Framework Adapter ───────────────┤ (blocked by Stage 1)
Stage 5: Tools & MCP ─────────────────────┤ (parallel with Stage 4, blocked by Stage 2+3)
Stage 6: Agent Builder ───────────────────┤ (blocked by Stage 3+4)
Stage 7: Agent Runner ────────────────────┤ (blocked by Stage 4+6)
Stage 8: Evaluator + Deployer ────────────┤ (blocked by Stage 7)
Stage 9: Wiring & Health ─────────────────┘ (blocked by all above)
```

---

## Stage 1: Foundation (5 tasks)

### T1: Project scaffolding with uv [S] DONE
- **What:** `uv init`, pyproject.toml with all deps, .python-version (3.13), .env.example, .gitignore, directory structure
- **Where:** Project root
- **Done when:** `uv sync` installs all deps; directory tree matches 02-architecture.md

### T2: FastAPI app factory + settings [M] DONE
- **What:** main.py (lifespan, app factory), config.py (pydantic-settings, all env vars), dependencies.py (DI stubs)
- **Where:** `app/main.py`, `app/config.py`, `app/dependencies.py`
- **Done when:** `uv run uvicorn app.main:app` starts without errors (empty routes)

### T3: Database infrastructure [M] DONE
- **What:** Async engine, session factory, declarative base, TimestampMixin, SoftDeleteMixin
- **Where:** `app/infrastructure/database.py`, `app/models/base.py`
- **Done when:** `get_db()` dependency yields async sessions; mixins importable

### T4: Core utilities [M] DONE
- **What:** Domain exceptions, constants/enums (AgentStatus, FrameworkType, etc.), Fernet encryption module, domain events
- **Where:** `app/core/exceptions.py`, `app/core/constants.py`, `app/core/encryption.py`, `app/core/events.py`
- **Done when:** `SecretEncryption.encrypt()`/`decrypt()` round-trips; enums importable; missing ENCRYPTION_KEY raises startup error

### T5: Docker Compose [M] DONE
- **What:** Dockerfile (multi-stage, uv-based), Dockerfile.dev, docker-compose.yml (app + postgres + redis + oneai-auth)
- **Where:** `docker/`
- **Done when:** `docker compose up` starts all 4 services; postgres accessible; auth health check passes

---

## Stage 2: Data Layer (4 tasks)

### T6: Auth + Agent domain models [M] DONE
- **What:** APIKey, Agent, AgentVersion ORM models
- **Where:** `app/models/api_key.py`, `app/models/agent.py`
- **Blocked by:** T3
- **Done when:** Models importable, have type hints, use mixins, JSONB config field on AgentVersion

### T7: Runner + Evaluator + Deployer domain models [M] DONE
- **What:** Session, Message, TestSuite, TestCase, EvalRun, EvalResult, Deployment ORM models
- **Where:** `app/models/session.py`, `app/models/evaluation.py`, `app/models/deployment.py`
- **Blocked by:** T3
- **Done when:** All models importable, FKs to agents, correct indexes

### T8: MCP + Tool domain models [M] DONE
- **What:** MCPServer, AgentMCPServer (junction), Tool ORM models
- **Where:** `app/models/mcp_server.py`, `app/models/tool.py`
- **Blocked by:** T3
- **Done when:** Models importable, encrypted JSONB fields marked, junction table has composite PK

### T9: Alembic setup + initial migration [M] DONE
- **What:** Alembic init, env.py configured for async, generate migration for all models
- **Where:** `migrations/`
- **Blocked by:** T6, T7, T8
- **Done when:** `alembic upgrade head` creates all tables; `alembic downgrade -1` is forward-only (documented as no downgrade)

---

## Stage 3: Auth Integration (5 tasks)

### T10: Core security module [M] DONE
- **What:** JWT decode/validate (shared HS256 secret, no signing), API key hashing (SHA-256), API key prefix extraction
- **Where:** `app/core/security.py`
- **Blocked by:** T4
- **Done when:** `decode_jwt()` returns user_id from sub claim; `hash_api_key()` produces deterministic hash; invalid/expired tokens raise specific exceptions

### T11: Auth client infrastructure [M] DONE
- **What:** httpx async client to OneAI-Auth API for profile lookups; retry logic; Redis caching (5-min TTL)
- **Where:** `app/infrastructure/auth_client.py`
- **Blocked by:** T2
- **Done when:** `AuthClient.get_user_profile(user_id)` returns profile or gracefully degrades; cached responses served from Redis

### T12: get_current_user dependency [M] DONE
- **What:** FastAPI dependency that handles dual auth (Bearer JWT + ApiKey header); returns AuthenticatedUser dataclass
- **Where:** `app/dependencies.py` (update)
- **Blocked by:** T10, T11
- **Done when:** JWT auth → user_id from sub; API key auth → user_id from DB lookup; invalid auth → 401

### T13: API Key CRUD [L] DONE
- **What:** Schemas (create/response/summary), repository, service (create/list/revoke/validate), endpoints
- **Where:** `app/api/v1/schemas/api_keys.py`, `app/repositories/api_key_repository.py`, `app/services/api_key_service.py`, `app/api/v1/endpoints/api_keys.py`
- **Blocked by:** T6, T12
- **Done when:** POST creates key (returns full key once), GET lists (prefix only), DELETE revokes; key_hash stored not raw key

### T14: Startup lifecycle [M] DONE
- **What:** Lifespan hook: (1) check ENCRYPTION_KEY present, (2) validate JWT_SECRET_KEY via test decode, (3) health check OneAI-Auth with 3 retries + 2s backoff → FATAL if fails
- **Where:** `app/main.py` (update lifespan)
- **Blocked by:** T10, T4
- **Done when:** Missing ENCRYPTION_KEY → app refuses to start; Auth unreachable → FATAL log + exit; all green → startup succeeds

---

## Stage 4: Framework Adapter (6 tasks)

### T15: Adapter protocol + registry [M] DONE
- **What:** FrameworkAdapter Protocol (all methods from 03-interfaces.md), AdapterRegistry with version checking, factory function
- **Where:** `app/core/adapter_protocol.py`, `app/adapters/registry.py`, `app/adapters/__init__.py`
- **Blocked by:** T4
- **Done when:** Protocol importable; registry registers/retrieves adapters by name; version mismatch logs warning

### T16: DeepAgents — model resolution + middleware [M] DONE
- **What:** resolve "provider:model" strings to BaseChatModel via init_chat_model(); MiddlewareConfig → ordered middleware list assembly
- **Where:** `app/adapters/deepagents/models.py`, `app/adapters/deepagents/middleware.py`
- **Blocked by:** T15
- **Done when:** "anthropic:claude-sonnet-4-6" resolves to ChatAnthropic; middleware toggles produce correct ordered list

### T17: DeepAgents — backends + subagents [M] DONE
- **What:** BackendConfig → StateBackend/FilesystemBackend instantiation; SyncSubAgentConfig → SubAgent dict, AsyncSubAgentConfig → AsyncSubAgent dict with inheritance rules
- **Where:** `app/adapters/deepagents/backends.py`, `app/adapters/deepagents/subagents.py`
- **Blocked by:** T15
- **Done when:** BackendConfig(type="state") → StateBackend(); SubAgentConfig with model=None inherits parent model

### T18: DeepAgents — main adapter [L] DONE
- **What:** DeepAgentsAdapter implementing FrameworkAdapter Protocol. Orchestrates: validate_config, create_runtime (wires all params to create_deep_agent()), execute (async iterator of AgentEvents), resume_after_interrupt, generate_sdk_package, attach_mcp_servers
- **Where:** `app/adapters/deepagents/adapter.py`, `app/adapters/deepagents/__init__.py`
- **Blocked by:** T16, T17
- **Done when:** create_runtime produces AgentRuntime wrapping CompiledStateGraph; execute yields AgentEvents; interrupt_on triggers interrupt event

### T19: Checkpointer infrastructure [M] DONE
- **What:** CheckpointerFactory: get_or_create(session_id) → AsyncSqliteSaver at data/checkpoints/{session_id}.db; cleanup method for expired checkpoints
- **Where:** `app/infrastructure/checkpointer.py`
- **Blocked by:** T2
- **Done when:** Factory creates/reuses SQLite files per session; cleanup deletes files older than CHECKPOINT_RETENTION_DAYS

### T20: Framework + adapter endpoints [S] DONE
- **What:** GET /frameworks, GET /frameworks/{name} → AdapterVersionInfo
- **Where:** `app/api/v1/endpoints/frameworks.py`
- **Blocked by:** T15
- **Done when:** Endpoints return registered adapters with version + compatibility info

---

## Stage 5: Tools & MCP (4 tasks — parallel with Stage 4)

### T21: Tool Registry [L] DONE
- **What:** Schemas, repository, service (list/register/get/test with auth validation), endpoints
- **Where:** `app/api/v1/schemas/tools.py`, `app/repositories/tool_repository.py`, `app/services/tool_service.py`, `app/api/v1/endpoints/tools.py`
- **Blocked by:** T8, T12
- **Done when:** CRUD works; POST /tools/{id}/test validates auth/connectivity; encrypted auth_config stored

### T22: MCP client infrastructure [L] DONE
- **What:** MCP protocol client supporting stdio (spawn process), SSE (connect endpoint), HTTP (request) transports; tool discovery via list_tools(); connection testing
- **Where:** `app/infrastructure/mcp_client.py`
- **Blocked by:** T2
- **Done when:** MCPClient.connect() + list_tools() works for all 3 transports; timeouts and error handling per Risk 11

### T23: MCP Server Manager — service + repository [L] DONE
- **What:** Schemas (create/update/response/test result/tool discovery), repository (CRUD + agent assignment), service (register, test, discover tools, assign/unassign, 3-strike skip)
- **Where:** `app/api/v1/schemas/mcp_servers.py`, `app/repositories/mcp_repository.py`, `app/services/mcp_service.py`
- **Blocked by:** T8, T12, T22
- **Done when:** Register encrypts env_vars; test connects + discovers tools; assign/unassign updates junction table; 3 consecutive failures → status=unhealthy

### T24: MCP Server endpoints [M] DONE
- **What:** All 10 MCP endpoints from 03-interfaces.md (CRUD, test, tools discovery, assign/unassign to agent)
- **Where:** `app/api/v1/endpoints/mcp_servers.py`
- **Blocked by:** T23
- **Done when:** All 10 endpoints return correct responses; secrets masked on GET; test endpoint returns MCPTestResult

---

## Stage 6: Agent Builder (3 tasks)

### T25: Agent schemas [M] DONE
- **What:** AgentCreate, AgentUpdate, AgentResponse, AgentVersionResponse; includes full config validation (model format, middleware config, backend config, subagent configs, interrupt_on)
- **Where:** `app/api/v1/schemas/agents.py`
- **Blocked by:** T4
- **Done when:** Pydantic models validate all AgentConfig fields; invalid model format rejected; response masks user_api_keys

### T26: Agent repository [M] DONE
- **What:** AgentRepository (CRUD by user, soft delete) + version management (create_version, get_versions, get_latest_version, get_version by number)
- **Where:** `app/repositories/agent_repository.py`
- **Blocked by:** T6
- **Done when:** create_agent + create_version works; list_agents filters by user_id + is_deleted; version numbers auto-increment per agent

### T27: Agent service + endpoints [L] DONE
- **What:** AgentService (create validates via adapter, update creates new version, encrypts user_api_keys); Agent endpoints (7 from 03-interfaces.md)
- **Where:** `app/services/agent_service.py`, `app/api/v1/endpoints/agents.py`
- **Blocked by:** T25, T26, T12, T15
- **Done when:** POST creates agent + version 1; PUT creates new version; GET returns masked keys; versions endpoint lists all versions

---

## Stage 7: Agent Runner (4 tasks)

### T28: SSE streaming infrastructure [M] DONE
- **What:** SSE event formatter (id, event, data fields); Last-Event-ID reconnection support (replay from stored events); keepalive pings (15s); timeout on stale connections (30s)
- **Where:** `app/infrastructure/streaming.py`
- **Blocked by:** T2
- **Done when:** SSE stream emits events with incrementing IDs; reconnection with Last-Event-ID replays missed events; keepalive pings sent

### T29: Runner schemas + session repository [M] DONE
- **What:** RunRequest, ResumeRequest, SessionResponse, MessageResponse schemas; SessionRepository (CRUD, add_message, get_messages by session)
- **Where:** `app/api/v1/schemas/runner.py`, `app/repositories/session_repository.py`
- **Blocked by:** T7, T4
- **Done when:** Schemas validate run/resume payloads; session repo stores messages with metadata; chronological retrieval works

### T30: Runner service [L] DONE
- **What:** RunnerService: run_agent (create session → load config → decrypt keys → create_runtime with checkpointer → execute → stream AgentEvents → persist messages); resume_session (load checkpoint → resume after HITL); list/get/delete sessions. Wraps execution in asyncio.wait_for (120s default)
- **Where:** `app/services/runner_service.py`
- **Blocked by:** T18, T19, T26, T28, T29
- **Done when:** Agent executes and streams via SSE; session persists messages; HITL interrupt pauses + resume works; timeout at 120s; MCP servers attached if configured

### T31: Runner endpoints [M] DONE
- **What:** POST /agents/{id}/run (SSE stream), POST /sessions/{id}/resume, GET /agents/{id}/sessions, GET /sessions/{id}, DELETE /sessions/{id}
- **Where:** `app/api/v1/endpoints/runner.py`
- **Blocked by:** T30
- **Done when:** Run returns StreamingResponse (SSE); resume continues after interrupt; session CRUD works; auth enforced on all endpoints

---

## Stage 8: Evaluator + Deployer (4 tasks)

### T32: Agent Evaluator [L] DONE
- **What:** Schemas + repository + service + endpoints. Test suite CRUD, run evaluation (iterate test cases, score responses: exact_match/contains/llm_judge), aggregate metrics, store results
- **Where:** `app/api/v1/schemas/evaluator.py`, `app/repositories/evaluation_repository.py`, `app/services/evaluator_service.py`, `app/api/v1/endpoints/evaluator.py`
- **Blocked by:** T30, T7
- **Done when:** Create test suite + cases; run eval against agent version; results stored with scores; aggregate metrics computed (pass_rate, avg_latency)

### T33: SDK packager infrastructure [M] DONE
- **What:** Generate standalone agent SDK as ZIP: pyproject.toml (uv-compatible), agent module with baked create_deep_agent() config, deepagents.toml, README, .env.example
- **Where:** `app/infrastructure/sdk_packager.py`
- **Blocked by:** T18
- **Done when:** generate_sdk_package(config) produces valid ZIP; extracted package has pyproject.toml with correct deps; README has uv sync instructions

### T34: Agent Deployer — service + repository [L] DONE
- **What:** Schemas (deploy request/response), DeploymentRepository, DeployerService (deploy hosted → create endpoint, undeploy, generate SDK download, list deployments)
- **Where:** `app/api/v1/schemas/deployer.py`, `app/repositories/deployment_repository.py`, `app/services/deployer_service.py`
- **Blocked by:** T30, T33
- **Done when:** Deploy creates active deployment with endpoint URL; undeploy sets status=stopped; SDK download returns ZIP

### T35: Deployer endpoints + hosted agent [M] DONE
- **What:** POST /agents/{id}/deploy, DELETE /deployments/{id}, GET /agents/{id}/deployments, GET /agents/{id}/sdk; POST /hosted/{deployment_id}/chat (SSE)
- **Where:** `app/api/v1/endpoints/deployer.py`
- **Blocked by:** T34
- **Done when:** Deploy returns endpoint URL; hosted agent receives traffic and runs via RunnerService; SDK downloads as ZIP

---

## Stage 9: Wiring & Health (3 tasks)

### T36: Health endpoints [S] DONE
- **What:** GET /health (status + version), GET /health/ready (db pool stats, redis ping, auth reachability, checkpoint dir size)
- **Where:** `app/api/v1/endpoints/health.py`
- **Blocked by:** T3, T11
- **Done when:** Health returns 200 with version; readiness fails if DB/auth unreachable; pool stats included

### T37: Router aggregation + final wiring [M] DONE
- **What:** Wire all v1 routers into router.py; register adapters in lifespan; verify all endpoints accessible
- **Where:** `app/api/router.py`, `app/api/v1/__init__.py`, `app/main.py` (update)
- **Blocked by:** All endpoint tasks (T13, T20, T21, T24, T27, T31, T32, T35, T36)
- **Done when:** All 38+ endpoints accessible via /api/v1/; OpenAPI docs generated at /docs

### T38: Telemetry + structured logging [M] DONE
- **What:** structlog setup (JSON output, request_id injection), OpenTelemetry traces for agent execution, Redis cache infrastructure
- **Where:** `app/infrastructure/telemetry.py`, `app/infrastructure/cache.py`
- **Blocked by:** T2
- **Done when:** All log entries are structured JSON with request_id; agent execution produces trace spans

---

## Dependency Graph Summary

```
T1 ─┬─ T2 ─┬─ T11 ──────────┐
    │      ├─ T19             │
    │      ├─ T22             │
    │      ├─ T28             │
    │      └─ T38             │
    ├─ T3 ─┬─ T6 ──┬─ T9 ──┐│
    │      ├─ T7 ──┤       ││
    │      └─ T8 ──┘       ││
    ├─ T4 ─┬─ T10 ─┐       ││
    │      ├─ T14  │       ││
    │      ├─ T15 ─┼─ T16  ││
    │      │       │  T17  ││
    │      │       │   ↓   ││
    │      │       │  T18  ││
    │      ├─ T25  │       ││
    │      └─ T29  │       ││
    └─ T5          │       ││
                   ↓       ↓↓
              T12 ← T10+T11 │
                ↓            │
              T13 ← T6+T12  │
              T21 ← T8+T12  │
              T23 ← T8+T12+T22
              T24 ← T23     │
              T26 ← T6      │
              T27 ← T25+T26+T12+T15
              T30 ← T18+T19+T26+T28+T29
              T31 ← T30
              T32 ← T30+T7
              T33 ← T18
              T34 ← T30+T33
              T35 ← T34
              T36 ← T3+T11
              T37 ← all endpoints
```

## Post-Phase 3: Bug Fixes & Quality (6 tasks)

Discovered during test stabilization and code review after the 38 core tasks were complete.

### T39: SQLite test compatibility shims [S] DONE
- **What:** JSONB→JSON column remapping, `gen_random_uuid()` function registration with `.hex` UUID format, event listener on `engine.sync_engine`
- **Where:** `tests/conftest.py`
- **Track:** Fast Track (1 layer, existing pattern, no new interfaces)
- **Done when:** All integration tests pass against in-memory SQLite; UUID lookups work (hex format, no dashes)

### T40: AdapterRegistry exception type corrections [S] DONE
- **What:** Registry raises `AdapterError` (not `EntityNotFoundError`) on duplicate registration and unknown framework lookup. Fixed test expectations.
- **Where:** `tests/unit/adapters/test_registry.py`
- **Track:** Fast Track
- **Done when:** `test_register_duplicate_raises` and `test_get_unknown_raises` use `AdapterError`

### T41: AgentService soft_delete return contract [S] DONE
- **What:** `soft_delete` returns `True` on success; service checks `if not deleted:`. Fixed mock to return `True` instead of `None`.
- **Where:** `tests/unit/services/test_agent_service.py`
- **Track:** Fast Track
- **Done when:** `test_soft_deletes` passes with correct return value expectation

### T42: Evaluator scoring edge cases [S] DONE
- **What:** `exact_match` uses case-insensitive `.lower()` comparison; `None` expected output auto-passes with score `1.0`. Fixed test assertions.
- **Where:** `tests/unit/services/test_evaluator_service.py`
- **Track:** Fast Track
- **Done when:** `test_exact_match_case_insensitive`, `test_exact_match_fail`, `test_contains_none_expected` all pass

### T43: AuthClient test rewrite [M] DONE
- **What:** `AuthClient` creates `httpx.AsyncClient` as context manager per call (no `_client` attribute). Rewrote tests to mock `httpx.AsyncClient` constructor.
- **Where:** `tests/unit/test_infrastructure.py`
- **Track:** Fast Track
- **Done when:** All `TestAuthClient` tests pass with correct mocking pattern

### T44: RunnerService config hydration — `_build_agent_config()` [L] DONE
- **What:** Private helper hydrates all 17 `AgentConfig` fields from stored JSONB dict. Includes `_parse_subagents()` (sync/async detection, async header decryption) and `_parse_interrupt_on()` (bool/InterruptConfig). Both `run_session()` and `resume_session()` call the helper. 18 new unit tests.
- **Where:** `app/services/runner.py`, `tests/unit/test_runner_helpers.py`
- **Track:** Full lifecycle (Ideas → Plan → Todo → Gates) — ADR-015
- **Done when:** All 17 fields reach the adapter; sync + async subagents parsed; encrypted headers decrypted; interrupt_on with bool and dict values handled; 18 new tests pass

---

## Size Distribution

| Size | Count | Tasks |
|------|-------|-------|
| S | 6 | T1, T36, T39-T42 |
| M | 24 | T2-T5, T6-T8, T10-T12, T14, T16-T17, T19-T20, T24-T26, T28-T29, T31, T35, T37-T38, T43 |
| L | 9 | T9, T13, T18, T21-T23, T27, T30, T32-T34, T44 |
| Total | 44 | (38 core + 6 post-Phase 3) |
