## ADR-002: Modular Monolith Over Microservices

**Date:** 2026-04-10
**Status:** Accepted
**Phase:** Plan (from Ideas phase recommendation)

### Context

A platform with distinct domains (Builder, Runner, Evaluator, Deployer) could be structured as independent microservices. This would provide maximum scalability and independent deployment. However, OneAI-Cortex is an open-source project starting with zero users and a single developer/small team.

### Decision

Start as a modular monolith with clear module boundaries. Each domain (Builder, Runner, Evaluator, Deployer) is a module within the monolith, not a separate service. Module boundaries are enforced via code conventions (separate service classes, repository classes, and API routers per domain).

### Consequences

**Positive:**
- Single `docker-compose up` for contributors — lower barrier to entry
- No distributed system complexity (no message brokers, service mesh, distributed tracing)
- Faster development cycles — changes across domains in a single commit
- Can extract microservices later along natural module boundaries

**Negative:**
- All domains share the same deployment unit — a bug in one can affect others
- Horizontal scaling is all-or-nothing (can't scale Runner independently of Builder)

**Neutral:**
- Module boundaries must be enforced by discipline, not by service isolation

### Alternatives Rejected

| Alternative | Why Rejected |
|-------------|-------------|
| Microservices from day one | XL effort, operational overhead (Kubernetes, message broker, distributed tracing), hostile to open-source contributors who need to run locally |

### Validation

- Module boundaries remain clean: no direct imports between domain modules (Builder doesn't import Runner internals)
- When any module grows beyond manageable size, extraction to a standalone service should require only interface wiring, not logic changes
