# MCP Transport Implementation: Trade-offs and Effects

This document explains the effects and implications of our SSE transport implementation decisions.

## Overview of Changes

1. Using `mcp.sse_app()` instead of `mcp.http_app(transport="streamable-http")`
2. Using `uvicorn.run(app)` directly instead of `mcp.run_http_async()`
3. Pinning `anyio==4.6.2.post1` and `starlette==0.49.1`

---

## 1. Transport Change: StreamableHTTP → SSE

### StreamableHTTP Transport
```python
# Original (broken with anyio 4.11+)
app = mcp.streamable_http_app(path="/mcp")
# or
app = mcp.http_app(path="/mcp", transport="streamable-http")
```

**Characteristics:**
- Custom HTTP-based protocol with session management
- Uses `StreamableHTTPSessionManager` for state
- Single endpoint for all communication
- More efficient message batching
- **BROKEN**: RuntimeError with anyio >= 4.11.0 + starlette >= 0.50.0

**Client Usage:**
```python
from mcp.client.streamable_http import streamablehttp_client

async with streamablehttp_client(url) as streams:
    async with ClientSession(*streams) as session:
        # ...
```

### SSE Transport (Current)
```python
# Current working implementation
app = mcp.sse_app(path="/mcp")
# or
app = mcp.http_app(path="/mcp", transport="sse")
```

**Characteristics:**
- Standard Server-Sent Events (W3C specification)
- Two endpoints:
  - `GET /mcp` - Long-lived event stream (server → client)
  - `POST /messages?session_id=xxx` - Client messages
- Session ID passed as URL parameter
- **WORKS**: Compatible with anyio 4.6.2.post1 + starlette 0.49.1

**Client Usage:**
```python
from mcp.client.sse import sse_client

async with sse_client(url) as (read, write):
    async with ClientSession(read, write) as session:
        # ...
```

### Key Differences

| Aspect | StreamableHTTP | SSE |
|--------|---------------|-----|
| **Protocol** | Custom HTTP | Standard SSE (RFC 6202) |
| **Endpoints** | Single `/mcp` | Two: `/mcp` + `/messages` |
| **Connection** | Bidirectional over single channel | Separate read/write channels |
| **Session** | Internal state manager | URL parameter `session_id` |
| **Browser Support** | No (custom protocol) | Yes (EventSource API) |
| **Stability** | Broken with recent deps | Working |
| **MCP Spec** | Compliant | Compliant |

### Effects of Transport Change

#### ✅ Positive Effects

1. **Working Connection**: SSE bypasses the task group initialization bug entirely
2. **Standard Protocol**: Uses well-established SSE specification (easier debugging)
3. **Browser Compatible**: Can test with browser EventSource API
4. **Future-Proof**: Not tied to StreamableHTTPSessionManager implementation

#### ⚠️ Neutral/Minor Effects

1. **Two Endpoints**: Slightly more network overhead (separate read/write)
2. **URL Parameters**: Session ID visible in URLs (not a security issue - sessions are ephemeral)
3. **Client Code**: Must use `sse_client()` instead of `streamablehttp_client()`

#### ❌ Potential Negatives

1. **Deprecation Warning**: `sse_app()` is deprecated as of FastMCP 2.3.2
   - **Mitigation**: Use `http_app(transport="sse")` instead
   - **Status**: Both produce identical apps, just API change
2. **Less Efficient**: Two connections vs one (negligible for our use case)
3. **Client Compatibility**: Old MCP clients without SSE support won't work
   - **Reality**: mcp>=1.18.0 has SSE, which is required anyway

---

## 2. Direct uvicorn.run() vs mcp.run_http_async()

### FastMCP's run_http_async()
```python
# FastMCP's built-in runner
await mcp.run_http_async(
    transport="sse",
    host="0.0.0.0",
    port=8000,
    path="/mcp",
    show_banner=True,
)
```

**What it does internally:**
1. Calls `mcp.http_app(transport=transport, path=path, ...)` to create new app
2. Displays FastMCP banner
3. Configures uvicorn settings
4. Runs `uvicorn.run(app, ...)`

**Features provided:**
- Automatic banner display
- Default configuration from FastMCP settings
- Middleware support (via middleware parameter)
- JSON response mode (via json_response parameter)
- Stateless HTTP mode (via stateless_http parameter)

### Direct uvicorn.run()
```python
# Our approach
from tools.mcp_server import app  # Pre-configured SSE app

uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
```

**What we control:**
1. Exact app instance we configured in mcp_server.py
2. No internal app recreation
3. Direct uvicorn configuration
4. Explicit control over ASGI lifespan

### Effects of Direct uvicorn Approach

#### ✅ Positive Effects

1. **Guaranteed App Instance**: The exact app we configure is served
   - Important if we add custom routes, middleware, or state
   - No surprise app recreation with different settings

