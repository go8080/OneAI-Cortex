# Phase 2 — Scope Definition

**Date:** 2026-04-10
**Project:** OneAI-Cortex v0.2.0
**Feature:** Categorized Pre-Built Tool Catalog with Tool Playground
**Input:** Phase 1 Recommendation — Idea C (Enum + Seed + Playground)

---

## In Scope

### Enums & Constants
1. `ToolCategory` StrEnum — 20 predefined categories: `search`, `research`, `browser`, `communication`, `devtools`, `files`, `database`, `data_analysis`, `speech_audio`, `image_vision`, `documents`, `moderation`, `weather_location`, `finance`, `travel`, `media`, `science`, `automation`, `blockchain`, `utility`
2. `ToolTestStatus` StrEnum — `untested`, `success`, `failed`

### Model Changes (Tool table)
3. Add `category` column (String(30), nullable, indexed) — nullable for backward compat with existing custom tools
4. Add `test_status` column (String(20), default="untested")
5. Add `last_tested_at` column (DateTime with timezone, nullable)
6. Add `test_detail` column (JSONB, nullable) — stores last test output/error snapshot
7. Add `required_keys` column (JSONB, default=[]) — list of API key names this tool needs (e.g., `["TAVILY_API_KEY"]`)
8. Add `input_schema` column (JSONB, default={}) — describes what query/parameters the tool accepts
9. Add `langchain_class` column (String(200), nullable) — fully qualified LangChain class path for instantiation (e.g., `"langchain_community.tools.tavily_search.TavilySearchResults"`)
10. Alembic migration for all new columns

### Schemas (Pydantic)
11. `ToolResponse` — add category, test_status, last_tested_at, required_keys, input_schema fields
12. `ToolTestRequest` — new schema: api_keys (dict), input (dict)
13. `ToolTestResponse` — new schema: status, output, error, latency_ms
14. `ToolCategoryResponse` — new schema: name, tool_count
15. Update `ToolCreate` — add optional category field

### Repository Changes
16. Update `list_tools` — add `category` filter parameter
17. Add `list_categories` — query distinct categories with tool counts
18. Add `update_test_result` — update test_status, test_detail, last_tested_at

### Service Changes
19. Update `ToolService.list_tools` — pass category filter to repository
20. Add `ToolService.list_categories` — return category list with counts
21. Add `ToolService.test_tool` — instantiate LangChain tool with user API keys, execute with user input, return output
22. New `ToolSeederService` — declarative mapping of LangChain tools → categories with metadata, idempotent seed on startup

### API Endpoints
23. `GET /tools/categories` — list all categories with tool counts
24. `GET /tools?category=search` — filter tools by category (extend existing endpoint)
25. `POST /tools/{tool_id}/test` — tool playground: provide API keys + input, get actual output
26. `GET /tools/{tool_id}` — updated response includes new fields

### Seeder Data
27. Declarative Python dict mapping 20 categories → LangChain tool definitions
28. Each tool entry: name, description, framework, category, langchain_class, required_keys, input_schema, schema_def
29. Startup hook to run seeder (idempotent — upsert by name)

### ADRs
30. ADR-016: Tool categorization via enum + model extension (over separate catalog table)
31. ADR-017: Tool playground — direct execution model (over staged validation)

---

## Explicitly Out of Scope

1. **Per-user test history** — only the latest global test result is stored; per-user tracking deferred
2. **Category metadata table** — no icons, descriptions, or sort order for categories; enum values only
3. **Sub-categories** — flat 20-category taxonomy only; no nesting
4. **Tool marketplace UI** — backend catalog only; frontend deferred
5. **Custom tool testing** — playground is for builtin (LangChain) tools only; custom tools have no `langchain_class`
6. **Async/streaming tool execution** — test endpoint is synchronous request-response
7. **Rate limiting on test endpoint** — deferred to platform-level rate limiting
8. **Tool versioning** — tools are not versioned; seeder overwrites metadata on re-seed
9. **Auto-discovery of new LangChain tools** — seeder mapping is manual; no dynamic scanning

---

## Assumptions

1. LangChain tools can be instantiated by passing API keys as constructor kwargs (confirmed by LangChain tool patterns)
2. The existing `tool_type` field ("builtin"/"custom") is sufficient to distinguish seeded vs user-created tools
3. OneAI-Auth JWT authentication is required for all new endpoints (same as existing tool endpoints)
4. The 20 category names are stable and won't change frequently
5. Tool test execution is fast enough for synchronous HTTP response (most LangChain tools respond in <5 seconds)
6. The existing `tools` table has zero or minimal rows in production (new deployments start empty)
7. LangChain community package (`langchain-community`) is available as a dependency
