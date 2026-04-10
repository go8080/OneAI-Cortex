# Changelog

All notable changes to OneAI-Cortex will be documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.1.0] - 2026-04-10

First implementation release. Full backend for the AI agent builder platform with
DeepAgents as the initial supported framework.

### Added

#### Core Infrastructure
- FastAPI application factory with async lifespan (startup/shutdown lifecycle)
- Pydantic-settings configuration (`app/config.py`) with environment variable support
- Structured logging via structlog (console + JSON output modes)
- Health endpoint (liveness) and readiness probe (database, Redis, auth checks)
- Domain exception hierarchy (`AppError` → 9 subclasses) with centralized HTTP mapping
- 12 `StrEnum` constants for all domain enumerations
- Fernet field-level encryption at rest for user secrets (`SecretEncryption`)
- Docker multi-stage build with `uv` package manager
- `docker-compose.yml` with PostgreSQL 16, Redis 7, and Cortex service
- `docker-compose.dev.yml` for local development (infra-only mode)
- Alembic async migration setup with all 13 model imports

#### Authentication & Security
- JWT token validation (HS256, shared secret with OneAI-Auth)
- Dual auth dependency: Bearer JWT + ApiKey header schemes
- API key CRUD (generate `ctx_`-prefixed keys, SHA-256 hashed storage)
- `get_current_user` FastAPI dependency with `AuthenticatedUser` context
- Auth client (`httpx`) for OneAI-Auth profile lookups and health checks
- Startup health check for OneAI-Auth (3 retries, 2s backoff)

#### ORM Models (13 tables)
- `ApiKey` — Cortex-local API keys with hashed storage
- `Agent`, `AgentVersion` — Immutable agent versioning with JSONB config
- `Session`, `Message` — Chat sessions with message history
- `TestSuite`, `TestCase`, `EvalRun`, `EvalResult` — Evaluation framework
- `Deployment` — Agent deployment records
- `McpServer`, `AgentMcpServer` — MCP server registry with agent junction table
- `Tool` — Tool registry with JSONB schema and encrypted auth config
- Base mixins: `TimestampMixin`, `SoftDeleteMixin`

#### Framework Adapter System
- `FrameworkAdapter` Protocol with version metadata and SDK compatibility range
- `AdapterRegistry` for framework lookup by name
- **DeepAgents adapter v1.0.0** — maps `AgentConfig` to all 17 `create_deep_agent()` parameters:
  - `models.py` — Model resolution via `init_chat_model()` (provider:model format)
  - `middleware.py` — Ordered middleware stack assembly (8 middleware types)
  - `backends.py` — StateBackend / FilesystemBackend selection
  - `subagents.py` — Sync (`SubAgent`) and async (`AsyncSubAgent`) subagent wiring
  - `adapter.py` — Full lifecycle: validate, create runtime, execute (SSE stream), resume HITL
- Adapter types: `AgentConfig`, `MiddlewareConfig`, `BackendConfig`, `InterruptConfig`, `ModelSpec`, `AgentRuntime`, `AgentEvent`, and 8 more

#### Agent Builder
- Agent CRUD with soft delete and ownership enforcement
- Immutable versioning (every config change creates a new `AgentVersion`)
- Config secret encryption (LLM API keys, async subagent auth headers)
- Paginated agent listing with total count
- Framework validation against registered adapters

#### Agent Runner
- Session management (create, list per agent)
- SSE streaming execution via `EventSourceResponse`
- Message persistence (user + assistant messages stored per session)
- HITL interrupt detection and resume endpoint
- Checkpointer factory (`AsyncSqliteSaver` per session at `data/checkpoints/`)
- Expired checkpoint cleanup utility

#### Agent Evaluator
- Test suite CRUD (per agent)
- Test case management with input/expected output pairs
- Evaluation orchestration: iterates cases, creates runtime, executes, scores
- Scoring methods: `exact_match`, `contains`, `llm_judge`
- Aggregated metrics: average score, pass rate, mean latency

#### Agent Deployer
- Deploy agent (creates deployment record with endpoint URL)
- Undeploy (sets status to stopped)
- Deployment listing per agent

#### MCP Server Manager
- MCP server CRUD with encrypted env vars and auth headers
- Connectivity testing (stdio and SSE/HTTP transports via `mcp` SDK)
- Status tracking (connected/disconnected/error) with tool discovery count
- Agent-to-MCP-server assignment junction table

#### Tool Registry
- Tool CRUD with JSONB schema definitions
- Encrypted auth config storage
- Framework-scoped tool listing

