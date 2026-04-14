# Phase 2 — Architecture Mapping

**Date:** 2026-04-14
**Project:** OneAI-Cortex v0.4.0
**Feature:** Google Connected Services — OAuth Token Management & Agent Integration

---

## Layer Cake Impact

| Layer | Changes | New Files | Modified Files |
|-------|---------|-----------|----------------|
| **API** | New connected services router with 5 endpoints | `app/api/connected_services.py` | `app/api/router.py` |
| **Schemas** | Request/response models for connected services | `app/schemas/connected_service.py` | — |
| **Service** | OAuth code exchange, token management, disconnect | `app/services/connected_service.py` | — |
| **Repository** | CRUD + lookup by (user_id, provider) | `app/repositories/connected_service.py` | — |
| **Models** | `ConnectedService` ORM model | `app/models/connected_service.py` | — |
| **Infrastructure** | Google OAuth HTTP client (token exchange, userinfo) | `app/infrastructure/google_oauth.py` | — |
| **Core/Constants** | `ServiceProvider`, `ConnectionStatus` enums | — | `app/core/constants.py` |
| **Config** | `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` env vars | — | `app/config.py` |
| **Migration** | Create `connected_services` table | `alembic/versions/c3d4e5f6g7h8_add_connected_services.py` | — |
| **Documentation** | ADRs, lifecycle docs, changelog | `docs/ADR/ADR-018-*.md`, `docs/ADR/ADR-019-*.md` | `CHANGELOG.md` |

---

## Connected Services Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         USER BROWSER                                     │
│                                                                           │
│  ┌──────────────────┐    ┌──────────────────────┐                        │
│  │  Connected        │    │  Google OAuth Popup   │                        │
│  │  Services Page    │───→│  (accounts.google)    │                        │
│  │  (OneAI-UI)       │    │                       │                        │
│  └────────┬─────────┘    └──────────┬────────────┘                        │
│           │                         │                                      │
│           │  1. User toggles        │  2. Google returns                   │
│           │     scopes & clicks     │     authorization code               │
│           │     "Connect"           │                                      │
└───────────┼─────────────────────────┼──────────────────────────────────────┘
            │                         │
            ▼                         ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      OneAI-Cortex (FastAPI)                               │
│                                                                           │
│  ┌─── API Layer ──────────────────────────────────────────────────┐      │
│  │  POST /api/v1/connected-services/google/connect                │      │
│  │  GET  /api/v1/connected-services                               │      │
│  │  GET  /api/v1/connected-services/google/scopes                 │      │
│  │  GET  /api/v1/connected-services/google/token                  │      │
│  │  DELETE /api/v1/connected-services/google                      │      │
│  └──────────────────────────┬─────────────────────────────────────┘      │
│                              │                                            │
│  ┌─── Service Layer ────────┴────────────────────────────────────┐      │
│  │  ConnectedServiceService                                       │      │
│  │  ├── connect_google(user_id, code, redirect_uri)              │      │
│  │  ├── get_google_scopes(user_id)                               │      │
│  │  ├── get_google_token(user_id)                                │      │
│  │  ├── list_connections(user_id)                                │      │
│  │  └── disconnect_google(user_id)                               │      │
│  └──────┬───────────────────────────────────┬────────────────────┘      │
│         │                                   │                            │
│  ┌──────┴──── Repository ──┐  ┌─────────────┴── Infrastructure ──┐      │
│  │ ConnectedServiceRepo    │  │ GoogleOAuthClient                 │      │
│  │ ├── create()            │  │ ├── exchange_code(code)           │      │
│  │ ├── get_by_user_and_    │  │ ├── refresh_access_token(        │      │
│  │ │   provider()          │  │ │   refresh_token)                │      │
│  │ ├── update()            │  │ └── get_user_info(access_token)  │      │
│  │ ├── delete()            │  └──────────────────────────────────┘      │
│  │ └── list_by_user()      │           │                                 │
│  └──────────┬──────────────┘           │                                 │
│             │                          ▼                                  │
│  ┌──────────┴──── Model ───┐  ┌────────────────────────────┐            │
│  │ ConnectedService        │  │ Google OAuth Endpoints      │            │
│  │ ├── id (UUID PK)        │  │ POST oauth2.googleapis.com  │            │
│  │ ├── user_id             │  │      /token                 │            │
│  │ ├── provider            │  │ GET  googleapis.com/oauth2  │            │
│  │ ├── refresh_token (enc) │  │      /v2/userinfo           │            │
│  │ ├── granted_scopes      │  └────────────────────────────┘            │
│  │ ├── provider_email      │                                             │
│  │ ├── status              │                                             │
│  │ └── timestamps          │                                             │
│  └─────────────────────────┘                                             │
│                                                                           │
│  ┌─── Encryption (existing) ─────────────────────────────────────┐      │
│  │  SecretEncryption.encrypt() → Fernet token stored in DB       │      │
│  │  SecretEncryption.decrypt() → plaintext for token refresh     │      │
│  └───────────────────────────────────────────────────────────────┘      │
└─────────────────────────────────────────────────────────────────────────┘
            │
            ▼ (future v0.5.0: agent tools call GET /connected-services/google/token)
┌─────────────────────────────────────────────────────────────────────────┐
│                      Agent Runtime (future)                               │
│                                                                           │
│  gmail_send tool → GET /connected-services/google/token                  │
│                  → uses access_token to call Gmail API                    │
│                  → POST gmail.googleapis.com/v1/users/me/messages/send   │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Key Files (New + Modified)

```
app/
├── api/
│   ├── connected_services.py     # NEW — 5 endpoint router
│   └── router.py                 # MOD — include connected_services router
├── schemas/
│   └── connected_service.py      # NEW — request/response models
├── services/
│   └── connected_service.py      # NEW — business logic
├── repositories/
│   └── connected_service.py      # NEW — data access
├── models/
│   └── connected_service.py      # NEW — ORM model
├── infrastructure/
│   └── google_oauth.py           # NEW — Google HTTP client
├── core/
│   └── constants.py              # MOD — add ServiceProvider, ConnectionStatus enums
├── config.py                     # MOD — add GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET
alembic/
└── versions/
    └── c3d4e5f6g7h8_add_connected_services.py  # NEW — migration
docs/
├── ADR/
│   ├── ADR-018-cortex-owned-connected-services.md  # NEW
│   └── ADR-019-provider-agnostic-connected-services-model.md  # NEW
└── cortex-v0.4.0/                # NEW — all planning docs
```

---

## What's NOT Changing

- All existing API endpoints — no route modifications (only addition)
- All existing SQLAlchemy models — no column additions to `agents`, `tools`, etc.
- All existing services — `AgentService`, `RunnerService`, `ToolService` untouched
- Encryption infrastructure — `SecretEncryption` reused as-is
- Auth integration — `AuthClient` unchanged; JWT auth unchanged
- Adapter layer — `DeepAgentsAdapter` untouched (tools will use token endpoint in v0.5.0)
