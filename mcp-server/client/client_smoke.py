"""Smoke test using official MCP SDK for Streamable HTTP transport.

Transport Matching:
- Server configured with: mcp.http_app(path="/mcp", transport="streamable-http")
- Client must use: streamablehttp_client() from mcp.client.streamable_http
- Both must use same path: "/mcp"

Why Streamable HTTP:
- Modern MCP transport (FastMCP 2.13+)
- Bidirectional: HTTP POST (client->server) + SSE stream (server->client)
- Stateless mode supported for scalability
- Replaces deprecated sse_app() method

Note on Attributes:
- MCP SDK uses camelCase: result.serverInfo.name, result.protocolVersion
- Not snake_case like result.server_info or result.protocol_version
"""

import asyncio
import os
from pathlib import Path

from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamablehttp_client


async def test_streamable_http_transport() -> bool | None:
    """Test with Streamable HTTP transport.

    Connects to the MCP server running in Docker and validates:
    1. Streamable HTTP connection establishment
    2. Session initialization (protocol handshake)
    3. Tool discovery (list_tools)
    4. Tool execution (call_tool)
    """
    print("\n" + "=" * 60)
    print("Testing Streamable HTTP Transport")
    print("=" * 60)

    try:
        # Streamable HTTP endpoint - connects to Docker container
        # From host: Port 8836 maps to 8000 in container (see dev1/docker-compose.yml)
        # From container: Use localhost:8000 directly
        if Path("/.dockerenv").exists():
            # Running inside container
            url = "http://localhost:8000/mcp"
        else:
            # Running on host
            url = os.getenv("MCP_URL", "http://127.0.0.1:8836/mcp")

        print(f"Connecting to {url}...")
        # streamablehttp_client returns (read_stream, write_stream, get_session_id) tuple
        async with (
            streamablehttp_client(url) as (read, write, get_session_id),
            ClientSession(read, write) as session,
        ):
            print("Connected successfully!")

            # Initialize session - required before any other operations
            print("\nInitializing session...")
            result = await session.initialize()
            # Note: Use camelCase attributes (serverInfo, protocolVersion)
            print(f"Server: {result.serverInfo.name}")
            print(f"Version: {result.serverInfo.version}")
            print(f"Protocol: {result.protocolVersion}")

            # Get session ID if available
            session_id = get_session_id()
            if session_id:
                print(f"Session ID: {session_id}")

            # List tools
            print("\nListing tools...")
            tools_result = await session.list_tools()
            tools = tools_result.tools
            print(f"Found {len(tools)} tools:")
            for tool in tools:
                desc = (
                    tool.description[:60] + "..."
                    if len(tool.description) > 60
                    else tool.description
                )
                print(f"  - {tool.name}: {desc}")

            # Call list_pools tool (safe, read-only)
            print("\nCalling tool: list_pools")
            result = await session.call_tool("list_pools", {})
            print(
                f"Tool result: {result.content[0].text if result.content else 'No content'}"
            )

            print("\n" + "=" * 60)
            print("ALL TESTS PASSED")
            print("=" * 60)
            return True

    except Exception as e:
        print(f"\nError: {type(e).__name__}: {e}")
        import traceback

        traceback.print_exc()
        return False


async def main() -> int:
    """Run smoke tests."""
    success = await test_streamable_http_transport()

    if success:
        print("\nMCP Server is working correctly!")
        return 0
    else:
        print("\nMCP Server test failed")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
