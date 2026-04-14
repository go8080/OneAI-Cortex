# Conversation Memory Architecture

> How OneAI-Cortex stores, retrieves, and manages conversation history for agent execution across multi-turn sessions.

---

## Table of Contents

1. [Overview](#1-overview)
2. [Dual-Layer Memory System](#2-dual-layer-memory-system)
3. [Layer 1: PostgreSQL Message Log](#3-layer-1-postgresql-message-log)
4. [Layer 2: LangGraph Checkpoint](#4-layer-2-langgraph-checkpoint)
5. [Data Flow: Single Chat Turn](#5-data-flow-single-chat-turn)
6. [Multi-Turn Memory: How Context Persists](#6-multi-turn-memory-how-context-persists)
7. [HITL Interrupt & Resume Flow](#7-hitl-interrupt--resume-flow)
8. [Configuration](#8-configuration)
9. [Cleanup & Retention](#9-cleanup--retention)
10. [Key Files Reference](#10-key-files-reference)

---

## 1. Overview

Cortex uses a **dual-layer memory system** to manage agent conversations:

- **Layer 1 (PostgreSQL)** — Permanent message log. Stores every user and assistant message in chronological order. Used for UI display, LLM context building, and audit trails.
- **Layer 2 (LangGraph Checkpoint)** — Temporary execution state. Stores the LangGraph graph's internal state in per-session SQLite files. Used for multi-step tool chains and Human-in-the-Loop (HITL) interrupt resumption.

These layers serve different purposes and operate independently. Deleting all checkpoints does not affect conversation history. Deleting messages does not affect in-flight execution state.

---

## 2. Dual-Layer Memory System

```
+-----------------------------------------------------------------------+
|                    CONVERSATION MEMORY                                  |
|                                                                         |
|   LAYER 1: Message Log (PostgreSQL)                                    |
|   +----------------------------------------------------+              |
|   |  sessions table --> messages table                  |              |
|   |  Stores: role, content, metadata, timestamps        |              |
|   |  Purpose: UI display, history reload, LLM context   |              |
|   |  Lifetime: permanent (until session deleted)         |              |
|   +----------------------------------------------------+              |
|                                                                         |
|   LAYER 2: Execution State (LangGraph Checkpoint)                      |
|   +----------------------------------------------------+              |
|   |  data/checkpoints/{session_id}.db (SQLite)          |              |
|   |  Stores: graph state, tool call state, interrupts   |              |
|   |  Purpose: resume after HITL, multi-step execution   |              |
|   |  Lifetime: configurable (default 7 days TTL)         |              |
|   +----------------------------------------------------+              |
+-----------------------------------------------------------------------+
```

### Why Two Layers?

| Concern | PostgreSQL | Checkpoint |
|---------|-----------|------------|
| "What was said" | Yes | No |
| "Where is execution paused" | No | Yes |
| UI needs to display messages | Yes | No |
| Agent needs to resume after interrupt | No | Yes |
| Survives server restart | Yes | Yes (file-based) |
| Survives checkpoint cleanup | Yes | No |

---

## 3. Layer 1: PostgreSQL Message Log

### Database Schema

```sql
CREATE TABLE sessions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id        UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    user_id         UUID NOT NULL,
    agent_version   INTEGER NOT NULL,        -- frozen version of agent config
    title           VARCHAR(255),            -- auto-generated from first message
    is_active       BOOLEAN NOT NULL DEFAULT true,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX ix_sessions_agent_user_active
    ON sessions (agent_id, user_id, is_active);
```

```sql
CREATE TABLE messages (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id      UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    role            VARCHAR(20) NOT NULL,    -- 'user' | 'assistant' | 'tool' | 'system'
    content         TEXT NOT NULL,           -- the actual message text
    metadata        JSONB NOT NULL DEFAULT '{}',  -- tool_calls, tool_results, etc.
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX ix_messages_session_created
    ON messages (session_id, created_at);
```

### ORM Models

```python
# app/models/session.py

class Session(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "sessions"

    agent_id: Mapped[UUID]           # FK to agents table
    user_id: Mapped[UUID]            # owner (from JWT sub claim)
    agent_version: Mapped[int]       # frozen config version
    title: Mapped[str | None]        # auto-set from first user message
    is_active: Mapped[bool]          # soft-close flag

    messages: Mapped[list[Message]]  # relationship, ordered by created_at


class Message(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "messages"

    session_id: Mapped[UUID]         # FK to sessions table
    role: Mapped[str]                # user | assistant | tool | system
    content: Mapped[str]             # message text
    meta: Mapped[dict]               # JSONB — tool_calls, tool_results
    created_at: Mapped[datetime]
```

### Repository Operations

```python
# app/repositories/session.py

class SessionRepository:
    create_session(data)              # Create new session
    get_session(session_id)           # Get session by ID
    list_sessions(agent_id, user_id)  # List sessions for agent+user
    list_user_sessions(user_id)       # List all sessions for user
    update_title(session_id, title)   # Set session title
    add_message(data)                 # Append message to session
    get_messages(session_id)          # Get all messages (chronological)
```

### Message Metadata (JSONB)

The `metadata` field on assistant messages stores structured tool interaction data:

```json
{
  "tool_calls": [
    {
      "id": "run-uuid",
      "name": "gmail_search",
      "args": {"query": "meeting notes"},
      "status": "completed"
    }
  ],
  "tool_results": [
    {
      "tool_call_id": "run-uuid",
      "output": "Found 3 emails matching 'meeting notes'..."
    }
  ]
}
```

---

## 4. Layer 2: LangGraph Checkpoint

### How It Works

Each session gets its own SQLite database file at `data/checkpoints/{session_id}.db`. This is created by LangGraph's `AsyncSqliteSaver`:

```python
# app/infrastructure/checkpointer.py

async def get_checkpointer(session_id: str) -> AsyncSqliteSaver:
    db_path = checkpoint_dir / f"{session_id}.db"
    return AsyncSqliteSaver.from_conn_string(str(db_path))
```

### What the Checkpoint Stores

LangGraph uses the checkpoint to persist:

- **Graph node position** — which node in the execution graph the agent is at
- **Accumulated state** — messages, tool call results accumulated during this turn
- **Interrupt state** — when HITL pauses execution, the checkpoint remembers exactly where
- **Pending tool calls** — tool calls that are awaiting approval or completion

### When Checkpoints Are Used

| Scenario | Checkpoint Role |
|----------|----------------|
| Single-turn chat (no tools) | Written but not critical — graph completes in one pass |
| Multi-step tool chain | Saved after each tool call node, enables crash recovery |
| HITL interrupt | Saves exact pause point, enables resume from approval |
| Server restart mid-execution | Can resume from last checkpoint (if runtime recreated) |

### Thread ID Binding

The checkpoint is bound to a session via `thread_id`:

```python
# In adapter.execute()
config = {"configurable": {"thread_id": session_id}}
graph.astream_events({"messages": messages}, config=config, version="v2")
```

LangGraph uses `thread_id` to find the correct SQLite file and save/restore state.

---

## 5. Data Flow: Single Chat Turn

```
User sends: "What are my meetings?"
    |
    v
+-- RunnerService.run_session(session_id, user_id, message) --------+
|                                                                     |
|  1. LOAD SESSION                                                   |
|     session = sessions.get_session(session_id)                     |
|     Retrieves: agent_id, agent_version, user_id                    |
|                                                                     |
|  2. LOAD AGENT CONFIG                                              |
|     agent = agents.get_by_id(session.agent_id)                     |
|     version = agents.get_version(agent_id, agent_version)          |
|     config_dict = version.config  (JSONB blob)                     |
|                                                                     |
|  3. DECRYPT API KEYS                                               |
|     user_api_keys = encryption.decrypt_dict_values(                |
|         config_dict["user_api_keys"])                              |
|                                                                     |
|  4. RESOLVE GOOGLE TOKEN (if google_oauth tools present)           |
|     google_token = connected_service.get_google_token(user_id)     |
|                                                                     |
|  5. CREATE RUNTIME                                                 |
|     runtime = adapter.create_runtime(config, keys, google_token)   |
|     runtime.session_id = str(session_id)  <-- checkpoint binding   |
|                                                                     |
|  6. STORE USER MESSAGE (PostgreSQL)                                |
|     sessions.add_message({                                         |
|         session_id, role: "user", content: "What are my meetings?" |
|     })                                                              |
|                                                                     |
|  7. LOAD FULL MESSAGE HISTORY (PostgreSQL)                         |
|     messages = sessions.get_messages(session_id)                   |
|     message_dicts = [{role, content}, {role, content}, ...]        |
|     This includes ALL prior turns + the new user message           |
|                                                                     |
|  8. EXECUTE AGENT                                                  |
|     adapter.execute(runtime, message_dicts, session_id)            |
|         |                                                           |
|         v                                                           |
|     graph.astream_events(                                          |
|         {"messages": message_dicts},   <-- full history            |
|         config={"configurable": {"thread_id": session_id}}         |
|     )                                                               |
|         |                                                           |
|         +-- LLM call --> tool call --> LLM call --> done           |
|         |   (checkpoint saved after each node)                     |
|         v                                                           |
|     Yields: AgentEvent stream (message, tool_call, tool_result)    |
|                                                                     |
|  9. STREAM TO UI (SSE)                                             |
|     sse_event_generator() --> EventSourceResponse                  |
|                                                                     |
| 10. STORE ASSISTANT RESPONSE (PostgreSQL)                          |
|     sessions.add_message({                                         |
|         session_id, role: "assistant",                              |
|         content: "You have 3 meetings tomorrow..."                 |
|     })                                                              |
+---------------------------------------------------------------------+
```

---

## 6. Multi-Turn Memory: How Context Persists

The agent receives conversation memory via **explicit message history passing** — not through LangGraph's internal state.

### Turn 1

```
User: "What are my meetings?"

RunnerService loads messages from PostgreSQL:
  [
    {role: "user", content: "What are my meetings?"}
  ]

Passes to adapter.execute() --> LLM sees 1 message
Agent responds: "You have 3 meetings tomorrow: ..."

PostgreSQL after turn 1:
  [user: "What are my meetings?"]
  [assistant: "You have 3 meetings tomorrow: ..."]
```

### Turn 2

```
User: "Cancel the 3pm one"

RunnerService loads ALL messages from PostgreSQL:
  [
    {role: "user",      content: "What are my meetings?"},
    {role: "assistant", content: "You have 3 meetings tomorrow: ..."},
    {role: "user",      content: "Cancel the 3pm one"}
  ]

Passes full array to adapter.execute() --> LLM sees 3 messages
Agent knows which meeting "the 3pm one" refers to from context
```

### Turn N

```
RunnerService always loads the COMPLETE message history:
  messages = sessions.get_messages(session_id)  # ALL messages, ordered by created_at

This grows linearly with conversation length.
The LLM receives the full history every turn.
```

### Context Window Implications

| Conversation Length | Message Count | Approximate Tokens |
|--------------------|--------------|--------------------|
| 5 turns | ~10 messages | ~2,000-5,000 |
| 20 turns | ~40 messages | ~10,000-20,000 |
| 50 turns | ~100 messages | ~25,000-50,000 |
| 100+ turns | ~200+ messages | May exceed context window |

**Current limitation:** No conversation summarization or truncation is implemented. Very long conversations may exceed the LLM's context window. The DeepAgents middleware stack includes a `summarization` middleware toggle (`MiddlewareConfig.summarization = True`) which, when active in the DeepAgents framework, can compress older messages.

---

## 7. HITL Interrupt & Resume Flow

The checkpoint is critical for Human-in-the-Loop (HITL) interrupts:

```
TURN START
    |
    v
Agent decides to call gmail_send(to="boss@co.com", subject="Report")
    |
    v
HITL interrupt triggered (tool is in agent's interrupt_on config)
    |
    +-- LangGraph checkpoint saves:
    |     - Graph paused at gmail_send node
    |     - Pending tool call arguments
    |     - All accumulated state
    |
    +-- SSE emits: event: interrupt
    |     data: {tool_name: "gmail_send", tool_args: {...}, message: "Approval required"}
    |
    v
UI shows approval dialog to user
    |
    |  (user clicks "Approve")
    v

POST /api/v1/run/sessions/{id}/resume
    Body: { "approved": true }
    |
    v
+-- RunnerService.resume_session() ---------------------------------+
|                                                                     |
|  1. Recreate runtime (same agent config, same API keys)            |
|  2. adapter.resume_after_interrupt(runtime, session_id, approved)  |
|  3. LangGraph loads checkpoint from SQLite                         |
|  4. Resumes from exact pause point (gmail_send node)               |
|  5. Executes the tool call                                         |
|  6. Continues graph execution (LLM processes tool result)          |
|  7. Yields remaining events via SSE                                |
+---------------------------------------------------------------------+
```

### Without Checkpoint

If the checkpoint didn't exist, there would be no way to resume from the exact interruption point. The agent would have to re-execute the entire turn, potentially making duplicate tool calls.

---

## 8. Configuration

```env
# === Checkpointing ===
CHECKPOINT_DIR=data/checkpoints        # Directory for SQLite checkpoint files
CHECKPOINT_RETENTION_DAYS=7            # Auto-cleanup after N days
```

```python
# app/config.py
class Settings(BaseSettings):
    checkpoint_dir: str = "data/checkpoints"
    checkpoint_retention_days: int = 7
```

### Agent-Level Toggle

Checkpointing can be enabled/disabled per agent in the config:

```python
# In AgentConfig (app/adapters/types.py)
@dataclass
class AgentConfig:
    checkpointing_enabled: bool = True  # default: on
```

When disabled, the agent runs without a checkpoint — HITL interrupts and crash recovery won't work.

---

## 9. Cleanup & Retention

```python
# app/infrastructure/checkpointer.py

def cleanup_expired_checkpoints(retention_days: int | None = None) -> int:
    """Remove checkpoint files older than retention_days.
    Returns count of removed files."""
    cutoff = time.time() - (days * 86400)
    removed = 0
    for db_file in checkpoint_dir.glob("*.db"):
        if db_file.stat().st_mtime < cutoff:
            db_file.unlink()
            removed += 1
    return removed
```

- Meant to be called from a periodic task or CLI command
- Only deletes `.db` files older than the retention period
- PostgreSQL messages are NOT affected — conversation history survives cleanup
- Default retention: 7 days

---

## 10. Key Files Reference

| File | Layer | Purpose |
|------|-------|---------|
| `app/models/session.py` | L1 (PostgreSQL) | Session + Message ORM models |
| `app/repositories/session.py` | L1 (PostgreSQL) | CRUD operations for sessions and messages |
| `app/services/runner.py` | Both | Orchestrates session lifecycle, history loading, execution |
| `app/infrastructure/checkpointer.py` | L2 (Checkpoint) | Creates per-session AsyncSqliteSaver instances |
| `app/adapters/deepagents/adapter.py` | L2 (Checkpoint) | Passes `thread_id` to LangGraph for checkpoint binding |
| `app/infrastructure/sse.py` | Neither | Converts AgentEvent stream to SSE format |
| `app/adapters/types.py` | Neither | AgentConfig (checkpointing_enabled), AgentRuntime (session_id), AgentEvent |
| `app/config.py` | Both | CHECKPOINT_DIR, CHECKPOINT_RETENTION_DAYS settings |
| `app/api/runner.py` | Neither | HTTP endpoints for session CRUD + chat + resume |

---

## Architecture Diagram

```
                 +---------------+
                 |   UI (SSE)    |
                 +-------+-------+
                         | POST /run/sessions/{id}/chat
                         v
               +-------------------+
               |  RunnerService    |
               |                   |
               |  1. Load session  |<---- PostgreSQL: sessions table
               |  2. Load config   |<---- PostgreSQL: agent_versions.config
               |  3. Decrypt keys  |<---- Fernet decryption
               |  4. Google token  |<---- Connected Services (if needed)
               |  5. Load history  |<---- PostgreSQL: messages table (ALL turns)
               |  6. Execute       |
               |  7. Save response |----> PostgreSQL: messages table
               +--------+----------+
                        |
                        v
               +-------------------+
               |  DeepAgents       |
               |  Adapter          |
               |                   |
               |  graph.astream(   |
               |    messages,      |<---- Full history from PostgreSQL
               |    thread_id      |<---- Links to SQLite checkpoint
               |  )                |
               +--------+----------+
                        |
              +---------+---------+
              |                   |
    +---------v--------+  +------v-----------+
    | LLM Provider     |  | SQLite           |
    | (Anthropic,      |  | Checkpoint       |
    |  OpenAI, etc.)   |  | {session_id}.db  |
    +------------------+  +------------------+
```

---

## Summary

| Question | Answer |
|----------|--------|
| How does the agent remember prior messages? | Full message history loaded from PostgreSQL and passed to LLM every turn |
| Where are messages stored? | PostgreSQL `messages` table (permanent) |
| Where is execution state stored? | SQLite files at `data/checkpoints/{session_id}.db` (temporary) |
| How does HITL resume work? | LangGraph checkpoint saves pause point; `resume_session()` loads it |
| What happens if checkpoints are deleted? | Conversation history is fine; HITL resume and crash recovery break |
| Is there conversation summarization? | DeepAgents middleware toggle exists (`summarization: true`) but relies on the framework |
| What's the context window limit? | No truncation — full history is passed; very long conversations may exceed LLM limits |
| How is session data cleaned up? | `cleanup_expired_checkpoints()` for SQLite; sessions persist in PostgreSQL |
