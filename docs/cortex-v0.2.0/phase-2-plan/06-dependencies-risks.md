# Phase 2 — Dependencies & Risks

**Date:** 2026-04-10
**Project:** OneAI-Cortex v0.2.0
**Feature:** Categorized Pre-Built Tool Catalog with Tool Playground

---

## Dependencies

| # | Dependency | Type | Status | Blocks |
|---|-----------|------|--------|--------|
| 1 | Existing `tools` table in PostgreSQL | DB | Done (v0.1.0) | Migration |
| 2 | `ToolType` enum (builtin/custom) in constants | Code | Done (v0.1.0) | Seeder logic |
| 3 | `ToolRepository` with CRUD methods | Code | Done (v0.1.0) | New repo methods |
| 4 | `ToolService` with encryption support | Code | Done (v0.1.0) | New service methods |
| 5 | `app/api/tools.py` router | Code | Done (v0.1.0) | New endpoints |
| 6 | `app/schemas/tool.py` Pydantic models | Code | Done (v0.1.0) | New schemas |
| 7 | JWT authentication middleware | Code | Done (v0.1.0) | All new endpoints |
| 8 | Alembic migration infrastructure | Code | Done (v0.1.0) | Column migration |
| 9 | `langchain-community` Python package | Dependency | **To verify** | Tool instantiation in playground |
| 10 | External API provider availability | External | Runtime | Playground test execution |

---

## New Dependencies (Added in v0.2.0)

| Package | Purpose | Version Constraint |
|---------|---------|-------------------|
| `langchain-community` | LangChain tool classes for playground instantiation | Already in project deps (verify version) |
| `langchain-core` | BaseTool base class for type checking | Already in project deps |

**Note:** No new external packages required. LangChain packages are already project dependencies from v0.1.0 (used by the DeepAgents adapter).

---

## Risks

| # | Risk | Likelihood | Impact | Mitigation |
|---|------|-----------|--------|------------|
| 1 | **Seeder mapping errors** — wrong category assignment for tools | Medium | Medium | Organize mapping by category in code; unit test that all entries have valid ToolCategory values; review mapping before merge |
| 2 | **LangChain tool constructor variation** — different tools expect API keys in different constructor kwargs | High | Medium | Seeder stores `key_mapping` per tool (maps generic key name → constructor kwarg name). Start with most common tools per category, expand incrementally |
| 3 | **External API rate limiting during tests** — provider throttles or blocks rapid test requests | Medium | Low | Return the provider's error message directly to user — they can adjust timing. No mitigation needed at platform level |
| 4 | **Tool execution timeout** — some tools take too long (e.g., web scraping) | Medium | Medium | Set a configurable timeout on `tool.invoke()` (default 30 seconds). Return `failed` with timeout error if exceeded |
| 5 | **LangChain version breaking changes** — tool class paths or signatures change between versions | Low | High | Pin LangChain version in pyproject.toml. `langchain_class` paths validated during seeder execution — broken imports logged as warnings |
| 6 | **Large seed data slows startup** — 196+ tool inserts on every boot | Low | Low | Seeder is idempotent (skip existing by name). First boot inserts all; subsequent boots are fast SELECT-only checks. Batch inserts with `flush()` |
| 7 | **Playground exposes sensitive output** — some tools might return sensitive data | Low | Medium | User provides their own API keys and queries — they control what data flows through. `test_detail` JSONB stores output; no encryption needed since user initiated the request |
| 8 | **Custom tools can't use playground** — `langchain_class` is null for custom tools | Expected | Low | Return 400 with clear message: "Playground is only available for built-in tools." Custom tool testing is out of scope (v0.2.0) |
| 9 | **Concurrent test updates** — two users test same tool simultaneously, last write wins for `test_status` | Medium | Low | Acceptable for v0.2.0 — per-user test tracking is out of scope. Last test result is stored globally |
| 10 | **Missing LangChain provider packages** — some tools need extra pip packages (e.g., `google-api-python-client`) | High | Medium | Seeder marks tools as `is_active=false` if their provider package is not importable. Playground validates tool can be instantiated before executing |

---

## Error Handling Strategy

| Error Scenario | HTTP Status | Error Message |
|---------------|-------------|---------------|
| Tool not found | 404 | `"Tool not found: {tool_id}"` |
| Tool has no `langchain_class` (custom tool) | 400 | `"Playground is only available for built-in tools with a LangChain class"` |
| Missing required API keys | 400 | `"Missing required API keys: {missing_keys}"` |
| Tool instantiation fails (bad class path) | 500 | `"Failed to instantiate tool: {error}"` |
| Tool execution fails (API error, timeout, etc.) | 200 | `ToolTestResponse(status="failed", error="{provider_error}")` |
| Tool execution succeeds | 200 | `ToolTestResponse(status="success", output={...})` |

**Design decision:** Tool execution errors (bad API key, provider errors, timeouts) return HTTP 200 with `status="failed"` in the response body — NOT HTTP 4xx/5xx. This is because the *endpoint* worked correctly; the *tool* failed. The user needs to see the error details, not get a generic HTTP error page.

**Design decision:** All tool invocations use `ainvoke()` (not `invoke()`). Not all LangChain tools implement native `_arun()` — some are sync-only. But `ainvoke()` handles both: native async tools get direct `_arun()` calls, sync-only tools get wrapped in `run_in_executor()` automatically. This ensures the FastAPI event loop is never blocked.

---

## Critical Path

```
Migration → Model Changes → Repository → Service → Seeder → API Endpoints → Integration Tests
                                            ↓
                                    Seed Data Mapping (can be done in parallel)
```

The seeder data mapping (`langchain_tools.py`) is the longest pole — it requires curating 196+ tools across 20 categories with metadata. This can be worked on in parallel with the code changes.
