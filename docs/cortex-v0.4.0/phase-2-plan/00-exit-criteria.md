# Phase 2 — Exit Criteria

**Date:** 2026-04-14
**Project:** OneAI-Cortex v0.4.0
**Feature:** Google Connected Services — OAuth Token Management & Agent Integration

---

## Exit Criteria Checklist

```
[x] Scope defined with explicit in/out boundaries (01-scope.md)
    - 15 in-scope deliverables across all layers
    - 8 explicitly out-of-scope items (agent tools, other providers, caching, frontend)
    - 6 assumptions documented
[x] Every affected layer identified with specific file changes (02-architecture.md)
    - Layer cake mapping: 8 layers impacted, 8 new files, 3 modified files
    - Full architecture diagram with component relationships
    - Key files index (new + modified)
[x] Interfaces between layers defined (03-interfaces.md)
    - 5 API contracts with request/response shapes and HTTP status codes
    - Service interface: 5 methods with signatures
    - Repository interface: 5 methods with signatures
    - Infrastructure interface: 3 methods with dataclass results
    - Schema definitions: 1 request + 4 response models
[x] Data flows traced end-to-end (04-data-flows.md)
    - 5 flows: connect, check status, get token, reconnect, disconnect
    - Each flow traced through all layers with token state transitions
    - Error paths documented (revoked token, missing connection)
[x] Data model documented (05-data-model.md)
    - New `connected_services` table with full SQL schema
    - SQLAlchemy ORM model definition
    - Encrypted field format (Fernet) documented
    - Scopes format rationale (space-separated per OAuth 2.0 spec)
    - Status lifecycle state machine with transitions
    - ERM showing relationship to users (via user_id, no FK)
[x] Dependencies mapped with status (06-dependencies-risks.md)
    - 12 dependencies: 8 met, 2 new config, 2 external setup
    - No new Python packages required
[x] Key risks identified with mitigations (06-dependencies-risks.md)
    - 8 risks documented with likelihood, impact, and mitigation
    - Error handling matrix: 8 scenarios with HTTP status codes
    - Security considerations table: 7 concerns with handling
[x] Design reviewed by user — APPROVED
[x] No open questions remain that block implementation
```

---

## ADR Index (v0.4.0)

| ADR | Title | Status |
|-----|-------|--------|
| ADR-018 | Cortex-owned connected services over Auth-delegated | Proposed |
| ADR-019 | Provider-agnostic connected services data model | Proposed |

---

## Phase 2 Status

**Phase 2 COMPLETE — Ready to proceed to Phase 3: Todo**
