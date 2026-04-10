# Phase 2 — Data Model

**Date:** 2026-04-10
**Project:** OneAI-Cortex

---

## Entity Relationship Overview

> **NOTE:** There is NO `users` table in Cortex. User identity is an opaque UUID
> from OneAI-Auth (JWT `sub` claim). All `user_id` columns are plain UUIDs with
> no foreign key — the source of truth for user data lives in OneAI-Auth's database.

```
 ┌──────────────────┐
 │  OneAI-Auth DB   │  ← EXTERNAL (separate database)
 │  users table     │     Cortex references user_id but does NOT join to it
 └────────┬─────────┘
          │ user_id (UUID, no FK)
          ▼
┌──────────────┐     ┌─────────────┐
│   agents     │────<│agent_versions│
└──────────────┘     └─────────────┘
      │
      ├──────────<┌──────────────┐
      │           │  sessions    │────<┌──────────┐
      │           └──────────────┘     │ messages │
      │                                └──────────┘
      ├──────────<┌──────────────┐
      │           │ test_suites  │────<┌────────────┐
      │           └──────────────┘     │ test_cases │
      │                  │             └────────────┘
      │                  └────────<┌──────────────┐
      │                            │  eval_runs   │────<┌──────────────┐
      │                            └──────────────┘     │ eval_results │
      │                                                 └──────────────┘
      ├──────────<┌──────────────┐
      │           │ deployments  │
      │           └──────────────┘
      │
      └──────────<┌───────────────────┐     ┌──────────────┐
                  │ agent_mcp_servers │>────│ mcp_servers  │
                  │ (junction)        │     └──────────────┘
                  └───────────────────┘       (user_id indexed)

┌──────────────┐  (user_id indexed, no FK)
│  api_keys    │
└──────────────┘

┌──────────────┐  (standalone, with auth_config for API keys)
│  tools       │
└──────────────┘
```

---

## Table Definitions

### api_keys (Cortex-local — for programmatic access)

> These are NOT the same as OneAI-Auth's JWT tokens. Cortex API keys let
> machines call hosted agent endpoints and the Cortex API without a JWT.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | UUID | PK | |
| user_id | UUID | NOT NULL, INDEXED | from OneAI-Auth JWT `sub` — no FK |
| name | VARCHAR(100) | NOT NULL | human-readable label |
| key_hash | VARCHAR(255) | UNIQUE, NOT NULL | SHA-256 hashed key |
| key_prefix | VARCHAR(8) | NOT NULL | first 8 chars for display/identification |
| is_active | BOOLEAN | DEFAULT true | revokable |
| last_used_at | TIMESTAMPTZ | NULLABLE | |
| created_at | TIMESTAMPTZ | DEFAULT now() | |

### agents

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | UUID | PK | |
| user_id | UUID | NOT NULL, INDEXED | from OneAI-Auth — no FK |
| name | VARCHAR(255) | NOT NULL | |
| description | TEXT | NULLABLE | |
| framework | VARCHAR(50) | NOT NULL, DEFAULT 'deepagents' | framework adapter key |
| status | VARCHAR(20) | NOT NULL, DEFAULT 'draft' | draft / active / archived |
| current_version | INTEGER | NOT NULL, DEFAULT 1 | points to latest version |
| is_deleted | BOOLEAN | DEFAULT false | soft delete |
| created_at | TIMESTAMPTZ | DEFAULT now() | |
| updated_at | TIMESTAMPTZ | DEFAULT now() | |

**Index:** `(user_id, is_deleted)` — list agents by user

### agent_versions

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | UUID | PK | |
| agent_id | UUID | FK → agents.id, NOT NULL | |
| version | INTEGER | NOT NULL | auto-incrementing per agent |
| config | JSONB | NOT NULL | full agent config snapshot |
| change_summary | TEXT | NULLABLE | what changed from previous |
| created_at | TIMESTAMPTZ | DEFAULT now() | immutable after creation |

**Unique constraint:** `(agent_id, version)`
**Index:** `(agent_id, version DESC)` — latest version lookup

