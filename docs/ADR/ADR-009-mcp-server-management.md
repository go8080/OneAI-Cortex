## ADR-009: MCP Server Management as First-Class Module

**Date:** 2026-04-10
**Status:** Accepted
**Phase:** Plan

### Context

Agents need access to external tools and data sources. The Model Context Protocol (MCP) is a standardized protocol for LLM-tool communication, supported by DeepAgents (via `mcp.json` config). Users' MCP servers may require API keys, authentication, and specific transport configurations (stdio, SSE, HTTP).

The platform needs to:
1. Let users register their MCP servers with connection details and auth
2. Test MCP server connectivity and discover available tools
3. Assign MCP servers to specific agents
4. Handle MCP auth securely (API keys for GitHub, Slack, databases, etc.)

### Decision

Create a dedicated **MCP Server Manager** module with full CRUD, connectivity testing, tool discovery, and agent assignment. MCP servers are stored in the database with encrypted auth credentials. Testing validates both connectivity AND authentication before an agent can use a server.

**Key design decisions:**
- MCP server configs are user-owned (each user manages their own servers)
- Auth credentials (API keys, tokens) stored in `env_vars` JSONB column, encrypted at rest
- Agent-to-MCP-server is a many-to-many relationship via junction table
- Framework adapters receive `MCPServerConfig` objects and handle the protocol-level integration
- Testing endpoint performs: connect → authenticate → list tools → return results
- Tool discovery results are cached in `tools_discovered` column to avoid repeated MCP calls

### Consequences

**Positive:**
- Users can bring any MCP-compatible tool server to their agents
- Centralized auth management — MCP API keys stored once, used by many agents
- Testing before assignment prevents agents from failing at runtime due to bad MCP configs
- Tool discovery gives users visibility into what tools an MCP server provides

**Negative:**
- Additional DB tables and API surface
- MCP protocol has transport variations (stdio, SSE, HTTP) that add complexity
- Stored credentials require encryption-at-rest infrastructure

**Neutral:**
- MCP support depends on the framework adapter implementing `attach_mcp_servers()`
- DeepAgents natively supports MCP via `mcp.json` — adapter translates our DB config to that format

### Alternatives Rejected

| Alternative | Why Rejected |
|-------------|-------------|
| Let users configure MCP only via agent config JSON | No centralized testing, no auth management, no reuse across agents |
| Store MCP config as files (like DeepAgents `mcp.json`) | Doesn't work in multi-tenant DB-backed platform; no auth encryption |
| Defer MCP to v0.2 | MCP is essential for real-world agent utility — tools like GitHub, Slack, databases all use MCP |

### Validation

- `POST /mcp-servers/{id}/test` returns tool list for a correctly configured server
- Agent execution with assigned MCP server can invoke MCP tools
- Invalid MCP auth returns clear error message (not a generic connection failure)
