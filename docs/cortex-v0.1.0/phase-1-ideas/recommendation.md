# Phase 1 — Recommendation

**Date:** 2026-04-10
**Status:** Accepted
**Project:** OneAI-Cortex

---

## Selected Approach

**Idea B — API-First Modular Monolith**

## Rationale

Idea B wins the decision matrix (106 vs 91 vs 68) because it balances shipping speed with long-term extensibility:

1. **Framework Adapter Layer** — The adapter interface means adding CrewAI, AutoGen, or any future framework is a module addition, not a platform rewrite
2. **Programmatic Control** — Using `create_deep_agent()` directly gives full control over agent lifecycle (streaming, checkpointing, persistence) without shelling out to CLI
3. **Contributor Experience** — Single `docker-compose up` to get the full stack running, single codebase to understand
4. **Multi-tenancy Ready** — DB-backed agent storage naturally supports multiple users and organizations from day one
5. **Modular → Micro** — Clear module boundaries mean we can extract microservices later if scale demands, without rewriting

## Key Risk

**Framework adapter abstraction** — If designed too tightly around DeepAgents' concepts (middleware, backends, LangGraph state), the interface won't fit other frameworks.

## Mitigation

Design the adapter interface around **user-facing concepts** (agent config, execution request, execution result) not framework internals. DeepAgents-specific concepts (middleware stack, LangGraph compiled graph) stay encapsulated inside the DeepAgents adapter.

## What We're Giving Up

- The speed of Idea A (could ship in days vs weeks)
- But Idea A's tight coupling to DeepAgents file conventions would force a rewrite when adding framework #2, costing more in the long run

---

## Rejected Alternatives

| Approach | Why Rejected | ADR Reference |
|----------|-------------|---------------|
| A — Thin Wrapper | Can't extend to other frameworks without rewrite; no structured evaluation; limited programmatic control | ADR-001 |
| C — Microservices | Premature complexity for 0-user open-source project; can extract services from modular monolith later if needed | ADR-002 |

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
