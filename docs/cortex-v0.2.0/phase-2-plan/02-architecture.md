# Phase 2 — Architecture Mapping

**Date:** 2026-04-10
**Project:** OneAI-Cortex v0.2.0
**Feature:** Categorized Pre-Built Tool Catalog with Tool Playground

---

## High-Level Module View

```
┌──────────────────────────────────────────────────────────────────────┐
│                        OneAI-Cortex v0.2.0                          │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                    EXISTING MODULES                          │    │
│  │  Auth │ Agents │ Runner │ Evaluator │ Deployer │ MCP Server │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │              ENHANCED MODULE (v0.2.0)                        │    │
│  │                                                               │    │
│  │  ┌──────────────────────────────────────────────────────┐   │    │
│  │  │              Tool Registry (Enhanced)                  │   │    │
│  │  │                                                        │   │    │
│  │  │  ┌──────────┐  ┌──────────┐  ┌───────────────────┐  │   │    │
│  │  │  │ Category  │  │Playground│  │   Tool Seeder     │  │   │    │
│  │  │  │ Browsing  │  │ (Test)   │  │   (Startup)       │  │   │    │
│  │  │  └──────────┘  └──────────┘  └───────────────────┘  │   │    │
│  │  └──────────────────────────────────────────────────────┘   │    │
│  └─────────────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Layer Cake Impact

| Layer | Changes | New Files | Modified Files |
|-------|---------|-----------|----------------|
| **API** | New endpoints: categories, test; extend list with category filter | — | `app/api/tools.py` |
| **Schemas** | New request/response models for test, categories | — | `app/schemas/tool.py` |
| **Service** | Category listing, tool playground execution, seeder service | `app/services/tool_seeder.py` | `app/services/tool.py` |
| **Repository** | Category query, test result update, category filter | — | `app/repositories/tool.py` |
| **Models** | 6 new columns on Tool table | — | `app/models/tool.py` |
| **Core** | 2 new enums: ToolCategory, ToolTestStatus | — | `app/core/constants.py` |
| **Infrastructure** | Seeder startup hook | — | `app/main.py` |
| **Migration** | Add columns to tools table | `alembic/versions/xxxx_add_tool_catalog_columns.py` | — |
| **Seed Data** | LangChain tool → category mapping | `app/services/seed_data/` | — |

---

## Project Structure (Changes Highlighted)

```
app/
├── api/
│   └── tools.py                    # MODIFIED — add categories + test endpoints
├── core/
│   └── constants.py                # MODIFIED — add ToolCategory, ToolTestStatus enums
├── models/
│   └── tool.py                     # MODIFIED — add 6 new columns
├── repositories/
│   └── tool.py                     # MODIFIED — add category filter, list_categories, update_test_result
├── schemas/
│   └── tool.py                     # MODIFIED — add ToolTestRequest, ToolTestResponse, ToolCategoryResponse, update ToolResponse
├── services/
│   ├── tool.py                     # MODIFIED — add list_categories, test_tool methods
│   ├── tool_seeder.py              # NEW — seeder service with idempotent startup seeding
│   └── seed_data/
│       ├── __init__.py             # NEW — package init
│       └── langchain_tools.py      # NEW — declarative tool → category mapping
├── main.py                         # MODIFIED — add seeder to lifespan startup
│
alembic/versions/
└── xxxx_add_tool_catalog_columns.py  # NEW — migration for 6 new columns

docs/
└── ADR/
    ├── ADR-016-tool-categorization-enum-extension.md  # NEW
    └── ADR-017-tool-playground-direct-execution.md    # NEW
```

---

## What's NOT Changing

- `app/models/agent.py` — Agent config still stores `tools: list[str]` (tool names); no change
- `app/services/runner.py` — Runner resolves tools by name; no change to execution flow
- `app/adapters/` — Framework adapters untouched
- `app/models/mcp_server.py` — MCP server module untouched
- `app/infrastructure/` — No infrastructure changes (DB engine, auth client, etc.)
- All existing API endpoints — backward compatible, no breaking changes
