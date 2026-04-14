## ADR-018: Cortex-Owned Connected Services Over Auth-Delegated

**Date:** 2026-04-14
**Status:** Accepted
**Phase:** Plan (from Ideas phase recommendation — Approach B)

### Context

AI agents in OneAI-Cortex need to call Google APIs (Gmail, Calendar, Drive) on behalf of users. This requires storing OAuth refresh tokens and issuing fresh access tokens on demand during agent execution.

The platform has two backend services: **OneAI-Auth** (user authentication, JWT issuance) and **OneAI-Cortex** (agent platform, tool execution). The decision is which service should own the Google OAuth token lifecycle.

Three approaches were evaluated:
- **A: Auth-Delegated** — Auth handles OAuth, Cortex calls Auth's internal endpoint for tokens
- **B: Cortex-Owned** — Cortex handles the entire OAuth lifecycle
- **C: Hybrid** — Cortex API surface, Auth token store, Redis cache

### Decision

**Cortex owns the entire connected services lifecycle** — OAuth code exchange, encrypted token storage, scope management, and fresh token issuance.

Key factors:
1. **Zero cross-service latency** — Agent tools resolve tokens from Cortex's local DB + a single call to Google. No intermediate service hop to Auth.
2. **Provider-agnostic model** — A single `connected_services` table supports Google, Slack, GitHub, and future providers without per-provider schema changes.
3. **Natural domain boundary** — Authentication (who are you?) belongs in Auth. Authorization for agent capabilities (what can your agents do?) belongs in Cortex. Connected services enable agent capabilities.
4. **No external blockers** — Auth doesn't need any changes. Cortex has all required infrastructure (Fernet encryption, httpx, FastAPI).

### Consequences

**Positive:**
- Agent token resolution is a local operation (DB read + Google HTTP call)
- Single service to deploy and debug for connected services features
- Clean extension point for future providers

**Negative:**
- Cortex takes on OAuth code exchange responsibility (broader scope than "agent platform")
- If a central credential vault is built later, connected services logic must migrate

**Neutral:**
- Auth service is unaware of connected services — no coupling, no coordination needed
- Frontend calls Cortex for connected services, same pattern as agents/tools/MCP servers

### Alternatives Rejected

| Alternative | Why Rejected |
|-------------|-------------|
| A — Auth-Delegated | Cross-service HTTP call per agent token request adds latency. Auth's `users` table doesn't scale to N providers (columns per provider). Blocked on Auth implementing 4 new endpoints. |
| C — Hybrid (Cortex API + Auth store + Redis cache) | Maximum complexity: 3 systems, proxy logic, cache invalidation. Two points of failure for every agent Google API call. Over-engineered for current needs. |

### Validation

How we'll know this decision was correct:
- Agent tools can resolve Google access tokens in <100ms (local DB + Google HTTP)
- Adding a second provider (e.g., Slack) requires only: new infrastructure client + service methods — no schema changes, no new table
- No cross-service deployment coordination needed for connected services features
