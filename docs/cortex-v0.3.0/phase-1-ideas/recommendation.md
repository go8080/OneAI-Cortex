# Phase 1 — Recommendation

**Date:** 2026-04-13
**Status:** Accepted
**Project:** OneAI-Cortex
**Feature:** Agent Configuration Pipeline — Frontend Integration Support

---

## Selected Approach

**Approach C — Minimal Backend Enhancement: Verify & Document**

## Rationale

Approach C wins the decision matrix (131 vs 127 vs 86) because the backend infrastructure already works — the correct action is to verify it end-to-end and document behavior for the frontend team:

1. **Encryption Pipeline Verified** — `AgentService._encrypt_config_secrets()` encrypts `user_api_keys` on create/update. `RunnerService.run_session()` decrypts via `self._encryption.decrypt_dict_values()` and passes plaintext keys to `adapter.create_runtime()`.

2. **Version API Verified** — `GET /agents/{id}/versions/{version}` returns `AgentVersion` with `config` JSONB. The `user_api_keys` field contains encrypted blobs (Fernet tokens), not plaintext.

3. **Error Messages Identifiable** — When `create_runtime()` fails due to missing API keys, the `AdapterError` message contains the original exception string from the LLM provider (e.g., "AuthenticationError", "api_key", "ANTHROPIC_API_KEY"). The frontend can pattern-match on these strings.

4. **Zero Code Changes** — If verification confirms existing behavior is correct, no backend code changes are needed. The value is in the verification itself and the documentation it produces.

## Key Risks

### Risk 1: Error messages change between LLM provider versions
LLM providers may change their error message format, breaking frontend pattern matching.

**Mitigation:** Pattern matching uses broad terms (`api.?key`, `unauthorized`, `authentication`) rather than exact strings. Can add structured error codes in a future version (Approach B) if this becomes fragile.

## What We're Giving Up

- Structured error codes (Approach B) — would make frontend error detection deterministic rather than heuristic
- Key status endpoint (Approach B) — would avoid sending encrypted blobs to frontend

---

## Rejected Alternatives

| Approach | Why Rejected | Notes |
|----------|-------------|-------|
| A — No Backend Changes | Nearly identical to C but skips verification — risks discovering issues at runtime | C adds verification at negligible cost |
| B — Error Codes + Endpoint | Over-engineered — new endpoint, new error infrastructure, refactors all adapters | Deferred to future version if heuristic error matching proves insufficient |

---

## Exit Criteria Status

```
[x] Problem statement written and specific
[x] 3 distinct approaches generated and documented
[x] Each approach has pros, cons, and effort estimate
[x] Decision matrix comparing approaches exists
[x] One approach recommended with explicit rationale
[x] Rejected alternatives documented with reasons
[x] Key risks identified with mitigations
[x] Recommendation reviewed by user — APPROVED
```

**Phase 1 COMPLETE — Ready to transition to Phase 2: Plan**
