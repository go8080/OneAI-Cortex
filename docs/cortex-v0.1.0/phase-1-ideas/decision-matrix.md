# Phase 1 — Decision Matrix

**Date:** 2026-04-10
**Project:** OneAI-Cortex
**Weight Rationale:** Greenfield open-source project → raised Extensibility and Alignment weights; added Contributor Friendliness as a first-class criterion.

---

## Weighted Scoring

| Criterion              | Weight | A (Thin Wrapper) | B (Modular Monolith) | C (Microservices) |
|------------------------|--------|-------------------|----------------------|-------------------|
| Simplicity             | 3      | 9/10              | 6/10                 | 3/10              |
| Extensibility          | 3      | 3/10              | 8/10                 | 9/10              |
| Time to deliver        | 3      | 9/10              | 6/10                 | 2/10              |
| Risk                   | 2      | 5/10              | 7/10                 | 4/10              |
| Alignment (arch.)      | 2      | 4/10              | 9/10                 | 7/10              |
| Contributor Friendly   | 2      | 7/10              | 8/10                 | 3/10              |
| **Weighted Total**     |        | **91**            | **106**              | **68**            |

---

## Score Breakdown

### Idea A — Thin Wrapper: 91
- Wins on Simplicity (27) and Time to deliver (27)
- Loses badly on Extensibility (9) — framework lock-in is the killer

### Idea B — Modular Monolith: 106 (WINNER)
- Strong across the board, no critical weakness
- Extensibility (24) + Alignment (18) + Contributor Friendly (16) carry it
- Moderate on Time to deliver (18) — acceptable for a long-term platform

### Idea C — Microservices: 68
- Extensibility (27) is its only strong point
- Crushed by Time to deliver (6), Simplicity (9), Contributor Friendly (6)
- The architecture can be extracted from B later if scale demands it
