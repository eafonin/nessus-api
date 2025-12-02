"""
Nessus FastMCP Client

High-level Python client for the Nessus MCP Server using FastMCP library.

This client provides:
- Type-safe wrapper methods for all 6 MCP tools
- Connection management and error handling
- Progress monitoring and logging
- Helper methods for common workflows
- Extensive debugging capabilities

Reference: @docs/fastMCPServer for FastMCP client documentation

Environment Variables:
    MCP_SERVER_URL: MCP server URL (default: http://localhost:8836/mcp)
                    Inside Docker: http://mcp-api:8000/mcp

Usage:
    async with NessusFastMCPClient() as client:  # Uses MCP_SERVER_URL env var
        # Run a scan
        task = await client.submit_scan(targets="192.168.1.1", scan_name="Quick Scan")
        task_id = task["task_id"]

        # Wait for completion
        status = await client.wait_for_completion(task_id, timeout=600)

        # Get results
        results = await client.get_results(task_id, schema_profile="brief")
        print(results)
"""

import asyncio
import json
import os
import time
from collections.abc import Callable
from typing import Any

from fastmcp import Client

# Default URL - uses environment variable if set
DEFAULT_MCP_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8836/mcp")


class NessusFastMCPClient:
    """
    High-level async client for Nessus MCP Server.

    This class wraps the FastMCP Client with Nessus-specific operations,
    providing a clean, type-safe interface for all MCP tools.

    Architecture:
        Client (this class) → FastMCP Client → HTTP/SSE Transport → MCP Server

    Attributes:
        url: MCP server HTTP endpoint (e.g., "http://localhost:8836/mcp")
        timeout: Default timeout for requests (seconds)
        client: Underlying FastMCP Client instance

    Reference Documentation:
        - @docs/fastMCPServer/clients/client.md - Client basics
        - @docs/fastMCPServer/clients/tools.md - Tool execution
        - @docs/fastMCPServer/clients/transports.md - HTTP transport
    """

    def __init__(
        self,
        url: str | None = None,
        timeout: float = 30.0,
        log_handler: Callable | None = None,
        progress_handler: Callable | None = None,
        debug: bool = False,
    ) -> None:
        """
        Initialize Nessus FastMCP Client.

        Args:
            url: MCP server HTTP endpoint. Defaults to MCP_SERVER_URL env var
                 or http://localhost:8836/mcp if not set.
            timeout: Default timeout for requests (seconds)
            log_handler: Optional callback for server log messages
            progress_handler: Optional callback for progress updates
            debug: Enable debug logging

        Example:
            # Uses MCP_SERVER_URL env var or default
            client = NessusFastMCPClient()

            # Or specify URL explicitly
            client = NessusFastMCPClient(
                url="http://mcp-api:8000/mcp",
                timeout=60.0,
                debug=True
            )
        """
        self.url = url or DEFAULT_MCP_URL
        self.timeout = timeout
        self.debug = debug

        # Create underlying FastMCP client
        self.client = Client(
            self.url,  # Use resolved URL (with env var default)
            log_handler=log_handler or self._default_log_handler,
            progress_handler=progress_handler or self._default_progress_handler,
            timeout=timeout,
        )

        self._connected = False

    async def __aenter__(self) -> "NessusFastMCPClient":
        """Enter async context manager - establishes connection."""
        await self.client.__aenter__()
        self._connected = True

        if self.debug:
            print(f"[DEBUG] Connected to MCP server: {self.url}")

        # Verify connection with ping
        await self.ping()

        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> bool:
        """Exit async context manager - closes connection."""
        self._connected = False
        await self.client.__aexit__(exc_type, exc_val, exc_tb)

        if self.debug:
            print("[DEBUG] Disconnected from MCP server")
        return False

    def _default_log_handler(self, message: object) -> None:
        """Default handler for server log messages."""
        if self.debug:
            print(
                f"[SERVER LOG] {message.data if hasattr(message, 'data') else message}"
            )

    def _default_progress_handler(
        self, progress: float, total: float | None, message: str | None
    ) -> None:
        """Default handler for progress updates."""
        if self.debug:
            pct = (progress / total * 100) if total else 0
            print(f"[PROGRESS] {pct:.1f}% - {message}")

    def is_connected(self) -> bool:
        """Check if client is connected to server."""
        return self._connected

    # ==========================================================================
    # Core MCP Operations
    # ==========================================================================

    async def ping(self) -> bool:
        """
        Ping the MCP server to verify connectivity.

        Returns:
            True if server is reachable

        Raises:
            Exception if server is unreachable
        """
        await self.client.ping()
        return True

    async def list_tools(self) -> list[dict[str, Any]]:
        """
        List all available MCP tools.

        Returns:
            List of tool definitions with name, description, and input schema

        Example:
            tools = await client.list_tools()
            for tool in tools:
                print(f"{tool['name']}: {tool['description']}")
        """
        tools = await self.client.list_tools()

        # Convert to dict for easier consumption
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "inputSchema": tool.inputSchema
                if hasattr(tool, "inputSchema")
                else None,
            }
            for tool in tools
        ]

    async def call_tool(
        self, tool_name: str, arguments: dict[str, Any], timeout: float | None = None
    ) -> Any:
        """
        Call an MCP tool directly (low-level method).

        Args:
            tool_name: Name of the tool to execute
            arguments: Tool arguments as dictionary
            timeout: Optional timeout override (seconds)

        Returns:
            Tool result data

        Raises:
            Exception if tool call fails

        Example:
            result = await client.call_tool(
                "run_untrusted_scan",
                {"targets": "192.168.1.1", "scan_name": "Test"}
            )
        """
        result = await self.client.call_tool(
            tool_name, arguments, timeout=timeout or self.timeout
        )

        # Return the structured data
        return result.data if hasattr(result, "data") else result

    # ==========================================================================
    # High-Level Nessus Operations
    # ==========================================================================

    async def submit_scan(
        self,
        targets: str,
        scan_name: str,
        description: str | None = None,
        scan_type: str = "untrusted",
        idempotency_key: str | None = None,
        timeout: float | None = None,
    ) -> dict[str, Any]:
        """
        Submit a new Nessus scan.

        Args:
            targets: Comma-separated list of targets (IPs, ranges, hostnames)
            scan_name: Human-readable scan name
            description: Optional scan description
            scan_type: "untrusted" or "trusted" (default: "untrusted")
            idempotency_key: Optional key to prevent duplicate submissions
            timeout: Optional timeout override

        Returns:
            Dict with task_id, status, and submission details

        Example:
            task = await client.submit_scan(
                targets="192.168.1.1,192.168.1.10-20",
                scan_name="Weekly Vulnerability Scan",
                description="Automated weekly scan",
                idempotency_key="weekly-scan-2025-01-01"
            )
            print(f"Task ID: {task['task_id']}")
        """
        tool_name = f"run_{scan_type}_scan"

        # Note: MCP tool parameter is 'name', not 'scan_name'
        arguments = {"targets": targets, "name": scan_name}

        if description:
            arguments["description"] = description

        if idempotency_key:
            arguments["idempotency_key"] = idempotency_key

        result = await self.call_tool(tool_name, arguments, timeout=timeout)

        if self.debug:
            print(f"[DEBUG] Submitted scan: {result.get('task_id')}")

        return result

    async def get_status(
        self, task_id: str, timeout: float | None = None
    ) -> dict[str, Any]:
        """
        Get scan task status.

        Args:
            task_id: Task ID from submit_scan()
            timeout: Optional timeout override

        Returns:
            Dict with status, progress, and scan details

        Example:
            status = await client.get_status("nessus-local-20251108-101039")
            print(f"Status: {status['status']}")
            print(f"Progress: {status.get('progress', 0)}%")
        """
        result = await self.call_tool(
            "get_scan_status", {"task_id": task_id}, timeout=timeout
        )

        if self.debug:
            print(
                f"[DEBUG] Task {task_id}: {result.get('status')} ({result.get('progress', 0)}%)"
            )

        return result

    async def get_results(
        self,
        task_id: str,
        schema_profile: str = "brief",
        custom_fields: list[str] | None = None,
        filters: dict[str, Any] | None = None,
        page: int = 1,
        page_size: int = 40,
        timeout: float | None = None,
    ) -> str:
        """
        Get scan results in JSON-NL format.

        Args:
            task_id: Task ID from completed scan
            schema_profile: "minimal", "summary", "brief", or "full"
            custom_fields: Optional list of custom fields (mutually exclusive with schema_profile)
            filters: Optional filters (e.g., {"severity": "4", "cvss_score": ">7.0"})
            page: Page number (1-indexed), or 0 for all data
            page_size: Results per page (10-100)
            timeout: Optional timeout override

        Returns:
            JSON-NL string with schema, metadata, vulnerabilities, pagination

        Example:
            # Get all critical vulnerabilities
            results = await client.get_results(
                task_id="nessus-local-20251108-101039",
                schema_profile="minimal",
                filters={"severity": "4"},
                page=0  # Get all data
            )

            # Parse JSON-NL
            for line in results.strip().split("\n"):
                data = json.loads(line)
                if data["type"] == "vulnerability":
                    print(f"Host: {data['host']}, CVE: {data.get('cve')}")
        """
        arguments = {
            "task_id": task_id,
            "schema_profile": schema_profile,
            "page": page,
            "page_size": page_size,
        }

        if custom_fields:
            arguments["custom_fields"] = custom_fields

        if filters:
            arguments["filters"] = filters

        result = await self.call_tool("get_scan_results", arguments, timeout=timeout)

        if self.debug:
            lines = result.strip().split("\n") if isinstance(result, str) else []
            print(f"[DEBUG] Retrieved {len(lines)} lines of results")

        return result

    async def list_scanners(self, timeout: float | None = None) -> dict[str, Any]:
        """
        List available Nessus scanners.

        Args:
            timeout: Optional timeout override

        Returns:
            Dict with scanner registry information

        Example:
            scanners = await client.list_scanners()
            for scanner in scanners.get("scanners", []):
                print(f"{scanner['name']}: {scanner['enabled']}")
        """
        result = await self.call_tool("list_scanners", {}, timeout=timeout)

        if self.debug:
            count = len(result.get("scanners", []))
            print(f"[DEBUG] Found {count} registered scanners")

        return result

    async def get_queue_status(self, timeout: float | None = None) -> dict[str, Any]:
        """
        Get Redis queue status.

        Args:
            timeout: Optional timeout override

        Returns:
            Dict with main queue and DLQ statistics

        Example:
            queue = await client.get_queue_status()
            print(f"Queue depth: {queue['main_queue_depth']}")
            print(f"DLQ depth: {queue['dlq_depth']}")
        """
        result = await self.call_tool("get_queue_status", {}, timeout=timeout)

        if self.debug:
            print(
                f"[DEBUG] Queue: {result.get('main_queue_depth')}, DLQ: {result.get('dlq_depth')}"
            )

        return result

    async def list_tasks(
        self,
        status: str | None = None,
        limit: int = 100,
        timeout: float | None = None,
    ) -> dict[str, Any]:
        """
        List scan tasks.

        Args:
            status: Optional filter by status ("queued", "running", "completed", "failed")
            limit: Maximum number of tasks to return
            timeout: Optional timeout override

        Returns:
            Dict with task list and total count

        Example:
            tasks = await client.list_tasks(status="completed", limit=10)
            for task in tasks["tasks"]:
                print(f"{task['task_id']}: {task['status']}")
        """
        arguments: dict[str, int | str] = {"limit": limit}
        if status:
            arguments["status_filter"] = status  # Server expects status_filter

        result = await self.call_tool("list_tasks", arguments, timeout=timeout)

        if self.debug:
            print(f"[DEBUG] Found {result.get('total', 0)} tasks")

        return result

    # ==========================================================================
    # Helper Methods
    # ==========================================================================

    async def wait_for_completion(
        self,
        task_id: str,
        timeout: float = 600,
        poll_interval: float = 10,
        progress_callback: Callable[[dict[str, Any]], None] | None = None,
    ) -> dict[str, Any]:
        """
        Wait for a scan task to complete.

        Args:
            task_id: Task ID to monitor
            timeout: Maximum time to wait (seconds)
            poll_interval: How often to check status (seconds)
            progress_callback: Optional callback for progress updates

        Returns:
            Final task status dict

        Raises:
            TimeoutError if task doesn't complete within timeout

        Example:
            def on_progress(status):
                print(f"Progress: {status.get('progress', 0)}%")

            final_status = await client.wait_for_completion(
                task_id="nessus-local-20251108-101039",
                timeout=600,
                progress_callback=on_progress
            )
            print(f"Final status: {final_status['status']}")
        """
        start_time = time.time()

        while True:
            elapsed = time.time() - start_time
            if elapsed > timeout:
                raise TimeoutError(f"Task {task_id} did not complete within {timeout}s")

            status = await self.get_status(task_id)

            # Call progress callback if provided
            if progress_callback:
                progress_callback(status)

            # Check if terminal state
            task_status = status.get("status")
            if task_status in ["completed", "failed", "cancelled"]:
                return status

            # Wait before next poll
            await asyncio.sleep(poll_interval)

    async def scan_and_wait(
        self,
        targets: str,
        scan_name: str,
        description: str | None = None,
        scan_type: str = "untrusted",
        timeout: float = 600,
        poll_interval: float = 10,
        progress_callback: Callable[[dict[str, Any]], None] | None = None,
    ) -> dict[str, Any]:
        """
        Submit a scan and wait for it to complete (convenience method).

        Args:
            targets: Comma-separated list of targets
            scan_name: Human-readable scan name
            description: Optional scan description
            scan_type: "untrusted" or "trusted"
            timeout: Maximum time to wait (seconds)
            poll_interval: How often to check status (seconds)
            progress_callback: Optional callback for progress updates

        Returns:
            Final task status dict

        Example:
            status = await client.scan_and_wait(
                targets="192.168.1.1",
                scan_name="Quick Scan",
                timeout=600
            )

            if status["status"] == "completed":
                results = await client.get_results(status["task_id"])
        """
        # Submit scan
        task = await self.submit_scan(
            targets=targets,
            scan_name=scan_name,
            description=description,
            scan_type=scan_type,
        )

        task_id = task["task_id"]

        # Wait for completion
        return await self.wait_for_completion(
            task_id=task_id,
            timeout=timeout,
            poll_interval=poll_interval,
            progress_callback=progress_callback,
        )

    async def get_critical_vulnerabilities(
        self, task_id: str, timeout: float | None = None
    ) -> list[dict[str, Any]]:
        """
        Get all critical vulnerabilities from a completed scan (helper method).

        Args:
            task_id: Task ID from completed scan
            timeout: Optional timeout override

        Returns:
            List of critical vulnerability dicts

        Example:
            critical = await client.get_critical_vulnerabilities(
                "nessus-local-20251108-101039"
            )
            print(f"Found {len(critical)} critical vulnerabilities")
        """
        # Get results with severity filter
        results = await self.get_results(
            task_id=task_id,
            schema_profile="brief",
            filters={"severity": "4"},
            page=0,  # Get all data
            timeout=timeout,
        )

        # Parse JSON-NL and extract vulnerabilities
        vulnerabilities = []
        for line in results.strip().split("\n"):
            data = json.loads(line)
            if data.get("type") == "vulnerability":
                vulnerabilities.append(data)

        return vulnerabilities

    async def get_vulnerability_summary(
        self, task_id: str, timeout: float | None = None
    ) -> dict[str, int]:
        """
        Get vulnerability count by severity (helper method).

        Args:
            task_id: Task ID from completed scan
            timeout: Optional timeout override

        Returns:
            Dict with counts per severity level

        Example:
            summary = await client.get_vulnerability_summary(
                "nessus-local-20251108-101039"
            )
            print(f"Critical: {summary.get('4', 0)}")
            print(f"High: {summary.get('3', 0)}")
        """
        # Get all results
        results = await self.get_results(
            task_id=task_id, schema_profile="minimal", page=0, timeout=timeout
        )

        # Count by severity
        severity_counts = {"1": 0, "2": 0, "3": 0, "4": 0}

        for line in results.strip().split("\n"):
            data = json.loads(line)
            if data.get("type") == "vulnerability":
                severity = data.get("severity", "0")
                if severity in severity_counts:
                    severity_counts[severity] += 1

        return severity_counts


# =============================================================================
# Convenience Functions
# =============================================================================


async def create_client(
    url: str = "http://localhost:8836/mcp", timeout: float = 30.0, debug: bool = False
) -> NessusFastMCPClient:
    """
    Create and connect a Nessus FastMCP client (convenience function).

    Args:
        url: MCP server HTTP endpoint
        timeout: Default timeout for requests
        debug: Enable debug logging

    Returns:
        Connected NessusFastMCPClient instance

    Example:
        client = await create_client(debug=True)
        try:
            await client.ping()
        finally:
            await client.__aexit__(None, None, None)
    """
    client = NessusFastMCPClient(url=url, timeout=timeout, debug=debug)
    await client.__aenter__()
    return client
