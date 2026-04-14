# Phase 1 — Recommendation

**Date:** 2026-04-14
**Status:** Accepted
**Project:** OneAI-Cortex
**Feature:** Google Connected Services — OAuth Token Management & Agent Integration

---

## Selected Approach

**Approach B — Cortex-Owned Connected Services**

## Rationale

Approach B wins the decision matrix (113 vs 85 vs 72) because it co-locates token management with token consumers, eliminates cross-service latency, and provides a clean extension path for future providers:

1. **Agents consume tokens — Cortex manages them.** When an agent tool needs a Google access token, the lookup is a local DB query + a single HTTP call to Google's token endpoint. No intermediate service hop.

2. **Provider-agnostic data model.** A single `connected_services` table with columns (`provider`, `refresh_token`, `granted_scopes`, `status`) supports Google, Slack, GitHub, and future providers without schema changes per provider.

3. **Existing infrastructure.** Cortex already has Fernet encryption (`SecretEncryption`, ADR-011), async HTTP (`httpx`), and the layered architecture (model → repo → service → API) to support this cleanly.

4. **Clean domain boundary.** Authentication (who are you?) stays in OneAI-Auth. Authorization for agent capabilities (what can your agents do?) lives in Cortex. Connected services are agent capabilities — they enable agents to act on behalf of users.

5. **No external blockers.** Auth doesn't need any changes. Frontend calls Cortex for connected services, same as it does for agents, tools, and MCP servers.

## Key Risks

### Risk 1: Cortex scope expands beyond "agent platform"
Cortex now handles OAuth code exchange, which is traditionally an "auth service" concern.

**Mitigation:** Isolate all OAuth logic in dedicated modules — `infrastructure/google_oauth.py` for the HTTP client, `services/connected_service.py` for business logic. The module boundary is clean enough to extract into a separate service later if needed.

### Risk 2: Google refresh token revocation
Users can revoke app access at `myaccount.google.com/permissions`, invalidating the stored refresh token without notifying Cortex.

**Mitigation:** When token refresh fails with a `400 invalid_grant` response from Google, update the connection status to `revoked` and return a clear error to the agent/frontend. The user must re-connect via the Connected Services page.

### Risk 3: Google returns refresh_token only on first consent
Google's OAuth only returns `refresh_token` when the user has not previously consented, or when `prompt=consent` is explicitly set.

**Mitigation:** Always include `prompt=consent` in the OAuth URL. This forces a fresh consent screen and guarantees a `refresh_token` in every code exchange.

## What We're Giving Up

- **"Auth owns all auth" purity** — Auth no longer centralizes all OAuth flows. But connected services are capability-authorization, not identity-authentication, making Cortex the correct owner.
- **Single token store** — Tokens for Google services live in Cortex's DB, not Auth's `users` table. This is acceptable because Auth never needs these tokens — only agents do.

---

## Rejected Alternatives

| Approach | Why Rejected | Notes |
|----------|-------------|-------|
| A — Auth-Delegated | Cross-service latency on every agent token call. Blocked on Auth implementing 4 new endpoints. `users` table doesn't scale to N providers. | Could revisit if a central credential vault service is built |
| C — Hybrid | Maximum complexity (3 systems), cache invalidation risk, two points of failure for agent execution | Over-engineered; Approach B is simpler and faster with equal or better extensibility |

---

## ADRs Required

| ADR | Title | Scope |
|-----|-------|-------|
| ADR-018 | Cortex-owned connected services over Auth-delegated | Service ownership decision |
| ADR-019 | Provider-agnostic connected services data model | Table design for multi-provider extensibility |

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
