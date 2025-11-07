#!/usr/bin/env python3
"""
Test if requests library handles HTTP 412 differently than httpx.

The wrapper scripts use requests, while our scanner uses httpx.
This test determines if the library makes a difference.
"""
import httpx
import requests
import asyncio
import urllib3

# Suppress SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

NESSUS_URL = "https://172.32.0.209:8834"
USERNAME = "nessus"
PASSWORD = "nessus"
STATIC_API_TOKEN = "af824aba-e642-4e63-a49b-0810542ad8a5"


def test_requests_library():
    """Test with requests library (what wrapper uses)."""
    print("=" * 80)
    print("TEST 1: REQUESTS LIBRARY (Wrapper Approach)")
    print("=" * 80)

    # Authenticate
    auth_response = requests.post(
        f'{NESSUS_URL}/session',
        headers={
            'Content-Type': 'application/json',
            'X-API-Token': STATIC_API_TOKEN
        },
        json={'username': USERNAME, 'password': PASSWORD},
        verify=False
    )
    session_token = auth_response.json()['token']
    print(f"✓ Authenticated: {session_token[:20]}...")

    # Create scan
    headers = {
        'Content-Type': 'application/json',
        'X-API-Token': STATIC_API_TOKEN,
        'X-Cookie': f'token={session_token}'
    }

    payload = {
        "uuid": "ad629e16-03b6-8c1d-cef6-ef8c9dd3c658d24bd260ef5f9e66",
        "settings": {
            "name": "TEST_requests_lib",
            "description": "Testing requests library",
            "text_targets": "172.32.0.215",
            "launch": "ONETIME",
            "enabled": False,
            "folder_id": 3,
            "scanner_id": 1
        }
    }

    print(f"POST {NESSUS_URL}/scans")

    try:
        response = requests.post(
            f'{NESSUS_URL}/scans',
            headers=headers,
            json=payload,
            verify=False,
            timeout=30
        )

        print(f"✓ Response received: Status {response.status_code}")
        print(f"✓ Response body length: {len(response.text)} bytes")
        print(f"Response: {response.text[:200]}")

        if response.status_code == 200:
            scan_id = response.json()['scan']['id']
            print(f"✓ SUCCESS: Scan created with ID {scan_id}")

            # Cleanup
            try:
                requests.put(
                    f'{NESSUS_URL}/scans/{scan_id}',
                    headers=headers,
                    json={'folder_id': 2},
                    verify=False
                )
                requests.delete(
                    f'{NESSUS_URL}/scans/{scan_id}',
                    headers=headers,
                    verify=False
                )
                print(f"✓ Cleanup complete")
            except Exception as e:
                print(f"⚠ Cleanup warning: {e}")

            return True
        else:
            print(f"✗ FAILED: Got status {response.status_code}")
            return False

    except requests.exceptions.ConnectionError as e:
        print(f"✗ FAILED: ConnectionError")
        print(f"Error: {e}")
        return False
    except Exception as e:
        print(f"✗ FAILED: {type(e).__name__}: {e}")
        return False


async def test_httpx_library():
    """Test with httpx library (what scanner uses)."""
    print("\n" + "=" * 80)
    print("TEST 2: HTTPX LIBRARY (Current Scanner)")
    print("=" * 80)

    # Authenticate
    async with httpx.AsyncClient(verify=False, timeout=30.0) as client:
        auth_response = await client.post(
            f'{NESSUS_URL}/session',
            headers={
                'Content-Type': 'application/json',
                'X-API-Token': STATIC_API_TOKEN
            },
            json={'username': USERNAME, 'password': PASSWORD}
        )
        session_token = auth_response.json()['token']
        print(f"✓ Authenticated: {session_token[:20]}...")

        # Create scan
        headers = {
            'Content-Type': 'application/json',
            'X-API-Token': STATIC_API_TOKEN,
            'X-Cookie': f'token={session_token}'
        }

        payload = {
            "uuid": "ad629e16-03b6-8c1d-cef6-ef8c9dd3c658d24bd260ef5f9e66",
            "settings": {
                "name": "TEST_httpx_lib",
                "description": "Testing httpx library",
                "text_targets": "172.32.0.215",
                "launch": "ONETIME",
                "enabled": False,
                "folder_id": 3,
                "scanner_id": 1
            }
        }

        print(f"POST {NESSUS_URL}/scans")

        try:
            response = await client.post(
                f'{NESSUS_URL}/scans',
                headers=headers,
                json=payload
            )

            print(f"✓ Response received: Status {response.status_code}")
            print(f"✓ Response body length: {len(response.text)} bytes")
            print(f"Response: {response.text[:200]}")

            if response.status_code == 200:
                scan_id = response.json()['scan']['id']
                print(f"✓ SUCCESS: Scan created with ID {scan_id}")
                return True
            else:
                print(f"✗ FAILED: Got status {response.status_code}")
                return False

        except httpx.ReadError as e:
            print(f"✗ FAILED: httpx.ReadError")
            print(f"Error: {e}")
            return False
        except Exception as e:
            print(f"✗ FAILED: {type(e).__name__}: {e}")
            return False


async def main():
    """Run both tests."""
    print("TESTING REQUESTS vs HTTPX LIBRARIES")
    print("Investigating which library wrapper scripts use")
    print("")

    # Test 1: requests library (wrapper)
    result1 = test_requests_library()

    # Test 2: httpx library (scanner)
    result2 = await test_httpx_library()

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"requests library:  {'✓ SUCCESS' if result1 else '✗ FAILED'}")
    print(f"httpx library:     {'✓ SUCCESS' if result2 else '✗ FAILED'}")

    if result1 and not result2:
        print("\n** CRITICAL FINDING: requests library works, httpx fails! **")
        print("** Solution: Scanner should use requests instead of httpx **")
    elif not result1 and not result2:
        print("\n** Both libraries fail - fundamental issue with Nessus server **")
    else:
        print("\n** No difference between libraries **")


if __name__ == "__main__":
    asyncio.run(main())
