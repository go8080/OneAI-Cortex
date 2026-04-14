# Phase 2 — Data Model

**Date:** 2026-04-10
**Project:** OneAI-Cortex v0.2.0
**Feature:** Categorized Pre-Built Tool Catalog with Tool Playground

---

## Existing `tools` Table (Before)

```sql
CREATE TABLE tools (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(100) UNIQUE NOT NULL,
    description     TEXT NOT NULL,
    framework       VARCHAR(50) NOT NULL,
    tool_type       VARCHAR(20) NOT NULL DEFAULT 'builtin',
    schema          JSONB NOT NULL,
    is_active       BOOLEAN NOT NULL DEFAULT true,
    auth_config     JSONB NOT NULL DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

---

## Updated `tools` Table (After)

```sql
CREATE TABLE tools (
    -- Existing columns (unchanged)
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(100) UNIQUE NOT NULL,
    description     TEXT NOT NULL,
    framework       VARCHAR(50) NOT NULL,
    tool_type       VARCHAR(20) NOT NULL DEFAULT 'builtin',
    schema          JSONB NOT NULL,
    is_active       BOOLEAN NOT NULL DEFAULT true,
    auth_config     JSONB NOT NULL DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- NEW: Categorization
    category        VARCHAR(30) NULL,               -- ToolCategory enum value, nullable for custom tools

    -- NEW: Tool metadata (for builtin/LangChain tools)
    langchain_class VARCHAR(200) NULL,              -- Fully qualified class path for dynamic import
    required_keys   JSONB NOT NULL DEFAULT '[]',    -- List of API key names needed ["TAVILY_API_KEY"]
    input_schema    JSONB NOT NULL DEFAULT '{}',    -- Input parameters the tool accepts

    -- NEW: Playground test results
    test_status     VARCHAR(20) NOT NULL DEFAULT 'untested',  -- ToolTestStatus enum
    last_tested_at  TIMESTAMPTZ NULL,               -- When the tool was last tested
    test_detail     JSONB NULL                      -- Last test output/error snapshot
);

-- NEW: Index for category filtering
CREATE INDEX ix_tools_category ON tools (category) WHERE category IS NOT NULL;

-- NEW: Index for browsing builtin tools by category
CREATE INDEX ix_tools_builtin_category ON tools (category, tool_type) WHERE is_active = true;
```

---

## New Columns Detail

| Column | Type | Default | Nullable | Purpose |
|--------|------|---------|----------|---------|
| `category` | VARCHAR(30) | — | Yes | Tool category from ToolCategory enum. Null for legacy custom tools |
| `langchain_class` | VARCHAR(200) | — | Yes | Fully qualified Python class path for LangChain tool instantiation. Null for custom tools |
| `required_keys` | JSONB | `[]` | No | List of API key names the tool needs (e.g., `["TAVILY_API_KEY"]`) |
| `input_schema` | JSONB | `{}` | No | Describes what query/parameters the tool accepts |
| `test_status` | VARCHAR(20) | `"untested"` | No | Last test result: untested, success, failed |
| `last_tested_at` | TIMESTAMPTZ | — | Yes | Timestamp of last test execution |
| `test_detail` | JSONB | — | Yes | Snapshot of last test result (output or error + latency) |

---

## `test_detail` JSONB Structure

**On success:**
```json
{
  "output": [ ... ],               // actual tool output (type varies per tool)
  "latency_ms": 850,
  "tested_at": "2026-04-10T12:00:00Z",
  "input_used": {"query": "..."}   // what input was tested
}
```

**On failure:**
```json
{
  "error": "401 Unauthorized — Invalid API key for Tavily",
  "latency_ms": 120,
  "tested_at": "2026-04-10T12:00:00Z",
  "input_used": {"query": "..."}
}
```

---

## `input_schema` JSONB Structure

```json
{
  "query": {
    "type": "string",
    "description": "Search query to execute",
    "required": true
  },
  "max_results": {
    "type": "integer",
    "description": "Maximum number of results to return",
    "required": false,
    "default": 5
  }
}
```

---

## Alembic Migration

```python
# alembic/versions/xxxx_add_tool_catalog_columns.py

"""Add tool catalog columns: category, langchain_class, required_keys, input_schema, test fields."""

def upgrade():
    op.add_column('tools', sa.Column('category', sa.String(30), nullable=True))
    op.add_column('tools', sa.Column('langchain_class', sa.String(200), nullable=True))
    op.add_column('tools', sa.Column('required_keys', JSONB, server_default='[]', nullable=False))
    op.add_column('tools', sa.Column('input_schema', JSONB, server_default='{}', nullable=False))
    op.add_column('tools', sa.Column('test_status', sa.String(20), server_default='untested', nullable=False))
    op.add_column('tools', sa.Column('last_tested_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('tools', sa.Column('test_detail', JSONB, nullable=True))

    op.create_index('ix_tools_category', 'tools', ['category'], postgresql_where=text("category IS NOT NULL"))
    op.create_index('ix_tools_builtin_category', 'tools', ['category', 'tool_type'], postgresql_where=text("is_active = true"))

def downgrade():
    op.drop_index('ix_tools_builtin_category')
    op.drop_index('ix_tools_category')
    op.drop_column('tools', 'test_detail')
    op.drop_column('tools', 'last_tested_at')
    op.drop_column('tools', 'test_status')
    op.drop_column('tools', 'input_schema')
    op.drop_column('tools', 'required_keys')
    op.drop_column('tools', 'langchain_class')
    op.drop_column('tools', 'category')
```

---

## ERM Impact

```
┌──────────────┐         ┌──────────────────┐         ┌──────────────┐
│   agents     │         │  agent_versions   │         │   sessions   │
│              │ 1    N  │                   │         │              │
│  id          ├────────→│  id               │         │              │
│  user_id     │         │  agent_id (FK)    │         │              │
│  name        │         │  version          │         │              │
│  framework   │         │  config (JSONB)───┼─────→ config.tools = ["tavily_search", ...]
│              │         │                   │         │  (references tools by NAME)
└──────────────┘         └──────────────────┘         └──────────────┘

                         ┌──────────────────────────────┐
                         │          tools                │
                         │  (ENHANCED — 6 new columns)   │
                         │                                │
                         │  id                            │
                         │  name (UNIQUE)  ←──────────── referenced by agent config
                         │  description                   │
                         │  framework                     │
                         │  tool_type                     │
                         │  schema (JSONB)                │
                         │  is_active                     │
                         │  auth_config (JSONB)           │
                         │  created_at                    │
                         │  + category        (NEW)       │
                         │  + langchain_class  (NEW)      │
                         │  + required_keys    (NEW)      │
                         │  + input_schema     (NEW)      │
                         │  + test_status      (NEW)      │
                         │  + last_tested_at   (NEW)      │
                         │  + test_detail      (NEW)      │
                         └──────────────────────────────┘
```

**Note:** No new tables. No new foreign keys. No new relationships. This is a pure column-addition migration on the existing `tools` table.
