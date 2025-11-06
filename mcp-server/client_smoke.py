"""Smoke test using official MCP SDK for SSE transport.

IMPORTANT: This client uses SSE (Server-Sent Events) transport to match the server.

Transport Matching:
- Server configured with: mcp.sse_app(path="/mcp") in mcp_server.py
- Client must use: sse_client() from mcp.client.sse
- Both must use same path: "/mcp"

Why SSE:
- Avoids task group initialization bugs with StreamableHTTP
- Provides stable bidirectional communication
- Compatible with MCP protocol requirements

Note on Attributes:
- MCP SDK uses camelCase: result.serverInfo.name, result.protocolVersion
- Not snake_case like result.server_info or result.protocol_version
"""
import asyncio
from mcp.client.session import ClientSession

# For SSE transport
# Requires: mcp>=1.18.0 for SSE support
try:
    from mcp.client.sse import sse_client
    HAS_SSE = True
except ImportError:
    print("Note: SSE transport not available in this MCP version")
    HAS_SSE = False


async def test_sse_transport():
    """Test with SSE transport.

    Connects to the MCP server running in Docker and validates:
    1. SSE connection establishment
    2. Session initialization (protocol handshake)
    3. Tool discovery (list_tools)
    4. Tool execution (call_tool)
    """
    if not HAS_SSE:
        print("Skipping SSE test - transport not available")
        return False

    print("\n" + "=" * 60)
    print("Testing SSE Transport")
    print("=" * 60)

    try:
        # SSE endpoint - connects to Docker container
        # Port 8835 on host maps to 8000 in container (see docker-compose.yml)
        url = "http://127.0.0.1:8835/mcp"

        print(f"Connecting to {url}...")
        # sse_client returns (read_stream, write_stream) tuple
        async with sse_client(url) as (read, write):
            async with ClientSession(read, write) as session:
                print("✓ Connected successfully!")

                # Initialize session - required before any other operations
                print("\nInitializing session...")
                result = await session.initialize()
                # Note: Use camelCase attributes (serverInfo, protocolVersion)
                print(f"✓ Server: {result.serverInfo.name}")
                print(f"✓ Version: {result.serverInfo.version}")
                print(f"✓ Protocol: {result.protocolVersion}")

                # List tools
                print("\nListing tools...")
                tools_result = await session.list_tools()
                tools = tools_result.tools
                print(f"✓ Found {len(tools)} tools:")
                for tool in tools:
                    print(f"  - {tool.name}: {tool.description}")

                # Call a tool
                if tools:
                    tool_name = tools[0].name
                    print(f"\nCalling tool: {tool_name}")
                    # Adjust arguments based on actual tool
                    if tool_name == "run_untrusted_scan":
                        result = await session.call_tool(tool_name, {
                            "targets": "192.168.1.1",
                            "name": "Smoke Test Scan"
                        })
                    else:
                        result = await session.call_tool(tool_name, {"input": "test"})

                    print(f"✓ Tool result: {result}")

                print("\n" + "=" * 60)
                print("✓ ALL TESTS PASSED")
                print("=" * 60)
                return True

    except Exception as e:
        print(f"\n✗ Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run smoke tests."""
    success = await test_sse_transport()

    if success:
        print("\n🎉 MCP Server is working correctly!")
        return 0
    else:
        print("\n❌ MCP Server test failed")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
