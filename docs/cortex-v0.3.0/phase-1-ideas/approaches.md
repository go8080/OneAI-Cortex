# Phase 1 — Evaluated Approaches

**Date:** 2026-04-13
**Status:** Evaluated
**Project:** OneAI-Cortex
**Feature:** Agent Configuration Pipeline — Frontend Integration Support

---

## Approach A: No Backend Changes — Frontend-Only Fix

**Description:** The backend is working correctly. All required endpoints exist. The fix is entirely on the frontend side — add API client methods, edit mode, and API key UI.

**How it works:**
- Frontend adds `getVersion()` API client method for existing endpoint
- Frontend adds edit mode to AgentWizard using existing `GET`/`PUT` agent APIs
- Frontend adds API key input UI, sends keys as `config.user_api_keys`
- Backend encryption pipeline handles the rest automatically

**Pros:**
- Zero backend changes — no risk of breaking existing functionality
- All endpoints already tested and documented
- Encryption/decryption pipeline proven in existing tests

**Cons:**
- Backend error messages for missing API keys are raw exception strings
- No structured error codes for frontend to parse reliably
- Version response returns encrypted key blobs — frontend must handle gracefully

**Effort:** S (Small — backend perspective, no changes)
**Dependencies:** None

---

## Approach B: Add Structured Error Codes + Key Status Endpoint (EVALUATED)

**Description:** Add structured error codes to `AdapterError` for missing API keys. Add a `GET /agents/{id}/key-status` endpoint that returns which keys are configured (without values).

**How it works:**
- Extend `AdapterError` with error codes: `MISSING_API_KEY`, `INVALID_API_KEY`
- New endpoint `GET /agents/{id}/key-status` returns `{ "ANTHROPIC_API_KEY": true, "OPENAI_API_KEY": false }`
- SSE error events include structured `error_code` field

**Pros:**
- Frontend can reliably detect API key errors via error code
- Key status endpoint avoids sending encrypted blobs to frontend

**Cons:**
- New endpoint adds API surface area
- Error code infrastructure is new pattern — affects all adapters
- Over-engineered for current needs

**Effort:** M (Medium)
**Dependencies:** AdapterError refactor, new endpoint, new schema

---

## Approach C: Minimal Backend Enhancement — Verify & Document (SELECTED)

**Description:** Verify existing backend behavior is correct and well-documented. Ensure error messages from `adapter.create_runtime()` contain identifiable strings for frontend pattern matching. No new endpoints, no error code infrastructure.

**How it works:**
- Verify `GET /agents/{id}/versions/{version}` returns encrypted `user_api_keys` correctly
- Verify `PUT /agents/{id}` with `config.user_api_keys` encrypts and stores correctly
- Verify `create_runtime()` error messages contain recognizable API key–related strings
- Document the encrypted key format so frontend knows to show "configured" indicators
- No code changes if verification passes

**Pros:**
- Zero or minimal backend changes
- Documents existing behavior for frontend team
- No new API surface area

**Cons:**
- Frontend must rely on string matching for error detection (fragile)
  - Acceptable because error messages come from LLM providers, which consistently mention "API key" or "unauthorized"

**Effort:** S (Small)
**Dependencies:** None
