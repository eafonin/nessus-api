# FastMCP Client Development Requirement

> **MANDATORY**: All future development iterations MUST use the FastMCP Client for testing and integration

## Overview

Starting immediately, **all development work** involving the Nessus MCP Server must use the `NessusFastMCPClient` for testing, debugging, and integration.

**This is a mandatory requirement, not a recommendation.**

---

## Requirement

### DO use FastMCP Client

```python
# ✅ CORRECT - Use FastMCP Client
async with NessusFastMCPClient("http://localhost:8835/mcp") as client:
    task = await client.submit_scan(targets="192.168.1.1", scan_name="Test")
    assert task["status"] == "queued"
```

### DO NOT use direct HTTP/curl

```bash
# ✗ INCORRECT - Do not use curl or direct HTTP
curl -X POST http://localhost:8835/mcp -d '{"method": "tools/call", ...}'
```

---

## Rationale

### 1. Type Safety

**Problem**: Manual HTTP requests have no type checking
**Solution**: Client provides typed method signatures

```python
# Type-safe method signature
async def submit_scan(
    self,
    targets: str,
    scan_name: str,
    description: Optional[str] = None,
    scan_type: str = "untrusted",
    timeout: Optional[float] = None
) -> Dict[str, Any]:
```

**Benefit**: Catch errors at development time, not runtime

### 2. Consistency

**Problem**: Multiple ways to call same API leads to inconsistency
**Solution**: Single, standardized client interface

**Benefit**: All code uses same patterns, easier to maintain

### 3. Testability

**Problem**: Integration tests with curl are brittle and hard to debug
**Solution**: Client provides clean, Pythonic test interface

```python
# ✅ Clean test code
async def test_scan_submission():
    async with NessusFastMCPClient() as client:
        task = await client.submit_scan(targets="192.168.1.1", scan_name="Test")
        assert task["status"] == "queued"
```

**Benefit**: Tests are readable, maintainable, and reliable

### 4. Debugging

**Problem**: Debugging curl commands is painful
**Solution**: Client has built-in debug mode

```python
# ✅ Enable debug logging
client = NessusFastMCPClient(debug=True)
# Prints all requests/responses
```

**Benefit**: Faster debugging, better visibility into requests

### 5. Error Handling

**Problem**: Manual HTTP requires custom error parsing
**Solution**: Client provides structured error handling

```python
try:
    task = await client.submit_scan(...)
except TimeoutError:
    # Handle timeout
except ConnectionError:
    # Handle connection issues
except ValueError:
    # Handle invalid parameters
```

**Benefit**: Clear, predictable error handling

---

## Applications

### Use Case 1: Integration Tests

**Old way** (manual HTTP):
```python
import requests
response = requests.post(
    "http://localhost:8835/mcp",
    json={"method": "tools/call", "params": {"name": "run_untrusted_scan", ...}}
)
result = response.json()["result"]["content"][0]["text"]
task = json.loads(result)
```

**New way** (FastMCP Client):
```python
async with NessusFastMCPClient() as client:
    task = await client.submit_scan(targets="192.168.1.1", scan_name="Test")
```

**Improvement**: 5 lines → 2 lines, type-safe, readable

### Use Case 2: Debugging

**Old way** (curl):
```bash
curl -X POST http://localhost:8835/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "id": 1, "method": "tools/call", ...}'
```

**New way** (FastMCP Client):
```python
async with NessusFastMCPClient(debug=True) as client:
    task = await client.submit_scan(...)
# Automatic request/response logging
```

**Improvement**: No manual JSON formatting, built-in logging

### Use Case 3: Production Code

**Old way** (requests library):
```python
import requests

def submit_scan(targets, scan_name):
    response = requests.post(
        "http://localhost:8835/mcp",
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "run_untrusted_scan",
                "arguments": {
                    "targets": targets,
                    "scan_name": scan_name
                }
            }
        }
    )
    # Parse nested response structure
    result = response.json()["result"]["content"][0]["text"]
    return json.loads(result)
```

**New way** (FastMCP Client):
```python
async with NessusFastMCPClient() as client:
    task = await client.submit_scan(targets, scan_name)
```

**Improvement**: 20+ lines → 2 lines, no manual protocol handling

---

## Enforcement

### Code Review Checklist

When reviewing code, **REJECT** any PR that:
- [ ] Uses `curl` for MCP server interaction
- [ ] Uses `requests` library for MCP endpoints
- [ ] Manually constructs MCP protocol messages
- [ ] Does not use `NessusFastMCPClient` for testing

**APPROVE** PRs that:
- [x] Use `NessusFastMCPClient` for all MCP operations
- [x] Have type hints on client method calls
- [x] Include error handling
- [x] Use async/await properly

### Examples of Acceptable Code

**Testing**:
```python
@pytest.mark.asyncio
async def test_scan_workflow():
    async with NessusFastMCPClient() as client:
        task = await client.submit_scan(targets="192.168.1.1", scan_name="Test")
        status = await client.wait_for_completion(task["task_id"], timeout=600)
        assert status["status"] == "completed"
```

**Production**:
```python
async def automated_scan(targets: List[str]):
    async with NessusFastMCPClient() as client:
        tasks = []
        for target in targets:
            task = await client.submit_scan(target, f"Scan-{target}")
            tasks.append(task)
        return tasks
```

