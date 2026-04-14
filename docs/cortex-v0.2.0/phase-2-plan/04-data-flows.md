# Phase 2 — Data Flows

**Date:** 2026-04-10
**Project:** OneAI-Cortex v0.2.0
**Feature:** Categorized Pre-Built Tool Catalog with Tool Playground

---

## Flow 1: Application Startup — Tool Seeding

```
App Startup (lifespan)
  → ToolSeederService.seed()
    → Load TOOL_CATALOG dict from seed_data/langchain_tools.py
    → For each category in TOOL_CATALOG:
        → For each tool_def in category tools:
            → ToolRepository.get_by_name(tool_def["name"])
            → If exists: SKIP (idempotent)
            → If not exists:
                → Build tool row: {
                    name, description, framework="langchain",
                    tool_type="builtin", category, langchain_class,
                    required_keys, input_schema, schema_def,
                    is_active=True, auth_config={}
                  }
                → ToolRepository.create(tool_row)
    → Log: "Seeded {created} tools, skipped {skipped} existing"
    → Commit transaction
```

---

## Flow 2: Browse Categories

```
Client → GET /tools/categories
  → Router: authenticate user (JWT)
    → ToolService.list_categories()
      → ToolRepository.list_categories()
        → SQL: SELECT category, COUNT(*) FROM tools
                WHERE is_active = true AND category IS NOT NULL
                GROUP BY category ORDER BY category
      ← Returns: [("search", 12), ("research", 8), ...]
    ← Transform to ToolCategoryResponse list with display_name
  ← Return 200: [{"name": "search", "display_name": "Search", "tool_count": 12}, ...]
```

---

## Flow 3: Browse Tools by Category

```
Client → GET /tools?category=search
  → Router: authenticate user (JWT), parse query params
    → ToolService.list_tools(category="search")
      → ToolRepository.list_tools(category="search", active_only=True)
        → SQL: SELECT * FROM tools
                WHERE is_active = true AND category = 'search'
                ORDER BY name
      ← Returns: list[Tool]
    ← Returns: list[Tool]
  ← Return 200: list[ToolResponse] (includes required_keys, input_schema, test_status)

Note: User sees what API keys are needed and what input format the tool expects
      BEFORE attempting to test it.
```

---

## Flow 4: Tool Playground — Test a Tool (Success Path)

```
Client → POST /tools/{tool_id}/test
  Body: {
    "api_keys": {"TAVILY_API_KEY": "tvly-abc123"},
    "input": {"query": "latest AI agent frameworks 2026"}
  }

  → Router: authenticate user (JWT), parse tool_id, validate body
    → ToolService.test_tool(tool_id, request)
      → ToolRepository.get_by_id(tool_id)
      ← Tool found (name="tavily_search", langchain_class="langchain_community.tools...")

      → Validate: tool.langchain_class is not None
        (custom tools without langchain_class → 400 error)

      → Validate: all tool.required_keys present in request.api_keys
        (missing keys → 400 error with list of missing keys)

      → Start timer
      → _instantiate_tool(tool.langchain_class, request.api_keys)
        → importlib.import_module(module_path)
        → getattr(module, class_name)
        → tool_instance = ToolClass(**mapped_api_keys)
      → await tool_instance.ainvoke(request.input)   # ainvoke — async-safe for ALL tools
      ← output = [{"title": "...", "url": "...", "snippet": "..."}]
      → Stop timer → latency_ms = 850

      → ToolRepository.update_test_result(
          tool_id, status="success",
          detail={"output": output, "latency_ms": 850, "tested_at": "..."},
          tested_at=now()
        )
        → SQL: UPDATE tools SET test_status='success', test_detail='{...}',
                last_tested_at=now() WHERE id = tool_id

    ← Return ToolTestResponse(status="success", output=[...], error=None, latency_ms=850)
  ← Return 200: {"status": "success", "output": [...], "error": null, "latency_ms": 850}
```

---

## Flow 5: Tool Playground — Test a Tool (Failure Path — Bad API Key)

```
Client → POST /tools/{tool_id}/test
  Body: {
    "api_keys": {"TAVILY_API_KEY": "invalid-key"},
    "input": {"query": "test"}
  }

  → Router: authenticate, validate
    → ToolService.test_tool(tool_id, request)
      → Tool found, langchain_class valid, required_keys present
      → Start timer
      → _instantiate_tool(tool.langchain_class, request.api_keys)
      → await tool_instance.ainvoke(request.input)   # ainvoke — async-safe for ALL tools
      ← RAISES: Exception("401 Unauthorized — Invalid API key")
      → Stop timer → latency_ms = 120

      → Catch exception → extract error message
      → ToolRepository.update_test_result(
          tool_id, status="failed",
          detail={"error": "401 Unauthorized — Invalid API key", "latency_ms": 120},
          tested_at=now()
        )

    ← Return ToolTestResponse(status="failed", output=None, error="401 Unauthorized — Invalid API key", latency_ms=120)
  ← Return 200: {"status": "failed", "output": null, "error": "...", "latency_ms": 120}
```

---

## Flow 6: Tool Playground — Missing Required Keys

```
Client → POST /tools/{tool_id}/test
  Body: {
    "api_keys": {},
    "input": {"query": "test"}
  }

  → Router: authenticate, validate
    → ToolService.test_tool(tool_id, request)
      → Tool found: required_keys=["TAVILY_API_KEY"]
      → Validate: "TAVILY_API_KEY" not in request.api_keys
      → RAISE ValidationError: "Missing required API keys: TAVILY_API_KEY"
  ← Return 400: {"detail": "Missing required API keys: TAVILY_API_KEY"}
```

---

## Flow 7: User Decision — Attach Tool to Agent

```
After successful test, user decides to use the tool in their agent:

Client → PATCH /agents/{agent_id}  (existing endpoint, NO changes needed)
  Body: {
    "config": {
      "tools": ["tavily_search", "wikipedia"]   ← add tested tool by name
    }
  }

  → Existing agent update flow (unchanged)
  → Creates new AgentVersion with updated config
  → Tool name references are resolved at runtime by RunnerService

Note: This flow is UNCHANGED. The playground just helps users make informed
      decisions about which tools to include. The agent config contract
      (tools as list of name strings) remains the same.
```

---

## Flow Summary

| # | Flow | Trigger | Layers Touched |
|---|------|---------|----------------|
| 1 | Tool Seeding | App startup | Service → Repository → DB |
| 2 | Browse Categories | GET /tools/categories | API → Service → Repository → DB |
| 3 | Browse by Category | GET /tools?category=X | API → Service → Repository → DB |
| 4 | Playground (success) | POST /tools/{id}/test | API → Service → LangChain → External API → Repository → DB |
| 5 | Playground (failure) | POST /tools/{id}/test | API → Service → LangChain → External API (error) → Repository → DB |
| 6 | Missing Keys | POST /tools/{id}/test | API → Service (validation) |
| 7 | Attach to Agent | PATCH /agents/{id} | Existing flow (unchanged) |
