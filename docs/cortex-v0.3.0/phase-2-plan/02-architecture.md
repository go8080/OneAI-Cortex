# Phase 2 — Architecture Mapping

**Date:** 2026-04-13
**Project:** OneAI-Cortex v0.3.0
**Feature:** Agent Configuration Pipeline — Frontend Integration Support

---

## Layer Cake Impact

| Layer | Changes | New Files | Modified Files |
|-------|---------|-----------|----------------|
| **API** | None — endpoints already exist | — | — |
| **Schemas** | None — response models already include config | — | — |
| **Service** | None — encryption/decryption already implemented | — | — |
| **Repository** | None — CRUD operations work correctly | — | — |
| **Models** | None — `AgentVersion.config` JSONB stores keys | — | — |
| **Infrastructure** | None — `SecretEncryption` service operational | — | — |
| **Documentation** | Verification results and API key flow docs | `docs/cortex-v0.3.0/` | `CHANGELOG.md` |

---

## Existing API Key Flow (Verified)

```
┌─────────────────────────────────────────────────────────────────────┐
│                    API KEY LIFECYCLE                                  │
│                                                                       │
│  1. STORAGE (agent create/update)                                    │
│  ┌──────────┐    ┌──────────────┐    ┌──────────────────┐          │
│  │ Frontend  │───→│ AgentService │───→│ AgentVersion     │          │
│  │ config:   │    │ _encrypt_    │    │ config (JSONB):  │          │
│  │ user_api_ │    │ config_      │    │ user_api_keys:   │          │
│  │ keys:     │    │ secrets()    │    │ {KEY: "gAAAAA.." │          │
│  │ {KEY:     │    │              │    │  (Fernet token)} │          │
│  │  "sk-ant" │    │ SecretEncrypt│    │                  │          │
│  │  }        │    │ .encrypt_    │    │                  │          │
│  └──────────┘    │ dict_values()│    └──────────────────┘          │
│                   └──────────────┘                                    │
│                                                                       │
│  2. RETRIEVAL (version response)                                     │
│  ┌──────────────────┐    ┌──────────┐                               │
│  │ AgentVersion     │───→│ Frontend │                               │
│  │ config.user_api_ │    │ sees:    │                               │
│  │ keys: encrypted  │    │ "gAAAAA."│  ← Encrypted, NOT plaintext   │
│  └──────────────────┘    │ → show   │                               │
│                           │ "Key set"│                               │
│                           └──────────┘                               │
│                                                                       │
│  3. RUNTIME (agent execution)                                        │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────┐      │
│  │RunnerService │───→│ SecretEncrypt│───→│ DeepAgentsAdapter│      │
│  │ run_session()│    │ .decrypt_    │    │ create_runtime() │      │
│  │ loads config │    │ dict_values()│    │ os.environ[KEY]  │      │
│  │              │    │ → plaintext  │    │ = "sk-ant..."    │      │
│  └──────────────┘    └──────────────┘    └──────────────────┘      │
│                                                                       │
│  4. CLEANUP (after execution)                                        │
│  ┌──────────────────┐                                               │
│  │ DeepAgentsAdapter │                                               │
│  │ finally: block    │                                               │
│  │ restore original  │                                               │
│  │ env vars          │                                               │
│  └──────────────────┘                                               │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Key Files (Verification Targets)

```
app/
├── services/
│   ├── agent.py              # _encrypt_config_secrets() — lines 134-146
│   └── runner.py             # run_session() decrypts keys — lines 92-94
├── adapters/
│   └── deepagents/
│       └── adapter.py        # create_runtime() sets env vars — lines 110-114
├── core/
│   └── encryption.py         # SecretEncryption.encrypt/decrypt_dict_values()
├── schemas/
│   └── agent.py              # AgentVersionResponse includes config
└── api/
    └── agents.py             # GET /{id}/versions/{version} endpoint
```

---

## What's NOT Changing

- All API endpoints — no route changes
- All Pydantic schemas — no field additions
- All SQLAlchemy models — no column additions
- All Alembic migrations — no new migrations
- All adapter code — no execution changes
- Runner service — no flow changes
- Encryption service — no algorithm changes