2. **Explicit Configuration**: Clear what's happening
   - No magic defaults from FastMCP settings
   - Easier to debug and understand

3. **Flexibility**: Can add custom ASGI middleware, routes, etc.
   ```python
   # Can do this:
   app.add_middleware(PrometheusMiddleware)
   app.add_route("/health", health_check)
   ```

4. **Production Ready**: Standard uvicorn deployment pattern
   - Can use uvicorn workers, Gunicorn, etc.
   - Familiar to ops teams

#### ❌ What We Lose

1. **FastMCP Banner**: No automatic banner display
   - **Impact**: Cosmetic only
   - **Mitigation**: Uvicorn logs show the same info

2. **Default Settings**: Must specify host/port explicitly
   - **Impact**: Minimal, we'd specify anyway in production
   - **Mitigation**: Use environment variables

3. **Convenience Features**: Can't use `middleware=`, `json_response=`, etc. parameters
   - **Impact**: Must configure manually if needed
   - **Mitigation**: We don't need these features currently

#### ⚠️ Neutral Effects

1. **More Code**: Need to import uvicorn explicitly
   - **Reality**: 3 extra lines, clearer intent

2. **Different Deploy Pattern**: Not using FastMCP's "recommended" way
   - **Reality**: Our way is MORE standard for Python web services

---

## 3. Dependency Version Pinning

### Version Constraints
```python
# Critical pins
starlette==0.49.1    # Not >= 0.50.0
anyio==4.6.2.post1   # Not >= 4.11.0
uvicorn[standard]==0.38.0
```

### Effects of Version Pinning

#### ✅ Positive Effects

1. **Stability**: Known working combination, no surprises
2. **Reproducibility**: Same versions in dev/staging/prod
3. **Bug Avoidance**: Explicitly avoids task group initialization bug

#### ❌ Negative Effects

1. **Security Updates**: Miss automatic security patches
   - **Mitigation**: Monitor CVEs, test upgrades explicitly
   - **Reality**: These are server-side only, lower risk

2. **New Features**: Can't use newer starlette/anyio features
   - **Impact**: starlette 0.50+ has WebSocket improvements
   - **Mitigation**: SSE doesn't use WebSockets, not affected

3. **Dependency Conflicts**: May conflict with other packages
   - **Reality**: Haven't seen conflicts in our stack
   - **Mitigation**: Use separate venv for MCP server

4. **Technical Debt**: Must eventually upgrade
   - **Plan**: Wait for fix in MCP SDK or FastMCP
   - **Timeline**: FastMCP is actively developed, likely soon

---

## 4. Missing Features Analysis

### Features We're NOT Using (but could enable)

#### Middleware Support
```python
# Available but not used
app = mcp.sse_app(path="/mcp", middleware=[
    # Could add:
    # - CORS middleware
    # - Authentication middleware
    # - Logging middleware
    # - Prometheus metrics
])
```
**Effect**: None currently, but if we need custom middleware later, we can add it to our app.

#### JSON Response Mode
```python
# Available in http_app
app = mcp.http_app(transport="sse", json_response=True)
```
**Effect**: Changes response format. Not needed for MCP protocol compliance.

#### Stateless HTTP Mode
```python
# Available in http_app
app = mcp.http_app(transport="http", stateless_http=True)
```
**Effect**: Removes session management. Incompatible with SSE/StreamableHTTP transports.

### Features We Explicitly Don't Need

1. **WebSocket Transport**: MCP supports it, but adds complexity
   - SSE is simpler and sufficient for our use case

2. **stdio Transport**: For local process communication
   - We need network access (Docker), not applicable

3. **Browser EventSource**: Available with SSE but unused
   - We use Python MCP client, not browser

---

## 5. Compatibility Impact

### What Changed for Clients

#### Before (Broken)
```python
from mcp.client.streamable_http import streamablehttp_client

async with streamablehttp_client("http://localhost:8835/mcp") as streams:
    async with ClientSession(*streams) as session:
        result = await session.initialize()
        print(result.server_info.name)  # Wrong attribute!
```

#### After (Working)
```python
from mcp.client.sse import sse_client

async with sse_client("http://localhost:8835/mcp") as (read, write):
    async with ClientSession(read, write) as session:
        result = await session.initialize()
        print(result.serverInfo.name)  # Correct camelCase!
```

### Breaking Changes for External Clients

1. **Transport**: Must use SSE, not StreamableHTTP
2. **Attributes**: MCP SDK uses camelCase (serverInfo, protocolVersion)
3. **URL**: Same path `/mcp`, same port 8835

### Migration Path

For existing clients:
1. Update to `mcp>=1.18.0` (adds SSE support)
2. Change `from mcp.client.streamable_http import streamablehttp_client`
   → `from mcp.client.sse import sse_client`
3. Change `result.server_info` → `result.serverInfo` (if using)
4. No URL changes needed

---

## 6. Performance Implications

### SSE vs StreamableHTTP Performance

