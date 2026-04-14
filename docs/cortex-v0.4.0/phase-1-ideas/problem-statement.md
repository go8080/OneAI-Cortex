# Phase 1 — Problem Statement

**Date:** 2026-04-14
**Status:** Accepted
**Project:** OneAI-Cortex
**Feature:** Google Connected Services — OAuth Token Management & Agent Integration

---

## Problem Definition

**What:** AI agents in OneAI-Cortex cannot access users' Google services (Gmail, Google Calendar, Google Drive). There is no mechanism to:

1. **Accept OAuth authorization codes** — The frontend (OneAI-UI) has a Connected Services page with toggles for Gmail, Calendar, and Drive, but no backend to exchange authorization codes for tokens.

2. **Store encrypted refresh tokens** — When a user completes Google OAuth consent, the resulting `refresh_token` and granted scopes need to be persisted securely in Cortex's database with field-level encryption.

3. **Issue fresh access tokens on demand** — During agent execution, when a tool like `gmail_send` or `calendar_create` needs to call a Google API, the platform must resolve a fresh short-lived `access_token` from the stored `refresh_token` — transparently, without user intervention.

4. **Manage connection lifecycle** — Users need to view connected services, update permissions (re-consent with different scopes), and disconnect services.

**Who:**
- End users who want agents to interact with their Google services on their behalf
- Agent tools (Gmail, Calendar, Drive) that need Google API access tokens at runtime
- Frontend team building the Connected Services UI against Cortex APIs

**Why now:** The OneAI-UI already has a Connected Services page (static mockup in `src/pages/ConnectedServices.tsx`) with scope toggles and a "Connect" button. The Google Identity Services (GIS) library is loaded. The only missing piece is the backend that accepts the authorization code and manages the token lifecycle.

**Constraints:**
- OneAI-Auth handles user authentication (login/register, JWT issuance) — it does NOT handle Google API tokens for agent use
- Cortex already has Fernet encryption infrastructure (`SecretEncryption`) for secrets at rest (ADR-011)
- Google OAuth 2.0 Authorization Code flow with `access_type=offline` is required to obtain `refresh_token`
- Google only returns `refresh_token` on first consent or when `prompt=consent` is forced
- The design must support adding future providers (Slack, GitHub, Notion) without structural changes
- UI calls Cortex for agent/tool management — Connected Services should follow the same pattern

**Success looks like:**
- User toggles Gmail + Calendar on Connected Services page, clicks "Connect", completes Google OAuth consent
- Cortex exchanges the authorization code for tokens, stores encrypted `refresh_token` and `granted_scopes`
- UI shows "Connected" badge with the user's Google email and enabled scopes
- During agent execution, a Gmail tool calls `GET /connected-services/google/token` and receives a fresh `access_token`
- User can disconnect Google, revoking Cortex's stored tokens
- Architecture supports adding Slack/GitHub providers in future versions