**Config JSONB structure (full — maps to all `create_deep_agent()` parameters):**
```json
{
  "model": "anthropic:claude-sonnet-4-6",
  "system_prompt": "You are a helpful assistant...",
  "tools": ["web_search", "calculator"],
  "mcp_servers": ["uuid-of-mcp-server-1", "uuid-of-mcp-server-2"],

  "subagents": [
    {
      "type": "sync",
      "name": "researcher",
      "description": "Conducts web research",
      "model": "anthropic:claude-sonnet-4-6",
      "system_prompt": "...",
      "tools": ["web_search"],
      "interrupt_on": null
    },
    {
      "type": "async",
      "name": "code-reviewer",
      "description": "Reviews code on remote server",
      "graph_id": "code-review-agent",
      "url": "http://remote-server:8000",
      "headers": {"Authorization": "gAAAAA...encrypted..."}
    }
  ],

  "middleware": {
    "todo_list": true,
    "filesystem": true,
    "subagent": true,
    "summarization": true,
    "patch_tool_calls": true,
    "async_subagent": true,
    "prompt_caching": true,
    "human_in_the_loop": false
  },

  "response_format": null,

  "backend": {
    "type": "state",
    "root_dir": null,
    "max_file_size_mb": 10
  },

  "interrupt_on": {
    "edit_file": true,
    "execute": {"message": "Approve shell command?"}
  },

  "checkpointing_enabled": true,

  "temperature": 0.7,
  "max_tokens": 4096,
  "recursion_limit": 100,
  "debug": false,

  "user_api_keys": {
    "anthropic": "gAAAAA...encrypted...",
    "openai": "gAAAAA...encrypted..."
  },

  "framework_adapter_version": "1.0.0",
  "framework_specific": {}
}
```

> **SECURITY:** `user_api_keys` values and async subagent `headers` values are **Fernet-encrypted** before storage.
> Services decrypt on read for agent execution, then discard.
> API GET responses return masked keys only: `{"anthropic": "sk-ant-ab...****"}`

**Checkpointing storage:** LangGraph checkpoints are stored in SQLite files at `data/checkpoints/{session_id}.db`.
These are NOT in PostgreSQL — they use LangGraph's native `AsyncSqliteSaver` format for compatibility.
Session metadata (user_id, agent_id, created_at) remains in PostgreSQL `sessions` table.

### sessions

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | UUID | PK | |
| agent_id | UUID | FK → agents.id, NOT NULL | |
| user_id | UUID | NOT NULL, INDEXED | |
| agent_version | INTEGER | NOT NULL | version used in this session |
| title | VARCHAR(255) | NULLABLE | auto-generated or user-set |
| is_active | BOOLEAN | DEFAULT true | |
| created_at | TIMESTAMPTZ | DEFAULT now() | |
| updated_at | TIMESTAMPTZ | DEFAULT now() | |

**Index:** `(agent_id, user_id, is_active)`

### messages

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | UUID | PK | |
| session_id | UUID | FK → sessions.id, NOT NULL | |
| role | VARCHAR(20) | NOT NULL | 'user', 'assistant', 'tool', 'system' |
| content | TEXT | NOT NULL | |
| metadata | JSONB | DEFAULT '{}' | tool calls, token counts, etc. |
| created_at | TIMESTAMPTZ | DEFAULT now() | |

**Index:** `(session_id, created_at)` — chronological message retrieval

### test_suites

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | UUID | PK | |
| agent_id | UUID | FK → agents.id, NOT NULL | |
| name | VARCHAR(255) | NOT NULL | |
| description | TEXT | NULLABLE | |
| scoring_method | VARCHAR(30) | NOT NULL, DEFAULT 'contains' | exact_match, contains, llm_judge |
| created_at | TIMESTAMPTZ | DEFAULT now() | |
| updated_at | TIMESTAMPTZ | DEFAULT now() | |

### test_cases

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | UUID | PK | |
| test_suite_id | UUID | FK → test_suites.id, NOT NULL | |
| name | VARCHAR(255) | NOT NULL | |
| input_message | TEXT | NOT NULL | what to send to the agent |
| expected_output | TEXT | NULLABLE | for automated scoring |
| tags | JSONB | DEFAULT '[]' | categorization |
| created_at | TIMESTAMPTZ | DEFAULT now() | |

### eval_runs

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | UUID | PK | |
| test_suite_id | UUID | FK → test_suites.id, NOT NULL | |
| agent_id | UUID | FK → agents.id, NOT NULL | |
| agent_version | INTEGER | NOT NULL | which version was evaluated |
| status | VARCHAR(20) | NOT NULL, DEFAULT 'pending' | pending, running, completed, failed |
| metrics | JSONB | DEFAULT '{}' | aggregate: pass_rate, avg_latency, etc. |
| started_at | TIMESTAMPTZ | NULLABLE | |
| completed_at | TIMESTAMPTZ | NULLABLE | |
| created_at | TIMESTAMPTZ | DEFAULT now() | |

### eval_results

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | UUID | PK | |
| eval_run_id | UUID | FK → eval_runs.id, NOT NULL | |
| test_case_id | UUID | FK → test_cases.id, NOT NULL | |
| actual_output | TEXT | NOT NULL | what the agent returned |
| score | FLOAT | NOT NULL | 0.0 to 1.0 |
| passed | BOOLEAN | NOT NULL | score >= threshold |
| latency_ms | INTEGER | NOT NULL | execution time |
| token_count | INTEGER | NULLABLE | tokens consumed |
| metadata | JSONB | DEFAULT '{}' | detailed scoring breakdown |
| created_at | TIMESTAMPTZ | DEFAULT now() | |

