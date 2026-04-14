# Phase 3 — Task Breakdown

**Date:** 2026-04-13
**Project:** OneAI-Cortex v0.3.0
**Input:** Phase 2 Plan (locked 2026-04-13)
**Status:** READY — 2 tasks (verification + documentation)

---

## Overview

This release is **verification and documentation only** — the backend API key infrastructure is already complete (v0.1.0). The 2 tasks verify end-to-end correctness and document behavior for the frontend team.

The primary implementation work is in OneAI-UI v0.2.0 (7 tasks). See `OneAI-UI/docs/ui-v0.2.0/phase-3-todo/task-breakdown.md` for the full frontend task list.

```
Stage 1: Verification (T5) ────────────────┐
Stage 2: Documentation (T7) ───────────────┘  (blocked by T5)
```

**Note:** Task IDs match the unified task tracker used across both projects.

---

## Stage 1: Verification (1 task)

### T5: Verify backend API key handling in version response [S]
- **What:** Verify the complete API key lifecycle:
  1. `POST /agents` with `config.user_api_keys` → keys encrypted by `AgentService._encrypt_config_secrets()`
  2. `GET /agents/{id}/versions/{version}` → returns encrypted Fernet tokens (not plaintext)
  3. `PUT /agents/{id}` with new `config.user_api_keys` → creates new version with re-encrypted keys
  4. `RunnerService.run_session()` → decrypts keys and passes plaintext to adapter
  5. `DeepAgentsAdapter.create_runtime()` → sets env vars, cleans up in finally block
  6. Error messages from missing keys contain identifiable strings (api_key, authentication, etc.)
- **Where:** Read-only verification of:
  - `app/services/agent.py` lines 134-146
  - `app/services/runner.py` lines 92-94
  - `app/adapters/deepagents/adapter.py` lines 110-114
  - `app/core/encryption.py`
  - `app/schemas/agent.py`
- **Produces:** Confirmed behavior documented in Phase 2 docs
- **Done when:** All 6 verification points confirmed, key overwrite semantics documented (replace, not merge)

---

## Stage 2: Documentation (1 task)

### T7: Update CHANGELOG [S]
- **What:** Add entry to `CHANGELOG.md` under `[Unreleased]`:
  - Documented API key lifecycle for frontend integration
  - Verified encryption/decryption pipeline end-to-end
  - Cataloged error message patterns for frontend error handling
- **Where:** `CHANGELOG.md`
- **Blocked by:** T5
- **Done when:** CHANGELOG entry exists; no code changes to document

---

## Dependency Graph

```
T5 (verify backend keys) ──→ T7 (CHANGELOG)
```

---

## Cross-Project Dependencies

The following OneAI-UI tasks depend on the Cortex verification (T5):

| UI Task | What | Why It Depends on T5 |
|---------|------|---------------------|
| T2 (edit mode) | Load existing agent data | Needs to know encrypted key format to handle correctly |
| T6 (chat error) | Improved error messages | Needs to know error message patterns for regex matching |

---

## Size Distribution

| Size | Count | Tasks |
|------|-------|-------|
| S | 2 | T5, T7 |
| **Total** | **2** | |

---

## Exit Criteria

```
[x] Every deliverable from the Plan is represented by at least one task
[x] All 2 tasks created in Claude Code's task tracker (TaskCreate)
[x] Each task has subject, description, and acceptance criteria
[x] Dependencies set between tasks (TaskUpdate with addBlockedBy)
[x] No task is larger than size S
[x] Task sequence is correct (verify before document)
[x] Cross-project dependencies documented
[x] Task list reviewed by user — APPROVED
```

**Phase 3 COMPLETE — Proceed to Gates 1-5 implementation.**
