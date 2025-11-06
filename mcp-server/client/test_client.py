"""Simple MCP client for testing MCP server."""
import asyncio
import sys
from pathlib import Path
from typing import Dict, Any

# Add fastmcp to path if running outside of installed package
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "venv" / "lib" / "python3.12" / "site-packages"))

try:
    from fastmcp.client import Client
    from fastmcp.client.transports import SSETransport  # Using SSE due to StreamableHTTP bug
except ImportError as e:
    print(f"Error: FastMCP client not installed. Please install with: pip install fastmcp")
    print(f"Details: {e}")
    sys.exit(1)


class NessusMCPClient:
    """MCP client for testing Nessus MCP server."""

    def __init__(self, base_url: str = None):
        # Auto-detect environment:
        # - Inside Docker container: connect to localhost:8000
        # - Outside Docker (host): connect to localhost:8835
        import os
        if base_url is None:
            if os.path.exists('/.dockerenv') or os.environ.get('CONTAINER'):
                base_url = "http://localhost:8000"  # Inside container
            else:
                base_url = "http://localhost:8835"  # On host

        self.base_url = base_url.rstrip("/")
        # Using SSE transport as workaround for StreamableHTTP task group initialization bug
        self.transport = SSETransport(f"{self.base_url}/mcp")
        self.client = Client(transport=self.transport)
        self._context_entered = False

    async def __aenter__(self):
        """Async context manager entry."""
        await self.client.__aenter__()
        self._context_entered = True
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._context_entered:
            await self.client.__aexit__(exc_type, exc_val, exc_tb)
        return False

    async def submit_scan(
        self,
        targets: str,
        name: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Submit untrusted scan."""
        if not self._context_entered:
            raise RuntimeError("Client must be used within async context manager")

        result = await self.client.call_tool(
            "run_untrusted_scan",
            arguments={
                "targets": targets,
                "name": name,
                **kwargs
            }
        )
        # FastMCP ToolResult has .data attribute containing the actual response
        return result.data if hasattr(result, 'data') else result

    async def get_status(self, task_id: str) -> Dict[str, Any]:
        """Get scan status."""
        if not self._context_entered:
            raise RuntimeError("Client must be used within async context manager")

        result = await self.client.call_tool(
            "get_scan_status",
            arguments={"task_id": task_id}
        )
        return result.data if hasattr(result, 'data') else result

    async def poll_until_complete(
        self,
        task_id: str,
        timeout: int = 300,
        poll_interval: int = 2
    ) -> Dict[str, Any]:
        """Poll status until scan completes."""
        start_time = asyncio.get_event_loop().time()

        while True:
            status = await self.get_status(task_id)

            if "error" in status:
                raise ValueError(f"Task error: {status['error']}")

            if status["status"] in {"completed", "failed", "timeout"}:
                return status

            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed > timeout:
                raise TimeoutError(f"Scan did not complete in {timeout}s")

            progress_str = f"{status.get('progress', 'N/A')}%" if status.get('progress') else "N/A"
            print(f"[{elapsed:.1f}s] Status: {status['status']}, Progress: {progress_str}")
            await asyncio.sleep(poll_interval)

    async def close(self):
        """Cleanup - for backward compatibility."""
        if self._context_entered:
            await self.client.__aexit__(None, None, None)


# Example usage
async def main():
    """Example workflow."""
    print("=" * 60)
    print("Phase 0: Mock Scan Workflow Test")
    print("=" * 60)

    try:
        async with NessusMCPClient() as client:
            # Submit scan
            print("\n1. Submitting scan...")
            task = await client.submit_scan(
                targets="192.168.1.1",
                name="Phase 0 Test Scan"
            )
            print(f"   ✓ Task submitted: {task['task_id']}")
            print(f"   ✓ Trace ID: {task['trace_id']}")
            print(f"   ✓ Scanner: {task['scanner_instance']}")

            # Poll until complete
            print("\n2. Polling status...")
            final_status = await client.poll_until_complete(task["task_id"], timeout=60)

            print("\n3. Final Status:")
            print(f"   ✓ Status: {final_status['status']}")
            print(f"   ✓ Progress: {final_status.get('progress', 'N/A')}%")
            print(f"   ✓ Scan ID: {final_status.get('nessus_scan_id')}")
            print(f"   ✓ Duration: {final_status['started_at']} → {final_status['completed_at']}")

            print("\n" + "=" * 60)
            print("✓ Phase 0 Test PASSED")
            print("=" * 60)

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    asyncio.run(main())
