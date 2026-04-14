# Phase 2 — Dependencies & Risks

**Date:** 2026-04-14
**Project:** OneAI-Cortex v0.4.0
**Feature:** Google Connected Services — OAuth Token Management & Agent Integration

---

## Dependencies

| # | Dependency | Type | Status | Blocks |
|---|-----------|------|--------|--------|
| 1 | `SecretEncryption` service (Fernet) | Code | Done (v0.1.0) | Refresh token encryption/decryption |
| 2 | `ENCRYPTION_KEY` environment variable | Config | Done (v0.1.0) | Encryption service init |
| 3 | `httpx` async HTTP client | Package | Done (v0.1.0, used by `AuthClient`) | Google OAuth HTTP calls |
| 4 | `structlog` structured logging | Package | Done (v0.1.0) | Service-level logging |
| 5 | `UUIDPrimaryKeyMixin`, `TimestampMixin` | Code | Done (v0.1.0) | ORM model base |
| 6 | FastAPI dependency injection (`Depends`) | Code | Done (v0.1.0) | Router → service wiring |
| 7 | JWT auth (`get_current_user`) | Code | Done (v0.1.0) | All endpoints require auth |
| 8 | Alembic migration infrastructure | Config | Done (v0.1.0) | Schema migration |
| 9 | `GOOGLE_CLIENT_ID` env var | Config | **NEW** | Google OAuth code exchange |
| 10 | `GOOGLE_CLIENT_SECRET` env var | Config | **NEW** | Google OAuth code exchange |
| 11 | Google Cloud project with OAuth consent screen | External | **User setup** | Google returns valid tokens |
| 12 | Google APIs enabled (Gmail, Calendar, Drive) | External | **User setup** | Scopes are recognized by Google |

**New dependencies:** Only env vars (#9, #10) and external Google setup (#11, #12). No new Python packages.

---

## Risks

| # | Risk | Likelihood | Impact | Mitigation |
|---|------|-----------|--------|------------|
| 1 | **Google refresh token revoked externally** — User revokes access at `myaccount.google.com/permissions` without notifying Cortex | Medium | Medium | When `refresh_access_token()` gets `400 invalid_grant`, update connection status to `revoked`. Return `410 Gone` with clear message. Frontend shows "Reconnect" prompt. |
| 2 | **Google only returns refresh_token on first consent** — Subsequent OAuth flows don't include `refresh_token` | High | High | Frontend MUST set `prompt: "consent"` in `initCodeClient()`. This forces consent screen and guarantees `refresh_token`. If `refresh_token` is null in response, raise `ValidationError`. |
| 3 | **Google token endpoint unreachable** — Network issues, Google outage | Low | High | `GoogleOAuthClient` uses `httpx` with 10s timeout. Return `502 Bad Gateway` with `"Google OAuth service unavailable"`. Agent tools should handle this gracefully and inform the user. |
| 4 | **GOOGLE_CLIENT_ID/SECRET not configured** — Deployed without env vars | Medium | Low | Feature gracefully disabled. `connect_google()` returns `501 Not Implemented` with `"Google OAuth not configured"`. Other endpoints unaffected. |
| 5 | **Encryption key rotation breaks stored tokens** — `ENCRYPTION_KEY` changes between deploys | Low | Critical | **Same risk as all encrypted fields in Cortex (ADR-011).** Document: rotating `ENCRYPTION_KEY` invalidates all Fernet tokens. Key rotation mechanism deferred; not unique to this feature. |
| 6 | **Concurrent reconnect race condition** — User double-clicks "Connect", two code exchanges happen | Low | Low | Unique constraint `(user_id, provider)` prevents duplicate rows. Second `create()` triggers `IntegrityError` → caught and converted to `update()` (upsert pattern). |
| 7 | **Scope string parsing inconsistency** — Google returns scopes in different order or with extra spaces | Low | Low | `granted_scopes.split()` handles multiple spaces. Scope comparison uses set operations, not string equality. |
| 8 | **`redirect_uri` mismatch** — Frontend sends wrong redirect_uri for code exchange | Medium | Medium | For popup-based flow (GIS `initCodeClient`), redirect_uri should be `"postmessage"`. Service normalizes empty string to `"postmessage"` as default. Document this in API contract. |

---

## Error Handling

| Error Scenario | Where | HTTP Status | Response |
|---------------|-------|-------------|----------|
| Google OAuth not configured | `connect_google()` | 501 | `"Google OAuth is not configured on this server"` |
| Invalid/expired auth code | `GoogleOAuthClient.exchange_code()` | 400 | `"Invalid or expired Google authorization code"` |
| No refresh_token in Google response | `connect_google()` | 400 | `"Google did not return a refresh token. Ensure prompt=consent is set."` |
| Google token endpoint unreachable | `GoogleOAuthClient.*` | 502 | `"Google OAuth service unavailable"` |
| No Google connection for user | `get_google_token()`, `disconnect_google()` | 404 | `"No Google account connected"` |
| Refresh token revoked | `get_google_token()` | 410 | `"Google access has been revoked. Please reconnect."` |
| Fernet decryption failure | `get_google_token()` | 500 | `"Failed to decrypt stored credentials"` (should not happen if key is consistent) |
| Duplicate connection (race) | `connect_google()` | 200 | Silently upserts — no error |

---

## Security Considerations

| Concern | Handling |
|---------|---------|
| Refresh token at rest | Fernet-encrypted (AES-128-CBC + HMAC-SHA256). Requires `ENCRYPTION_KEY` to decrypt. |
| Access token at rest | **Never stored.** Generated on-demand, returned in response, not persisted. |
| `GOOGLE_CLIENT_SECRET` | Stored in env var only. Never logged, never returned in API responses. |
| Token in transit | HTTPS enforced in production. Development uses localhost. |
| Scope over-granting | Cortex stores whatever scopes Google returns. The UI controls which scopes are requested. |
| Token endpoint authentication | All endpoints require JWT auth (`Authorization: Bearer <jwt>`). |
| Hard delete on disconnect | Refresh tokens are **permanently deleted**, not soft-deleted. No recovery possible after disconnect. |

---

## Critical Path

```
T1 (constants) ──→ T2 (model + migration) ──→ T3 (repository) ──→ T4 (google client)
                                                        │                    │
                                                        ▼                    ▼
                                                   T5 (service) ◄───────────┘
                                                        │
                                                        ▼
                                                   T6 (schemas + API)
                                                        │
                                                        ▼
                                               T7 (config + router wiring)
                                                        │
                                                        ▼
                                               T8 (tests)
                                                        │
                                                        ▼
                                               T9 (ADRs + CHANGELOG)
```
