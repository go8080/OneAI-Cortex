# OneAI-Cortex

Open-source AI agent builder platform. Build, test, evaluate, and deploy agents powered by multiple AI frameworks — starting with [DeepAgents](https://github.com/langchain-ai/deep-agents).

## Features

- **Agent Builder** — Create and version AI agents with full configuration (model, middleware, subagents, tools)
- **Agent Runner** — Execute agents via SSE streaming with session persistence and human-in-the-loop (HITL) support
- **Agent Evaluator** — Test suites with automated scoring (exact match, contains, LLM judge)
- **Agent Deployer** — Deploy agents with endpoint management
- **MCP Server Manager** — Register, test, and assign MCP tool servers to agents (stdio/SSE/HTTP)
- **Tool Registry** — Manage tools with schema definitions and encrypted auth
- **Framework Adapters** — Pluggable adapter system with semantic versioning; DeepAgents v1.0.0 ships first
- **Security** — JWT auth (via OneAI-Auth), API keys, Fernet encryption at rest for all secrets

## Architecture

```
API Layer (FastAPI)  →  Service Layer  →  Repository Layer  →  Models (SQLAlchemy 2.0)
                                                                     ↓
                                                              Infrastructure
                                                        (DB, Auth Client, MCP, SSE)
```

Modular monolith with strict layer separation. See `docs/cortex-v0.1.0/phase-2-plan/02-architecture.md` for the full module diagram.

## Tech Stack

| Category | Technology |
|----------|-----------|
| Runtime | Python 3.13+ |
| Framework | FastAPI, Pydantic v2 |
| ORM | SQLAlchemy 2.0 (async), Alembic |
| Database | PostgreSQL 16, Redis 7 |
| AI Framework | DeepAgents, LangChain, LangGraph |
| Auth | JWT (HS256 shared secret with OneAI-Auth) |
| Encryption | Fernet (AES-128-CBC + HMAC-SHA256) |
| Streaming | SSE via sse-starlette |
| Logging | structlog (JSON + console) |
| Packages | uv |
| Containers | Docker (multi-stage builds) |

## Setup

See **[docs/quick_setup.md](docs/quick_setup.md)** for the full step-by-step guide (environment config, Docker, migrations, Postman import, troubleshooting).

## Prerequisites

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) package manager
- PostgreSQL 16
- Redis 7
- [OneAI-Auth](https://github.com/anthropics/OneAI-Auth) service running (hard dependency)

## Quick Start

### 1. Clone and install

```bash
git clone https://github.com/anthropics/OneAI-Cortex.git
cd OneAI-Cortex
uv sync
```

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env` with your values:

```env
JWT_SECRET_KEY=your-shared-secret        # Must match OneAI-Auth
ENCRYPTION_KEY=<generate-with-fernet>     # python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
DATABASE_URL=postgresql+asyncpg://cortex:cortex@localhost:5432/cortex
AUTH_SERVICE_URL=http://localhost:8001     # OneAI-Auth URL
```

### 3. Start infrastructure

```bash
# PostgreSQL + Redis only (app runs locally)
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d
```

### 4. Run migrations

```bash
uv run alembic upgrade head
```

### 5. Start the server

```bash
uv run uvicorn app.main:app --reload --port 8000
```

API docs at [http://localhost:8000/api/docs](http://localhost:8000/api/docs).

### Full Docker deployment

```bash
docker compose up -d   # Starts Cortex + PostgreSQL + Redis
```

## API Overview

All endpoints under `/api/v1`. Authenticated via `Authorization: Bearer <jwt>` or `Authorization: ApiKey <key>`.

| Module | Endpoints | Description |
|--------|----------|-------------|
| Health | `GET /health`, `GET /health/ready` | Liveness and readiness probes |
| API Keys | `POST/GET/DELETE /api-keys` | Manage Cortex API keys |
| Agents | `POST/GET/PUT/DELETE /agents` | Agent CRUD with immutable versioning |
| Runner | `POST /sessions`, `POST /sessions/{id}/chat`, `POST /sessions/{id}/resume` | Execute agents via SSE |
| Evaluator | `POST/GET /agents/{id}/test-suites`, run evals | Automated agent testing |
| Deployer | `POST/GET/DELETE /agents/{id}/deploy` | Agent deployment management |
| Frameworks | `GET /frameworks` | List registered framework adapters |
| Tools | `POST/GET /tools` | Tool registry |
| MCP Servers | `POST/GET/DELETE /mcp-servers`, `POST /mcp-servers/{id}/test` | MCP server management |

## Development

```bash
uv sync --group dev
uv run pytest                  # Run tests
uv run ruff check .            # Lint
uv run ruff format .           # Format
uv run mypy app/               # Type check
```

## Project Structure

```
oneai-cortex/
├── app/
│   ├── main.py                # FastAPI app factory
│   ├── config.py              # Settings (pydantic-settings)
│   ├── dependencies.py        # DI: get_db, get_current_user, get_adapter
│   ├── api/                   # Endpoints (flat, /api/v1 prefix)
│   ├── schemas/               # Pydantic request/response models
│   ├── services/              # Business logic
│   ├── repositories/          # Data access (SQLAlchemy)
│   ├── models/                # ORM models (13 tables)
│   ├── adapters/              # Framework adapters (DeepAgents v1.0.0)
│   ├── core/                  # Security, encryption, constants, events
│   └── infrastructure/        # DB, auth client, MCP client, SSE, logging
├── alembic/                   # Database migrations
├── tests/                     # Unit + integration tests
├── Dockerfile                 # Multi-stage build with uv
├── docker-compose.yml         # Full stack (app + postgres + redis)
├── docker-compose.dev.yml     # Dev mode (infra only)
└── pyproject.toml             # Dependencies (uv-managed)
```

## API Testing (Postman)

Import `OneAI-Cortex.postman_collection.json` from the project root into Postman. Includes 36 pre-configured requests across 9 folders with auto-saved variables. See [docs/quick_setup.md](docs/quick_setup.md#step-6--import-postman-collection) for details.

## Documentation

| Document | Description |
|----------|-------------|
| [docs/quick_setup.md](docs/quick_setup.md) | Step-by-step setup guide with troubleshooting |
| [CHANGELOG.md](CHANGELOG.md) | Release notes for v0.1.0 |
| `docs/cortex-v0.1.0/phase-1-ideas/` | Design exploration and decision matrices |
| `docs/cortex-v0.1.0/phase-2-plan/` | Architecture, interfaces, data flows, exit criteria |
| `docs/cortex-v0.1.0/phase-3-todo/` | Task breakdown (38 tasks across 9 stages) |
| `docs/cortex-v0.1.0/ADR/` | 14 Architecture Decision Records |
| `OneAI-Cortex.postman_collection.json` | Postman collection (36 requests, 9 folders) |

## License

MIT