### deployments

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | UUID | PK | also used as endpoint slug |
| agent_id | UUID | FK → agents.id, NOT NULL | |
| user_id | UUID | NOT NULL, INDEXED | |
| agent_version | INTEGER | NOT NULL | pinned version |
| type | VARCHAR(20) | NOT NULL | 'hosted' or 'sdk_download' |
| status | VARCHAR(20) | NOT NULL, DEFAULT 'active' | active, stopped, expired |
| endpoint_url | VARCHAR(500) | NULLABLE | for hosted type |
| download_count | INTEGER | DEFAULT 0 | for sdk_download type |
| created_at | TIMESTAMPTZ | DEFAULT now() | |
| stopped_at | TIMESTAMPTZ | NULLABLE | |

### tools

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | UUID | PK | |
| name | VARCHAR(100) | UNIQUE, NOT NULL | e.g., 'web_search' |
| description | TEXT | NOT NULL | |
| framework | VARCHAR(50) | NOT NULL | which adapter provides this |
| tool_type | VARCHAR(20) | NOT NULL, DEFAULT 'builtin' | builtin, custom |
| schema | JSONB | NOT NULL | input/output schema |
| is_active | BOOLEAN | DEFAULT true | |
| auth_config | JSONB | DEFAULT '{}' | **ENCRYPTED VALUES** — keys plaintext, values Fernet-encrypted (API keys, auth headers for tools) |
| created_at | TIMESTAMPTZ | DEFAULT now() | |

### mcp_servers

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | UUID | PK | |
| user_id | UUID | NOT NULL, INDEXED | owner (from OneAI-Auth) |
| name | VARCHAR(255) | NOT NULL | human-readable label |
| description | TEXT | NULLABLE | |
| transport | VARCHAR(20) | NOT NULL | 'stdio', 'sse', 'http' |
| url | VARCHAR(500) | NULLABLE | for sse/http transports |
| command | VARCHAR(500) | NULLABLE | for stdio transport (e.g., 'npx @modelcontextprotocol/server-github') |
| args | JSONB | DEFAULT '[]' | command arguments for stdio |
| env_vars | JSONB | DEFAULT '{}' | **ENCRYPTED VALUES** — keys plaintext, values Fernet-encrypted (API keys for GitHub, Slack, etc.) |
| auth_header | TEXT | NULLABLE | **ENCRYPTED** — Fernet-encrypted Bearer token for http transport |
| status | VARCHAR(20) | NOT NULL, DEFAULT 'untested' | untested, healthy, unhealthy |
| last_tested_at | TIMESTAMPTZ | NULLABLE | |
| tools_discovered | JSONB | DEFAULT '[]' | cached tool list from last test |
| created_at | TIMESTAMPTZ | DEFAULT now() | |
| updated_at | TIMESTAMPTZ | DEFAULT now() | |

**Index:** `(user_id, status)` — list servers by user filtered by health

### agent_mcp_servers (junction)

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| agent_id | UUID | FK → agents.id, NOT NULL | |
| mcp_server_id | UUID | FK → mcp_servers.id, NOT NULL | |
| created_at | TIMESTAMPTZ | DEFAULT now() | |

**Primary key:** `(agent_id, mcp_server_id)`

---

## Migration Strategy

- Alembic for all schema changes
- Every migration is forward-only (no downgrades in production)
- UUID primary keys via PostgreSQL `gen_random_uuid()`
- All timestamps use `TIMESTAMPTZ` (timezone-aware)
- JSONB for flexible/nested data (agent configs, metadata, eval metrics)
- Soft deletes on agents (preserve history); hard deletes on sessions (user privacy)

## Encryption at Rest

- **All user-provided secrets encrypted via Fernet** (AES-128-CBC + HMAC-SHA256) before DB storage
- `ENCRYPTION_KEY` env var — single `.env` file, generated via `Fernet.generate_key()`
- Services encrypt/decrypt; repositories handle opaque ciphertext
- API responses **never return raw secrets** — masked prefixes only (e.g., `"sk-ant-ab...****"`)
- Tampered ciphertext → `InvalidToken` exception → logged as security event
- Missing `ENCRYPTION_KEY` → app refuses to start

**Encrypted fields summary:**

| Table | Field | What's encrypted |
|-------|-------|------------------|
| `agent_versions` | `config.user_api_keys` (values) | LLM API keys (Anthropic, OpenAI, Google) |
| `mcp_servers` | `env_vars` (values) | MCP server API keys (GitHub, Slack, DB tokens) |
| `mcp_servers` | `auth_header` | Bearer tokens for HTTP MCP transport |
| `tools` | `auth_config` (values) | Tool API keys and auth credentials |
