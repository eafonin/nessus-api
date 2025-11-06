"""Run the MCP server using uvicorn with the SSE app.

IMPORTANT: This module runs the ASGI app directly with uvicorn.run()
instead of using FastMCP's built-in run_http_async() or run_sse_async().

Rationale:
- FastMCP's run_*_async() methods create a new app instance internally
- This bypasses any customizations made to the app object in mcp_server.py
- Direct uvicorn.run() ensures the exact app we configured is served
- Necessary for SSE transport with proper lifespan management

The app is imported from mcp_server.py where it's created via mcp.sse_app().
"""
import sys
import uvicorn

# Add /app to path for imports to work in Docker container
# This allows imports like "from tools.mcp_server import app" to work
sys.path.insert(0, '/app')

from tools.mcp_server import app

if __name__ == "__main__":
    # Run uvicorn with the SSE app
    # host=0.0.0.0 allows connections from outside the container
    # port=8000 is mapped to 8835 on host via docker-compose
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info",
    )
