# Phase 2 — Scope Definition

**Date:** 2026-04-13
**Project:** OneAI-Cortex v0.3.0
**Feature:** Agent Configuration Pipeline — Frontend Integration Support
**Input:** Phase 1 Recommendation — Approach C (Verify & Document)

---

## In Scope

### Verification Tasks
1. Verify `GET /agents/{id}/versions/{version}` returns encrypted `user_api_keys` in config JSONB
2. Verify `PUT /agents/{id}` with `config.user_api_keys` encrypts keys via `SecretEncryption.encrypt_dict_values()`
3. Verify `AgentService._encrypt_config_secrets()` handles the `user_api_keys` field correctly
4. Verify `RunnerService.run_session()` decrypts keys and passes plaintext to `adapter.create_runtime()`
5. Verify `DeepAgentsAdapter.create_runtime()` sets API keys as environment variables
6. Verify error messages from `create_runtime()` failure contain identifiable API key–related strings
7. Document the encrypted key format (Fernet tokens) for frontend reference

### Documentation
8. Document the full API key flow: frontend → encryption → storage → decryption → runtime
9. Document the version response shape with encrypted fields highlighted
10. Document error message patterns for frontend pattern matching

---

## Explicitly Out of Scope

1. **Structured error codes** — Approach B deferred; frontend uses string pattern matching for now
2. **Key status endpoint** — No `GET /agents/{id}/key-status`; frontend infers from encrypted blob presence
3. **API key validation endpoint** — No pre-validation of keys against LLM providers
4. **Backend code changes** — If verification passes, no code changes needed
5. **New Alembic migrations** — No schema changes
6. **New Pydantic schemas** — No new request/response models

---

## Assumptions

1. `SecretEncryption` service is correctly configured with `ENCRYPTION_KEY` environment variable
2. Fernet token format produces opaque strings that the frontend cannot and should not decrypt
3. LLM provider error messages consistently contain terms like "api_key", "unauthorized", "authentication"
4. The existing test suite covers encryption/decryption round-trips
5. No concurrent encryption key rotation is happening during this feature's deployment
