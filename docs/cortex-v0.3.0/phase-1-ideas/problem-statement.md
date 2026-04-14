# Phase 1 — Problem Statement

**Date:** 2026-04-13
**Status:** Accepted
**Project:** OneAI-Cortex
**Feature:** Agent Configuration Pipeline — Frontend Integration Support

---

## Problem Definition

**What:** Three connected failures in the agent creation → configuration → execution pipeline span both the frontend (OneAI-UI) and backend (OneAI-Cortex):

1. **Agent edit flow incomplete** — The frontend cannot load saved agent prompts because it lacks an API client method for the existing `GET /agents/{id}/versions/{version}` endpoint. The backend serves this data correctly, but the UI never calls it.

2. **LLM API key input missing** — The backend fully supports encrypted `user_api_keys` storage in `AgentVersion.config` (ADR-007, ADR-011), including encryption on write and decryption at runtime. However, the frontend has no UI to input API keys, so the field is always empty.

3. **Chat execution fails** — When `RunnerService.run_session()` loads an agent with empty `user_api_keys`, it passes `{}` to `adapter.create_runtime()`. The DeepAgents adapter calls `resolve_model()` without the required LLM provider API key in the environment, causing an `AdapterError`. The error is streamed back as an SSE `error` event, but the message is a raw exception string — not user-friendly.

**Who:**
- Every user attempting the core workflow: create agent → configure → chat
- Frontend team integrating with Cortex APIs for agent management

**Why now:** The backend APIs are complete and working, but the frontend integration gap makes the entire platform unusable for the primary flow.

**Constraints:**
- No backend API changes required — all endpoints exist and work correctly
- `SecretEncryption` service handles `user_api_keys` encryption/decryption (ADR-011)
- Version config JSONB stores encrypted keys — frontend receives encrypted blobs
- Error events from `adapter.execute()` are generic strings — no structured error codes

**Success looks like:**
- Frontend successfully calls existing version endpoint to load agent configs
- API keys flow through: frontend → `POST /agents` config → encryption → `AgentVersion.config` → decryption at runtime → `adapter.create_runtime()`
- Agents with valid API keys execute successfully via SSE streaming
- Backend error messages for missing API keys are identifiable by the frontend
