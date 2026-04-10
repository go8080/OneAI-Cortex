# Phase 1 — Evaluated Approaches

**Date:** 2026-04-10
**Status:** Evaluated
**Project:** OneAI-Cortex

---

## Idea A: Thin Wrapper — File-Based

**Approach:** Treat each agent as a directory (`deepagents.toml` + `AGENTS.md` + skills/) managed via Git. Platform is a thin API around the DeepAgents CLI.

**How it works:**
- Each user agent = a Git repo/directory with DeepAgents config files
- Platform API wraps `deepagents dev`, `deepagents deploy`
- Testing = run agent headlessly via `deepagents prompt`
- SDK export = zip the directory with a `requirements.txt`

**Pros:**
- Minimal code to write
- Leverages existing DeepAgents CLI tooling directly
- Stays close to upstream, easy to track updates

**Cons:**
- Tightly coupled to DeepAgents file conventions
- Hard to add non-DeepAgents frameworks later (would need rewrite)
- Limited programmatic control over agent lifecycle
- No structured evaluation system

**Effort:** S (Small)
**Dependencies:** DeepAgents CLI, Git

---

## Idea B: API-First Modular Monolith (SELECTED)

**Approach:** FastAPI backend with domain modules (Builder, Runner, Evaluator, Deployer). Agent configs stored in DB, executed programmatically via `create_deep_agent()`.

**How it works:**
- **Builder Module** — API to define agents: model, tools, subagents, skills, system prompt → stored as structured JSON in PostgreSQL
- **Runner Module** — Takes agent config from DB, calls `create_deep_agent()`, executes with streaming, returns results via WebSocket/SSE
- **Evaluator Module** — Runs agent against test suites, scores responses (accuracy, latency, cost), stores metrics
- **Deployer Module** — Hosts agent as a persistent endpoint OR generates downloadable SDK package (Python package with pinned config)
- **Framework Adapter Layer** — DeepAgents is the first adapter; interface defined so CrewAI/AutoGen adapters can be added later

**Pros:**
- Full programmatic control over agent lifecycle
- Clean, versioned API surface
- Framework-agnostic adapter interface from day one
- Structured evaluation with stored metrics
- Proper multi-tenancy support
- Contributors can run everything via `docker-compose up`

**Cons:**
- More upfront work than Idea A
- Must maintain framework adapter abstraction layer
- Database schema design required upfront

**Effort:** L (Large)
**Dependencies:** FastAPI, PostgreSQL, DeepAgents SDK, Redis (task queues)

---

## Idea C: Microservices from Day One

**Approach:** Separate services for each domain — Builder Service, Runner Service, Evaluator Service, Deployer Service — communicating via message queues.

**How it works:**
- Each domain = independent FastAPI service with its own database
- RabbitMQ/Kafka for inter-service communication
- Kubernetes-native deployment model
- Each service scales independently

**Pros:**
- Maximum horizontal scalability
- Independent deployment cycles
- Team parallelism (different teams own different services)

**Cons:**
- Massive upfront complexity for an open-source project starting out
- Operational overhead (service mesh, distributed tracing, message brokers)
- Harder for contributors to run locally
- Premature optimization — no users yet to justify distributed architecture

**Effort:** XL (Extra Large)
**Dependencies:** FastAPI, PostgreSQL, message broker (RabbitMQ/Kafka), Kubernetes, container orchestration
