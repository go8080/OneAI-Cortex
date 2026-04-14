# Phase 2 — Data Model

**Date:** 2026-04-13
**Project:** OneAI-Cortex v0.3.0
**Feature:** Agent Configuration Pipeline — Frontend Integration Support

---

## No Schema Changes

This feature requires **zero database schema changes**. The existing data model fully supports the API key flow.

---

## Existing Schema (Relevant Tables)

### `agents` Table

```sql
CREATE TABLE agents (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL,
    name            VARCHAR(255) NOT NULL,
    description     TEXT,
    framework       VARCHAR(50) NOT NULL DEFAULT 'deepagents',
    status          VARCHAR(20) NOT NULL DEFAULT 'draft',
    current_version INTEGER NOT NULL DEFAULT 1,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at      TIMESTAMPTZ
);
```

### `agent_versions` Table

```sql
CREATE TABLE agent_versions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id        UUID NOT NULL REFERENCES agents(id),
    version         INTEGER NOT NULL,
    config          JSONB NOT NULL,           -- ← API keys stored here (encrypted)
    change_summary  TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(agent_id, version)
);
```

---

## `config` JSONB Structure (with `user_api_keys`)

```json
{
  "model": "anthropic:claude-sonnet-4-6",
  "system_prompt": "You are a helpful assistant.",
  "tools": [],
  "mcp_servers": [],
  "middleware": {},
  "temperature": 0.7,
  "max_tokens": 4096,
  "recursion_limit": 100,
  "checkpointing_enabled": true,
  "debug": false,
  "user_api_keys": {
    "ANTHROPIC_API_KEY": "gAAAAABm...Fernet-encrypted-token..."
  }
}
```

### Encrypted Key Format

The `user_api_keys` values are **Fernet tokens** produced by `cryptography.fernet.Fernet`:

- Format: `gAAAAAB` prefix + base64-encoded (timestamp + IV + ciphertext + HMAC)
- Typical length: ~120-200 characters depending on plaintext length
- Deterministic? **No** — same plaintext produces different tokens (timestamp + random IV)
- Frontend should treat these as **opaque strings** — presence indicates "key configured"

---

## ERM (No Changes)

```
┌──────────────┐         ┌──────────────────┐         ┌──────────────┐
│   agents     │         │  agent_versions   │         │   sessions   │
│              │ 1    N  │                   │ 1    N  │              │
│  id          ├────────→│  id               │←────────┤  agent_id    │
│  user_id     │         │  agent_id (FK)    │         │  agent_version│
│  name        │         │  version          │         │  user_id     │
│  framework   │         │  config (JSONB)───┼─────→ config.user_api_keys: encrypted
│  status      │         │  change_summary   │         │              │
│  current_ver │         │  created_at       │         │              │
└──────────────┘         └──────────────────┘         └──────────────┘
```
