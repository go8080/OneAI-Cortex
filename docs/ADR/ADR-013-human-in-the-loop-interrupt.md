## ADR-013: Human-in-the-Loop via `interrupt_on` + SSE

**Date:** 2026-04-10
**Status:** accepted
**Phase:** Plan (from gap analysis review)

### Context

DeepAgents supports pausing agent execution before specific tool calls via the `interrupt_on`
parameter, which triggers `HumanInTheLoopMiddleware`. This is critical for safety — users may
want to approve dangerous operations like file edits, shell commands, or API calls before
the agent executes them.

In a server context, we need a mechanism to:
1. Pause execution and notify the client via SSE
2. Wait for user approval/rejection
3. Resume execution from the exact checkpoint

### Decision

Implement HITL as a first-class feature using SSE events + a resume endpoint:

1. **Configuration:** `interrupt_on` field in AgentConfig maps tool names to `true` or
   `InterruptConfig` with a custom message. Stored in agent_versions.config JSONB.

2. **Interrupt flow:**
   - Agent hits a tool in `interrupt_on` → LangGraph pauses at checkpoint
   - SSE emits `AgentEvent(type="interrupt")` with tool_name, tool_args, session_id
   - Checkpoint state persisted via AsyncSqliteSaver

3. **Resume flow:**
   - Client calls `POST /api/v1/sessions/{id}/resume` with `{approved, modified_args}`
   - RunnerService loads checkpoint, calls `FrameworkAdapter.resume_after_interrupt()`
   - If approved: tool executes, agent continues streaming
   - If rejected: tool skipped, LLM told "Tool call rejected by user"

4. **SSE event type:** New `"interrupt"` type added to AgentEvent.type enum.

### Consequences

**Positive:**
- Users have explicit control over dangerous agent actions
- Checkpoint-based resume is crash-safe — survives server restarts
- Fits naturally into existing SSE streaming pattern

**Negative:**
- Adds complexity to the Runner service and SSE protocol
- Clients must handle a new event type and implement approval UI
- Long-lived checkpoints consume disk space (mitigated by retention policy)

**Neutral:**
- `interrupt_on` inherits from parent to sync subagents by default (DeepAgents behavior)
- Async subagents handle HITL on their own remote server

### Alternatives Rejected

| Alternative | Why Rejected |
|-------------|-------------|
| WebSocket for bidirectional HITL | SSE already handles streaming; adding WS doubles protocol complexity (ADR-005) |
| Polling-based resume (client polls for interrupt state) | Wasteful; SSE push is real-time and already implemented |
| No HITL in v0.1 | Safety risk — users need approval gates for production agents |

### Validation
- Integration test: agent with `interrupt_on={"execute": True}` pauses before shell command
- Resume with approved=True → command executes, agent completes
- Resume with approved=False → command skipped, LLM continues gracefully
- Server restart during interrupt → checkpoint loads, resume still works
