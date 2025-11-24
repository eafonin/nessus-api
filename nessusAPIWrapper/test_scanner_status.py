#!/usr/bin/env python3
"""
Scanner Status Test

Tests both Nessus scanners and displays:
- Last Updated
- Plugin Set
- Activation Code
- Licensed Hosts

Uses the same access patterns as the MCP server.
"""
import httpx
import json
import sys
from datetime import datetime
from typing import Dict, Any, Optional


# Scanner Configuration (matching MCP server pattern)
SCANNERS = {
    'Scanner 1': {
        'url': 'https://172.30.0.3:8834',
        'activation_code': '8WVN-N99G-LHTF-TQ4D-LTAX',
        'username': 'nessus',
        'password': 'nessus'
    },
    'Scanner 2': {
        'url': 'https://172.30.0.4:8834',
        'activation_code': 'XS6C-BFB6-VUMK-Y5MU-AWNG',
        'username': 'nessus',
        'password': 'nessus'
    }
}


def get_scanner_status(url: str, timeout: float = 10.0) -> Optional[Dict[str, Any]]:
    """Get scanner status from /server/status endpoint."""
    try:
        with httpx.Client(verify=False, timeout=timeout) as client:
            response = client.get(f'{url}/server/status')
            return response.json() if response.status_code == 200 else None
    except Exception as e:
        print(f"Error fetching status from {url}: {e}", file=sys.stderr)
        return None


def extract_x_api_token(url: str, timeout: float = 10.0) -> Optional[str]:
    """Extract X-API-Token from nessus6.js (MCP server pattern)."""
    import re
    try:
        with httpx.Client(verify=False, timeout=timeout) as client:
            response = client.get(f'{url}/nessus6.js')
            if response.status_code == 200:
                pattern = r'getApiToken[^}]+?return[\'"]([A-F0-9-]{30,})[\'"]'
                match = re.search(pattern, response.text, re.IGNORECASE)
                if match:
                    return match.group(1)
    except Exception as e:
        print(f"Error extracting X-API-Token from {url}: {e}", file=sys.stderr)
    return None


def authenticate(url: str, username: str, password: str, api_token: str, timeout: float = 10.0) -> Optional[str]:
    """Authenticate and get session token."""
    try:
        with httpx.Client(verify=False, timeout=timeout) as client:
            response = client.post(
                f'{url}/session',
                json={'username': username, 'password': password},
                headers={'Content-Type': 'application/json', 'X-API-Token': api_token}
            )
            if response.status_code == 200:
                return response.json().get('token')
    except Exception as e:
        print(f"Error authenticating to {url}: {e}", file=sys.stderr)
    return None


def get_scanner_properties(url: str, session_token: Optional[str] = None, timeout: float = 10.0) -> Optional[Dict[str, Any]]:
    """Get scanner properties from /server/properties endpoint."""
    headers = {}
    if session_token:
        headers['X-Cookie'] = f'token={session_token}'

    try:
        with httpx.Client(verify=False, timeout=timeout) as client:
            response = client.get(f'{url}/server/properties', headers=headers)
            return response.json() if response.status_code == 200 else None
    except Exception as e:
        print(f"Error fetching properties from {url}: {e}", file=sys.stderr)
        return None


def format_timestamp(timestamp: Optional[int]) -> str:
    """Convert Unix timestamp to human-readable format."""
    if not timestamp or timestamp == 0:
        return "N/A"
    try:
        return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
    except Exception:
        return "Invalid"


def parse_plugin_set_date(plugin_set: str) -> str:
    """Parse plugin set string (format: YYYYMMDDTTTT) to readable date."""
    if not plugin_set or plugin_set == 'Unknown':
        return "N/A"
    try:
        # Format: 202511120851 = 2025-11-12 08:51
        if len(plugin_set) >= 8:
            year = plugin_set[0:4]
            month = plugin_set[4:6]
            day = plugin_set[6:8]
            hour = plugin_set[8:10] if len(plugin_set) >= 10 else "00"
            minute = plugin_set[10:12] if len(plugin_set) >= 12 else "00"
            return f"{year}-{month}-{day} {hour}:{minute}"
    except Exception:
        pass
    return plugin_set