**Debugging**:
```python
async with NessusFastMCPClient(debug=True) as client:
    task = await client.submit_scan(targets="192.168.1.1", scan_name="Debug")
    # Check logs for request/response details
```

---

## Documentation References

### Client Documentation

1. **Implementation**: [`client/nessus_fastmcp_client.py`](./client/nessus_fastmcp_client.py)
   - Source code for `NessusFastMCPClient`
   - All method signatures and docstrings
   - 740 lines of documented code

2. **Architecture**: [`FASTMCP_CLIENT_ARCHITECTURE.md`](./FASTMCP_CLIENT_ARCHITECTURE.md)
   - Complete architecture documentation
   - Detailed data flow diagrams
   - Component interaction patterns

3. **Examples**: [`client/examples/`](./client/examples/)
   - 5 progressive examples
   - From basic usage to complete workflows
   - Copy-paste ready code

4. **Tests**: [`tests/integration/test_fastmcp_client.py`](./tests/integration/test_fastmcp_client.py)
   - Comprehensive test suite
   - Integration test patterns
   - Reference implementations

### FastMCP Documentation

5. **FastMCP Client Basics**: `@docs/fastMCPServer/clients/client.md`
   - Official FastMCP client documentation
   - Protocol details
   - Transport layer

6. **Tool Operations**: `@docs/fastMCPServer/clients/tools.md`
   - Tool invocation patterns
   - Result handling

7. **HTTP Transport**: `@docs/fastMCPServer/clients/transports.md`
   - HTTP/SSE transport details
   - Connection management

---

## Migration Guide

### For Existing Code Using curl

**Before**:
```bash
#!/bin/bash
curl -X POST http://localhost:8835/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
      "name": "run_untrusted_scan",
      "arguments": {
        "targets": "192.168.1.1",
        "scan_name": "Weekly Scan"
      }
    }
  }'
```

**After**:
```python
#!/usr/bin/env python3
import asyncio
from client.nessus_fastmcp_client import NessusFastMCPClient

async def main():
    async with NessusFastMCPClient() as client:
        task = await client.submit_scan(
            targets="192.168.1.1",
            scan_name="Weekly Scan"
        )
        print(f"Task ID: {task['task_id']}")

if __name__ == "__main__":
    asyncio.run(main())
```

### For Existing Code Using requests

**Before**:
```python
import requests

response = requests.post(
    "http://localhost:8835/mcp",
    json={"method": "tools/call", "params": {"name": "get_scan_status", "arguments": {"task_id": task_id}}}
)
status = json.loads(response.json()["result"]["content"][0]["text"])
```

**After**:
```python
from client.nessus_fastmcp_client import NessusFastMCPClient

async with NessusFastMCPClient() as client:
    status = await client.get_status(task_id)
```

---

## FAQ

### Q: Can I still use curl for quick testing?

**A**: No. Use the FastMCP client even for quick tests. It's actually faster:

```python
# Quick test (one-liner)
python -c "import asyncio; from client.nessus_fastmcp_client import NessusFastMCPClient; asyncio.run(NessusFastMCPClient().__aenter__().ping())"
```

Or use example scripts:
```bash
python client/examples/01_basic_usage.py
```

### Q: What about CI/CD pipelines?

**A**: Use the client in CI/CD. It's more reliable than curl:

```yaml
# .github/workflows/test.yml
- name: Run integration tests
  run: |
    pytest tests/integration/test_fastmcp_client.py -v
```

### Q: What about performance?

**A**: The client has negligible overhead (<1ms per request) and provides connection pooling, which is **faster** than repeated curl calls.

### Q: Can I use the client synchronously?

**A**: No, the client is async-only. Use `asyncio.run()`:

```python
import asyncio
from client.nessus_fastmcp_client import NessusFastMCPClient

def main():
    async def _inner():
        async with NessusFastMCPClient() as client:
            return await client.submit_scan(...)
    return asyncio.run(_inner())
```

### Q: What if I need custom HTTP headers?

**A**: The client inherits from FastMCP Client, which supports custom headers. See `@docs/fastMCPServer/clients/transports.md` for configuration options.

---

## Summary

### Requirements

1. ✅ **MUST** use `NessusFastMCPClient` for all MCP server interactions
2. ✅ **MUST** use async/await patterns
3. ✅ **MUST** include error handling
4. ✅ **MUST** use type hints

### Prohibited

1. ✗ **MUST NOT** use `curl` for MCP server interaction
2. ✗ **MUST NOT** use `requests` library for MCP endpoints
3. ✗ **MUST NOT** manually construct MCP protocol messages
4. ✗ **MUST NOT** skip client in tests "for simplicity"

### Resources

- **Client code**: [`client/nessus_fastmcp_client.py`](./client/nessus_fastmcp_client.py)
- **Examples**: [`client/examples/`](./client/examples/)
- **Architecture**: [`FASTMCP_CLIENT_ARCHITECTURE.md`](./FASTMCP_CLIENT_ARCHITECTURE.md)
- **Tests**: [`tests/integration/test_fastmcp_client.py`](./tests/integration/test_fastmcp_client.py)

---

**Last Updated**: 2025-11-08
**Version**: 1.0
**Status**: **MANDATORY REQUIREMENT**
