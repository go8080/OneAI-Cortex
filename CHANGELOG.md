# Changelog

All notable changes to OneAI-Cortex will be documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased] — v0.4.0

### Added

#### Google Connected Services — OAuth Token Management
- `POST /api/v1/connected-services/google/connect` — Exchange Google authorization code for tokens, store encrypted refresh token
- `GET /api/v1/connected-services` — List all connected services for the authenticated user
- `GET /api/v1/connected-services/google/scopes` — Get Google connection status and granted scopes
- `GET /api/v1/connected-services/google/token` — Get fresh Google access token from stored refresh token (for agent runtime)
- `DELETE /api/v1/connected-services/google` — Disconnect Google, permanently delete stored tokens

#### Provider-Agnostic Data Model
- `connected_services` table with `(user_id, provider)` unique constraint — supports Google, Slack, GitHub without schema changes
- `ServiceProvider` and `ConnectionStatus` StrEnum constants
- Fernet-encrypted `refresh_token` storage (reuses existing `SecretEncryption` infrastructure, ADR-011)
- Hard delete on disconnect — tokens not retained after user disconnects

#### Infrastructure
- `GoogleOAuthClient` — async HTTP client for Google's token exchange (`oauth2.googleapis.com/token`) and userinfo endpoints
- Graceful feature toggle: `GOOGLE_CLIENT_ID` + `GOOGLE_CLIENT_SECRET` env vars; feature disabled if absent (returns 502)
- `ServiceError` exception type for external service failures (mapped to HTTP 502)

#### Google Agent Tools — Gmail, Calendar, Drive
- `ToolAuthType` enum: `api_key` (default), `google_oauth`, `none` — declares how each tool authenticates
- `auth_type` column on `tools` table — tools declare their auth mechanism in the catalog
- Gmail tools (`gmail_search`, `gmail_send_message`, `gmail_get_message`, `gmail_create_draft`) — use LangChain community Gmail tools with OAuth credentials
- Calendar tools (`google_calendar_list_events`, `google_calendar_create_event`) — custom BaseTool implementations calling Google Calendar API
- Drive tools (`google_drive_search`, `google_drive_read`) — custom BaseTool implementations calling Google Drive API (supports Docs, Sheets, plain text)
- `google_tools.py` — Google OAuth tool builders that create API credentials from access tokens
- Runtime bridge: `RunnerService` detects `google_oauth` tools → fetches token from Connected Services → passes to adapter → tools receive proper credentials (no env var sniffing)

#### Database Changes
- Alembic migration `c3d4e5f6g7h8`: new `connected_services` table with unique constraint + user_id index
- Alembic migration `d4e5f6g7h8i9`: `auth_type` column on `tools` table + backfill Gmail tools as `google_oauth`

#### New Dependencies
- `google-auth` — Google OAuth credential objects
- `google-api-python-client` — Google API client (Gmail, Calendar, Drive)

### Architecture Decisions
- ADR-018: Cortex-owned connected services over Auth-delegated (zero cross-service latency, natural domain boundary)
- ADR-019: Provider-agnostic connected services data model (single table with provider discriminator)

#### Test Suite (+31 tests)
- Unit tests: ConnectedServiceService (connect, reconnect, scopes, token refresh, revocation, disconnect, validation)
- Unit tests: GoogleOAuthClient (code exchange, token refresh, userinfo, error handling)
- Integration tests: all 5 endpoints (connect, list, scopes, token, disconnect) with happy + error paths

---

## [Unreleased] — v0.3.0

### Documented
- API key lifecycle verified end-to-end for frontend integration (encryption → storage → decryption → env injection → cleanup)
- Error message patterns cataloged for frontend regex matching (`api_key`, `authentication`, `unauthorized`)
- Key overwrite semantics documented: `PUT /agents/{id}` replaces entire `user_api_keys` dict (not merge)
- Fernet token format documented for frontend reference (opaque `gAAAAAB` prefix strings)

---

## [Unreleased] — v0.2.0

### Added

#### Categorized Pre-Built Tool Catalog
- 20 tool categories: search, research, browser, communication, devtools, files, database, data_analysis, speech_audio, image_vision, documents, moderation, weather_location, finance, travel, media, science, automation, blockchain, utility
- `ToolCategory` and `ToolTestStatus` StrEnum constants
- 61 curated LangChain tools seeded at startup via `ToolSeederService` (idempotent — safe to re-run)
- Seed data mapping with `langchain_class`, `required_keys`, and `input_schema` per tool
- `GET /api/v1/tools/categories` — Browse categories with tool counts
- `GET /api/v1/tools?category=search` — Filter tools by category
- Category + tool_type partial indexes for fast browsing queries

#### Tool Playground
- `POST /api/v1/tools/{id}/test` — Execute any built-in tool with user-provided API keys and input
- Direct execution model: provide keys + input → see actual output → decide whether to use
- Dynamic LangChain tool instantiation via `importlib` with `ainvoke()` (async-safe for all tools)
- Test results persisted: `test_status`, `test_detail` (JSONB), `last_tested_at`
- Returns HTTP 200 with `status="success"|"failed"` — endpoint worked, status indicates tool outcome

#### Database Changes
- Alembic migration `a1b2c3d4e5f6`: 7 new columns on `tools` table (category, langchain_class, required_keys, input_schema, test_status, last_tested_at, test_detail)
- 2 partial indexes: `ix_tools_category`, `ix_tools_builtin_category`

### Architecture Decisions
- ADR-016: Tool categorization via enum + model extension (over separate catalog tables)
- ADR-017: Tool playground direct execution model (over staged validation)

#### Test Suite (208 tests, +19)
- Unit tests: ToolSeederService (seed, idempotency, field validation), ToolService (category listing, display name formatting, playground execution success/failure, validation errors)
- Integration tests: category browsing, category filter, playground 404/422 error paths

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
