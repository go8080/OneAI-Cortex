## ADR-016: Tool Categorization via Enum + Model Extension

**Date:** 2026-04-10
**Status:** accepted
**Phase:** Plan (from Ideas phase — Idea C selected)

### Context

OneAI-Cortex ships with a flat, empty tool registry. Users must manually register every tool via API. There is no way to browse tools by domain or discover pre-built tools from the LangChain ecosystem. The platform needs a categorized tool catalog with 20 predefined categories (search, research, browser, communication, devtools, files, database, data_analysis, speech_audio, image_vision, documents, moderation, weather_location, finance, travel, media, science, automation, blockchain, utility).

Three approaches were evaluated:
- A: Add category column only (no structured seeder)
- B: Separate tool_categories + tool_catalog tables
- C: Category enum + seeder service on existing model

### Decision

Extend the existing `tools` table with a `category` column (VARCHAR(30), nullable) and a `ToolCategory` StrEnum with 20 values. A dedicated `ToolSeederService` populates the table at startup with LangChain tool definitions mapped to categories via a declarative Python dictionary. Each seeded tool includes metadata: `langchain_class`, `required_keys`, and `input_schema`.

### Consequences

**Positive:**
- No new tables — single table queries for all tool operations
- Category enum is type-safe and self-documenting
- Declarative seeder is reviewable, testable, and idempotent
- `tool_type` (builtin/custom) naturally distinguishes seeded vs user-created tools
- Follows existing architectural patterns (column extension, not new entities)

**Negative:**
- No rich category metadata (icons, descriptions, sort order) — categories are enum strings only
- Flat hierarchy — no sub-categories without schema change
- Category is nullable — custom tools may have no category

**Neutral:**
- Seeder data lives in code (Python dict), not in a config file or separate database
- Category filtering adds one WHERE clause to existing queries

### Alternatives Rejected

| Alternative | Why Rejected |
|-------------|-------------|
| A — Category column only | No structured seeder; ad-hoc tool management unmaintainable for 196+ tools |
| B — Separate catalog tables | Over-engineered; two new tables + dual-source tool resolution for what a column + seeder achieves |

### Validation

- All 20 categories populated with at least 1 tool after seeding
- `GET /tools?category=search` returns only search-category tools
- `GET /tools/categories` returns 20 categories with correct counts
- Existing custom tool creation still works (category=null)
- Seeder is idempotent — re-running creates 0 new tools
