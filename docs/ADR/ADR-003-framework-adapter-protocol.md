## ADR-003: Framework Adapter Protocol Design

**Date:** 2026-04-10
**Status:** Accepted
**Phase:** Plan

### Context

OneAI-Cortex must support multiple agent frameworks starting with DeepAgents. The platform needs an abstraction layer that decouples core modules (Builder, Runner, Evaluator, Deployer) from any specific framework's internals.

### Decision

Define a `FrameworkAdapter` Protocol using Python's `typing.Protocol` with methods modeled around **user-facing concepts** (validate config, create runtime, execute, generate SDK), not framework internals (middleware, backends, LangGraph state).

Key design rules:
- No LangChain/LangGraph/DeepAgents types cross the adapter boundary
- The adapter returns platform-defined types: `AgentConfig`, `AgentRuntime`, `AgentEvent`, `SDKPackage`
- Framework-specific settings use a `framework_specific: dict` escape hatch in `AgentConfig`
- Each adapter registers itself in an `AdapterRegistry` keyed by framework name

### Consequences

**Positive:**
- Adding a new framework = implementing 6 methods in a new adapter class
- Service layer code never changes when a new framework is added
- Testing is straightforward — mock the protocol, not framework internals

**Negative:**
- Some framework-specific power features may be hard to expose through the generic interface
- The `framework_specific` escape hatch could become a dumping ground if not reviewed

**Neutral:**
- `AgentRuntime._internal` holds the framework's native object (opaque to the platform)

### Alternatives Rejected

| Alternative | Why Rejected |
|-------------|-------------|
| Direct DeepAgents integration (no adapter) | Locks platform to one framework; every service would import DeepAgents |
| Plugin system with dynamic loading | Over-engineering for v0.1; adapter registry is simpler and sufficient |
| REST API per framework (sidecar model) | Adds network hops, operational complexity, harder to stream |

### Validation

- When CrewAI adapter is added (future), no changes required to AgentService, RunnerService, EvaluatorService, or DeployerService
- Framework adapter boundary check: `grep -r "from deepagents" app/services/` returns zero results
