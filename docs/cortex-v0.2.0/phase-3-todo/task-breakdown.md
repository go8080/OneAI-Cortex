# Phase 3 — Task Breakdown

**Date:** 2026-04-10
**Project:** OneAI-Cortex v0.2.0
**Feature:** Categorized Pre-Built Tool Catalog with Tool Playground
**Input:** Phase 2 Plan (locked 2026-04-10)
**Status:** READY — 14 tasks across 8 stages

---

## Overview

14 tasks organized into 8 stages following the critical path.
Each task is sized S-L (no XL). Dependencies enforce layer ordering.

```
Stage 1: Core & Model (T1-T3) ────────────────┐
Stage 2: Schemas (T4) ────────────────────────┤ (parallel with Stage 3)
Stage 3: Repository (T5) ─────────────────────┤ (blocked by Stage 1)
Stage 4: Service (T6-T8) ─────────────────────┤ (blocked by Stage 2+3)
Stage 5: API (T9) ────────────────────────────┤ (blocked by Stage 2+4)
Stage 6: Integration (T10) ───────────────────┤ (blocked by Stage 4)
Stage 7: Tests (T11-T13) ─────────────────────┤ (blocked by Stage 4+5)
Stage 8: Documentation (T14) ─────────────────┘ (blocked by all above)
```

---

## Stage 1: Core & Model (3 tasks)

### T1: Add ToolCategory and ToolTestStatus enums [S]
- **What:** 2 new StrEnum classes — ToolCategory (20 values), ToolTestStatus (untested, success, failed)
- **Where:** `app/core/constants.py`
- **Done when:** Both enums importable, all values match Phase 2 spec

### T2: Add 7 new columns to Tool model [M]
- **What:** category, langchain_class, required_keys, input_schema, test_status, last_tested_at, test_detail
- **Where:** `app/models/tool.py`
- **Blocked by:** T1
- **Done when:** All columns defined with correct types, defaults, nullability

### T3: Create Alembic migration [S]
- **What:** Migration adds 7 columns + 2 partial indexes (ix_tools_category, ix_tools_builtin_category)
- **Where:** `alembic/versions/xxxx_add_tool_catalog_columns.py`
- **Blocked by:** T2
- **Done when:** `alembic upgrade head` adds all columns; downgrade removes them

---

## Stage 2: Schemas (1 task — parallel with Stage 3)

### T4: Update Pydantic schemas [M]
- **What:** Update ToolResponse + ToolCreate; new ToolTestRequest, ToolTestResponse, ToolCategoryResponse
- **Where:** `app/schemas/tool.py`
- **Done when:** All 5 schemas defined; ToolResponse includes new fields; aliases preserved

---

## Stage 3: Repository (1 task)

### T5: Update ToolRepository [M]
- **What:** Add category filter to list_tools(); new list_categories(); new update_test_result()
- **Where:** `app/repositories/tool.py`
- **Blocked by:** T2
- **Done when:** Category filtering works; list_categories returns counts; test results persist

---

## Stage 4: Service (3 tasks)

### T6: Update ToolService — categories + playground [L]
- **What:** Update list_tools (category param); new list_categories(); new test_tool() with dynamic LangChain tool instantiation via importlib + ainvoke()
- **Where:** `app/services/tool.py`
- **Blocked by:** T4, T5
- **Done when:** Categories return with counts; playground executes LangChain tools; errors caught and returned

### T7: Create seed data mapping [L]
- **What:** Declarative TOOL_CATALOG dict — 20 categories → tool definitions with name, description, langchain_class, required_keys, input_schema, schema_def. Curated subset (5-10 per category)
- **Where:** `app/services/seed_data/__init__.py`, `app/services/seed_data/langchain_tools.py`
- **Done when:** All 20 categories have entries; all langchain_class paths are valid

### T8: Create ToolSeederService [M]
- **What:** Idempotent seed() method — loads TOOL_CATALOG, skips existing by name, creates new as builtin/langchain. Handles import failures gracefully.
- **Where:** `app/services/tool_seeder.py`
- **Blocked by:** T5, T7
- **Done when:** seed() creates new, skips existing; re-run creates 0; import failures handled

