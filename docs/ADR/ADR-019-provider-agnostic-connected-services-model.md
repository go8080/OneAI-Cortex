## ADR-019: Provider-Agnostic Connected Services Data Model

**Date:** 2026-04-14
**Status:** Accepted
**Phase:** Plan (from Ideas phase recommendation — Approach B)

### Context

OneAI-Cortex needs to store OAuth credentials for external service providers (Google, and future: Slack, GitHub, Notion). The data model must support multiple providers without per-provider schema changes.

Two data model approaches were considered:
- **Per-provider columns on `users` table** — `google_refresh_token`, `google_scopes`, `slack_refresh_token`, etc.
- **Provider-agnostic `connected_services` table** — `(user_id, provider, refresh_token, granted_scopes, status)`

### Decision

**Use a provider-agnostic `connected_services` table** with a `provider` discriminator column and a unique constraint on `(user_id, provider)`.

```sql
CREATE TABLE connected_services (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL,
    provider        VARCHAR(50) NOT NULL,
    provider_email  VARCHAR(255),
    refresh_token   TEXT NOT NULL,          -- Fernet-encrypted
    granted_scopes  TEXT NOT NULL DEFAULT '',
    status          VARCHAR(20) NOT NULL DEFAULT 'active',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (user_id, provider)
);
```

Key design choices:
1. **`provider` as VARCHAR, not FK** — Providers are defined in code (`ServiceProvider` enum), not in a separate table. Adding a provider is a code change, not a migration.
2. **`granted_scopes` as space-separated TEXT** — Matches OAuth 2.0 spec (RFC 6749 Section 3.3). Avoids JSONB overhead for a simple list.
3. **`refresh_token` encrypted with Fernet** — Reuses existing `SecretEncryption` infrastructure (ADR-011).
4. **Hard delete on disconnect** — Tokens are not soft-deleted. When a user disconnects, the row and encrypted token are permanently removed.
5. **No `access_token` column** — Access tokens are short-lived (~1 hour) and fetched on demand. Storing them would create stale data.

### Consequences

**Positive:**
- Adding a new provider requires zero schema changes — same table, new `provider` value
- Single repository serves all providers
- Clean query patterns: `WHERE user_id = ? AND provider = ?`
- One connection per user per provider enforced at DB level

**Negative:**
- Provider-specific fields (e.g., Slack `team_id`) would need to go in a JSONB `metadata` column or a separate table — acceptable trade-off for initial simplicity
- No foreign key to a `providers` table — provider validity is enforced in application code

**Neutral:**
- Scopes are provider-specific strings — no normalization across providers
- Each provider's infrastructure client handles its own token exchange format

### Alternatives Rejected

| Alternative | Why Rejected |
|-------------|-------------|
| Per-provider columns on `users` table | Doesn't scale: each new provider adds 2-3 columns. Migrations required per provider. Cross-service issue: Cortex doesn't own the `users` table (Auth does). |
| Separate table per provider (`google_connections`, `slack_connections`) | Duplicates schema. Repository per provider. N tables instead of N rows. |
| JSONB `metadata` column for all provider data | Loses type safety. Can't enforce NOT NULL on `refresh_token`. Harder to query and index. |

### Validation

How we'll know this decision was correct:
- Adding Slack/GitHub support requires: `ServiceProvider.SLACK` enum value + `SlackOAuthClient` infrastructure + service methods. No migration, no new table.
- Query performance for token lookup: single index scan on `(user_id, provider)` unique constraint
- No schema change PRs for new provider integrations
