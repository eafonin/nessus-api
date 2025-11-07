"""
Async utility to extract X-API-Token from Nessus Web UI.

Based on nessusAPIWrapper/get_api_token.py but using async httpx.

The X-API-Token is:
- Hardcoded in /nessus6.js
- Required for all Web UI operations
- Changes when Nessus is rebuilt/reinstalled
- NOT returned in authentication responses

This module fetches it dynamically to ensure compatibility after Nessus rebuilds.
"""

import re
import httpx
import logging
from typing import Optional

logger = logging.getLogger(__name__)


async def extract_api_token(nessus_url: str, verify_ssl: bool = False) -> Optional[str]:
    """
    Extract X-API-Token from Nessus Web UI JavaScript (async version).

    Args:
        nessus_url: Nessus base URL (e.g., https://172.32.0.209:8834)
        verify_ssl: Enable SSL verification (False for self-signed certs)

    Returns:
        X-API-Token string, or None if extraction failed

    Raises:
        httpx.HTTPError: If request fails
    """
    try:
        async with httpx.AsyncClient(verify=verify_ssl, timeout=10.0) as client:
            # Fetch the main JavaScript file
            response = await client.get(f'{nessus_url}/nessus6.js')

            if response.status_code != 200:
                logger.error(f"Failed to fetch nessus6.js: HTTP {response.status_code}")
                return None

            # Search for the getApiToken function
            # Pattern: {key:"getApiToken",value:function(){return"<TOKEN>"}}
            pattern = r'getApiToken[^}]+return["\']([A-F0-9-]+)["\']'
            match = re.search(pattern, response.text)

            if match:
                token = match.group(1)
                logger.info(f"Extracted X-API-Token: {token}")
                return token
            else:
                logger.error("Could not find API token in nessus6.js")
                return None

    except Exception as e:
        logger.error(f"Error extracting API token: {e}")
        return None


async def verify_token(
    nessus_url: str,
    token: str,
    username: str,
    password: str,
    verify_ssl: bool = False
) -> bool:
    """
    Verify the X-API-Token by attempting authentication.

    Args:
        nessus_url: Nessus base URL
        token: X-API-Token to verify
        username: Nessus username
        password: Nessus password
        verify_ssl: Enable SSL verification

    Returns:
        True if token is valid (authentication succeeds)
    """
    try:
        async with httpx.AsyncClient(verify=verify_ssl, timeout=10.0) as client:
            headers = {
                'Content-Type': 'application/json',
                'X-API-Token': token
            }

            payload = {
                'username': username,
                'password': password
            }

            response = await client.post(
                f'{nessus_url}/session',
                json=payload,
                headers=headers
            )

            success = response.status_code == 200
            if success:
                logger.info("X-API-Token verification successful")
            else:
                logger.warning(f"X-API-Token verification failed: HTTP {response.status_code}")

            return success

    except Exception as e:
        logger.error(f"Error verifying API token: {e}")
        return False


async def fetch_and_verify_token(
    nessus_url: str,
    username: str,
    password: str,
    verify_ssl: bool = False
) -> Optional[str]:
    """
    Fetch X-API-Token and verify it works.

    Args:
        nessus_url: Nessus base URL
        username: Nessus username (for verification)
        password: Nessus password (for verification)
        verify_ssl: Enable SSL verification

    Returns:
        Verified X-API-Token, or None if extraction/verification failed
    """
    token = await extract_api_token(nessus_url, verify_ssl)

    if not token:
        return None

    # Verify the token works
    is_valid = await verify_token(nessus_url, token, username, password, verify_ssl)

    if is_valid:
        return token
    else:
        logger.error("Extracted token failed verification")
        return None