---

## Stage 5: API (1 task)

### T9: Update tool API routes [M]
- **What:** GET /tools/categories; update GET /tools with ?category= filter; POST /tools/{tool_id}/test playground endpoint
- **Where:** `app/api/tools.py`
- **Blocked by:** T4, T6
- **Done when:** All endpoints return correct responses; auth enforced; error cases handled per spec

---

## Stage 6: Integration (1 task)

### T10: Wire seeder into app startup [S]
- **What:** Add ToolSeederService.seed() call to app/main.py lifespan after DB init
- **Where:** `app/main.py`
- **Blocked by:** T8
- **Done when:** App startup seeds tools; logs created/skipped counts; idempotent on restart

---

## Stage 7: Tests (3 tasks)

### T11: Unit tests — ToolSeederService [M]
- **What:** Test idempotency, category coverage, skip logic, import failure handling, return values
- **Where:** `tests/unit/services/test_tool_seeder.py`
- **Blocked by:** T8
- **Done when:** All seeder scenarios covered

### T12: Unit tests — ToolService new methods [M]
- **What:** Test list_categories, test_tool success/failure/missing keys/custom tool/timeout, test result persistence
- **Where:** `tests/unit/services/test_tool_service.py`
- **Blocked by:** T6
- **Done when:** All new methods tested with mock LangChain tool

### T13: Integration tests — tool API endpoints [M]
- **What:** Test categories endpoint, category filtering, playground success/failure/missing keys/custom tool/404
- **Where:** `tests/integration/test_tools_api.py`
- **Blocked by:** T9
- **Done when:** All endpoint scenarios covered; auth enforced; response schemas validated

---

## Stage 8: Documentation (1 task)

### T14: Update CHANGELOG.md and finalize ADRs [S]
- **What:** CHANGELOG [Unreleased] section; ADR-016 + ADR-017 status → accepted
- **Where:** `CHANGELOG.md`, `docs/ADR/ADR-016-*.md`, `docs/ADR/ADR-017-*.md`
- **Blocked by:** T9, T10, T13
- **Done when:** CHANGELOG accurate; ADRs accepted; no stale docs

---

## Dependency Graph

```
T1 (enums)
 ↓
T2 (model) ──────────┐
 ↓                    ↓
T3 (migration)    T5 (repo) ──────────┐
                     ↓                 ↓
T4 (schemas) ──→ T6 (service) ──→ T8 (seeder) ← T7 (seed data)
 │               ↓     ↓              ↓
 │            T12(test) │           T10 (startup wire)
 │                      ↓           T11 (seeder tests)
 └──────────→ T9 (API endpoints)
                  ↓
               T13 (integration tests)
                  ↓
               T14 (docs) ← T9 + T10 + T13
```

## Parallel Opportunities

| Task(s) | Can run in parallel with | Why |
|---------|------------------------|-----|
| T4 (schemas) | T3 (migration), T5 (repo) | Schemas don't depend on model or repo |
| T7 (seed data) | T4, T5, T6 | Data mapping is independent of code layers |
| T11 (seeder tests) | T12 (service tests) | Independent test suites |

---

## Size Distribution

| Size | Count | Tasks |
|------|-------|-------|
| S | 4 | T1, T3, T10, T14 |
| M | 8 | T2, T4, T5, T8, T9, T11, T12, T13 |
| L | 2 | T6, T7 |
| **Total** | **14** | |

---

## Exit Criteria

```
[x] Every deliverable from the Plan is represented by at least one task
[x] All 14 tasks created in Claude Code's task tracker (TaskCreate)
[x] Each task has subject, description, and acceptance criteria
[x] Dependencies set between tasks (TaskUpdate with addBlockedBy)
[x] No task is larger than size L
[x] Task sequence respects layer dependency order
[x] Parallel-safe tasks identified (T4||T5, T7||code tasks, T11||T12)
[ ] Task list reviewed by user
```

**Phase 3 READY FOR REVIEW → Then proceed to Gates 1-5 implementation.**
