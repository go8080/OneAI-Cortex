## ADR-011: Field-Level Encryption at Rest for User Secrets

**Date:** 2026-04-10
**Status:** Accepted
**Phase:** Plan

### Context

OneAI-Cortex stores multiple categories of user-provided secrets:

| Secret Type | Where Stored | Example |
|------------|-------------|---------|
| LLM API keys | Agent config JSONB (`agent_versions.config`) | `sk-ant-...`, `sk-proj-...` |
| MCP server env vars | `mcp_servers.env_vars` JSONB | `GITHUB_TOKEN=ghp_...`, `SLACK_BOT_TOKEN=xoxb-...` |
| MCP server auth headers | `mcp_servers.auth_header` | `Bearer eyJ...` |
| Tool auth configs | `tools.auth_config` JSONB | `{"api_key": "..."}` |
| Cortex API key hashes | `api_keys.key_hash` | Already hashed (SHA-256), not reversible — OK |

If the database is compromised (SQL injection, backup theft, insider threat), all user API keys for LLMs, GitHub, Slack, databases, etc. are exposed in plaintext. This is a critical security vulnerability.

### Decision

Implement **field-level encryption at rest** using Fernet (AES-128-CBC + HMAC-SHA256) from Python's `cryptography` library for all reversible secrets stored in the database.

#### Architecture

```
┌──────────────────────────────────────────────────────┐
│                    Encryption Layer                    │
│                                                        │
│  ENCRYPTION_KEY (env var)                              │
│       │                                                │
│       ▼                                                │
│  ┌──────────────────┐                                  │
│  │ core/encryption.py│                                 │
│  │                    │                                │
│  │  encrypt(plain)    │ ──→ Fernet token (base64)     │
│  │  decrypt(cipher)   │ ──→ plaintext                 │
│  │  encrypt_dict(d)   │ ──→ dict with values encrypted│
│  │  decrypt_dict(d)   │ ──→ dict with values decrypted│
│  └──────────────────┘                                  │
│                                                        │
│  Used by: services (encrypt before repo.create,        │
│           decrypt after repo.get)                      │
│  NOT used by: repositories (they see opaque strings)   │
└──────────────────────────────────────────────────────┘
```

#### What gets encrypted (and what doesn't)

| Field | Encrypted? | Why |
|-------|-----------|-----|
| `agent_versions.config` → `api_keys` nested field | YES | LLM API keys (Anthropic, OpenAI, Google) |
| `mcp_servers.env_vars` (all values) | YES | Contains API keys for GitHub, Slack, DBs, etc. |
| `mcp_servers.auth_header` | YES | Bearer tokens for HTTP MCP transport |
| `tools.auth_config` (all values) | YES | API keys for tools that need auth |
| `api_keys.key_hash` | NO — already one-way hashed | SHA-256 hash, not reversible, by design |
| `mcp_servers.url` | NO | Not a secret (server address) |
| `mcp_servers.command` | NO | Not a secret (executable path) |
| `agent_versions.config` → non-secret fields | NO | model name, system_prompt, temperature are not secrets |

#### Key Management

1. **`ENCRYPTION_KEY`** — Fernet key stored as environment variable in `.env`
2. **Generated once:** `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` 
3. **Shared** in the single `.env` file (same pattern as `JWT_SECRET_KEY`)
4. **Startup validation:** If `ENCRYPTION_KEY` is missing or invalid, Cortex refuses to start
5. **Key rotation (future):** Support multiple keys with a `key_id` prefix on ciphertext; decrypt tries all keys; re-encrypt on read with latest key

#### Encryption boundary

- **Services encrypt** before passing data to repositories
- **Services decrypt** after receiving data from repositories
- **Repositories never see plaintext secrets** — they store and retrieve opaque encrypted strings
- **API layer never sees raw secrets** on GET responses — encrypted fields are masked (e.g., `"sk-ant-...****"`) or omitted entirely

### Consequences

**Positive:**
- Database compromise does not expose user API keys
- Encryption key is outside the database (env var) — attacker needs both DB and server access
- Fernet is authenticated encryption — tampered ciphertext is detected and rejected
- Simple API: `encrypt(plaintext) → ciphertext`, `decrypt(ciphertext) → plaintext`

**Negative:**
- Cannot search/filter/index on encrypted fields (acceptable — we never query by API key value)
- Key loss = data loss for all encrypted fields (mitigated: backup the key)
- Small performance overhead for encrypt/decrypt (negligible for the volume of operations)

**Neutral:**
- Fernet tokens are ~50% larger than plaintext (base64 + IV + HMAC overhead)
- Same pattern can be adopted by OneAI-Auth for `google_refresh_token` (currently plaintext)

### Alternatives Rejected

| Alternative | Why Rejected |
|-------------|-------------|
| PostgreSQL pgcrypto (DB-level encryption) | Key must be in SQL query — visible in logs, `pg_stat_statements`; doesn't protect against DB-level compromise |
| Full-disk encryption only | Doesn't protect against SQL injection or application-level data leaks |
| HashiCorp Vault / AWS KMS | Over-engineering for v0.1; adds infrastructure dependency; can migrate later |
| Don't store secrets at all (pass per-request) | Bad UX — users would need to provide all API keys on every request |

### Validation

- Encrypted fields in database are not readable without `ENCRYPTION_KEY`
- `GET /api/v1/agents/{id}` never returns raw API keys — only masked prefixes
- `GET /api/v1/mcp-servers/{id}` never returns raw env_vars — only key names (not values)
- Tampering with ciphertext in DB raises `InvalidToken` error, logged as security event
- Missing `ENCRYPTION_KEY` env var → startup fails with clear error
