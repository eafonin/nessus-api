#!/usr/bin/env python3
"""
Low-level investigation of httpx.ReadError on Nessus write operations.

This script isolates the HTTP request from scanner wrapper to identify:
1. Whether issue is in our code or Nessus server
2. HTTP client configuration problems
3. Network/timeout issues
4. Whether operations succeed despite error
"""
import httpx
import asyncio
import logging
import json
import sys
from typing import Optional

# Configure verbose logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/tmp/httpx_debug.log')
    ]
)

logger = logging.getLogger(__name__)

# Nessus configuration
NESSUS_URL = "https://172.32.0.209:8834"
USERNAME = "nessus"
PASSWORD = "nessus"
STATIC_API_TOKEN = "af824aba-e642-4e63-a49b-0810542ad8a5"


class HTTPDebugger:
    """Minimal HTTP client with extensive debugging."""

    def __init__(self, url: str):
        self.url = url
        self.session_token: Optional[str] = None

    async def authenticate(self, client: httpx.AsyncClient) -> str:
        """Authenticate and get session token."""
        logger.info("=" * 80)
        logger.info("AUTHENTICATION")
        logger.info("=" * 80)

        headers = {
            'Content-Type': 'application/json',
            'X-API-Token': STATIC_API_TOKEN
        }

        payload = {
            'username': USERNAME,
            'password': PASSWORD
        }

        logger.info(f"POST {self.url}/session")
        logger.info(f"Headers: {headers}")
        logger.info(f"Payload: {json.dumps(payload, indent=2)}")

        try:
            response = await client.post(
                f'{self.url}/session',
                headers=headers,
                json=payload
            )

            logger.info(f"Response status: {response.status_code}")
            logger.info(f"Response headers: {dict(response.headers)}")
            logger.info(f"Response body: {response.text}")

            data = response.json()
            self.session_token = data['token']

            logger.info(f"✓ Authentication successful, token: {self.session_token[:20]}...")
            return self.session_token

        except Exception as e:
            logger.error(f"✗ Authentication failed: {type(e).__name__}: {e}")
            raise

    def build_headers(self, web_ui_marker: bool = False) -> dict:
        """Build headers for authenticated requests."""
        headers = {
            'Content-Type': 'application/json',
            'X-API-Token': STATIC_API_TOKEN,
            'X-Cookie': f'token={self.session_token}'
        }

        if web_ui_marker:
            headers['X-KL-kfa-Ajax-Request'] = 'Ajax_Request'

        return headers

    async def test_create_scan(self, client: httpx.AsyncClient) -> Optional[int]:
        """Test POST /scans (create scan operation)."""
        logger.info("=" * 80)
        logger.info("TEST: CREATE SCAN (POST /scans)")
        logger.info("=" * 80)

        headers = self.build_headers()

        payload = {
            "uuid": "ad629e16-03b6-8c1d-cef6-ef8c9dd3c658d24bd260ef5f9e66",
            "settings": {
                "name": "DEBUG_minimal_test",
                "description": "Minimal test for httpx.ReadError investigation",
                "text_targets": "172.32.0.215",
                "launch": "ONETIME",
                "enabled": False,
                "folder_id": 3,
                "scanner_id": 1
            }
        }

        logger.info(f"POST {self.url}/scans")
        logger.info(f"Headers: {json.dumps(headers, indent=2)}")
        logger.info(f"Payload: {json.dumps(payload, indent=2)}")

        try:
            logger.info("Sending request...")
            response = await client.post(
                f'{self.url}/scans',
                headers=headers,
                json=payload
            )

            logger.info(f"✓ Response received!")
            logger.info(f"Response status: {response.status_code}")
            logger.info(f"Response headers: {dict(response.headers)}")
            logger.info(f"Response body: {response.text}")

            data = response.json()
            scan_id = data['scan']['id']
            logger.info(f"✓ Scan created with ID: {scan_id}")
            return scan_id

        except httpx.ReadError as e:
            logger.error("✗ httpx.ReadError caught!")
            logger.error(f"Error type: {type(e).__name__}")
            logger.error(f"Error message: {e}")
            logger.error(f"Error args: {e.args}")

            # Check if scan was created despite error
            logger.info("Checking if scan was created despite error...")
            try:
                list_response = await client.get(
                    f'{self.url}/scans',
                    headers=self.build_headers()
                )
                scans = list_response.json()['scans']
                debug_scans = [s for s in scans if 'DEBUG_minimal_test' in s['name']]

                if debug_scans:
                    logger.warning(f"⚠ OPERATION SUCCEEDED DESPITE ERROR!")
                    logger.warning(f"Found {len(debug_scans)} scan(s) with DEBUG name")
                    for scan in debug_scans:
                        logger.warning(f"  - Scan ID {scan['id']}: {scan['name']}")
                    return debug_scans[-1]['id']  # Return most recent
                else:
                    logger.info("No debug scans found - operation truly failed")

            except Exception as check_error:
                logger.error(f"Error checking scan list: {check_error}")

            return None

        except Exception as e:
            logger.error(f"✗ Unexpected error: {type(e).__name__}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None

    async def test_launch_scan(self, client: httpx.AsyncClient, scan_id: int) -> Optional[str]:
        """Test POST /scans/{id}/launch."""
        logger.info("=" * 80)
        logger.info(f"TEST: LAUNCH SCAN (POST /scans/{scan_id}/launch)")
        logger.info("=" * 80)

        headers = self.build_headers(web_ui_marker=True)

        logger.info(f"POST {self.url}/scans/{scan_id}/launch")
        logger.info(f"Headers: {json.dumps(headers, indent=2)}")

        try:
            logger.info("Sending request...")
            response = await client.post(
                f'{self.url}/scans/{scan_id}/launch',
                headers=headers
            )

            logger.info(f"✓ Response received!")
            logger.info(f"Response status: {response.status_code}")
            logger.info(f"Response headers: {dict(response.headers)}")
            logger.info(f"Response body: {response.text}")

            data = response.json()
            scan_uuid = data.get('scan_uuid')
            logger.info(f"✓ Scan launched with UUID: {scan_uuid}")
            return scan_uuid

        except httpx.ReadError as e:
            logger.error("✗ httpx.ReadError caught!")
            logger.error(f"Error type: {type(e).__name__}")
            logger.error(f"Error message: {e}")

            # Check if scan was launched despite error
            logger.info("Checking if scan was launched despite error...")
            try:
                await asyncio.sleep(2)
                status_response = await client.get(
                    f'{self.url}/scans/{scan_id}',
                    headers=self.build_headers()
                )
                status = status_response.json()['info']['status']
                logger.warning(f"⚠ Scan status after error: {status}")

                if status in ['running', 'pending']:
                    logger.warning(f"⚠ OPERATION SUCCEEDED DESPITE ERROR!")
                    logger.warning(f"Scan is now {status}")
                    return "unknown-uuid-but-launched"
                else:
                    logger.info(f"Scan status is {status} - operation truly failed")

            except Exception as check_error:
                logger.error(f"Error checking status: {check_error}")

            return None

        except Exception as e:
            logger.error(f"✗ Unexpected error: {type(e).__name__}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None


async def test_different_clients():
    """Test with different httpx client configurations."""

    debugger = HTTPDebugger(NESSUS_URL)

    # Configuration 1: Default (similar to scanner)
    logger.info("\n" + "=" * 80)
    logger.info("CONFIGURATION 1: Default httpx client")
    logger.info("=" * 80)

    try:
        async with httpx.AsyncClient(
            verify=False,
            timeout=30.0
        ) as client:
            # Authenticate
            await debugger.authenticate(client)

            # Test create scan
            scan_id = await debugger.test_create_scan(client)

            if scan_id:
                logger.info(f"\n✓ Create scan succeeded with ID: {scan_id}")

                # Test launch scan
                scan_uuid = await debugger.test_launch_scan(client, scan_id)

                if scan_uuid:
                    logger.info(f"✓ Launch scan succeeded with UUID: {scan_uuid}")
                else:
                    logger.warning("✗ Launch scan failed")

            else:
                logger.warning("✗ Create scan failed")

    except Exception as e:
        logger.error(f"Configuration 1 failed: {e}")
        import traceback
        logger.error(traceback.format_exc())

    # Configuration 2: Longer timeout
    logger.info("\n" + "=" * 80)
    logger.info("CONFIGURATION 2: Extended timeout (60s)")
    logger.info("=" * 80)

    try:
        async with httpx.AsyncClient(
            verify=False,
            timeout=60.0
        ) as client:
            await debugger.authenticate(client)
            scan_id = await debugger.test_create_scan(client)

            if scan_id:
                logger.info(f"✓ Create with extended timeout succeeded: {scan_id}")

    except Exception as e:
        logger.error(f"Configuration 2 failed: {e}")

    # Configuration 3: HTTP/1.1 only
    logger.info("\n" + "=" * 80)
    logger.info("CONFIGURATION 3: Force HTTP/1.1")
    logger.info("=" * 80)

    try:
        async with httpx.AsyncClient(
            verify=False,
            timeout=30.0,
            http2=False  # Force HTTP/1.1
        ) as client:
            await debugger.authenticate(client)
            scan_id = await debugger.test_create_scan(client)

            if scan_id:
                logger.info(f"✓ Create with HTTP/1.1 succeeded: {scan_id}")

    except Exception as e:
        logger.error(f"Configuration 3 failed: {e}")


async def main():
    """Run all debug tests."""
    logger.info("=" * 80)
    logger.info("HTTPX.READERROR LOW-LEVEL INVESTIGATION")
    logger.info("=" * 80)
    logger.info(f"Nessus URL: {NESSUS_URL}")
    logger.info(f"Log file: /tmp/httpx_debug.log")
    logger.info("")

    await test_different_clients()

    logger.info("\n" + "=" * 80)
    logger.info("INVESTIGATION COMPLETE")
    logger.info("=" * 80)
    logger.info("See /tmp/httpx_debug.log for full details")


if __name__ == "__main__":
    asyncio.run(main())
