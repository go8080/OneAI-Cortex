## ADR-005: SSE for Agent Execution Streaming

**Date:** 2026-04-10
**Status:** Accepted
**Phase:** Plan

### Context

Agent execution produces a stream of events (text chunks, tool calls, tool results) that must be delivered to the client in real-time. Two options: WebSocket or Server-Sent Events (SSE).

### Decision

Use Server-Sent Events (SSE) for agent execution streaming. Implement via `sse-starlette` library with FastAPI's `StreamingResponse`.

### Consequences

**Positive:**
- Simpler than WebSocket — HTTP-based, works through proxies/CDNs/load balancers
- Built-in reconnection via `Last-Event-ID` header
- Client-side: native `EventSource` API, no library needed
- Unidirectional (server → client) matches our use case — client sends one request, server streams back
- Compatible with standard HTTP auth (JWT in header)

**Negative:**
- Unidirectional only — client can't send mid-stream messages (not needed for v0.1)
- Limited to text data (binary would need base64 encoding)

**Neutral:**
- Can upgrade to WebSocket later if bidirectional streaming is needed (e.g., interrupt/cancel mid-execution)

### Alternatives Rejected

| Alternative | Why Rejected |
|-------------|-------------|
| WebSocket | Bidirectional not needed for v0.1; more complex connection management; harder through proxies |
| Long polling | Higher latency, more server load, worse developer experience |
| gRPC streaming | Not browser-friendly without grpc-web proxy; overhead for this use case |

### Validation

- SSE stream delivers first token within 500ms of request
- Reconnection with `Last-Event-ID` resumes from correct event
