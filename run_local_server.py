"""Run local MCP server for testing with fixed versions."""
import asyncio
import os
import sys

# Set up paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'mcp-server'))
os.environ.setdefault("DATA_DIR", os.path.join(os.path.dirname(__file__), 'mcp-server/data/tasks'))

print("=" * 80)
print("Starting local MCP server with fixed versions...")
print("=" * 80)

# Import after path setup
from tools.mcp_server import mcp

async def main():
    """Run the server."""
    print("Calling mcp.run_http_async()...")
    await mcp.run_http_async(
        host="127.0.0.1",
        port=8835,
        transport="sse",  # Using SSE transport
        path="/mcp",
        show_banner=True,
    )

if __name__ == "__main__":
    asyncio.run(main())
