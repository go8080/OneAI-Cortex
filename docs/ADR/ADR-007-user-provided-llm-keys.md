## ADR-007: User-Provided LLM API Keys

**Date:** 2026-04-10
**Status:** Accepted
**Phase:** Plan

### Context

Agents need LLM API keys (Anthropic, OpenAI, Google, etc.) to execute. The platform could either proxy all LLM calls with platform-owned keys (and bill users) or require users to provide their own keys.

### Decision

Users provide their own LLM API keys. Keys are passed per-request (not stored server-side) or stored encrypted in user settings (future). For v0.1, keys are provided in the run request or via environment variables for hosted deployments.

### Consequences

**Positive:**
- No billing/payment infrastructure needed
- No platform liability for LLM costs
- Users control their own rate limits and usage
- Simpler architecture — platform doesn't proxy LLM calls

**Negative:**
- Users must manage their own API keys
- Platform can't optimize (batch, cache) LLM calls across users
- Must handle "invalid key" errors gracefully

**Neutral:**
- Can add platform-managed keys as a premium feature later

### Alternatives Rejected

| Alternative | Why Rejected |
|-------------|-------------|
| Platform-managed keys with billing | Requires payment infrastructure, usage tracking, billing system — massive scope for v0.1 |
| Stored encrypted keys | Security risk if DB is compromised; deferred to v0.2 with proper key vault |

### Validation

- Agent execution fails with clear error message when invalid API key is provided
- No LLM API keys are ever logged or persisted in plaintext
