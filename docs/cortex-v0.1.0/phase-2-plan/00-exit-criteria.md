# Phase 2 — Plan: Exit Criteria

**Date:** 2026-04-10
**Project:** OneAI-Cortex
**Status:** PHASE 3 COMPLETE

---

## Exit Criteria Checklist

```
[x] Scope defined with explicit in/out boundaries              → 01-scope.md (22 in-scope, 18 out-of-scope, 9 assumptions)
[x] Every affected layer identified with specific file changes  → 02-architecture.md (8 modules mapped incl. expanded adapter with 5 submodules)
[x] Interfaces between layers defined                           → 03-interfaces.md (full 17-param AgentConfig, 36+ API endpoints, HITL resume, service + repo interfaces)
[x] At least one data flow traced end-to-end                    → 04-data-flows.md (9 flows: create, run, run+MCP, HITL interrupt/resume, checkpointed session, MCP test, evaluate, deploy, SDK)
[x] All architectural decisions have ADRs written               → ADR-001 through ADR-015
[x] Dependencies mapped with status                             → 06-dependencies-risks.md (21 deps incl. aiosqlite, langgraph-checkpoint-sqlite)
[x] Key risks identified with mitigations                       → 06-dependencies-risks.md (18 risks incl. HITL state loss, checkpoint growth, middleware ordering)
[x] Design reviewed by user                                     ← APPROVED 2026-04-10
[x] No open questions that would block implementation           → All resolved in ADRs
```

---

## Phase 2 Document Index

| Doc | Contents |
|-----|----------|
| `01-scope.md` | 22 in-scope items (incl. full param mapping, middleware, HITL, backends, checkpointing), 18 out-of-scope (incl. deferred skills, memory, CompiledSubAgent), 9 assumptions |
| `02-architecture.md` | Module diagram, 8 modules, expanded adapter (5 submodules: adapter, middleware, backends, models, subagents), checkpointer infrastructure |
| `03-interfaces.md` | Full 17-param AgentConfig, 10 supporting types (incl. SyncSubAgentConfig, AsyncSubAgentConfig, MiddlewareConfig, BackendConfig, InterruptConfig, ModelSpec), 36+ API endpoints, HITL resume endpoint, parameter mapping table |
| `04-data-flows.md` | 9 end-to-end flows: Create Agent, Run Agent (SSE), Run with MCP, HITL Interrupt/Resume (Flow 2c), Checkpointed Session (Flow 2d), MCP Test, Evaluate, Deploy, SDK |
| `05-data-model.md` | 12 tables, expanded config JSONB (middleware, backend, interrupt_on, response_format, recursion_limit, debug, subagent types), checkpoint storage in SQLite |
| `06-dependencies-risks.md` | 21 dependencies, 18 risks w/ mitigations (incl. HITL state loss, checkpoint growth, middleware ordering), critical path |

## ADR Index

| ADR | Decision |
|-----|----------|
| ADR-001 | Modular monolith over thin CLI wrapper |
| ADR-002 | Modular monolith over microservices |
| ADR-003 | Framework adapter Protocol design (user-facing concepts, not framework internals) |
| ADR-004 | PostgreSQL as primary storage with JSONB for semi-structured data |
| ADR-005 | SSE for agent execution streaming (over WebSocket) |
| ADR-006 | Immutable agent versioning (every update = new version) |
| ADR-007 | User-provided LLM API keys (no platform-managed keys in v0.1) |
| ADR-008 | External auth via OneAI-Auth — HARD DEPENDENCY, shared JWT secret |
| ADR-009 | MCP server management as first-class module (register, test, assign, discover tools) |
| ADR-010 | Semantic versioning for framework adapters (adapter version + SDK compatibility range) |
| ADR-011 | Field-level encryption at rest for all user secrets (Fernet, ENCRYPTION_KEY env var) |
| ADR-012 | Full `create_deep_agent()` parameter mapping — AgentConfig covers all 17 params |
| ADR-013 | Human-in-the-loop via `interrupt_on` + SSE interrupt/resume pattern |
| ADR-014 | LangGraph checkpointing (AsyncSqliteSaver) for session continuity |
| ADR-015 | Private config hydration helper (`_build_agent_config`) in RunnerService — single source of truth for all 17 AgentConfig fields |

---

## Key Changes in This Revision

| Change | Why |
|--------|-----|
| Added MCP Server Manager module | Agents need external tools via MCP; API keys for MCP servers need secure management |
| OneAI-Auth → HARD DEPENDENCY | App MUST NOT start without Auth; startup health check enforced |
| JWT_SECRET_KEY recommendation | Shared `.env` or secrets manager as single source of truth; startup validation via test decode |
| Framework adapter versioning | Prevents silent SDK breakage; each adapter declares semver + compatibility range |
| Tool/MCP auth testing endpoints | Tools and MCP servers may have API keys that need validation before agent uses them |
| Removed "DeepAgents API changes" risk | Deferred to next version — adapter versioning handles this systematically |
| Python 3.13+ | Updated runtime requirement |
| **Added encryption at rest (ADR-011)** | All user secrets (LLM keys, MCP env vars, tool auth) Fernet-encrypted in DB; API responses mask secrets |
| **Full `create_deep_agent()` parameter mapping (ADR-012)** | AgentConfig now covers all 17 params — middleware toggles, backend selection, model resolution, recursion limit, debug mode |
| **HITL interrupt/resume (ADR-013)** | `interrupt_on` config pauses execution before dangerous tools; SSE interrupt event + resume endpoint |
| **Subagent types: sync + async** | SubAgent (in-process, inherits parent config) and AsyncSubAgent (remote Agent Protocol server) |
| **Checkpointing (ADR-014)** | AsyncSqliteSaver for persistent session state; enables HITL resume + conversation continuity |
| **Structured output** | `response_format` field for typed JSON agent responses |
| **Backend selection** | StateBackend (default, ephemeral) or FilesystemBackend (persistent, root_dir-scoped) |
| **Expanded adapter to 5 submodules** | adapter.py, middleware.py, backends.py, models.py, subagents.py — each handles one mapping concern |
| **Deferred: skills, memory, CompiledSubAgent, StoreBackend** | Explicitly out of scope for v0.1 to keep focus tight |

