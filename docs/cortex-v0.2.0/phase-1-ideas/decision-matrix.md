# Phase 1 — Decision Matrix

**Date:** 2026-04-10
**Project:** OneAI-Cortex
**Feature:** Categorized Pre-Built Tool Catalog with Tool Playground
**Weight Rationale:** Extending existing architecture → raised Alignment and Simplicity weights. Feature involves real tool execution with user input → raised Risk weight.

---

## Weighted Scoring

| Criterion          | Weight | A (Category Column) | B (Catalog Table) | C (Enum + Seed + Playground) |
|--------------------|--------|---------------------|--------------------|------------------------------|
| Simplicity         | 3      | 7/10                | 3/10               | 8/10                         |
| Extensibility      | 2      | 4/10                | 9/10               | 7/10                         |
| Time to deliver    | 3      | 7/10                | 3/10               | 7/10                         |
| Risk               | 3      | 5/10                | 5/10               | 7/10                         |
| Alignment (arch.)  | 2      | 7/10                | 4/10               | 9/10                         |
| Testability        | 2      | 5/10                | 7/10               | 8/10                         |
| Performance        | 1      | 8/10                | 6/10               | 7/10                         |
| **Weighted Total** |        | **93**              | **73**             | **118**                      |

---

## Score Breakdown

### Idea A — Category Column: 93
- Strong on Simplicity (21) and Time to deliver (21)
- Weak on Extensibility (8) — no structured seeder, no tool metadata
- Risk (15) — no `required_keys` metadata means users don't know what keys to provide
- Testability (10) — no metadata in seeder means test endpoint can't guide users

### Idea B — Catalog Table: 73
- Wins on Extensibility (18) — rich catalog model with metadata
- Crushed by Simplicity (9) and Time to deliver (9) — two new tables is excessive
- Alignment (8) — introduces divergent patterns from existing tool system
- Risk (15) — dual-source tool resolution increases runtime failure surface

### Idea C — Enum + Seed + Playground: 118 (WINNER)
- Strong across all criteria with no critical weakness
- **Risk (21)** — tool metadata (`required_keys`, `input_schema`) guides users to provide correct inputs; natural provider errors handle the rest
- **Alignment (18)** — extends existing model and MCP server testing pattern
- **Testability (16)** — seeder metadata makes the catalog self-documenting for the playground
- Simplicity (24) stays high — column additions, not new tables
