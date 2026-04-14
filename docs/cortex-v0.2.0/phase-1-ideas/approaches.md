# Phase 1 — Evaluated Approaches

**Date:** 2026-04-10
**Status:** Evaluated
**Project:** OneAI-Cortex
**Feature:** Categorized Pre-Built Tool Catalog with Tool Playground

---

## Idea A: Category Column — Minimal Extension

**Approach:** Add a `category` column (StrEnum) to the existing `tools` table, a seeder script for LangChain tools, and a basic test endpoint.

**How it works:**
- Add `ToolCategory` enum (20 values) to `app/core/constants.py`
- Add `category` column to `Tool` model (nullable for backward compatibility)
- New Alembic migration for the column addition
- Ad-hoc seed script that inserts all LangChain tools with category, name, description, schema
- Update `list_tools` API to accept `?category=search` filter
- Add `GET /tools/categories` endpoint to list available categories
- Add `POST /tools/{tool_id}/test` — accepts API keys + input query, executes tool, returns output

**Pros:**
- Minimal structural change — extends existing model with one column
- Single table queries, no joins needed
- Backward compatible (custom tools can have null category)

**Cons:**
- No structured seeder — tool insertion is ad-hoc and fragile
- Flat hierarchy — cannot do sub-categories without another migration
- No test result persistence — users can't see past test results
- No seeder service means manual tool data maintenance
- Test endpoint has no metadata about what inputs/keys each tool requires

**Effort:** M (Medium)
**Dependencies:** Alembic migration, seed data mapping

---

## Idea B: Catalog Table — Separate Data Model

**Approach:** Create new `tool_categories` and `tool_catalog` tables for pre-built tools, keeping the existing `tools` table exclusively for custom tools.

**How it works:**
- `tool_categories` table: id, name, display_name, description, icon, sort_order
- `tool_catalog` table: id, category_id (FK), name, description, provider, langchain_module, schema, required_keys, is_available
- Existing `tools` table untouched (custom tools stay there)
- New API router: `GET /catalog/categories`, `GET /catalog/categories/{slug}/tools`
- `POST /catalog/tools/{id}/test` — accepts API keys + input, executes tool, returns output
- Agent config runner resolves tool names from both `tools` and `tool_catalog` tables

**Pros:**
- Clean separation: catalog (pre-built, read-only) vs tools (custom, user-managed)
- Category metadata (description, icon) enables rich marketplace UI
- `required_keys` field tells the user what API keys are needed upfront

**Cons:**
- Two new tables, new models, new repositories, new API router
- Runner must resolve tool names from two sources (dual-table lookup)
- Over-engineered for current needs
- Significant migration complexity

**Effort:** L (Large)
**Dependencies:** Two new models, two migrations, new API router, runner service changes

---

## Idea C: Enum + Seed + Playground — Structured Extension (SELECTED)

**Approach:** Add category enum to the existing Tool model, a dedicated seeder service with tool metadata (including required API keys and input schema), and a playground-style test endpoint where users provide their keys + query and see actual output.

**How it works:**
- `ToolCategory` enum with 20 values in `app/core/constants.py`
- Add columns to Tool model: `category` (String, indexed), `test_status` (String, default="untested"), `last_tested_at` (DateTime, nullable), `test_detail` (JSONB, nullable)
- Each tool in the seeder includes metadata: `required_keys` (what API keys the tool needs), `input_schema` (what parameters/query the tool accepts)
- Dedicated seeder service in `app/services/tool_seeder.py` with a declarative mapping dictionary
- `GET /tools/categories` endpoint returns distinct categories with tool counts
- `GET /tools?category=search` filters by category
- `POST /tools/{tool_id}/test` — **Tool Playground endpoint:**
  - User provides: `api_keys` (dict of required keys) + `input` (query/parameters as per the tool)
  - Endpoint instantiates the LangChain tool with the provided keys
  - Executes with the user's input and returns the **actual output**
  - If key is invalid → tool execution fails with the provider's error (401, 403, etc.)
  - If input is wrong → tool returns an error message explaining what it expected
  - If output looks good → user decides to use the tool in their agent
  - Stores: `test_status` (success/failed), `test_detail` (JSONB with output + error if any), `last_tested_at`
- Seeder runs at application startup (idempotent — skips existing tools)
- Pre-built tools marked `tool_type=builtin`, user tools remain `tool_type=custom`

**Pros:**
- Simple extension of existing architecture — adds columns, not tables
- **Users see real output** — they decide if the tool is useful, not a schema validator
- Tool metadata (`required_keys`, `input_schema`) tells users exactly what to provide
- Natural error handling — provider errors are more informative than custom validation
- Follows the MCP server testing pattern (`status`, `last_tested_at`) with richer output via `test_detail`
- No new tables or joins — uses existing model and queries
- `tool_type` already distinguishes builtin vs custom
- Idempotent seeder means safe restarts and upgrades

**Cons:**
- No per-user test history — `test_status` is global, last tester wins
- No rich category metadata (icons, descriptions) — categories are just enum values
- Tool instantiation requires knowing each tool's constructor signature and key mapping

**Effort:** M (Medium)
**Dependencies:** Alembic migration for new columns, seeder data mapping with tool metadata, LangChain tool instantiation logic
