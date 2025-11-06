"""Direct ASGI test without uvicorn."""
import asyncio
import os
os.environ.setdefault("DATA_DIR", "/app/data/tasks")

async def test_asgi_call():
    """Test ASGI app directly."""
    print("Importing app...")
    from tools.mcp_server import app

    print(f"App type: {type(app)}")
    print(f"App routes: {[r.path for r in app.routes]}")

    # Create a test HTTP scope for /mcp GET
    scope = {
        'type': 'http',
        'asgi': {'version': '3.0'},
        'http_version': '1.1',
        'method': 'GET',
        'scheme': 'http',
        'path': '/mcp',
        'query_string': b'',
        'root_path': '',
        'headers': [
            [b'host', b'localhost:8000'],
            [b'user-agent', b'test'],
        ],
        'server': ('localhost', 8000),
        'client': ('127.0.0.1', 50000),
    }

    received_messages = []
    sent_messages = []

    async def receive():
        # Simulate receiving the request
        if not received_messages:
            received_messages.append({'type': 'http.request', 'body': b''})
        return received_messages[-1]

    async def send(message):
        print(f"  SEND: {message['type']}")
        sent_messages.append(message)

    print("\nCalling ASGI app with GET /mcp...")
    try:
        await app(scope, receive, send)
        print(f"\n✓ Call completed")
        print(f"  Sent {len(sent_messages)} messages:")
        for msg in sent_messages:
            print(f"    - {msg['type']}: {msg.get('status', 'N/A')}")
    except Exception as e:
        print(f"\n✗ Exception: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_asgi_call())
