"""Simple SSE connection test."""
import asyncio
import sys

async def test_sse():
    """Test basic SSE connection."""
    try:
        from mcp.client.sse import sse_client
        from mcp.client.session import ClientSession

        url = "http://127.0.0.1:8835/mcp"
        print(f"Connecting to {url}...")

        # Set a shorter timeout for testing
        async with asyncio.timeout(10):
            async with sse_client(url) as (read, write):
                print("✓ SSE client connected!")

                async with ClientSession(read, write) as session:
                    print("✓ ClientSession created!")

                    # Try initialize
                    print("Sending initialize request...")
                    result = await session.initialize()

                    print(f"✓ Initialize successful!")
                    print(f"  Server: {result.server_info.name}")
                    print(f"  Version: {result.server_info.version}")

                    return True

    except asyncio.TimeoutError:
        print("✗ Timeout waiting for server response")
        return False
    except Exception as e:
        print(f"✗ Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    result = asyncio.run(test_sse())
    sys.exit(0 if result else 1)
