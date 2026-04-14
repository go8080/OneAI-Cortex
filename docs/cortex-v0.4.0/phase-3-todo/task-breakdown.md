# Phase 3 — Task Breakdown

**Date:** 2026-04-14
**Project:** OneAI-Cortex v0.4.0
**Input:** Phase 2 Plan (locked 2026-04-14)
**Status:** READY — 9 tasks across 5 stages

---

## Overview

This release adds the Connected Services infrastructure to OneAI-Cortex — OAuth code exchange, encrypted token storage, scope management, and fresh token issuance for Google. The provider-agnostic data model supports future Slack/GitHub/Notion integrations.

```
Stage 1: Foundation ─────────── T1 (constants) → T2 (model + migration)
Stage 2: Data Layer ─────────── T3 (repository)
Stage 3: Infrastructure ─────── T4 (google OAuth client)
Stage 4: Business Logic ─────── T5 (service) → T6 (schemas + API) → T7 (config + wiring)
Stage 5: Quality ────────────── T8 (tests) → T9 (ADRs + CHANGELOG)
```

---

## Stage 1: Foundation (2 tasks)

### T1: Add ServiceProvider and ConnectionStatus enums [S]
- **What:** Add new enums to `app/core/constants.py`:
  - `ServiceProvider(StrEnum)`: `GOOGLE = "google"`, `SLACK = "slack"`, `GITHUB = "github"`
  - `ConnectionStatus(StrEnum)`: `ACTIVE = "active"`, `REVOKED = "revoked"`, `EXPIRED = "expired"`
- **Where:** `app/core/constants.py` — append to existing enums, update `__all__`
- **Done when:** Enums importable and used by model/service layers

### T2: Create ConnectedService ORM model + Alembic migration [M]
- **What:**
  1. Create `app/models/connected_service.py` with `ConnectedService` model:
     - Uses `UUIDPrimaryKeyMixin`, `TimestampMixin` from `app/models/base.py`
     - Columns: `user_id`, `provider`, `provider_email`, `refresh_token`, `granted_scopes`, `status`
     - Unique constraint: `(user_id, provider)`
     - Index: `user_id`
  2. Create Alembic migration for `connected_services` table
- **Where:** `app/models/connected_service.py` (new), `alembic/versions/` (new migration)
- **Blocked by:** T1 (uses `ConnectionStatus` enum default)
- **Done when:** `alembic upgrade head` creates the table; model is importable

---

## Stage 2: Data Layer (1 task)

### T3: Create ConnectedServiceRepository [S]
- **What:** Create `app/repositories/connected_service.py` with:
  - `create(data: dict) -> ConnectedService`
  - `get_by_user_and_provider(user_id: UUID, provider: str) -> ConnectedService | None`
  - `update(service_id: UUID, data: dict) -> ConnectedService | None`
  - `list_by_user(user_id: UUID) -> list[ConnectedService]`
  - `delete(service_id: UUID) -> bool` (hard delete)
- **Where:** `app/repositories/connected_service.py` (new)
- **Blocked by:** T2 (needs ORM model)
- **Pattern:** Follow `app/repositories/agent.py` — constructor takes `AsyncSession`, uses `select()` + `execute()`
- **Done when:** All 5 methods implemented; follows existing repository patterns

---

## Stage 3: Infrastructure (1 task)

### T4: Create GoogleOAuthClient [M]
- **What:** Create `app/infrastructure/google_oauth.py` with:
  - Dataclasses: `GoogleTokenResult(access_token, refresh_token, expires_in, scope)`, `GoogleUserInfo(email, name, picture)`
  - `GoogleOAuthClient(client_id, client_secret, timeout)`:
    - `exchange_code(code, redirect_uri) -> GoogleTokenResult` — POST to `https://oauth2.googleapis.com/token` with `grant_type=authorization_code`
    - `refresh_access_token(refresh_token) -> GoogleTokenResult` — POST to `https://oauth2.googleapis.com/token` with `grant_type=refresh_token`
    - `get_user_info(access_token) -> GoogleUserInfo` — GET `https://www.googleapis.com/oauth2/v2/userinfo`
  - Handle error responses: `invalid_grant` (revoked), `invalid_client` (bad config), network errors
- **Where:** `app/infrastructure/google_oauth.py` (new)
- **Pattern:** Follow `app/infrastructure/auth_client.py` — uses `httpx.AsyncClient`, `structlog` logging, returns dataclasses
- **Done when:** All 3 methods implemented; error handling covers revoked tokens and network failures

---

## Stage 4: Business Logic (3 tasks)

### T5: Create ConnectedServiceService [L]
- **What:** Create `app/services/connected_service.py` with:
  - Constructor: `(repo, google_client, encryption)`
  - `connect_google(user_id, code, redirect_uri)`:
    1. Check Google OAuth is configured (CLIENT_ID/SECRET present)
    2. Exchange code via `GoogleOAuthClient.exchange_code()`
    3. Fetch user info via `GoogleOAuthClient.get_user_info()`
    4. Validate `refresh_token` is present (raise if None)
    5. Encrypt `refresh_token` via `SecretEncryption.encrypt()`
    6. Upsert: create or update `connected_services` row
    7. Return `ConnectedServiceResponse`
  - `get_google_scopes(user_id)` — lookup + return status/scopes/email
  - `get_google_token(user_id)`:
    1. Load connection, decrypt refresh_token
    2. Call `GoogleOAuthClient.refresh_access_token()`
    3. If `invalid_grant`: update status to `revoked`, raise error
    4. Return fresh access_token
  - `list_connections(user_id)` — list all providers
  - `disconnect_google(user_id)` — hard delete
