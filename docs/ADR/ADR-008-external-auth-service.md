## ADR-008: External Auth via OneAI-Auth Service

**Date:** 2026-04-10
**Status:** Accepted
**Phase:** Plan

### Context

OneAI-Cortex needs user authentication and identity management. A separate service, **OneAI-Auth** (`OneAI-Auth/`), already exists with production-grade capabilities:

- Email/password registration + login (Argon2 hashing)
- JWT tokens (HS256, 60-min access, 30-day refresh with rotation)
- OAuth: Google, Microsoft, LinkedIn
- User profiles (bio, skills, interests, geolocation)
- Rate limiting, structured logging, soft deletes
- FastAPI + async PostgreSQL + Alembic

Building auth into Cortex would duplicate this work.

### Decision

Cortex delegates all authentication to OneAI-Auth as an external service:

1. **Token validation is local** — Cortex shares `JWT_SECRET_KEY` with OneAI-Auth and decodes JWTs locally using `python-jose`. No HTTP call to Auth on every request.

2. **User identity is opaque** — The `sub` claim (UUID) from the JWT is the user identifier for all Cortex resources. No `users` table in Cortex DB.

3. **Profile enrichment is on-demand** — When display name or avatar is needed, Cortex calls OneAI-Auth's `/api/v1/users/profile` via `httpx` async client.

4. **Cortex-local API keys** — Cortex manages its own API keys (stored in Cortex DB) for programmatic access to hosted agents and the Cortex API. These are an alternative to JWT for machine-to-machine scenarios.

5. **Dual auth support** — The `get_current_user()` FastAPI dependency accepts either `Bearer <jwt>` (from OneAI-Auth) or `ApiKey <key>` (from Cortex) in the Authorization header.

### Consequences

**Positive:**
- Zero auth code duplication — registration, login, OAuth, token refresh all handled by Auth
- Cortex codebase stays focused on agent lifecycle, not user management
- Auth can evolve independently (add Apple Sign-In, SAML, etc.) without Cortex changes
- Stateless JWT validation scales horizontally without Auth being a bottleneck

**Negative:**
- Shared `JWT_SECRET_KEY` is a coupling point — must be kept in sync
- Profile lookups add network latency (mitigated: cache with TTL)
- If Auth is down, new logins fail (but existing JWT holders can still use Cortex)
- No foreign key constraints on `user_id` — orphaned data possible if user deleted in Auth

**Neutral:**
- Docker Compose includes OneAI-Auth as a dependency service for local dev

### Alternatives Rejected

| Alternative | Why Rejected |
|-------------|-------------|
| Build auth into Cortex | Duplicates existing production-grade work; couples auth evolution to Cortex releases |
| Use Auth as a token-validation proxy (HTTP call per request) | Adds latency and creates Auth as a single point of failure; HS256 shared secret enables local validation |
| Shared database between Auth and Cortex | Tight coupling; migration conflicts; violates service boundaries |

### Validation

- Cortex can validate a JWT issued by OneAI-Auth without any HTTP call to Auth
- `grep -r "from app.models.user" app/` returns zero results (no User model in Cortex)
- Health check endpoint reports Auth connectivity status for monitoring
- If Auth is unreachable, existing authenticated users can still operate via cached JWTs
