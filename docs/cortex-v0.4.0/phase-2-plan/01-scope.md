# Phase 2 — Scope Definition

**Date:** 2026-04-14
**Project:** OneAI-Cortex v0.4.0
**Feature:** Google Connected Services — OAuth Token Management & Agent Integration
**Input:** Phase 1 Recommendation — Approach B (Cortex-Owned Connected Services)

---

## In Scope

### Database & Model Layer
1. New `connected_services` table with provider-agnostic schema (UUID PK, user_id, provider, encrypted refresh_token, granted_scopes, status, provider_email)
2. Alembic migration for table creation
3. SQLAlchemy ORM model `ConnectedService` with `UUIDPrimaryKeyMixin`, `TimestampMixin`

### Repository Layer
4. `ConnectedServiceRepository` — CRUD operations, lookup by `(user_id, provider)`

### Service Layer
5. `ConnectedServiceService` — OAuth code exchange, token storage, scope management, fresh token issuance, disconnect
6. Encrypt `refresh_token` before storage using existing `SecretEncryption` (Fernet)
7. Decrypt `refresh_token` at runtime to call Google's token refresh endpoint

### Infrastructure Layer
8. `GoogleOAuthClient` — HTTP client for Google OAuth endpoints:
   - `POST https://oauth2.googleapis.com/token` (code exchange + token refresh)
   - `GET https://www.googleapis.com/oauth2/v2/userinfo` (fetch user email/name)

### API Layer
9. New router `connected_services.py` with endpoints:
   - `GET /api/v1/connected-services` — List all connected services for the user
   - `GET /api/v1/connected-services/google/scopes` — Get Google connection status + granted scopes
   - `POST /api/v1/connected-services/google/connect` — Exchange auth code for tokens, store connection
   - `DELETE /api/v1/connected-services/google` — Disconnect Google (delete stored tokens)
   - `GET /api/v1/connected-services/google/token` — Get fresh Google access token (for agent runtime)

### Schema Layer
10. Pydantic request/response models: `GoogleConnectRequest`, `ConnectedServiceResponse`, `GoogleScopesResponse`, `GoogleTokenResponse`

### Constants
11. New enums: `ServiceProvider` (google, slack, github), `ConnectionStatus` (active, revoked, expired)

### Configuration
12. New env vars: `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` (optional — feature disabled if not set)

### Documentation
13. ADR-018: Cortex-owned connected services
14. ADR-019: Provider-agnostic data model
15. CHANGELOG.md update

---

## Explicitly Out of Scope

1. **Google agent tools** (gmail_send, calendar_create, drive_list) — Deferred to v0.5.0. This version builds the token infrastructure; tools consume it later.
2. **Non-Google providers** (Slack, GitHub, Notion) — Table supports them, but no implementation yet.
3. **Token caching in Redis** — Fresh tokens are fetched on demand from Google. Caching is a future optimization.
4. **Frontend changes** (OneAI-UI) — UI already has the Connected Services page. Wiring it to these endpoints is a separate UI release.
5. **Token encryption key rotation** — Single Fernet key; rotation mechanism deferred.
6. **Service-to-service auth** for the internal token endpoint — Protected by JWT auth (same as all Cortex endpoints). mTLS/API key protection deferred to production hardening.
7. **Audit logging** for token issuance — Structured logging via structlog is included, but a dedicated audit table is deferred.
8. **Google consent screen verification** — Required for production but is a Google Cloud Console process, not a code change.

---

## Assumptions

1. `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` will be provided via environment variables. If absent, the Google connect endpoint returns 501 Not Implemented.
2. The frontend uses Google Identity Services (GIS) library (`initCodeClient`) with `access_type: "offline"` and `prompt: "consent"` to obtain an authorization code.
3. The frontend sends the authorization code to Cortex's `POST /connected-services/google/connect` with `redirect_uri: ""` (postmessage flow).
4. `httpx` is already a dependency of OneAI-Cortex (used by `AuthClient`). No new packages needed.
5. Google's token endpoint returns `refresh_token` when `prompt=consent` is set.
6. One Google connection per user (unique constraint on `user_id + provider`). Reconnecting overwrites the previous connection.