- **Where:** `app/services/connected_service.py` (new)
- **Blocked by:** T3 (repository), T4 (Google client)
- **Pattern:** Follow `app/services/agent.py` — constructor injection, encryption via `SecretEncryption`, domain exceptions
- **Done when:** All 5 methods implemented; encryption round-trip verified; error paths handle revoked tokens

### T6: Create Pydantic schemas + API router [M]
- **What:**
  1. Create `app/schemas/connected_service.py`:
     - `GoogleConnectRequest(code, redirect_uri)`
     - `ConnectedServiceResponse(id, provider, provider_email, status, granted_scopes, created_at, updated_at)`
     - `GoogleScopesResponse(connected, scopes, email)`
     - `GoogleTokenResponse(access_token, expires_in, scopes)`
     - `ConnectedServiceListResponse(items, total)`
  2. Create `app/api/connected_services.py` with 5 endpoints:
     - `POST /google/connect` → 201/200
     - `GET /` → 200
     - `GET /google/scopes` → 200
     - `GET /google/token` → 200
     - `DELETE /google` → 204
- **Where:** `app/schemas/connected_service.py` (new), `app/api/connected_services.py` (new)
- **Blocked by:** T5 (service layer)
- **Pattern:** Follow `app/api/agents.py` + `app/schemas/agent.py` — `Depends(get_current_user)`, service instantiation in endpoint
- **Done when:** All 5 endpoints match interface spec from `03-interfaces.md`; schemas validate correctly

### T7: Update config + wire router [S]
- **What:**
  1. Add to `app/config.py`:
     - `google_client_id: str = ""` (optional — empty = feature disabled)
     - `google_client_secret: str = ""` (optional)
  2. Add to `app/api/router.py`:
     - Import and include `connected_services` router at prefix `/connected-services`
  3. Wire `GoogleOAuthClient` initialization at app startup (only if config is set)
- **Where:** `app/config.py` (mod), `app/api/router.py` (mod), possibly `app/main.py` (mod)
- **Blocked by:** T6 (router exists)
- **Done when:** `GET /api/v1/connected-services` returns 200; feature disabled gracefully when env vars absent

---

## Stage 5: Quality (2 tasks)

### T8: Write tests [M]
- **What:**
  1. **Unit tests** for `ConnectedServiceService`:
     - `test_connect_google_success` — mock Google client, verify encryption + storage
     - `test_connect_google_reconnect` — existing connection, verify upsert
     - `test_connect_google_no_refresh_token` — verify validation error
     - `test_get_google_scopes_connected` — verify response shape
     - `test_get_google_scopes_not_connected` — verify `connected=False`
     - `test_get_google_token_success` — verify decrypt + refresh flow
     - `test_get_google_token_revoked` — verify status update + 410
     - `test_disconnect_google` — verify hard delete
  2. **Unit tests** for `GoogleOAuthClient`:
     - `test_exchange_code_success` — mock httpx, verify request body
     - `test_exchange_code_invalid` — mock 400 response
     - `test_refresh_token_revoked` — mock `invalid_grant` response
  3. **Integration tests** for API endpoints:
     - `test_connect_endpoint` — POST with mock Google
     - `test_scopes_endpoint_connected` — GET after connect
     - `test_scopes_endpoint_not_connected` — GET before connect
     - `test_token_endpoint` — GET with mock Google refresh
     - `test_disconnect_endpoint` — DELETE + verify gone
- **Where:** `tests/unit/services/test_connected_service.py`, `tests/unit/infrastructure/test_google_oauth.py`, `tests/integration/api/test_connected_services.py`
- **Blocked by:** T7 (full stack wired)
- **Done when:** All tests pass; coverage for happy path + error paths

### T9: Write ADRs + update CHANGELOG [S]
- **What:**
  1. Create `docs/ADR/ADR-018-cortex-owned-connected-services.md`
  2. Create `docs/ADR/ADR-019-provider-agnostic-connected-services-model.md`
  3. Update `CHANGELOG.md` under `[Unreleased]`:
     - Added: Connected Services API (`POST /connected-services/google/connect`, etc.)
     - Added: `connected_services` table with provider-agnostic schema
     - Added: `GoogleOAuthClient` infrastructure for token exchange
     - Added: Fernet-encrypted refresh token storage
  4. Update `OneAI-Cortex.postman_collection.json` with new endpoints
- **Where:** `docs/ADR/` (2 new files), `CHANGELOG.md` (mod), `OneAI-Cortex.postman_collection.json` (mod)
- **Blocked by:** T8 (all code complete and tested)
- **Done when:** ADRs follow template; CHANGELOG entry exists; Postman collection has all 5 endpoints

---

## Dependency Graph

```
T1 (constants) ──→ T2 (model + migration)
                          │
                          ▼
                    T3 (repository)
                          │
            T4 (google client)
                │         │
                ▼         ▼
              T5 (service) ◄──── T3 + T4
                    │
                    ▼
              T6 (schemas + API)
                    │
                    ▼
              T7 (config + wiring)
                    │
                    ▼
              T8 (tests)
                    │
                    ▼
              T9 (ADRs + CHANGELOG)
```

---

## Size Distribution

| Size | Count | Tasks |
|------|-------|-------|
| S | 4 | T1, T3, T7, T9 |
| M | 3 | T2, T4, T6 |
| L | 2 | T5, T8 |
| **Total** | **9** | |

---

## Exit Criteria

```
[x] Every deliverable from the Plan is represented by at least one task
[x] All 9 tasks documented with subject, description, and acceptance criteria
[x] Dependencies set between tasks (blocking relationships documented)
[x] No task is larger than size L
[x] Task sequence is correct (foundation → data → infra → logic → quality)
[x] Each task follows an existing codebase pattern (reference file cited)
[x] Task list reviewed by user — APPROVED
```

**Phase 3 COMPLETE — Proceed to Gates 1-5 implementation.**
