# Phase 1 — Recommendation

**Date:** 2026-04-10
**Status:** Accepted
**Project:** OneAI-Cortex
**Feature:** Categorized Pre-Built Tool Catalog with Tool Playground

---

## Selected Approach

**Idea C — Enum + Seed + Playground (Structured Extension)**

## Rationale

Idea C wins the decision matrix (118 vs 93 vs 73) because it delivers a simple, user-driven tool testing experience without over-engineering:

1. **Existing Model Extension** — Adding `category`, `test_status`, `last_tested_at`, and `test_detail` (JSONB) to the Tool model reuses the existing table
2. **Tool Playground — Try Before You Use** — The test endpoint is straightforward:
   - User provides their API keys + input query/parameters
   - Tool executes and returns the actual output
   - User sees the real results and decides whether to use the tool in their agent
   - No artificial validation layers — the tool execution itself is the test
3. **Natural Error Handling** — If the API key is wrong, the provider returns 401. If input is bad, the tool says what it expected. These errors are more informative than any custom validation we'd write
4. **Tool Metadata in Seeder** — Each tool entry includes `required_keys` (what API keys to provide) and `input_schema` (what query/parameters the tool accepts), so the API can tell users exactly what they need
5. **Declarative Seeder** — A Python dict mapping `{category: [tool_definitions]}` is reviewable, testable, and includes all metadata needed for the playground
6. **Built-in Distinction** — `tool_type` already separates `builtin` from `custom`

## The Playground Flow

```
User browses: GET /tools?category=search
    → Sees: TavilySearch, GoogleSearch, BraveSearch, ...
    → Picks TavilySearch
    → Sees required_keys: ["TAVILY_API_KEY"], input_schema: {"query": "string"}

User tests:  POST /tools/{id}/test
    Body: {
      "api_keys": {"TAVILY_API_KEY": "tvly-abc123"},
      "input": {"query": "latest AI agent frameworks 2026"}
    }

    → Response: {
        "status": "success",
        "output": [
          {"title": "...", "url": "...", "snippet": "..."},
          ...
        ],
        "latency_ms": 850
      }

    OR on failure:
    → Response: {
        "status": "failed",
        "error": "401 Unauthorized — Invalid API key for Tavily",
        "latency_ms": 120
      }

User decides: "Output looks good → attach to my agent"
    → Updates agent config: {"tools": ["tavily_search", ...]}
```

## Key Risks

### Risk 1: Seeder data accuracy
Mapping 196+ LangChain tools to 20 categories with metadata (`required_keys`, `input_schema`) requires careful curation.

**Mitigation:** Declarative mapping dict organized by category, unit tested for completeness and valid enum values. Tool metadata derived from LangChain tool class signatures.

### Risk 2: Tool constructor variation
Each LangChain tool has a different constructor — different key names, different init patterns.

**Mitigation:** Seeder stores the LangChain class path + key mapping per tool. A factory function maps `api_keys` dict to the tool's constructor kwargs. Start with the most-used tools per category, expand coverage incrementally.

## What We're Giving Up

- Per-user test history (Idea B's approach) — we store only the latest test result globally
- Rich category metadata (icons, descriptions) — categories are enum values only
- These can be added later if a marketplace UI is needed

---

## Rejected Alternatives

| Approach | Why Rejected | ADR Reference |
|----------|-------------|---------------|
| A — Category Column | No structured seeder; no tool metadata (`required_keys`, `input_schema`); users don't know what to provide | ADR-016 |
| B — Catalog Table | Over-engineered — two new tables, dual-source tool resolution; premature for current needs | ADR-016 |

---

## Exit Criteria Status

```
[x] Problem statement written and specific
[x] 3 distinct approaches generated and documented
[x] Each approach has pros, cons, and effort estimate
[x] Decision matrix comparing approaches exists
[x] One approach recommended with explicit rationale
[x] Rejected alternatives documented with reasons
[x] Key risks identified with mitigations
[x] Recommendation reviewed by user — APPROVED
```

**Phase 1 COMPLETE — Ready to transition to Phase 2: Plan**
