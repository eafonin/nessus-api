# Minimal Fix Summary: Task Group Bug

## 🎯 Bottom Line

**THE ONLY FIX NEEDED**: Pin `starlette==0.49.1` and `anyio==4.6.2.post1`

**TRANSPORT CHOICE**: Irrelevant. Both SSE and StreamableHTTP use Server-Sent Events internally.

---

## 🚨 Critical Discovery

**StreamableHTTP == SSE** (they're the same thing!)

When I tested `streamable_http_app()`, the server responded with:
```
Content-Type: text/event-stream
event: message
data: {"jsonrpc":"2.0",...}
```

**This proves**: StreamableHTTP uses SSE for server→client communication.

---

## What Actually Fixes The Bug

### ✅ Required Changes
```txt
# requirements-api.txt
starlette==0.49.1
anyio==4.6.2.post1
```

That's it. These version pins fix the "Task group is not initialized" error.

### ❌ NOT Required
- Switching from `sse_app()` to `streamable_http_app()`
- Removing SSE dependencies (they're needed by both transports)
- Any code changes besides version pins

---

## Transport Comparison

| Aspect | `sse_app()` | `streamable_http_app()` |
|--------|-------------|-------------------------|
| **Uses SSE?** | ✅ Yes (explicit) | ✅ Yes (hidden) |
| **Deprecated?** | ❌ No | ⚠️ Yes (as of 2.3.2) |
| **Endpoints** | GET /mcp (SSE stream) | POST /mcp (SSE stream) |
| **Clarity** | Clear about using SSE | Misleading name |
| **SSE Gotchas Apply?** | ✅ Yes | ✅ Yes (same) |

**Recommendation**: Use `sse_app()` - it's clearer and not deprecated.

---

## Changes Made (Current State)

### mcp-server/tools/mcp_server.py
```python
# BEFORE (SSE - explicit)
app = mcp.sse_app(path="/mcp")

# TRIED (StreamableHTTP - misleading)
app = mcp.streamable_http_app(path="/mcp")  # Deprecated!
# ^ Still uses SSE internally!

# AFTER (back to SSE - best choice)
app = mcp.sse_app(path="/mcp")
```

### requirements-api.txt
```txt
# CRITICAL VERSION PINS (the actual fix)
starlette==0.49.1
anyio==4.6.2.post1

# SSE dependencies (pulled in by mcp>=1.18.0)
# sse-starlette installed automatically as transitive dependency
```

### client/client_smoke.py
```python
# Match server transport
from mcp.client.sse import sse_client

async with sse_client(url) as (read, write):
    # Works!
```

---

## Why All SSE Gotchas Still Apply

Both transports use SSE, which means:

### Operational Requirements
1. ⚠️ **Proxy Buffering**: Must disable (`X-Accel-Buffering: no`)
2. ⚠️ **Long Timeouts**: Need 3600s+ for long-lived connections
3. ⚠️ **Multi-Worker**: Requires sticky sessions OR Redis pub/sub
4. ℹ️ **Heartbeats**: Should implement for connection health
5. ℹ️ **Observability**: Access logs won't close until stream ends

### Why?
Because **both transports** use `Content-Type: text/event-stream` for responses.

---

## Test Results

### ✅ What Works
```bash
# Server responds correctly
curl -H "Accept: application/json, text/event-stream" \
     -X POST http://localhost:8000/mcp \
     -d '{"jsonrpc":"2.0","id":1,"method":"initialize",...}'

# Response: 200 OK
# Content-Type: text/event-stream
# Body: event: message\ndata: {...}
```

### ✅ Version Pins Work
- `starlette==0.49.1` + `anyio==4.6.2.post1`
- Lifespan context enters successfully
- Task group initializes correctly
- No RuntimeError

### ❌ What Doesn't Help
- Switching to `streamable_http_app()` (same behavior)
- Trying to avoid SSE (impossible with current MCP SDK)
- Removing SSE dependencies (needed by both transports)

---

## Minimal Required Changes (Final)

### 1. Pin Versions (requirements-api.txt)
```txt
starlette==0.49.1
anyio==4.6.2.post1
```

### 2. Choose Transport (mcp_server.py)
```python
# Option A: SSE (recommended - clear, not deprecated)
app = mcp.sse_app(path="/mcp")

# Option B: StreamableHTTP (not recommended - deprecated, misleading)
app = mcp.streamable_http_app(path="/mcp")
# ^ Same as Option A internally!
```

### 3. Match Client Transport
```python
# If using sse_app():
from mcp.client.sse import sse_client
async with sse_client(url) as (read, write):
    ...

# If using streamable_http_app():
from mcp.client.streamable_http import streamablehttp_client
async with streamablehttp_client(url) as (read, write, _):
    ...
# ^ Both use SSE for server→client!
```

---

## Recommendation

### Phase 0 (Current)
✅ **Keep using `sse_app()`**
- Explicit about using SSE
- Not deprecated
- Clearer for future maintainers
- Same behavior as StreamableHTTP

### Why Not StreamableHTTP?
1. Deprecated (warning: "Use http_app() instead")
2. Misleading name (actually uses SSE)
3. No operational benefit (same SSE gotchas)
4. Less clear for documentation

---

## Lessons Learned

### What We Thought
"StreamableHTTP might be simpler than SSE"

### What We Found
"StreamableHTTP **IS** SSE (with a different API)"

### The Real Fix
"Just pin `starlette==0.49.1` and `anyio==4.6.2.post1`"

---

## Files Modified

1. **mcp-server/tools/mcp_server.py**
   - Back to `sse_app()`
   - Added documentation about SSE requirements

2. **mcp-server/client/client_smoke.py**
   - Back to `sse_client()`
   - Updated comments with findings

3. **mcp-server/requirements-api.txt**
   - Version pins (the actual fix)
   - Updated comments

4. **Documentation**
   - MINIMAL_FIX_SUMMARY.md (this file)
   - ALTERNATIVE_FIX_ANALYSIS.md (detailed comparison)
   - SSE_GOTCHAS_RESPONSES.md (operational gotchas)
   - ULTRATHINK_SUMMARY.md (original analysis - now outdated)

---

## Next Steps

### For Phase 1
1. Add SSE operational mitigations (see SSE_GOTCHAS_RESPONSES.md)
2. Implement heartbeats (20s interval)
3. Add observability middleware
4. Choose scaling strategy (sticky sessions or Redis)

### For Future Versions
Monitor upstream for bug fix:
- https://github.com/modelcontextprotocol/python-sdk/issues/1467
- Test with `starlette>=0.50.0` + `anyio>=4.11.0`
- Unpin when confirmed stable

---

## Summary

**The bug**: anyio 4.11+ + starlette 0.50+ breaks task group initialization
**The fix**: Pin to anyio==4.6.2.post1 + starlette==0.49.1
**Transport choice**: Irrelevant (both use SSE)
**Recommendation**: Use `sse_app()` (clearer, not deprecated)
**Complexity**: Same for both transports (all SSE gotchas apply)

---

*Analysis completed: 2025-11-06*
*Generated with Claude Code*
