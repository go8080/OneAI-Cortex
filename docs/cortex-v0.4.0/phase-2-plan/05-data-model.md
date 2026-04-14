# Phase 2 — Data Model

**Date:** 2026-04-14
**Project:** OneAI-Cortex v0.4.0
**Feature:** Google Connected Services — OAuth Token Management & Agent Integration

---

## New Table: `connected_services`

### SQL Schema

```sql
CREATE TABLE connected_services (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL,
    provider        VARCHAR(50) NOT NULL,       -- 'google', 'slack', 'github', etc.
    provider_email  VARCHAR(255),               -- email address from the provider
    refresh_token   TEXT NOT NULL,              -- Fernet-encrypted refresh token
    granted_scopes  TEXT NOT NULL DEFAULT '',   -- space-separated OAuth scope URIs
    status          VARCHAR(20) NOT NULL DEFAULT 'active',  -- 'active', 'revoked', 'expired'
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- One connection per user per provider
    CONSTRAINT uq_connected_services_user_provider UNIQUE (user_id, provider)
);

-- Query pattern: lookup by user + provider (covered by unique constraint)
-- Query pattern: list all connections for a user
CREATE INDEX ix_connected_services_user_id ON connected_services (user_id);
```

### Column Reference

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | No | Primary key, server-generated |
| `user_id` | UUID | No | Owner of this connection (from JWT `sub` claim) |
| `provider` | VARCHAR(50) | No | Service provider identifier: `google`, `slack`, `github` |
| `provider_email` | VARCHAR(255) | Yes | Email address from the provider's userinfo endpoint |
| `refresh_token` | TEXT | No | **Fernet-encrypted** long-lived refresh token |
| `granted_scopes` | TEXT | No | Space-separated list of granted OAuth scopes |
| `status` | VARCHAR(20) | No | Connection status: `active`, `revoked`, `expired` |
| `created_at` | TIMESTAMPTZ | No | When the connection was first established |
| `updated_at` | TIMESTAMPTZ | No | When the connection was last modified (reconnect, status change) |

### Constraints

| Constraint | Type | Columns | Purpose |
|-----------|------|---------|---------|
| PK | Primary Key | `id` | Row identity |
| `uq_connected_services_user_provider` | Unique | `(user_id, provider)` | One connection per user per provider |
| `ix_connected_services_user_id` | Index | `user_id` | Fast lookup: list all connections for a user |

---

## SQLAlchemy ORM Model

```python
class ConnectedService(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """OAuth connection to an external service provider."""

    __tablename__ = "connected_services"
    __table_args__ = (
        UniqueConstraint("user_id", "provider", name="uq_connected_services_user_provider"),
        Index("ix_connected_services_user_id", "user_id"),
    )

    user_id: Mapped[UUID] = mapped_column(nullable=False)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    provider_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    refresh_token: Mapped[str] = mapped_column(Text, nullable=False)     # Fernet-encrypted
    granted_scopes: Mapped[str] = mapped_column(Text, nullable=False, server_default="")
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="active"
    )
```

---

## Encrypted Field Format

The `refresh_token` column stores a **Fernet token** produced by `cryptography.fernet.Fernet`:

- Format: `gAAAAAB` prefix + base64-encoded (timestamp + IV + ciphertext + HMAC)
- Typical length: ~200 characters for a Google refresh token
- Non-deterministic: same plaintext produces different tokens each time (random IV)
- Requires `ENCRYPTION_KEY` env var to decrypt — stored ciphertext is useless without it

### Encryption/Decryption Pattern

```python
# At storage time (connect_google)
encrypted = self._encryption.encrypt(google_refresh_token)
# → "gAAAAABm...Fernet-token..."

# At runtime (get_google_token)
plaintext = self._encryption.decrypt(encrypted)
# → "1//0eXxYzAbC..."  (Google refresh token)
```

---

## Scopes Format

The `granted_scopes` column stores a **space-separated string** of OAuth scope URIs, matching Google's token response format:

```
openid https://www.googleapis.com/auth/gmail.modify https://www.googleapis.com/auth/calendar https://www.googleapis.com/auth/userinfo.email https://www.googleapis.com/auth/userinfo.profile
```

**Parsing:** `scopes_list = granted_scopes.split()` (split on whitespace)

**Why space-separated, not JSONB array?**
- Matches Google's token response format (space-separated `scope` string)
- Simpler storage — no JSON encoding/decoding overhead
- Easy to query with `LIKE` if needed: `WHERE granted_scopes LIKE '%gmail.modify%'`
- Consistent with OAuth 2.0 spec (RFC 6749 Section 3.3: scope = space-delimited list)

---

## Status Lifecycle

```
                  connect_google()
                        │
                        ▼
                   ┌─────────┐
                   │  active  │ ← initial state
                   └────┬─────┘
                        │
          ┌─────────────┼─────────────┐
          │             │             │
    reconnect()    token_revoked   disconnect()
          │         (Google)          │
          ▼             │             ▼
    ┌─────────┐   ┌────┴─────┐   [DELETED]
    │  active  │   │ revoked  │   (hard delete)
    │ (updated)│   └──────────┘
    └─────────┘         │
                   reconnect()
                        │
                        ▼
                   ┌─────────┐
                   │  active  │
                   │ (updated)│
                   └─────────┘
```

| From | Event | To | Notes |
|------|-------|----|-------|
| — | `connect_google()` | `active` | First connection |
| `active` | `connect_google()` (reconnect) | `active` | Updated token + scopes |
| `active` | Google returns `invalid_grant` | `revoked` | User revoked at Google |
| `revoked` | `connect_google()` (reconnect) | `active` | User re-consents |
| `active` / `revoked` | `disconnect_google()` | **DELETED** | Hard delete — tokens not retained |

---

## ERM (Entity Relationship)

```
┌──────────────┐                ┌──────────────────────┐
│   users       │                │  connected_services   │
│  (OneAI-Auth) │ 1          N  │                       │
│               │◄──────────────│  user_id              │
│  id (UUID)    │               │  provider             │
│  email        │               │  provider_email       │
│               │               │  refresh_token (enc)  │
│               │               │  granted_scopes       │
│               │               │  status               │
└──────────────┘                │  created_at           │
                                │  updated_at           │
                                └──────────────────────┘

Note: No FK to users table — Cortex doesn't have access to Auth's DB.
user_id is validated via JWT auth (same shared secret).
```

---

## No Changes to Existing Tables

This feature adds one new table. No modifications to:
- `agents`, `agent_versions`
- `sessions`, `messages`
- `tools`
- `mcp_servers`, `agent_mcp_servers`
- `api_keys`
- `deployments`, `deployment_endpoints`
- `eval_test_suites`, `eval_test_cases`, `eval_runs`