def extract_scanner_info(name: str, config: Dict[str, str]) -> Dict[str, Any]:
    """Extract key information from scanner endpoints."""
    url = config['url']
    username = config['username']
    password = config['password']

    # Authenticate to get full data
    api_token = extract_x_api_token(url)
    session_token = None
    if api_token:
        session_token = authenticate(url, username, password, api_token)

    # Get both endpoints
    status = get_scanner_status(url)
    properties = get_scanner_properties(url, session_token)

    info = {
        'name': name,
        'url': url,
        'activation_code': config['activation_code'],
        'status': 'Unknown',
        'last_updated': 'N/A',
        'plugin_set': 'N/A',
        'licensed_hosts': 'N/A',
        'feed_type': 'N/A',
        'license_type': 'N/A',
        'expiration_date': 'N/A',
        'reachable': False
    }

    # Parse status endpoint
    if status:
        info['reachable'] = True
        info['status'] = status.get('status', 'Unknown')

        # Get feed status
        detailed_status = status.get('detailed_status', {})
        feed_status = detailed_status.get('feed_status', {})
        if feed_status:
            info['feed_status'] = feed_status.get('status', 'Unknown')

    # Parse properties endpoint
    if properties:
        info['reachable'] = True

        # License information
        license_info = properties.get('license', {})
        if license_info:
            info['license_type'] = license_info.get('type', 'Unknown')
            info['activation_code'] = license_info.get('activation_code', config['activation_code'])
            info['expiration_date'] = format_timestamp(license_info.get('expiration_date'))

            # Licensed hosts (IPs)
            ips = license_info.get('ips', 0)
            info['licensed_hosts'] = f"{ips} IPs" if ips > 0 else "Unlimited"

        # Nessus type (Essentials/Professional/etc.)
        nessus_type = properties.get('nessus_type', '')
        if nessus_type:
            info['feed_type'] = nessus_type

        # Server version
        server_version = properties.get('server_version', 'Unknown')
        info['server_version'] = server_version

        # Plugin set (loaded_plugin_set or plugin_set)
        plugin_set = properties.get('plugin_set') or properties.get('loaded_plugin_set', 'Unknown')
        if plugin_set and plugin_set != 'Unknown':
            info['plugin_set'] = plugin_set
            # Parse plugin set as date (format: YYYYMMDDHHMMM)
            info['last_updated'] = parse_plugin_set_date(plugin_set)

    return info


def print_json_output(scanners_info: Dict[str, Dict[str, Any]]):
    """Print scanner information as JSON."""
    print(json.dumps(scanners_info, indent=2))


def print_table_output(scanners_info: Dict[str, Dict[str, Any]]):
    """Print scanner information as human-readable table."""
    print("\n" + "="*100)
    print(f"{'Scanner Status Report':<100}")
    print("="*100 + "\n")

    for scanner_name, info in scanners_info.items():
        reachable_icon = "✅" if info['reachable'] else "❌"
        status_icon = "✅" if info['status'] == 'ready' else "⚠️"

        print(f"Scanner: {scanner_name} {reachable_icon}")
        print(f"  URL:              {info['url']}")
        print(f"  Status:           {info['status']} {status_icon}")
        print(f"  Activation Code:  {info['activation_code']}")
        print(f"  License Type:     {info['license_type']}")
        print(f"  Licensed Hosts:   {info['licensed_hosts']}")
        print(f"  Feed Type:        {info['feed_type']}")
        print(f"  Plugin Set:       {info['plugin_set']}")
        print(f"  Last Updated:     {info['last_updated']}")
        print(f"  Expires:          {info['expiration_date']}")
        print(f"  Server Version:   {info.get('server_version', 'N/A')}")
        print()

    print("="*100 + "\n")


def main():
    """Main test function."""
    import argparse

    parser = argparse.ArgumentParser(description='Test Nessus scanner status')
    parser.add_argument('--json', action='store_true', help='Output as JSON')
    parser.add_argument('--scanner', choices=['1', '2', 'both'], default='both',
                       help='Which scanner to test (default: both)')
    args = parser.parse_args()

    # Select scanners to test
    if args.scanner == '1':
        scanners_to_test = {'Scanner 1': SCANNERS['Scanner 1']}
    elif args.scanner == '2':
        scanners_to_test = {'Scanner 2': SCANNERS['Scanner 2']}
    else:
        scanners_to_test = SCANNERS

    # Collect information
    scanners_info = {}
    for name, config in scanners_to_test.items():
        print(f"Testing {name}...", file=sys.stderr)
        scanners_info[name] = extract_scanner_info(name, config)

    # Output results
    if args.json:
        print_json_output(scanners_info)
    else:
        print_table_output(scanners_info)

    # Exit code based on scanner status
    all_ready = all(info['status'] == 'ready' for info in scanners_info.values())
    sys.exit(0 if all_ready else 1)


if __name__ == '__main__':
    main()
