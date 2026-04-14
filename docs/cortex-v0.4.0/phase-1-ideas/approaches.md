# Phase 1 — Evaluated Approaches

**Date:** 2026-04-14
**Status:** Evaluated
**Project:** OneAI-Cortex
**Feature:** Google Connected Services — OAuth Token Management & Agent Integration

---

## Approach A: Auth-Delegated (Cortex as Consumer)

**Description:** OAuth token management lives in OneAI-Auth. Cortex adds an infrastructure client to fetch tokens and implements Google agent tools.

**How it works:**
- Auth adds 4 new endpoints: `POST /auth/google/code`, `GET /auth/google/scopes`, `GET /auth/google/token`, `GET /auth/google/token/internal`
- Auth stores `google_refresh_token` and `google_scopes` on the `users` table
- Cortex adds `GoogleTokenClient` in infrastructure to call Auth's internal token endpoint
- Cortex implements Gmail/Calendar/Drive tools that use the token client
- UI calls Auth directly for OAuth flow, Cortex for agent execution

**Pros:**
- Separation of concerns — Auth owns all OAuth-related flows
- Less code in Cortex
- Single token store on the existing `users` table

**Cons:**
- Cross-service HTTP call for every agent Google API invocation (latency)
- Two services must be modified, tested, and deployed together
- Auth becomes a bottleneck for agent execution performance
- Auth's `users` table grows with provider-specific columns (doesn't scale to N providers)
- Harder to extend — adding Slack/GitHub means adding more columns to Auth's `users` table

**Effort:** M (Medium)
**Dependencies:** OneAI-Auth must implement 4 new endpoints first. Cortex blocked until Auth is ready.

---

## Approach B: Cortex-Owned Connected Services (SELECTED)

**Description:** Cortex owns the entire connected services lifecycle — OAuth code exchange, encrypted token storage, scope management, fresh token issuance, and agent tool integration.

**How it works:**
- New `connected_services` table in Cortex DB with provider-agnostic schema (provider, encrypted refresh token, scopes, status)
- New API endpoints: `POST /connected-services/google/connect`, `GET /connected-services`, `GET /connected-services/google/scopes`, `DELETE /connected-services/google`
- New infrastructure client `GoogleOAuthClient` calls Google's token endpoint directly (`https://oauth2.googleapis.com/token`)
- Cortex exchanges Google auth code, fetches user info, stores encrypted tokens
- Internal endpoint `GET /connected-services/google/token` resolves fresh access tokens for agent runtime
- Provider-agnostic model: same `connected_services` table supports Google, Slack, GitHub, etc.

**Pros:**
- Zero cross-service latency for token retrieval during agent execution
- Single deploy — no Auth changes required
- Natural home: agents consume tokens, so Cortex should manage them
- Provider-agnostic table design scales to N providers without schema changes
- Cortex already has Fernet encryption infrastructure (ADR-011)
- Clean separation: Auth = identity (who are you?), Cortex = capability (what can your agents do?)

**Cons:**
- Cortex takes on OAuth code exchange responsibility (broader scope)
- New dependency: `httpx` calls to Google's OAuth and UserInfo endpoints
- Slightly more code in Cortex (new model, repo, service, API, infrastructure client)

**Effort:** L (Large)
**Dependencies:** `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` environment variables. No new Python packages (`httpx` already in deps).

---

## Approach C: Hybrid (Cortex API, Auth Token Store)

**Description:** Cortex exposes the Connected Services API to the frontend, but proxies token operations to Auth for storage and refresh.

**How it works:**
- UI calls Cortex for all connected services operations (single API surface)
- Cortex proxies OAuth code exchange to Auth
- Auth stores tokens on `users` table
- Cortex caches access tokens in Redis with TTL matching `expires_in`
- Agent tools check Redis cache first, fallback to Auth's internal endpoint

**Pros:**
- Single API surface for the frontend (all calls go to Cortex)
- Redis caching reduces repeated calls to Auth for the same token
- Auth retains ownership of all OAuth credentials

**Cons:**
- Most complex: two services, proxy layer, Redis caching, cache invalidation
- Cache invalidation is hard — user disconnects in Auth, cached token in Redis still valid
- Still depends on Auth for token refresh (latency on cache miss)
- Two points of failure for every agent Google API call
- Over-engineered for current needs

**Effort:** L+ (Large-plus)
**Dependencies:** Auth endpoints + Redis caching logic + cache invalidation strategy
