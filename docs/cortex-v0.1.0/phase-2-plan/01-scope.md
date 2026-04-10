# Phase 2 — Scope Definition

**Date:** 2026-04-10
**Status:** Draft
**Project:** OneAI-Cortex
**Input:** Phase 1 Recommendation — Idea B (API-First Modular Monolith)

---

## In Scope (v0.1.0 — Foundation)

1. **Project Scaffolding** — FastAPI app factory, config, Docker setup, DB infrastructure; `uv` for project init, dependency management, and lockfile (`uv.lock`)
2. **OneAI-Auth Integration** — HARD DEPENDENCY; app must not start without Auth connectivity; JWT token validation using shared secret; auth client for user profile lookups; Cortex-local API key management for programmatic agent access
3. **Agent Builder Module** — CRUD for agent configurations (model, tools, subagents, MCP servers, system prompt, skills)
4. **Agent Versioning** — Immutable agent versions; every save creates a new version
5. **Agent Runner Module** — Execute agents via SSE streaming; conversation sessions with message history
6. **Agent Evaluator Module** — Define test suites, run agents against test cases, score and store metrics
7. **Agent Deployer Module** — Host agents as persistent API endpoints; generate downloadable SDK packages
8. **Framework Adapter Layer** — Abstract interface with semantic versioning + DeepAgents adapter (first implementation); version tags for compatibility tracking
9. **MCP Server Module** — Register MCP servers, test connectivity/auth, assign MCP servers to agents, manage MCP tool discovery
10. **Tool Registry** — Register and manage tools available to agents; validate tool API keys/auth
11. **Encryption at Rest** — All user-provided secrets (LLM API keys, MCP env vars, tool auth configs) encrypted via Fernet (AES-128-CBC + HMAC-SHA256) before database storage; `ENCRYPTION_KEY` from `.env`
12. **Database Schema** — PostgreSQL with Alembic migrations (no users table — user identity from OneAI-Auth)
13. **API Documentation** — OpenAPI auto-generated + usage guides
14. **Docker Compose** — Local dev stack (app + postgres + redis + oneai-auth)
15. **Full `create_deep_agent()` Parameter Mapping** — AgentConfig covers all 17 parameters: model, tools, system_prompt, middleware, subagents, response_format, checkpointer, backend, interrupt_on, debug, name, cache, temperature, max_tokens, recursion_limit, and framework-specific escape hatch
16. **Middleware Configuration** — Expose DeepAgents' 10-middleware stack as toggleable config per agent (TodoList, Filesystem, SubAgent, Summarization, PatchToolCalls, AsyncSubAgent, PromptCaching, HumanInTheLoop); users can enable/disable and reorder custom middleware
17. **Subagent Support (Sync + Async)** — SubAgent (sync, in-process) and AsyncSubAgent (remote, non-blocking via Agent Protocol); each with distinct config shapes. Auto-generated general-purpose subagent if none provided
18. **Human-in-the-Loop (HITL)** — `interrupt_on` configuration per tool name; pauses SSE streaming for user approval; resume endpoint to continue execution after approval/rejection
19. **Backend Selection** — StateBackend (default, ephemeral in-memory) and FilesystemBackend (persistent, root_dir-scoped); configurable per agent
20. **Model Resolution** — `provider:model` format (e.g., `anthropic:claude-sonnet-4-6`, `openai:gpt-5`) with validation against supported providers; default: `claude-sonnet-4-6`
21. **Structured Output** — `response_format` parameter for typed JSON responses from agents; passed through to LangGraph's structured output system
22. **Checkpointing** — LangGraph-native checkpointing for conversation continuity; AsyncSqliteSaver for persistent sessions; enables resume after server restart

## Explicitly Out of Scope

- **Frontend/UI** — API-first; UI is a separate project later
- **User registration/login/OAuth** — handled entirely by OneAI-Auth; Cortex only validates tokens
- **Second framework adapter** (CrewAI, AutoGen, etc.) — interface designed for it, not implemented
- **Billing/payments** — open source, no monetization layer
- **Agent marketplace/sharing** — users manage their own agents
- **Kubernetes deployment manifests** — Docker Compose only
- **Real-time collaboration** — single-user agent editing
- **Custom tool development SDK** — users select from registered tools or MCP servers
- **GPU/compute scheduling** — agents run on the host machine
- **Rate limiting / usage quotas** — deferred to v0.2.0 (OneAI-Auth handles its own rate limiting)
- **Skills system** (SKILL.md files, skill registry, layered loading) — deferred to v0.2.0
- **Memory system** (AGENTS.md persistent agent memory) — deferred to v0.2.0
- **CompiledSubAgent** (pre-built runnables) — only sync SubAgent + AsyncSubAgent in v0.1
- **CompositeBackend / StoreBackend** — only StateBackend + FilesystemBackend in v0.1
- **Sandbox providers** (LangSmith, Docker isolation) — deferred to v0.2.0
- **Custom middleware authoring** — users toggle built-in middleware only in v0.1
- **LangSmith integration** — observability enhancement, deferred
- **Summarization middleware tuning** — works with defaults in v0.1

## Assumptions

1. DeepAgents SDK is stable enough to use `create_deep_agent()` programmatically in a server context
2. **OneAI-Auth is running and reachable — HARD DEPENDENCY** — Cortex MUST NOT start if Auth health check fails at startup; single shared `.env` file for `JWT_SECRET_KEY` and `ENCRYPTION_KEY`
3. PostgreSQL is the only required DB dependency (+ Redis for task queues/caching); OneAI-Auth has its own separate DB
4. Agents execute synchronously within a request context (no long-running background agent jobs in v0.1.0, except via SSE streaming)
5. LLM API keys are provided by users (platform doesn't proxy or pay for LLM calls)
6. MCP servers are user-managed external services; Cortex registers and tests connectivity but does not host MCP servers
7. Single-node deployment is sufficient for v0.1.0
8. Python 3.13+ is the minimum runtime
9. OneAI-Auth JWT payload contains `sub` (user UUID), `exp`, and `type` fields — Cortex uses `sub` as the user identifier for all owned resources
