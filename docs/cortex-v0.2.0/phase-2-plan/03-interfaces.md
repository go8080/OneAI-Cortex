# Phase 2 — Interface Design

**Date:** 2026-04-10
**Project:** OneAI-Cortex v0.2.0
**Feature:** Categorized Pre-Built Tool Catalog with Tool Playground

---

## 1. New Enums

```python
# app/core/constants.py

class ToolCategory(StrEnum):
    """Pre-defined tool categories for the built-in catalog."""
    SEARCH = "search"
    RESEARCH = "research"
    BROWSER = "browser"
    COMMUNICATION = "communication"
    DEVTOOLS = "devtools"
    FILES = "files"
    DATABASE = "database"
    DATA_ANALYSIS = "data_analysis"
    SPEECH_AUDIO = "speech_audio"
    IMAGE_VISION = "image_vision"
    DOCUMENTS = "documents"
    MODERATION = "moderation"
    WEATHER_LOCATION = "weather_location"
    FINANCE = "finance"
    TRAVEL = "travel"
    MEDIA = "media"
    SCIENCE = "science"
    AUTOMATION = "automation"
    BLOCKCHAIN = "blockchain"
    UTILITY = "utility"


class ToolTestStatus(StrEnum):
    """Status of the last tool test execution."""
    UNTESTED = "untested"
    SUCCESS = "success"
    FAILED = "failed"
```

---

## 2. API Contracts

### GET /tools/categories
List all tool categories with their tool counts.

**Auth:** Required (JWT)
**Response:** `200 OK`
```json
[
  { "name": "search", "display_name": "Search", "tool_count": 12 },
  { "name": "research", "display_name": "Research", "tool_count": 8 },
  ...
]
```

### GET /tools?category={category}&framework={framework}
List tools filtered by category and/or framework (extends existing endpoint).

**Auth:** Required (JWT)
**Query Params:**
- `category: str | None` — filter by ToolCategory value
- `framework: str | None` — existing filter (unchanged)

**Response:** `200 OK` — `list[ToolResponse]` (updated with new fields)
```json
[
  {
    "id": "uuid",
    "name": "tavily_search",
    "description": "AI-powered search engine...",
    "framework": "langchain",
    "tool_type": "builtin",
    "category": "search",
    "schema": { ... },
    "is_active": true,
    "required_keys": ["TAVILY_API_KEY"],
    "input_schema": {
      "query": { "type": "string", "description": "Search query", "required": true }
    },
    "test_status": "untested",
    "last_tested_at": null,
    "created_at": "2026-04-10T..."
  }
]
```

### POST /tools/{tool_id}/test
Tool playground — execute a tool with user-provided API keys and input.

**Auth:** Required (JWT)
**Path Params:** `tool_id: UUID`
**Request Body:** `ToolTestRequest`
```json
{
  "api_keys": {
    "TAVILY_API_KEY": "tvly-abc123..."
  },
  "input": {
    "query": "latest AI agent frameworks 2026"
  }
}
```

**Response (success):** `200 OK` — `ToolTestResponse`
```json
{
  "status": "success",
  "output": [
    { "title": "...", "url": "...", "snippet": "..." }
  ],
  "error": null,
  "latency_ms": 850
}
```

**Response (failure):** `200 OK` — `ToolTestResponse`
```json
{
  "status": "failed",
  "output": null,
  "error": "401 Unauthorized — Invalid API key for Tavily",
  "latency_ms": 120
}
```

