"""MCP client — connects to MCP servers for tool discovery and health checks."""

from __future__ import annotations

import time
from typing import Any

import structlog
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from app.adapters.types import MCPServerConfig, MCPTestResult, ToolSpec
from app.core.exceptions import MCPConnectionError

__all__ = ["MCPClient"]

logger = structlog.get_logger(__name__)


class MCPClient:
    """Manages connections to MCP servers for tool discovery and testing."""

    async def test_connection(self, config: MCPServerConfig) -> MCPTestResult:
        """Test connectivity to an MCP server and discover its tools."""
        start = time.monotonic()

        try:
            if config.transport == "stdio":
                return await self._test_stdio(config, start)
            else:
                # SSE and HTTP transports
                return await self._test_http(config, start)
        except Exception as exc:
            latency = int((time.monotonic() - start) * 1000)
            logger.warning(
                "mcp.test_failed",
                server=config.name,
                transport=config.transport,
                error=str(exc),
            )
            return MCPTestResult(
                reachable=False,
                error=str(exc),
                latency_ms=latency,
            )

    async def _test_stdio(self, config: MCPServerConfig, start: float) -> MCPTestResult:
        """Test an stdio-based MCP server."""
        if not config.command:
            return MCPTestResult(reachable=False, error="stdio transport requires 'command'")

        server_params = StdioServerParameters(
            command=config.command,
            args=config.args,
            env={**config.env} if config.env else None,
        )

        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools_response = await session.list_tools()

                tools = [
                    ToolSpec(
                        name=t.name,
                        description=t.description or "",
                        input_schema=t.inputSchema if hasattr(t, "inputSchema") else {},
                    )
                    for t in tools_response.tools
                ]

                latency = int((time.monotonic() - start) * 1000)
                return MCPTestResult(
                    reachable=True,
                    tools_discovered=tools,
                    latency_ms=latency,
                )

    async def _test_http(self, config: MCPServerConfig, start: float) -> MCPTestResult:
        """Test an SSE or HTTP-based MCP server."""
        if not config.url:
            return MCPTestResult(
                reachable=False, error=f"{config.transport} transport requires 'url'"
            )

        from mcp.client.sse import sse_client

        headers: dict[str, str] = {}
        if config.auth_header:
            headers["Authorization"] = config.auth_header

        async with sse_client(config.url, headers=headers) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools_response = await session.list_tools()

                tools = [
                    ToolSpec(
                        name=t.name,
                        description=t.description or "",
                        input_schema=t.inputSchema if hasattr(t, "inputSchema") else {},
                    )
                    for t in tools_response.tools
                ]

                latency = int((time.monotonic() - start) * 1000)
                return MCPTestResult(
                    reachable=True,
                    tools_discovered=tools,
                    latency_ms=latency,
                )
