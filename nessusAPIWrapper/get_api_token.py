"""
Extract the X-API-Token from Nessus Web UI

This token is required for Web UI endpoint operations but is NOT returned
in authentication responses. It's hardcoded in the nessus6.js file.

Usage:
    # Get token as output
    python get_api_token.py

    # Export as environment variable
    export NESSUS_API_TOKEN=$(python get_api_token.py)
"""
import re
import sys
import urllib3
import requests

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

NESSUS_URL = 'https://172.30.0.3:8834'


def extract_api_token_from_js():
    """
    Extract X-API-Token from the Nessus Web UI JavaScript

    Returns:
        str: The X-API-Token value, or None if not found
    """
    try:
        # Fetch the main JavaScript file
        response = requests.get(
            f'{NESSUS_URL}/nessus6.js',
            verify=False,
            timeout=10
        )

        if response.status_code != 200:
            print(f"Error: Failed to fetch nessus6.js (HTTP {response.status_code})", file=sys.stderr)
            return None

        # Search for the getApiToken function
        # Pattern: {key:"getApiToken",value:function(){return"<TOKEN>"}}
        pattern = r'getApiToken[^}]+return["\']([a-fA-F0-9-]+)["\']'
        match = re.search(pattern, response.text)

        if match:
            return match.group(1)
        else:
            print("Error: Could not find API token in nessus6.js", file=sys.stderr)
            return None

    except Exception as e:
        print(f"Error extracting API token: {e}", file=sys.stderr)
        return None


def verify_token(token):
    """
    Verify the token by attempting to use it for authentication

    Returns:
        bool: True if token is valid
    """
    try:
        headers = {
            'Content-Type': 'application/json',
            'X-API-Token': token
        }

        payload = {
            'username': 'nessus',
            'password': 'nessus'
        }

        response = requests.post(
            f'{NESSUS_URL}/session',
            json=payload,
            headers=headers,
            verify=False,
            timeout=10
        )

        return response.status_code == 200

    except Exception:
        return False


if __name__ == "__main__":
    token = extract_api_token_from_js()

    if token:
        # Verify it works
        if verify_token(token):
            print(token)
            sys.exit(0)
        else:
            print("Error: Extracted token failed verification", file=sys.stderr)
            sys.exit(1)
    else:
        sys.exit(1)
