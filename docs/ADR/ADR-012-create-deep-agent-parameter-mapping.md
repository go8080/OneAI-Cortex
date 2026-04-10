## ADR-012: Full `create_deep_agent()` Parameter Mapping Strategy

**Date:** 2026-04-10
**Status:** accepted
**Phase:** Plan (from gap analysis review)

### Context

The DeepAgents `create_deep_agent()` function accepts 17 parameters that control agent behavior:
model, tools, system_prompt, middleware, subagents, skills, memory, response_format, context_schema,
checkpointer, store, backend, interrupt_on, debug, name, cache.

Our initial `AgentConfig` only covered ~6 of these (model, system_prompt, tools, subagents, temperature,
max_tokens). This left critical functionality inaccessible: middleware toggling, backend selection,
human-in-the-loop, structured output, checkpointing, and model resolution.

### Decision

Map all 17 parameters through `AgentConfig` using framework-agnostic names. The DeepAgents adapter
translates `AgentConfig` fields into the exact `create_deep_agent()` call. Specifically:

**Mapped in v0.1:**
- `model` → `model` (via `resolve_model()` — "provider:model" string format)
- `system_prompt` → `system_prompt`
- `tools` → `tools` (resolved from tool registry to BaseTool instances)
- `subagents` → `subagents` (SyncSubAgentConfig → SubAgent, AsyncSubAgentConfig → AsyncSubAgent)
- `middleware` → `middleware` (MiddlewareConfig toggles → ordered middleware list)
- `response_format` → `response_format` (JSON schema passthrough)
- `backend` → `backend` (BackendConfig → StateBackend or FilesystemBackend)
- `interrupt_on` → `interrupt_on` (dict passthrough, enables HumanInTheLoopMiddleware)
- `checkpointing_enabled` → `checkpointer` (True → AsyncSqliteSaver, False → None)
- `debug` → `debug`
- `name` → `name`
- `temperature`, `max_tokens` → applied to model instance during resolution
- `recursion_limit` → set on CompiledStateGraph after creation

**Deferred to v0.2:**
- `skills` → Skills middleware not in v0.1
- `memory` → Memory/AGENTS.md not in v0.1
- `store` → StoreBackend not in v0.1
- `cache` → Uses prompt caching defaults
- `context_schema` → Advanced typing feature

**Subagent types supported:**
- SubAgent (sync, in-process) — inherits parent model/tools/interrupt_on if not specified
- AsyncSubAgent (remote, non-blocking) — requires graph_id, url, headers
- CompiledSubAgent — deferred to v0.2

### Consequences

**Positive:**
- Users can configure every meaningful aspect of agent behavior through the API
- Framework-agnostic naming means future adapters follow the same config shape
- Escape hatch (`framework_specific`) handles unforeseen needs

**Negative:**
- AgentConfig is larger — more fields to validate
- Some DeepAgents concepts (middleware ordering) are simplified (toggle only, no reorder)

**Neutral:**
- Deferred parameters can be added in v0.2 without breaking the existing config schema (JSONB)

### Alternatives Rejected

| Alternative | Why Rejected |
|-------------|-------------|
| Pass-through dict (no typed config) | No validation, no documentation, no IDE support |
| Map only "safe" parameters | Leaves users unable to configure middleware, backends, HITL |
| Expose framework-native types in API | Leaky abstraction — violates adapter protocol design (ADR-003) |

### Validation
- Every AgentConfig field that maps to a `create_deep_agent()` param has an integration test
- Config round-trip test: create via API → read back → verify all fields preserved
- Invalid model string returns clear validation error (not a framework crash)
