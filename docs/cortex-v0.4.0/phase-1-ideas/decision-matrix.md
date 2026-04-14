# Phase 1 — Decision Matrix

**Date:** 2026-04-14
**Project:** OneAI-Cortex
**Feature:** Google Connected Services — OAuth Token Management & Agent Integration
**Weight Rationale:** Greenfield module with future provider extensibility → raised Extensibility and Alignment weights. New external integration (Google APIs) → raised Risk weight.

---

## Weighted Scoring

| Criterion          | Weight | A (Auth-Delegated) | B (Cortex-Owned) | C (Hybrid) |
|--------------------|--------|---------------------|-------------------|------------|
| Simplicity         | 3      | 6/10                | 8/10              | 4/10       |
| Extensibility      | 3      | 5/10                | 9/10              | 6/10       |
| Time to deliver    | 3      | 5/10                | 7/10              | 4/10       |
| Risk               | 2      | 7/10                | 6/10              | 5/10       |
| Alignment (arch.)  | 2      | 6/10                | 8/10              | 5/10       |
| Testability        | 1      | 6/10                | 8/10              | 5/10       |
| Performance        | 1      | 4/10                | 9/10              | 6/10       |
| **Weighted Total** |        | **85**              | **113**           | **72**     |

---

## Score Breakdown

### Approach A — Auth-Delegated: 85
- Decent Simplicity (18) — less Cortex code, but cross-service coordination adds complexity
- Weak Extensibility (15) — `users` table grows columns per provider; doesn't scale
- Weak Time to deliver (15) — blocked on Auth implementing 4 new endpoints first
- Good Risk (14) — Auth is a known service, but cross-service dependency adds failure modes
- **Key weakness:** Every agent Google API call requires a network hop to Auth

### Approach B — Cortex-Owned: 113 (WINNER)
- Strong Simplicity (24) — single service, no proxies, no cross-service coordination
- Wins Extensibility (27) — provider-agnostic table design, same schema for Google/Slack/GitHub
- Good Time to deliver (21) — no external blockers; Auth changes not needed
- Moderate Risk (12) — Cortex takes on new OAuth responsibility, but isolated in its own module
- Strong Performance (9) — zero network hop for token retrieval at agent execution time
- **Key strength:** Provider-agnostic model + zero-latency token resolution

### Approach C — Hybrid: 72
- Worst Simplicity (12) — three systems (Cortex + Auth + Redis), proxy logic, cache invalidation
- Moderate Extensibility (18) — provider-agnostic API surface, but Auth storage is still per-column
- Worst Time to deliver (12) — requires changes to both services + Redis caching layer
- Weak Risk (10) — cache invalidation bugs, two points of failure, proxy failure modes
- **Key weakness:** Maximum complexity for marginal benefit
