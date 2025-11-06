"""Standalone test to verify MCP server works."""
import asyncio
import os
import sys
from pathlib import Path

# Add paths
sys.path.insert(0, str(Path(__file__).parent))

# Override DATA_DIR for local testing
os.environ.setdefault("DATA_DIR", str(Path(__file__).parent / "data" / "tasks"))

from fastmcp import FastMCP, Client
from fastmcp.client.transports import StreamableHttpTransport
from fastmcp.utilities.tests import run_server_async


async def main():
    """Test the MCP server standalone."""
    print("=" * 60)
    print("Standalone MCP Server Test")
    print("=" * 60)

    # Import the server
    from tools.mcp_server import mcp

    # Start server in background
    async with run_server_async(mcp, port=9999) as server_url:
        print(f"\nServer running at: {server_url}")

        # Connect client
        print("\nConnecting client...")
        async with Client(transport=StreamableHttpTransport(server_url)) as client:
            print("✓ Client connected successfully!")

            # List tools
            print("\nListing tools...")
            tools = await client.list_tools()
            print(f"✓ Found {len(tools)} tools:")
            for tool in tools:
                print(f"  - {tool.name}")

            # Call run_untrusted_scan
            print("\nSubmitting scan...")
            result = await client.call_tool(
                "run_untrusted_scan",
                arguments={
                    "targets": "192.168.1.1",
                    "name": "Standalone Test Scan"
                }
            )
            print(f"✓ Scan submitted: {result.data}")

            print("\n" + "=" * 60)
            print("✓ All tests PASSED!")
            print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
