# Quick Setup Guide

Get OneAI-Cortex running locally in under 10 minutes.

---

## Prerequisites

| Requirement | Version | Check |
|-------------|---------|-------|
| Python | 3.13+ | `python --version` |
| uv | latest | `uv --version` |
| Docker & Docker Compose | latest | `docker compose version` |
| Git | any | `git --version` |

**External service:**
- [OneAI-Auth](https://github.com/anthropics/OneAI-Auth) must be running on port 8001 (hard dependency)

---

## Step 1 — Clone & Install

```bash
git clone https://github.com/anthropics/OneAI-Cortex.git
cd OneAI-Cortex

# Install all dependencies (including dev tools)
uv sync --group dev
```

This creates a `.venv/` directory with all packages pinned via `uv.lock`.

---

## Step 2 — Configure Environment

```bash
cp .env.example .env
```

Edit `.env` and fill in the **required** values:

```env
# REQUIRED — Must match the same key in OneAI-Auth's .env
JWT_SECRET_KEY=change-me-to-a-long-random-string

# REQUIRED — Generate with:
#   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# WARNING: Back this up. Losing this key makes all encrypted secrets unrecoverable.
ENCRYPTION_KEY=your-generated-fernet-key

# Database (defaults work with docker-compose)
DATABASE_URL=postgresql+asyncpg://cortex:cortex@localhost:5432/cortex

# OneAI-Auth URL (must be reachable at startup)
AUTH_SERVICE_URL=http://localhost:8001
```

### All Configuration Options

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `JWT_SECRET_KEY` | — | Yes | Shared secret with OneAI-Auth (HS256) |
| `JWT_ALGORITHM` | `HS256` | No | JWT signing algorithm |
| `ENCRYPTION_KEY` | — | Yes | Fernet key for encrypting secrets at rest |
| `DATABASE_URL` | `postgresql+asyncpg://cortex:cortex@localhost:5432/cortex` | No | Async PostgreSQL connection string |
| `DB_POOL_SIZE` | `10` | No | SQLAlchemy connection pool size |
| `DB_MAX_OVERFLOW` | `20` | No | Max connections above pool size |
| `DB_POOL_TIMEOUT` | `30` | No | Seconds to wait for a connection |
| `DB_POOL_RECYCLE` | `1800` | No | Recycle connections after N seconds |
| `REDIS_URL` | `redis://localhost:6379/0` | No | Redis connection string |
| `AUTH_SERVICE_URL` | `http://localhost:8001` | No | OneAI-Auth base URL |
| `AGENT_EXECUTION_TIMEOUT_SECONDS` | `120` | No | Max agent execution time |
| `CHECKPOINT_DIR` | `data/checkpoints` | No | Directory for session checkpoints |
| `CHECKPOINT_RETENTION_DAYS` | `7` | No | Auto-cleanup checkpoints older than N days |
| `OTLP_ENDPOINT` | `http://localhost:4317` | No | OpenTelemetry collector endpoint |
| `ENVIRONMENT` | `development` | No | Environment name (development/staging/production) |
| `LOG_LEVEL` | `INFO` | No | Logging level (DEBUG/INFO/WARNING/ERROR) |

---

## Step 3 — Start Infrastructure

### Option A: Local development (recommended)

Start only PostgreSQL and Redis via Docker — run the app locally for hot reload:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d
```

Verify services are running:

```bash
docker compose ps
# Should show: postgres (healthy), redis (healthy)
```

### Option B: Full Docker stack

Start everything including the Cortex app:

```bash
docker compose up -d
```

If using Option B, skip Steps 4 and 5 — the app container handles migrations and startup.

---

## Step 4 — Run Database Migrations

```bash
uv run alembic upgrade head
```

This creates all 13 tables:

| Table | Description |
|-------|-------------|
| `api_keys` | Cortex-issued API keys (SHA-256 hashed) |
| `agents` | Agent definitions with soft delete |
| `agent_versions` | Immutable agent config snapshots |
| `sessions` | Chat sessions per agent |
| `messages` | Message history per session |
| `test_suites` | Evaluation test suites |
| `test_cases` | Individual test cases |
| `eval_runs` | Evaluation execution records |
| `eval_results` | Per-case evaluation results |
| `deployments` | Agent deployment records |
| `mcp_servers` | Registered MCP tool servers |
| `agent_mcp_servers` | Agent-to-MCP-server assignments |
| `tools` | Tool registry |

---

## Step 5 — Start the Server

```bash
uv run uvicorn app.main:app --reload --port 8000
```

You should see:

```
startup.encryption_key_validated
startup.jwt_secret_validated
startup.auth_service_healthy
startup.database_initialized
startup.adapters_registered    adapters=['deepagents']
startup.complete               version=0.1.0
```

### Verify it works

```bash
# Liveness check
curl http://localhost:8000/api/v1/health
# → {"status": "ok", "version": "0.1.0"}

# Readiness check (all dependencies)
curl http://localhost:8000/api/v1/health/ready
# → {"ready": true, "db": "ok", "redis": "ok", "auth": "ok"}
```

**API Documentation:** [http://localhost:8000/api/docs](http://localhost:8000/api/docs) (Swagger UI)

---

## Step 6 — Import Postman Collection

A pre-built Postman collection is included at the project root:

```
OneAI-Cortex.postman_collection.json
```

### Import steps:

1. Open Postman
2. Click **Import** (top-left)
3. Drag the `.json` file or browse to it
4. The collection appears as **"OneAI-Cortex API v0.1.0"**

### Configure variables:

In Postman, go to the collection's **Variables** tab and set:

| Variable | Value | Notes |
|----------|-------|-------|
| `base_url` | `http://localhost:8000` | Already set by default |
| `jwt_token` | *(your JWT from OneAI-Auth)* | Get by logging in to OneAI-Auth |
| `api_key` | *(auto-filled after "Create API Key")* | Or paste an existing key |

### Recommended test flow:

Run these requests in order — IDs auto-save between requests:

```
1. Health → Liveness Check
2. API Keys → Create API Key
3. Agents → Create Agent
4. Runner → Create Session
5. Runner → Chat (SSE Stream)
6. Evaluator → Create Test Suite
7. Evaluator → Create Test Case
8. Evaluator → Run Evaluation
9. MCP Servers → Create MCP Server (stdio)
10. MCP Servers → Test MCP Server
```

---

## Running Tests

The test suite contains **171 tests** (130 unit + 41 integration) that run against in-memory SQLite:

```bash
# Run all tests
uv run pytest

# Run with verbose output
uv run pytest -v

# Run only unit tests
uv run pytest tests/unit/

# Run only integration tests
uv run pytest tests/integration/

# Run a specific test file
uv run pytest tests/unit/services/test_agent_service.py

# Stop on first failure
uv run pytest -x
```

Tests use SQLite with compatibility shims for PostgreSQL features (JSONB, `gen_random_uuid()`). No external services required.

---

## Development Commands

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=app --cov-report=term-missing

# Lint
uv run ruff check .

# Format
uv run ruff format .

# Type check
uv run mypy app/

# Create a new migration
uv run alembic revision --autogenerate -m "description of change"

# Apply migrations
uv run alembic upgrade head

# Rollback one migration
uv run alembic downgrade -1
```

---

## Troubleshooting

### `RuntimeError: ENCRYPTION_KEY is required but not set`

Generate a Fernet key and add it to `.env`:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### `RuntimeError: JWT_SECRET_KEY is required but not set`

Add `JWT_SECRET_KEY` to `.env`. Must match OneAI-Auth's key exactly.

### `startup.auth_service_unreachable`

OneAI-Auth is not running or not reachable at `AUTH_SERVICE_URL`. The app will still start (warning only), but all authenticated endpoints will fail.

```bash
# Check if Auth is running
curl http://localhost:8001/api/v1/health
```

### Database connection refused

Ensure PostgreSQL is running:

```bash
docker compose ps
# If postgres is not healthy:
docker compose up -d postgres
```

### `ModuleNotFoundError` on startup

Dependencies not installed. Run:

```bash
uv sync
```

### Port 8000 already in use

```bash
# Find the process
lsof -i :8000        # macOS/Linux
netstat -ano | findstr :8000   # Windows

# Use a different port
uv run uvicorn app.main:app --reload --port 8080
```

### `UndefinedTableError: relation "agents" does not exist`

Database migrations haven't been applied. Run:

```bash
uv run alembic upgrade head
```

This creates all 13 tables. If using Docker, the container runs migrations on startup — rebuild with `docker compose up -d --build`.

### `AdapterError: Invalid model spec ... expected 'provider:model' format`

The agent config stores `model` as a dict (`{"provider": "openai", "model_id": "gpt-4o", ...}`) which is the correct API format — the runner normalizes it to `"openai:gpt-4o"` internally. If you see this error, ensure the model config has both `provider` and `model_id` keys. You can also pass the string format directly: `"model": "openai:gpt-4o"`.

### Checkpoint directory errors

Ensure the checkpoint directory exists:

```bash
mkdir -p data/checkpoints
```

---

## What's Next?

Once the server is running:

1. **Explore the API** — Open [http://localhost:8000/api/docs](http://localhost:8000/api/docs) for interactive Swagger docs
2. **Create your first agent** — Use the Postman collection or Swagger UI
3. **Connect MCP servers** — Register external tool servers for your agents
4. **Run evaluations** — Build test suites to measure agent quality
5. **Read the architecture** — `docs/cortex-v0.1.0/phase-2-plan/02-architecture.md`
6. **Check ADRs** — `docs/cortex-v0.1.0/ADR/` for design decision context
