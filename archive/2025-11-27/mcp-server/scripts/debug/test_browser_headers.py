#!/usr/bin/env python3
"""
Test if browser headers prevent HTTP 412 ReadError.

Compare two approaches:
1. Minimal headers (current scanner implementation)
2. Full browser simulation (wrapper implementation)
"""
import httpx
import asyncio
import sys

NESSUS_URL = "https://172.32.0.209:8834"
USERNAME = "nessus"
PASSWORD = "nessus"
STATIC_API_TOKEN = "af824aba-e642-4e63-a49b-0810542ad8a5"


async def authenticate(client: httpx.AsyncClient) -> str:
    """Get session token."""
    response = await client.post(
        f'{NESSUS_URL}/session',
        headers={
            'Content-Type': 'application/json',
            'X-API-Token': STATIC_API_TOKEN
        },
        json={'username': USERNAME, 'password': PASSWORD}
    )
    return response.json()['token']


async def test_minimal_headers(session_token: str):
    """Test with minimal headers (current scanner approach)."""
    print("=" * 80)
    print("TEST 1: MINIMAL HEADERS (Current Scanner)")
    print("=" * 80)

    headers = {
        'Content-Type': 'application/json',
        'X-API-Token': STATIC_API_TOKEN,
        'X-Cookie': f'token={session_token}'
    }

    payload = {
        "uuid": "ad629e16-03b6-8c1d-cef6-ef8c9dd3c658d24bd260ef5f9e66",
        "settings": {
            "name": "TEST_minimal_headers",
            "description": "Testing minimal headers",
            "text_targets": "172.32.0.215",
            "launch": "ONETIME",
            "enabled": False,
            "folder_id": 3,
            "scanner_id": 1
        }
    }

    print(f"Headers: {list(headers.keys())}")
    print(f"POST {NESSUS_URL}/scans")

    try:
        async with httpx.AsyncClient(verify=False, timeout=30.0) as client:
            response = await client.post(
                f'{NESSUS_URL}/scans',
                headers=headers,
                json=payload
            )

            print(f"✓ SUCCESS: Status {response.status_code}")
            print(f"Response: {response.text[:200]}")
            return True

    except httpx.ReadError as e:
        print(f"✗ FAILED: httpx.ReadError")
        print(f"Error: {e}")
        return False
    except Exception as e:
        print(f"✗ FAILED: {type(e).__name__}: {e}")
        return False


async def test_browser_headers(session_token: str):
    """Test with full browser simulation (wrapper approach)."""
    print("\n" + "=" * 80)
    print("TEST 2: FULL BROWSER HEADERS (Wrapper Approach)")
    print("=" * 80)

    headers = {
        'Accept': '*/*',
        'Accept-Encoding': 'gzip, deflate, br, zstd',
        'Accept-Language': 'en-US,en;q=0.9,ru;q=0.8',
        'Connection': 'keep-alive',
        'Content-Type': 'application/json',
        'Host': '172.32.0.209:8834',
        'Origin': f'https://172.32.0.209:8834',
        'Referer': f'https://172.32.0.209:8834/',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-origin',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36',
        'X-API-Token': STATIC_API_TOKEN,
        'X-Cookie': f'token={session_token}',
        'sec-ch-ua': '"Google Chrome";v="141", "Not?A_Brand";v="8", "Chromium";v="141"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"'
    }

    payload = {
        "uuid": "ad629e16-03b6-8c1d-cef6-ef8c9dd3c658d24bd260ef5f9e66",
        "settings": {
            "name": "TEST_browser_headers",
            "description": "Testing browser headers",
            "text_targets": "172.32.0.215",
            "launch": "ONETIME",
            "enabled": False,
            "folder_id": 3,
            "scanner_id": 1
        }
    }

    print(f"Headers: {list(headers.keys())}")
    print(f"POST {NESSUS_URL}/scans")

    try:
        async with httpx.AsyncClient(verify=False, timeout=30.0) as client:
            response = await client.post(
                f'{NESSUS_URL}/scans',
                headers=headers,
                json=payload
            )

            print(f"✓ SUCCESS: Status {response.status_code}")
            print(f"Response: {response.text[:200]}")

            # Get scan ID and cleanup
            try:
                scan_id = response.json()['scan']['id']
                print(f"Scan ID: {scan_id}")
                print("Cleaning up test scan...")

                # Delete scan
                await client.put(
                    f'{NESSUS_URL}/scans/{scan_id}',
                    headers=headers,
                    json={'folder_id': 2}
                )
                await client.delete(
                    f'{NESSUS_URL}/scans/{scan_id}',
                    headers=headers
                )
                print("✓ Cleanup complete")
            except Exception as cleanup_error:
                print(f"⚠ Cleanup warning: {cleanup_error}")

            return True

    except httpx.ReadError as e:
        print(f"✗ FAILED: httpx.ReadError")
        print(f"Error: {e}")
        return False
    except Exception as e:
        print(f"✗ FAILED: {type(e).__name__}: {e}")
        return False


async def main():
    """Run both tests."""
    print("TESTING BROWSER HEADERS vs MINIMAL HEADERS")
    print("Investigating HTTP 412 ReadError issue")
    print("")

    # Authenticate
    async with httpx.AsyncClient(verify=False, timeout=30.0) as client:
        session_token = await authenticate(client)
        print(f"✓ Authenticated, token: {session_token[:20]}...\n")

    # Test 1: Minimal headers (current approach)
    result1 = await test_minimal_headers(session_token)

    # Test 2: Browser headers (wrapper approach)
    result2 = await test_browser_headers(session_token)

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Minimal headers:  {'✓ SUCCESS' if result1 else '✗ FAILED'}")
    print(f"Browser headers:  {'✓ SUCCESS' if result2 else '✗ FAILED'}")

    if result2 and not result1:
        print("\n** CONCLUSION: Browser headers prevent the ReadError! **")
        print("** Scanner should use full browser simulation headers **")
    elif not result2 and not result1:
        print("\n** CONCLUSION: Both approaches fail - server-side issue **")
    else:
        print("\n** CONCLUSION: Headers don't affect the issue **")


if __name__ == "__main__":
    asyncio.run(main())
