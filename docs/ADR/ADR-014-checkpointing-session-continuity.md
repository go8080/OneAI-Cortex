## ADR-014: LangGraph Checkpointing for Session Continuity

**Date:** 2026-04-10
**Status:** accepted
**Phase:** Plan (from gap analysis review)

### Context

Without checkpointing, agent state lives only in memory during execution. If the server
restarts mid-conversation, or a user returns to a session later, the agent has no memory
of prior turns beyond what's replayed from the messages table. LangGraph supports native
checkpointing that serializes the full graph state (including tool results, intermediate
steps, and agent memory) to persistent storage.

This is also required for HITL (ADR-013) — interrupt/resume needs the graph state
persisted at the interrupt point.

### Decision

Use LangGraph's `AsyncSqliteSaver` for checkpoint persistence:

1. **Storage:** Each session gets its own SQLite file at `data/checkpoints/{session_id}.db`
2. **Lifecycle:** Created on first run, reused on subsequent turns, deleted on session delete
3. **Configuration:** `checkpointing_enabled: true` (default) in AgentConfig
4. **Thread ID:** LangGraph's `thread_id` config maps to Cortex's `session_id`
5. **Cleanup:** Background job deletes checkpoint files older than `CHECKPOINT_RETENTION_DAYS` (default: 7)

**Why SQLite over PostgreSQL for checkpoints:**
- LangGraph's checkpoint format is designed for SQLite — native support, no custom serialization
- Checkpoints are per-session, not queried across sessions — no need for relational queries
- Avoids bloating the main PostgreSQL database with serialized binary state
- SQLite files are easy to clean up (delete file = delete all checkpoints for session)

### Consequences

**Positive:**
- Conversations survive server restarts
- HITL interrupt/resume works reliably
- Users can return to a session days later and continue naturally
- Native LangGraph integration — no custom serialization code

**Negative:**
- Disk space grows with active sessions (mitigated by retention policy)
- SQLite files not backed up with PostgreSQL (separate backup strategy needed)
- Single-node assumption — SQLite files are local (acceptable for v0.1, see scope)

**Neutral:**
- Session metadata (user_id, agent_id, timestamps) stays in PostgreSQL — only graph state is in SQLite
- Future: could migrate to PostgreSQL-based checkpointer (`langgraph-checkpoint-postgres`) for multi-node

### Alternatives Rejected

| Alternative | Why Rejected |
|-------------|-------------|
| No checkpointing (replay from messages) | Loses intermediate state, tool results, agent reasoning; HITL impossible |
| PostgreSQL checkpointer | Extra serialization complexity; LangGraph's SQLite support is more mature |
| Redis for checkpoints | Not persistent by default; checkpoints too large for Redis memory |
| In-memory only (MemorySaver) | Lost on server restart; defeats the purpose |

### Validation
- Integration test: start conversation → restart server → continue conversation with context
- HITL test: interrupt → restart server → resume from checkpoint succeeds
- Cleanup test: sessions older than retention period have checkpoint files deleted
- Disk monitoring: health endpoint reports checkpoint directory size