#### API Surface (39 routes under `/api/v1`)
- `GET /api/v1/health` — Liveness probe
- `GET /api/v1/health/ready` — Readiness probe
- `POST/GET/DELETE /api/v1/api-keys` — API key management
- `POST/GET/PUT/DELETE /api/v1/agents` — Agent CRUD
- `GET /api/v1/agents/{id}/versions` — Version listing
- `POST /api/v1/sessions`, `POST /api/v1/sessions/{id}/chat`, `POST /api/v1/sessions/{id}/resume` — Runner
- `POST/GET /api/v1/agents/{id}/test-suites` — Evaluator suites
- `POST/GET /api/v1/agents/{id}/test-suites/{id}/cases` — Test cases
- `POST /api/v1/agents/{id}/test-suites/{id}/run` — Run evaluation
- `GET /api/v1/agents/{id}/eval-runs` — Eval results
- `POST/GET/DELETE /api/v1/agents/{id}/deploy` — Deployer
- `GET /api/v1/frameworks` — Adapter listing
- `POST/GET /api/v1/tools` — Tool registry
- `POST/GET/DELETE /api/v1/mcp-servers` — MCP server management
- `POST /api/v1/mcp-servers/{id}/test` — MCP connectivity test

### Architecture Decisions (14 ADRs)
- ADR-001: Modular monolith over thin CLI wrapper
- ADR-002: Modular monolith over microservices
- ADR-003: Framework adapter Protocol (user-facing concepts, not framework internals)
- ADR-004: PostgreSQL + JSONB for semi-structured data
- ADR-005: SSE for agent execution streaming
- ADR-006: Immutable agent versioning
- ADR-007: User-provided LLM API keys (no platform keys in v0.1)
- ADR-008: External auth via OneAI-Auth (hard dependency, shared JWT)
- ADR-009: MCP server management as first-class module
- ADR-010: Semantic versioning for framework adapters
- ADR-011: Field-level Fernet encryption at rest for user secrets
- ADR-012: Full `create_deep_agent()` 17-parameter mapping
- ADR-013: HITL via `interrupt_on` + SSE interrupt/resume pattern
- ADR-014: LangGraph checkpointing (AsyncSqliteSaver) for session continuity
- ADR-015: `_build_agent_config()` helper for run/resume consistency

#### Test Suite (189 tests)
- **Unit tests (148)** — Core modules (security, encryption, constants, events), adapter layer (registry, types, DeepAgents adapter), services (agent, API key, deployer, evaluator, MCP server, tool), runner helpers (_normalize_model, _build_agent_config), SSE infrastructure, auth client
- **Integration tests (41)** — Full API endpoint tests via in-memory SQLite with JSONB→JSON remapping and `gen_random_uuid()` shim; agent CRUD + versioning, API keys, tools, MCP servers, frameworks, health, exception handler mapping
- Test infrastructure: async SQLite engine with PostgreSQL compatibility shims, mock adapter fixtures, FastAPI dependency overrides, `httpx.ASGITransport` async client

#### Developer Experience
- Quick setup guide (`docs/quick_setup.md`) — prerequisites through troubleshooting
- Postman collection (`OneAI-Cortex.postman_collection.json`) — 36 pre-configured requests across 9 folders with auto-saved variables and test scripts
- Comprehensive `.env.example` with all configuration options documented

### Fixed
- `ModuleNotFoundError: No module named 'deepagent'` — Corrected import paths to `deepagents` (plural) and rewrote middleware assembly to not duplicate framework internals
- `AdapterError: Invalid model spec` — Added `_normalize_model()` to handle dict and string model config formats
- OpenAI 400 Bad Request for agent names with spaces — Added `sanitize_agent_name()` regex to replace invalid characters
- **RunnerService config hydration gap** — `run_session()` and `resume_session()` now pass all 17 `AgentConfig` fields to the adapter via `_build_agent_config()` helper. Previously 6 fields were silently dropped (subagents, middleware, interrupt_on, backend, response_format, framework_specific) and `resume_session` only passed 2 of 17. (ADR-015)

### Tech Stack
- Python 3.13+ / FastAPI / SQLAlchemy 2.0 (async) / Pydantic v2
- PostgreSQL 16 / Redis 7 / Alembic (async)
- DeepAgents SDK / LangChain / LangGraph
- structlog / httpx / cryptography (Fernet) / sse-starlette
- uv (package management) / Docker (multi-stage builds)