**Error cases:**
- `404` — tool_id not found
- `400` — missing required API keys (validated against tool's `required_keys`)
- `400` — tool has no `langchain_class` (custom tools can't be tested via playground)

---

## 3. Schema Definitions

```python
# app/schemas/tool.py — NEW/MODIFIED schemas

class ToolTestRequest(BaseModel):
    """Request body for tool playground test."""
    api_keys: dict[str, str]        # {"TAVILY_API_KEY": "tvly-..."}
    input: dict[str, Any]           # {"query": "search terms"}

class ToolTestResponse(BaseModel):
    """Response from tool playground test."""
    status: str                     # "success" | "failed"
    output: Any | None = None       # actual tool output (varies per tool)
    error: str | None = None        # error message if failed
    latency_ms: int                 # execution time in milliseconds

class ToolCategoryResponse(BaseModel):
    """Category with tool count."""
    name: str                       # "search"
    display_name: str               # "Search"
    tool_count: int                 # 12

class ToolResponse(BaseModel):      # UPDATED — add new fields
    id: UUID
    name: str
    description: str
    framework: str
    tool_type: str
    category: str | None = None
    schema_def: dict[str, Any]      # serialization_alias="schema"
    is_active: bool
    required_keys: list[str] = []
    input_schema: dict[str, Any] = {}
    test_status: str = "untested"
    last_tested_at: datetime | None = None
    created_at: datetime

class ToolCreate(BaseModel):        # UPDATED — add optional category
    name: str
    description: str
    framework: str
    tool_type: str = "custom"
    category: str | None = None     # NEW — optional for custom tools
    schema_def: dict[str, Any]      # alias="schema"
    auth_config: dict[str, Any] = {}
```

---

## 4. Service Layer Interfaces

### ToolService (modified)

```python
class ToolService:
    async def create_tool(self, data: ToolCreate) -> Tool
    async def get_tool(self, tool_id: UUID) -> Tool
    async def list_tools(self, *, framework: str | None = None, category: str | None = None) -> list[Tool]
    async def update_tool(self, tool_id: UUID, data: ToolUpdate) -> Tool

    # NEW methods
    async def list_categories(self) -> list[ToolCategoryResponse]
    async def test_tool(self, tool_id: UUID, request: ToolTestRequest) -> ToolTestResponse
```

### ToolSeederService (new)

```python
class ToolSeederService:
    async def seed(self) -> dict[str, int]
        """Seed all builtin tools from the declarative mapping.
        Returns: {"created": N, "skipped": M}
        Idempotent — skips tools that already exist by name.
        """
```

---

## 5. Repository Layer Interfaces

### ToolRepository (modified)

```python
class ToolRepository:
    async def create(self, data: dict) -> Tool
    async def get_by_id(self, tool_id: UUID) -> Tool | None
    async def get_by_name(self, name: str) -> Tool | None
    async def list_tools(self, *, framework: str | None = None, category: str | None = None, active_only: bool = True) -> list[Tool]
    async def update(self, tool_id: UUID, data: dict) -> Tool | None

    # NEW methods
    async def list_categories(self) -> list[tuple[str, int]]
        """Returns list of (category_name, tool_count) tuples, ordered by name."""

    async def update_test_result(self, tool_id: UUID, status: str, detail: dict, tested_at: datetime) -> Tool | None
        """Update test_status, test_detail, and last_tested_at for a tool."""
```

---

## 6. Seeder Data Interface

```python
# app/services/seed_data/langchain_tools.py

TOOL_CATALOG: dict[str, list[dict]] = {
    "search": [
        {
            "name": "tavily_search",
            "description": "AI-powered search engine that returns relevant results with snippets",
            "langchain_class": "langchain_community.tools.tavily_search.TavilySearchResults",
            "required_keys": ["TAVILY_API_KEY"],
            "input_schema": {
                "query": {"type": "string", "description": "Search query", "required": True}
            },
            "schema_def": { ... }
        },
        # ... more search tools
    ],
    "research": [ ... ],
    "browser": [ ... ],
    # ... all 20 categories
}
```

---

## 7. Tool Instantiation & Execution

```python
# Inside ToolService.test_tool()

def _instantiate_tool(langchain_class: str, api_keys: dict[str, str]) -> BaseTool:
    """Dynamically import and instantiate a LangChain tool.

    Args:
        langchain_class: Fully qualified class path (e.g., "langchain_community.tools.tavily_search.TavilySearchResults")
        api_keys: User-provided API keys mapped to the tool's constructor kwargs

    Returns:
        Instantiated LangChain BaseTool ready for invocation
    """
```

This factory uses Python's `importlib` to dynamically load the tool class and passes `api_keys` as constructor kwargs. Each tool in the seeder mapping specifies which key names map to which constructor params.

### Async Execution Strategy

**All tool invocations MUST use `ainvoke()`, not `invoke()`.**

Not all LangChain tools implement native async (`_arun()`). However, `ainvoke()` is safe for ALL tools:

| Tool async support | What `ainvoke()` does |
|-------------------|----------------------|
| Has `_arun()` (e.g., Tavily) | Calls `_arun()` directly — true async I/O |
| Sync-only `_run()` (e.g., DuckDuckGo, ReadFile) | Wraps `_run()` in `run_in_executor()` — offloads to thread pool |

This ensures the FastAPI event loop is **never blocked**, regardless of whether the underlying tool is sync or async.

```python
# In ToolService.test_tool():
async def test_tool(self, tool_id: UUID, request: ToolTestRequest) -> ToolTestResponse:
    ...
    tool_instance = _instantiate_tool(tool.langchain_class, request.api_keys)
    output = await tool_instance.ainvoke(request.input)  # Always ainvoke, never invoke
    ...
```
