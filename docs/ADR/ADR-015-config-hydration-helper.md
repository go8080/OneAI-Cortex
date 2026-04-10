## ADR-015: Private Config Hydration Helper in RunnerService

**Date:** 2026-04-10
**Status:** accepted
**Phase:** Plan (from Ideas phase — Idea B selected)

### Context

`RunnerService.run_session()` constructs `AgentConfig` with only 10 of 17 fields.
Six fields — `subagents`, `middleware`, `interrupt_on`, `backend`, `response_format`,
`framework_specific` — are silently dropped. `resume_session()` is worse, passing only
`name` and `model` (2 of 17 fields).

The adapter layer (`DeepAgentsAdapter.create_runtime()`) already consumes all 17 fields
correctly. The gap is entirely in the service → adapter handoff.

This means sub-agents, HITL interrupts, custom backends, structured output, and
middleware toggles are broken for all users despite being configurable in the API.

### Decision

Add a private `_build_agent_config(config_dict, agent_name, encryption)` function in
`app/services/runner.py` that hydrates a complete `AgentConfig` from the stored version
config dict. Both `run_session()` and `resume_session()` call this helper.

The helper handles:
- Model normalization (reuses existing `_normalize_model()`)
- Nested dataclass construction (`MiddlewareConfig`, `BackendConfig`)
- Subagent list parsing (sync vs async detection, async header decryption)
- `interrupt_on`, `response_format`, `framework_specific` passthrough
- Graceful fallback to `AgentConfig` defaults for missing fields

### Consequences

**Positive:**
- All 17 AgentConfig fields reach the adapter — sub-agents, HITL, backends work
- Single source of truth for config hydration (no duplication between methods)
- Helper is independently unit-testable
- Decryption stays in the service layer (layer cake compliance)

**Negative:**
- One new ~40-line function in runner.py
- Subagent parsing adds dict-to-dataclass mapping complexity

**Neutral:**
- `user_api_keys` decryption stays separate (passed as second arg to `create_runtime`)
- Evaluator service still uses minimal AgentConfig (out of scope — it only needs name/model/prompt for scoring)

### Alternatives Rejected

| Alternative | Why Rejected |
|-------------|-------------|
| Inline hydration in each method | Duplication between run_session and resume_session; bloated methods; subagent parsing too complex for inline |
| `AgentConfig.from_stored_config()` classmethod | Puts decryption in the types layer — types should be passive data carriers, not know about `SecretEncryption` |

### Validation
- Unit tests for `_build_agent_config()` covering: all scalar fields, MiddlewareConfig, BackendConfig, sync/async subagents, encrypted header decryption, missing fields default gracefully
- Integration test: create agent with interrupt_on config, verify runtime receives it
- All 171 existing tests continue to pass
