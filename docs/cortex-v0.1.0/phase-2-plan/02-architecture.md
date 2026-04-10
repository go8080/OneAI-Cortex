# Phase 2 — Architecture Mapping

**Date:** 2026-04-10
**Project:** OneAI-Cortex

---

## High-Level Module Architecture

```
                    ┌──────────────────────┐
                    │   OneAI-Auth         │  ← EXTERNAL SERVICE (HARD DEPENDENCY)
                    │   (JWT issuer,       │     Cortex MUST NOT start if Auth
                    │    user management,  │     health check fails
                    │    OAuth providers)  │
                    └──────────┬───────────┘
                               │ JWT tokens (HS256, shared secret)
            ┌──────────────────┤
            │                  ▼
            │  ┌────────────────────────────┐
            │  │  User's MCP Servers       │  ← EXTERNAL (user-managed)
            │  │  (stdio, SSE, HTTP)       │     Cortex registers & tests
            │  └────────────┬──────────────┘     but does NOT host
            │               │ MCP protocol
            ▼               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           OneAI-Cortex                                  │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │  Auth Integration Layer (JWT validation + Auth API client)        │  │
│  │  get_current_user() — HARD DEP: startup fails if Auth unreachable │  │
│  └─────────────────────────────┬─────────────────────────────────────┘  │
│                                 │ user_id (UUID)                        │
│  ┌──────────┐ ┌──────────┐ ┌───┴─────┐ ┌───────────┐ ┌──────────┐     │
│  │  Agent   │ │  Agent   │ │  MCP    │ │   Agent   │ │  Agent   │     │
│  │ Builder  │ │  Runner  │ │ Server  │ │ Evaluator │ │ Deployer │     │
│  │          │ │          │ │ Manager │ │           │ │          │     │
│  └────┬─────┘ └────┬─────┘ └───┬─────┘ └─────┬─────┘ └────┬─────┘     │
│       │             │           │             │             │            │
│  ─────┼─────────────┼───────────┼─────────────┼─────────────┼────────   │
│       │             │           │             │             │            │
│  ┌────┴─────────────┴───────────┴─────────────┴─────────────┴────────┐  │
│  │              Framework Adapter Layer (versioned: semver)           │  │
│  │  ┌──────────────────────┐  ┌────────────┐  ┌──────────────────┐  │  │
│  │  │ DeepAgents Adapter   │  │ (CrewAI    │  │ (AutoGen adapter │  │  │
│  │  │ v1.0.0               │  │  future)   │  │  future)         │  │  │
│  │  │ compat: da>=0.5,<1.0 │  │            │  │                  │  │  │
│  │  └──────────────────────┘  └────────────┘  └──────────────────┘  │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                      Shared Infrastructure                        │  │
│  │  Database │ Config │ Tool Registry │ MCP Client │ API Key Mgmt   │  │
│  └───────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Layer Cake Mapping

### Module: Auth Integration (with OneAI-Auth)

> **OneAI-Auth** is an external service (separate repo at `OneAI-Auth/`).
> Cortex does NOT own user registration, login, or OAuth — it only validates
> tokens issued by OneAI-Auth and manages Cortex-local API keys.

**Integration Pattern:** Shared-secret JWT validation (HS256)
- Cortex and OneAI-Auth share the same `JWT_SECRET_KEY`
- Cortex decodes tokens locally — no HTTP call to Auth on every request
- User UUID from token `sub` claim is the identity reference for all Cortex resources
- For profile enrichment (display name, avatar), Cortex calls OneAI-Auth API on-demand

| Layer | Changes | Files |
|-------|---------|-------|
| API | API key CRUD (Cortex-local keys for programmatic agent access) | `api/api_keys.py`, `api/router.py` |
| Schemas | API key request/response | `schemas/api_key.py` |
| Service | API key management | `services/api_key.py` |
| Repository | API key persistence | `repositories/api_key.py` |
| Models | APIKey ORM (no User model — user_id is an opaque UUID from Auth) | `models/api_key.py` |
| Core | JWT decode + validate (no signing), API key hashing | `core/security.py` |
| Infrastructure | Auth API client (httpx) for profile lookups | `infrastructure/auth_client.py` |
| Config | JWT_SECRET_KEY, AUTH_SERVICE_URL | `config.py` |

**What lives WHERE:**

| Concern | Owner | Notes |
|---------|-------|-------|
| User registration | OneAI-Auth | `/api/v1/auth/register` |
| Login (email/password) | OneAI-Auth | `/api/v1/auth/login` |
| OAuth (Google, Microsoft, LinkedIn) | OneAI-Auth | `/api/v1/auth/google`, etc. |
| Token refresh + rotation | OneAI-Auth | `/api/v1/auth/refresh` |
| JWT token validation | **Cortex** (local) | Decode with shared secret, check `exp` and `type` |
| User profile data | OneAI-Auth | `/api/v1/users/profile` — Cortex fetches on-demand |
| Cortex API keys | **Cortex** (local) | For programmatic access to hosted agents |

### Module: Agent Builder

| Layer | Changes | Files |
|-------|---------|-------|
| API | Agent CRUD, version listing | `api/agents.py` |
| Schemas | Agent create/update/response | `schemas/agent.py` |
| Service | Agent config validation, versioning | `services/agent.py` |
| Repository | Agent & version persistence | `repositories/agent.py` |
| Models | Agent, AgentVersion ORM | `models/agent.py` |

### Module: Agent Runner

| Layer | Changes | Files |
|-------|---------|-------|
| API | Run agent (SSE), session mgmt, HITL resume | `api/runner.py` |
| Schemas | ChatRequest, ResumeRequest, SessionResponse | `schemas/runner.py` |
| Service | Agent execution, session mgmt | `services/runner.py` |
| Repository | Session & message persistence | `repositories/session.py` |
| Models | Session, Message ORM | `models/session.py` |
| Infrastructure | SSE streaming utilities | `infrastructure/sse.py` |

### Module: Agent Evaluator

| Layer | Changes | Files |
|-------|---------|-------|
| API | Test suite CRUD, run evaluation | `api/evaluator.py` |
| Schemas | TestSuite, TestCase, EvalResult | `schemas/evaluator.py` |
| Service | Evaluation orchestration, scoring | `services/evaluator.py` |
| Repository | Test suite & result persistence | `repositories/evaluator.py` |
| Models | TestSuite, TestCase, EvalRun, EvalResult | `models/evaluation.py` |

### Module: Agent Deployer

| Layer | Changes | Files |
|-------|---------|-------|
| API | Deploy, undeploy, download SDK | `api/deployer.py` |
| Schemas | DeployRequest, DeploymentResponse | `schemas/deployer.py` |
| Service | Deployment mgmt, SDK generation | `services/deployer.py` |
| Repository | Deployment records | `repositories/deployment.py` |
| Models | Deployment ORM | `models/deployment.py` |

### Module: MCP Server Manager

| Layer | Changes | Files |
|-------|---------|-------|
| API | MCP server CRUD, test connectivity, assign to agent | `api/mcp_servers.py` |
| Schemas | MCPServerCreate, MCPServerResponse, MCPTestResult | `schemas/mcp_server.py` |
| Service | MCP registration, connectivity testing, tool discovery | `services/mcp_server.py` |
| Repository | MCP server & assignment persistence | `repositories/mcp_server.py` |
| Models | McpServer, AgentMcpServer (junction) | `models/mcp_server.py` |
| Infrastructure | MCP client (stdio/SSE/HTTP transport) | `infrastructure/mcp_client.py` |

### Module: Framework Adapter (Versioned)

> Each adapter carries a **semantic version** and declares the framework SDK version range
> it is compatible with. This prevents silent breakage when framework SDKs update.
> The adapter is responsible for mapping `AgentConfig` to `create_deep_agent()` parameters,
> including middleware stack assembly, backend instantiation, model resolution,
> subagent wiring, interrupt_on config, and checkpointer setup.

| Layer | Changes | New Files | Modified Files |
|-------|---------|-----------|----------------|
| Core | Adapter protocol with version metadata | `core/adapter_protocol.py` | — |
| Adapters | DeepAgents adapter v1.0.0 (maps AgentConfig → 17 `create_deep_agent()` params) | `adapters/deepagents_adapter.py` | — |
| Adapters | Versioned registry/factory | `adapters/__init__.py`, `adapters/registry.py` | — |
| Infrastructure | Checkpointer factory (AsyncSqliteSaver per session) | `infrastructure/checkpointer.py` | — |

### Module: Tool Registry

| Layer | Changes | New Files | Modified Files |
|-------|---------|-----------|----------------|
| API | List/register tools | `endpoints/tools.py` | `router.py` |
| Schemas | ToolSpec, ToolResponse | `schemas/tools.py` | — |
| Service | Tool management | `services/tool_service.py` | — |
| Repository | Tool persistence | `repositories/tool_repository.py` | — |
| Models | Tool ORM | `models/tool.py` | — |

---

## Full Project Structure

```
oneai-cortex/
├── app/
│   ├── __init__.py                    # Version: "0.1.0"
│   ├── main.py                        # FastAPI app factory — NOTHING else
│   ├── config.py                      # Settings via pydantic-settings
│   ├── dependencies.py                # get_db, get_current_user, get_adapter, etc.
│   │
│   ├── api/                           # Endpoints — flat structure, /api/v1/ prefix via router
│   │   ├── __init__.py
│   │   ├── router.py                  # Aggregates all v1 routers with /api/v1 prefix
│   │   ├── exception_handlers.py      # Maps domain exceptions → HTTP status codes
│   │   ├── health.py                  # Health + readiness probes
│   │   ├── api_keys.py                # Cortex API key CRUD (programmatic access)
│   │   ├── agents.py                  # Agent CRUD + versions
│   │   ├── runner.py                  # Execute agent, sessions, HITL resume
│   │   ├── evaluator.py               # Test suites, run evals
│   │   ├── deployer.py                # Deploy, undeploy, SDK download
│   │   ├── frameworks.py              # Framework adapter listing
│   │   ├── mcp_servers.py             # MCP server CRUD, test, assign to agents
│   │   └── tools.py                   # Tool registry
│   │
│   ├── schemas/                       # Pydantic request/response models
│   │   ├── __init__.py
│   │   ├── api_key.py
│   │   ├── agent.py
│   │   ├── runner.py
│   │   ├── evaluator.py
│   │   ├── deployer.py
│   │   ├── framework.py
│   │   ├── mcp_server.py
│   │   └── tool.py
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── api_key.py                 # Cortex-local API key management
│   │   ├── agent.py
│   │   ├── runner.py
│   │   ├── evaluator.py
│   │   ├── deployer.py
│   │   ├── mcp_server.py              # MCP server registration, testing, assignment
│   │   └── tool.py
│   │
│   ├── repositories/
│   │   ├── __init__.py
│   │   ├── base.py                    # Generic CRUD base
│   │   ├── api_key.py                 # Cortex API keys
│   │   ├── agent.py
│   │   ├── session.py
│   │   ├── evaluator.py
│   │   ├── deployment.py
│   │   ├── mcp_server.py              # MCP server configs + agent assignments
│   │   └── tool.py
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── base.py                    # Declarative base, TimestampMixin, SoftDeleteMixin
│   │   ├── api_key.py                 # APIKey (no User model — user_id is UUID from Auth)
│   │   ├── agent.py                   # Agent, AgentVersion
│   │   ├── session.py                 # Session, Message
│   │   ├── evaluation.py             # TestSuite, TestCase, EvalRun, EvalResult
│   │   ├── deployment.py             # Deployment
│   │   ├── mcp_server.py             # MCPServer, AgentMCPServer (junction)
│   │   └── tool.py                    # Tool
│   │
│   ├── adapters/                      # Framework adapter layer (versioned)
│   │   ├── __init__.py
│   │   ├── protocol.py               # FrameworkAdapter Protocol definition
│   │   ├── types.py                  # Shared types (AgentConfig, AgentRuntime, AgentEvent, etc.)
│   │   ├── registry.py               # Adapter registry — lookup by framework name
│   │   └── deepagents/               # DeepAgents adapter v1.0.0
│   │       ├── __init__.py
│   │       ├── adapter.py            # FrameworkAdapter implementation
│   │       ├── middleware.py          # MiddlewareConfig → middleware stack assembly
│   │       ├── backends.py           # BackendConfig → StateBackend/FilesystemBackend
│   │       ├── models.py             # Model resolution (provider:model → BaseChatModel)
│   │       └── subagents.py          # SubAgentConfig → SubAgent/AsyncSubAgent dicts
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── exceptions.py             # Domain exceptions (AppError hierarchy)
│   │   ├── events.py                 # Domain events (AgentEvent dataclass)
│   │   ├── security.py               # JWT validation (decode only), API key hashing, AuthenticatedUser
│   │   ├── encryption.py             # Fernet encrypt/decrypt for secrets at rest
│   │   └── constants.py              # 12 StrEnums: AgentStatus, FrameworkType, MCPTransport, etc.
│   │
│   └── infrastructure/
│       ├── __init__.py
│       ├── database.py               # Async engine + session factory
│       ├── auth_client.py            # httpx client to OneAI-Auth API (profile lookups)
│       ├── mcp_client.py             # MCP protocol client (stdio/SSE/HTTP transports)
│       ├── sse.py                    # SSE event serialization (AgentEvent → EventSource)
│       ├── checkpointer.py           # LangGraph checkpointer factory (AsyncSqliteSaver)
│       └── logging.py                # structlog configuration (JSON/console output)
│
├── tests/
│   ├── conftest.py
│   ├── unit/
│   │   ├── services/
│   │   ├── repositories/
│   │   └── adapters/
│   ├── integration/
│   │   └── api/
│   └── factories.py
│
├── alembic/
│   ├── env.py                     # Async migration runner, imports all models
│   └── versions/
│
├── Dockerfile                     # Multi-stage build with uv
├── docker-compose.yml             # App + Postgres + Redis
├── docker-compose.dev.yml         # Dev override (infra only, app runs locally)
├── .dockerignore
│
├── docs/
│   ├── quick_setup.md             # Step-by-step setup guide with troubleshooting
│   ├── cortex-v0.1.0/
│   │   ├── phase-1-ideas/
│   │   ├── phase-2-plan/
│   │   ├── phase-3-todo/
│   │   └── ADR/
│   └── ARCHITECTURE.md
│
├── OneAI-Cortex.postman_collection.json  # 36 requests, 9 folders, auto-saved variables
├── CHANGELOG.md                   # Release notes (Keep a Changelog format)
├── pyproject.toml                 # Single source of truth for deps + tools (uv-managed)
├── uv.lock                        # Deterministic lockfile (committed to git)
├── .python-version                # Python version pin for uv
├── .env.example
├── .pre-commit-config.yaml
└── README.md
```