---

**Phase 2 LOCKED ✓ — Approved 2026-04-10**
**Phase 3 COMPLETE ✓ — All 38 core tasks + 6 post-Phase-3 fixes (T39–T44) implemented 2026-04-10**

---

## Phase 3 — Implementation Exit Criteria

All 38 tasks (T1–T38) across 9 stages have been implemented and verified.

### Stage Completion Summary

| Stage | Tasks | Description | Status |
|-------|-------|-------------|--------|
| Stage 0 | T1–T3 | Project scaffold, pyproject.toml, config | ✓ COMPLETE |
| Stage 1 | T4–T5 | Core utilities (constants, encryption, events), Docker | ✓ COMPLETE |
| Stage 2 | T6–T9 | ORM models (13 tables), Alembic migrations | ✓ COMPLETE |
| Stage 3 | T10–T14 | Auth (JWT + API key), security, auth client, startup lifecycle | ✓ COMPLETE |
| Stage 4 | T15–T19 | Adapter protocol, registry, DeepAgents adapter (5 submodules), checkpointer | ✓ COMPLETE |
| Stage 5 | T20–T24 | Framework endpoints, tool registry, MCP server manager | ✓ COMPLETE |
| Stage 6 | T25–T27 | Agent builder (CRUD + versioning + config encryption) | ✓ COMPLETE |
| Stage 7 | T28–T31 | Agent runner (sessions, SSE streaming, HITL resume) | ✓ COMPLETE |
| Stage 8 | T32–T38 | Evaluator, deployer, router wiring, health probes, logging, exception handlers | ✓ COMPLETE |

### Implementation Verification Checklist

```
[x] All 13 ORM models registered in Base.metadata
[x] All imports verified clean (no circular imports)
[x] Encryption round-trip verified (encrypt → decrypt, dict values)
[x] JWT encode/decode round-trip verified
[x] API key generation + hashing verified
[x] 9 routers aggregated under /api/v1 prefix
[x] 39 API routes wired and verified
[x] Exception handlers map all domain exceptions to HTTP status codes
[x] Structured logging configured (console + JSON modes)
[x] Health + readiness probes implemented
[x] Startup lifecycle validates ENCRYPTION_KEY, JWT_SECRET_KEY, Auth health
[x] DeepAgents adapter registered in AdapterRegistry on app.state
[x] SSE streaming infrastructure in place (event_to_sse_data, sse_event_generator)
[x] Checkpointer factory (AsyncSqliteSaver per session) implemented
[x] Docker multi-stage build with uv configured
[x] Alembic async migrations configured with all model imports
```

### Key Metrics

| Metric | Value |
|--------|-------|
| Total tasks | 38 |
| Tasks completed | 38 |
| ORM tables | 13 |
| API routes | 39 |
| Adapter submodules | 5 |
| ADRs written | 15 |
| Domain exceptions | 9 |
| StrEnum constants | 12 |

### Test Suite

| Metric | Value |
|--------|-------|
| Unit tests | 148 |
| Integration tests | 41 |
| **Total tests** | **189** |

All 189 tests pass against in-memory SQLite with PostgreSQL compatibility shims.

---

## Post-Phase 3 — Bug Fixes & Quality (T39–T44)

Fixes discovered during test stabilization and code review after Phase 3 completion.
All fixes followed the lifecycle (Ideas → Plan → Todo → Gates) or Fast Track as appropriate.

| Task | Fix | ADR |
|------|-----|-----|
| T39 | SQLite test shims: JSONB→JSON remapping, `gen_random_uuid()` registration (`.hex` format) | — (Fast Track) |
| T40 | `AdapterRegistry` raises `AdapterError` on duplicate/unknown — test corrections | — (Fast Track) |
| T41 | `AgentService.soft_delete` return value contract — test correction | — (Fast Track) |
| T42 | Evaluator scoring: case-insensitive `exact_match`, `None` expected auto-pass — test corrections | — (Fast Track) |
| T43 | `AuthClient` test rewrite — mock `httpx.AsyncClient` constructor, not instance attribute | — (Fast Track) |
| T44 | **RunnerService config hydration gap** — `_build_agent_config()` helper passes all 17 AgentConfig fields; `_parse_subagents()` + `_parse_interrupt_on()` helpers; 18 new unit tests | ADR-015 |

### Documentation Deliverables

```
[x] CHANGELOG.md — v0.1.0 release notes (Keep a Changelog format)
[x] README.md — Full project overview (features, setup, architecture, API, dev commands)
[x] docs/quick_setup.md — Step-by-step guide (env config, Docker, migrations, Postman, troubleshooting)
[x] OneAI-Cortex.postman_collection.json — 36 requests, 9 folders, auto-saved variables
[x] task-breakdown.md — All 38 tasks marked DONE with completion summary
[x] 02-architecture.md — Project structure tree updated to match implementation
[x] 00-exit-criteria.md — Phase 3 completion checklist added (this file)
```
