## ADR-006: Immutable Agent Versioning

**Date:** 2026-04-10
**Status:** Accepted
**Phase:** Plan

### Context

Users will iterate on agent configurations over time. The platform needs to track changes, support rollback, and ensure that deployed agents and evaluation results reference a specific, unchanging configuration.

### Decision

Every agent update creates a new immutable version in `agent_versions`. The `agents` table tracks `current_version` (pointer to latest). Versions are never modified after creation.

- `PUT /agents/{id}` → creates version N+1, updates `current_version`
- Deployments pin to a specific version number
- Evaluation runs record which version was tested
- Sessions record which version was used

### Consequences

**Positive:**
- Full audit trail of every configuration change
- Deployments are stable — updating the agent doesn't break live deployments
- Evaluation results are reproducible — tied to exact config
- Rollback = change `current_version` pointer, no data loss

**Negative:**
- Storage grows with every edit (mitigated: JSONB configs are small, ~1-5KB each)
- Listing all versions of a heavily-edited agent could be long (mitigated: pagination)

**Neutral:**
- Version numbers are per-agent integers (1, 2, 3...), not global

### Alternatives Rejected

| Alternative | Why Rejected |
|-------------|-------------|
| Mutable config (overwrite in place) | Breaks deployed agents; no audit trail; evaluations become unreproducible |
| Git-based versioning | Over-engineering; requires Git infrastructure; simple integer versions are sufficient for config snapshots |
| Event sourcing | Complexity disproportionate to value for configuration changes |

### Validation

- Deployed agent continues serving version N after agent is updated to version N+1
- Evaluation results show correct version number when queried historically
