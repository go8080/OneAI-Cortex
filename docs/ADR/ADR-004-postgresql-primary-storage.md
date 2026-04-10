## ADR-004: PostgreSQL as Primary Storage

**Date:** 2026-04-10
**Status:** Accepted
**Phase:** Plan

### Context

The platform needs persistent storage for users, agents, configs, sessions, messages, evaluations, and deployments. Storage must handle structured data (users, agents) and semi-structured data (agent configs, evaluation metrics).

### Decision

Use PostgreSQL as the single primary data store with JSONB columns for semi-structured data (agent configs, metadata, eval metrics). Access via async SQLAlchemy 2.0 with Alembic migrations.

### Consequences

**Positive:**
- JSONB gives schema flexibility for agent configs without a document DB
- Single database simplifies operations, backups, and transactions
- Excellent ecosystem (Alembic, pgAdmin, monitoring tools)
- ACID compliance for multi-table operations (e.g., create agent + version atomically)

**Negative:**
- JSONB queries are slower than normalized columns for complex filtering
- No built-in full-text search for message content (would need pg_trgm or external)

**Neutral:**
- SQLite can be swapped in for local dev/testing via engine URL change

### Alternatives Rejected

| Alternative | Why Rejected |
|-------------|-------------|
| MongoDB | Stronger JSONB story but weaker for relational data (users, deployments); team familiarity with PostgreSQL |
| SQLite for production | Cannot handle concurrent writes from multiple agent executions |
| PostgreSQL + Redis for sessions | Premature split; PostgreSQL handles session volume fine for v0.1 |

### Validation

- Agent config JSONB queries perform under 50ms for single-agent lookups
- Migration pipeline works: `alembic upgrade head` from clean DB succeeds
