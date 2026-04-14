# Phase 2 — Dependencies & Risks

**Date:** 2026-04-13
**Project:** OneAI-Cortex v0.3.0
**Feature:** Agent Configuration Pipeline — Frontend Integration Support

---

## Dependencies

| # | Dependency | Type | Status | Blocks |
|---|-----------|------|--------|--------|
| 1 | `SecretEncryption` service with Fernet | Code | Done (v0.1.0) | Key encryption/decryption |
| 2 | `ENCRYPTION_KEY` environment variable | Config | Done (v0.1.0) | Encryption service init |
| 3 | `AgentService._encrypt_config_secrets()` | Code | Done (v0.1.0) | Key storage |
| 4 | `RunnerService.run_session()` decryption | Code | Done (v0.1.0) | Key retrieval at runtime |
| 5 | `DeepAgentsAdapter.create_runtime()` env injection | Code | Done (v0.1.0) | Key usage |
| 6 | `GET /agents/{id}/versions/{version}` endpoint | API | Done (v0.1.0) | Frontend data loading |
| 7 | `PUT /agents/{id}` endpoint with config | API | Done (v0.1.0) | Frontend save |
| 8 | `AgentVersionResponse` Pydantic schema | Code | Done (v0.1.0) | API response shape |
| 9 | LLM provider SDKs (anthropic, openai, google) | Dependency | Done (v0.1.0) | Error message patterns |

**All dependencies are met.** No new packages, no infrastructure changes.

---

## Risks

| # | Risk | Likelihood | Impact | Mitigation |
|---|------|-----------|--------|------------|
| 1 | **Encrypted keys returned to frontend** — security concern if tokens are reversible without server key | None (by design) | N/A | Fernet tokens require `ENCRYPTION_KEY` to decrypt. Frontend cannot decrypt. This is expected behavior. |
| 2 | **LLM error message format changes** — provider SDK updates change error strings | Low | Medium | Frontend uses broad regex patterns. Provider errors consistently mention "api_key" or "authentication" across versions |
| 3 | **Environment variable collision** — `create_runtime()` sets env vars that affect other concurrent requests | Medium | High | **Already mitigated** — adapter uses `env_backup` dict and `finally` block to restore original values. However, concurrent requests on the same process could still see each other's env vars. For production, consider per-request isolation |
| 4 | **Empty `user_api_keys` dict vs missing field** — frontend might send `{}` vs not sending the field at all | Low | Low | `_encrypt_config_secrets()` checks `if "user_api_keys" in config and config["user_api_keys"]` — handles both cases correctly |
| 5 | **Key overwrite semantics** — frontend sends partial keys (e.g., only `OPENAI_API_KEY`), previous `ANTHROPIC_API_KEY` lost | Medium | Medium | Backend replaces entire `user_api_keys` dict on update (not merge). Frontend should send ALL keys if any are set. Document this behavior. |

---

## Error Handling (Existing — Verified)

| Error Scenario | Where | What Happens |
|---------------|-------|--------------|
| Agent not found | `RunnerService.run_session()` line 83 | `EntityNotFoundError("Agent", "id", ...)` → 404 |
| Version not found | `RunnerService.run_session()` line 87 | `EntityNotFoundError("AgentVersion", ...)` → 404 |
| Empty API keys | `adapter.create_runtime()` line 165 | `AdapterError("Failed to create agent runtime: ...")` → SSE error event |
| Invalid API key | LLM provider SDK | `AuthenticationError` → caught by adapter → `AdapterError` → SSE error event |
| Decryption failure | `SecretEncryption.decrypt_dict_values()` | `InvalidToken` exception → 500 (should not happen if key is consistent) |

---

## Critical Path

```
Verification (T5) → Documentation (T7)
         ↓
No code changes expected — verification-only release
```