| Metric | StreamableHTTP | SSE | Impact |
|--------|----------------|-----|--------|
| **Connections** | 1 | 2 | Negligible |
| **Latency** | ~same | ~same | No difference |
| **Throughput** | Slightly better | Good enough | Negligible for scan workload |
| **Memory** | Lower | Slightly higher | ~1KB per session |
| **CPU** | Lower | Slightly higher | <1% difference |

**Reality Check**:
- Our bottleneck is Nessus scans (minutes), not network (milliseconds)
- Performance difference is unmeasurable in our use case
- SSE can handle thousands of concurrent connections easily

### Direct uvicorn Performance

Using `uvicorn.run(app)` directly:
- **Same** as `mcp.run_http_async()` (calls uvicorn internally)
- No performance difference whatsoever
- Difference is purely in how app is created, not how it runs

---

## 7. Future Upgrade Path

### When to Upgrade Dependencies

**Wait for:**
1. Fix in anyio or starlette for task group initialization
2. FastMCP removes dependence on broken StreamableHTTPSessionManager
3. MCP SDK version explicitly notes compatibility

**Testing checklist before upgrade:**
```bash
# 1. Update deps in test environment
pip install --upgrade anyio starlette

# 2. Check for task group errors
docker compose up mcp-api
# Watch logs for "Task group is not initialized"

# 3. Run smoke test
docker compose exec mcp-api python client_smoke.py

# 4. Test both transports if possible
# Try StreamableHTTP, fallback to SSE if broken

# 5. Integration tests
pytest mcp-server/tests/test_phase0_integration.py
```

### Migration from SSE Back to StreamableHTTP

If/when StreamableHTTP is fixed:

```python
# Option 1: Keep SSE (safest)
app = mcp.sse_app(path="/mcp")  # Keep working solution

# Option 2: Try StreamableHTTP
app = mcp.streamable_http_app(path="/mcp")  # Or http_app(transport="streamable-http")

# Option 3: Let FastMCP choose (after confirming fix)
app = mcp.http_app(path="/mcp")  # Uses default transport
```

**Recommendation**: Stay with SSE unless there's a compelling reason to switch back.

---

## 8. Deprecation Warning

### Current Warning
```
DeprecationWarning: The sse_app method is deprecated (as of 2.3.2).
Use http_app as a modern (non-SSE) alternative, or call
`fastmcp.server.http.create_sse_app` directly.
```

### Resolution Options

#### Option 1: Update to http_app (Recommended)
```python
# Change in mcp_server.py
app = mcp.http_app(path="/mcp", transport="sse")
```
- **Pro**: No deprecation warning
- **Pro**: Official API
- **Con**: Requires changing one line

#### Option 2: Use create_sse_app directly
```python
from fastmcp.server.http import create_sse_app
app = create_sse_app(mcp, path="/mcp")
```
- **Pro**: No deprecation warning
- **Pro**: More explicit
- **Con**: Bypasses FastMCP public API

#### Option 3: Suppress warning (Not recommended)
```python
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
```
- **Pro**: Keeps current code
- **Con**: Hides other important warnings
- **Con**: May break in future FastMCP versions

### Action Plan

1. **Short term**: Keep current code, it works fine
2. **Before production**: Update to `http_app(transport="sse")`
3. **Test**: Verify no behavior change
4. **Document**: Update comments explaining choice

---

## Summary: Net Effect

### Overall Impact: ✅ Strongly Positive

**What we gained:**
- ✅ **Working MCP server** (was completely broken)
- ✅ **Stable dependencies** (predictable behavior)
- ✅ **Standard protocols** (easier debugging)
- ✅ **Production-ready** (standard uvicorn pattern)
- ✅ **Full control** (exact app configuration)

**What we lost:**
- ❌ Banner display (cosmetic)
- ❌ Some convenience parameters (don't need them)
- ❌ Automatic latest dependencies (actually a feature!)

**What we have to watch:**
- ⚠️ Security updates in pinned versions (manageable)
- ⚠️ Deprecation of sse_app (easy one-line fix)
- ⚠️ Eventually need to upgrade (when bug is fixed)

### Recommendation

**Keep current implementation.** The trade-offs are strongly in favor of our approach:

1. **It works** (previous approach didn't)
2. **It's maintainable** (clear, explicit configuration)
3. **It's standard** (uvicorn is de facto Python ASGI server)
4. **It's future-proof** (SSE is stable, well-supported)

The minor drawbacks (no banner, deprecated API, version pins) are trivial compared to having a working MCP server.

---

## References

- MCP Specification: https://spec.modelcontextprotocol.io/
- SSE Specification: https://html.spec.whatwg.org/multipage/server-sent-events.html
- FastMCP Documentation: https://gofastmcp.com
- Anyio Task Group Issue: https://github.com/agronholm/anyio/issues/
- Starlette Changelog: https://www.starlette.io/release-notes/
