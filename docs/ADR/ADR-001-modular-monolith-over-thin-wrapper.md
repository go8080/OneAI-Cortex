## ADR-001: Modular Monolith Over Thin CLI Wrapper

**Date:** 2026-04-10
**Status:** Accepted
**Phase:** Plan (from Ideas phase recommendation)

### Context

OneAI-Cortex needs an architecture that supports multiple agent frameworks starting with DeepAgents. The simplest approach would be a thin wrapper around the DeepAgents CLI (`deepagents dev`, `deepagents deploy`), treating each agent as a file directory. However, this locks the platform into DeepAgents' file conventions and CLI interface.

### Decision

Use an API-first modular monolith with a framework adapter layer. Agent configurations are stored in PostgreSQL, and frameworks are integrated programmatically (e.g., `create_deep_agent()`) rather than via CLI wrappers.

### Consequences

**Positive:**
- Framework-agnostic adapter interface enables adding new frameworks as modules
- Full programmatic control over agent lifecycle (streaming, checkpointing)
- Multi-tenancy via DB-backed storage from day one
- Single deployable unit simplifies operations

**Negative:**
- More upfront work than a thin wrapper
- Must design and maintain the adapter abstraction layer
- Risk of over-engineering the adapter if not kept focused on user-facing concepts

**Neutral:**
- Contributors work in one codebase (neither simpler nor harder, just different from microservices)

### Alternatives Rejected

| Alternative | Why Rejected |
|-------------|-------------|
| Thin CLI Wrapper (Idea A) | Can't extend to other frameworks without full rewrite; no structured evaluation; limited control |
| Microservices (Idea C) | Premature distributed complexity for a project with 0 users; can extract later |

### Validation

- When framework #2 (e.g., CrewAI) is added, it should require only a new adapter module — no changes to Builder, Runner, Evaluator, or Deployer modules
- Agent creation-to-execution latency should be under 2 seconds for simple agents
