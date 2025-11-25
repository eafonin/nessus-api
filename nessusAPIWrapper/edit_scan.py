"""
Edit Nessus scan basic parameters (name, description, targets)
Bypasses API license restrictions by using direct HTTP requests
"""
import sys
from get_api_token import extract_api_token_from_js
import urllib3
import requests
from tenable.nessus import Nessus

# Disable SSL warnings for localhost/self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Nessus configuration
NESSUS_URL = 'https://172.30.0.3:8834'
ACCESS_KEY = 'dca6c2f38119ba7eb2f40ddec670f680d7d1fb3cf8cf1f93ffdc7f8d7165b044'
SECRET_KEY = '45b6a702ceb4005b933cee1bd9b09cea96a82a1da68977cf4982c31ea8c83d79'
# Fetch X-API-Token dynamically from Nessus Web UI
STATIC_API_TOKEN = extract_api_token_from_js()
if not STATIC_API_TOKEN:
    print("Error: Failed to fetch X-API-Token from Nessus Web UI", file=sys.stderr)
    sys.exit(1)

# Credentials
USERNAME = 'nessus'
PASSWORD = 'nessus'


def authenticate(username, password):
    """
    Authenticate with Nessus web UI and get session token

    Args:
        username: Nessus username
        password: Nessus password

    Returns:
        tuple: (api_token, session_token) or (None, None) on failure
    """
    url = f"{NESSUS_URL}/session"

    headers = {
        'Accept': '*/*',
        'Accept-Encoding': 'gzip, deflate, br, zstd',
        'Accept-Language': 'en-US,en;q=0.9,ru;q=0.8',
        'Connection': 'keep-alive',
        'Content-Type': 'application/json',
        'Host': '172.30.0.3:8834',
        'Origin': 'https://172.30.0.3:8834',
        'Referer': 'https://172.30.0.3:8834/',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-origin',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36',
        'X-API-Token': STATIC_API_TOKEN,
        'sec-ch-ua': '"Google Chrome";v="141", "Not?A_Brand";v="8", "Chromium";v="141"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"'
    }

    payload = {
        'username': username,
        'password': password
    }

    try:
        session = requests.Session()
        response = session.post(url, json=payload, headers=headers, verify=False)

        if response.status_code == 200:
            response_data = response.json()
            session_token = response_data.get('token')

            if session_token:
                print(f"[AUTH SUCCESS] Logged in as {username}")
                return STATIC_API_TOKEN, session_token
            else:
                print("[AUTH FAILED] No session token in response")
                print(f"Response: {response.text}")
                return None, None
        else:
            print(f"[AUTH FAILED] Status code: {response.status_code}")
            print(f"Response: {response.text}")
            return None, None

    except Exception as e:
        print(f"Error during authentication: {e}")
        return None, None


def get_scan_status(scan_id):
    """
    Get scan status

    Args:
        scan_id: The scan ID

    Returns:
        str: Scan status or None
    """
    nessus = Nessus(
        url=NESSUS_URL,
        access_key=ACCESS_KEY,
        secret_key=SECRET_KEY,
        ssl_verify=False
    )

    try:
        scans_data = nessus.scans.list()
        for scan in scans_data.get('scans', []):
            if str(scan.get('id')) == str(scan_id):
                return scan.get('status')
        return None
    except Exception as e:
        print(f"Error getting scan status: {e}")
        return None


def get_scan_details(scan_id):
    """
    Get full scan configuration details using API

    Args:
        scan_id: The scan ID to retrieve

    Returns:
        dict: Full scan configuration or None on failure
    """
    nessus = Nessus(
        url=NESSUS_URL,
        access_key=ACCESS_KEY,
        secret_key=SECRET_KEY,
        ssl_verify=False
    )

    try:
        scan_config = nessus.editor.details('scan', scan_id)
        return scan_config
    except Exception as e:
        print(f"Error getting scan details via API: {e}")
        import traceback
        traceback.print_exc()
        return None


def extract_settings_from_editor_config(editor_config):
    """
    Extract flat settings dict from nested editor config structure

    Args:
        editor_config: The config from editor.details

    Returns:
        dict: Flat settings dictionary
    """
    settings = {}

    # Process each settings section (basic, advanced, assessment, discovery, report)
    for section_name, section_data in editor_config.get('settings', {}).items():
        if not isinstance(section_data, dict):
            continue

        # Extract inputs from this section
        inputs = section_data.get('inputs')
        if inputs:
            for input_item in inputs:
                input_id = input_item.get('id')
                default_value = input_item.get('default')

                if input_id and default_value is not None:
                    settings[input_id] = default_value

        # Extract group-level settings
        groups = section_data.get('groups')
        if groups:
            for group in groups:
                if isinstance(group, dict):
                    # Extract enabled, rrules, timezone, etc from schedule group
                    for key in ['enabled', 'rrules', 'timezone', 'starttime', 'agent_scan_launch_type']:
                        if key in group and group[key] is not None:
                            settings[key] = group[key]

                    # Extract emails and filters from email notification group
                    for key in ['emails', 'filters', 'filter_type']:
                        if key in group and group[key] is not None:
                            settings[key] = group[key]

    return settings


def update_scan(scan_id, api_token, session_token, name=None, description=None, targets=None):
    """
    Update scan parameters

    Args:
        scan_id: The scan ID to update
        api_token: X-API-Token
        session_token: Session token
        name: New scan name (optional)
        description: New scan description (optional)
        targets: New target IPs/hostnames (optional)

    Returns:
        bool: True if successful, False otherwise
    """
    # First, get the current scan configuration using API
    print(f"Retrieving current configuration for scan {scan_id}...")
    scan_config = get_scan_details(scan_id)

    if not scan_config:
        return False

    # Extract flat settings from the nested editor structure
    settings = extract_settings_from_editor_config(scan_config)

    if not settings:
        print("[FAILED] Could not extract settings from scan configuration")
        return False

    # Update the fields that were provided
    if name is not None:
        settings['name'] = name
        print(f"Updating name to: {name}")

    if description is not None:
        settings['description'] = description
        print(f"Updating description to: {description}")

    if targets is not None:
        settings['text_targets'] = targets
        print(f"Updating targets to: {targets}")

    # Build the payload - we need to send the full configuration
    payload = {
        'uuid': scan_config.get('uuid'),
        'settings': settings
    }

    # Add plugins configuration if present
    if 'plugins' in scan_config:
        payload['plugins'] = scan_config['plugins']

    # Add credentials (preserve existing)
    payload['credentials'] = scan_config.get('credentials', {'add': {}, 'edit': {}, 'delete': []})

    # Make the PUT request
    url = f"{NESSUS_URL}/scans/{scan_id}"

    headers = {
        'Accept': '*/*',
        'Accept-Encoding': 'gzip, deflate, br, zstd',
        'Accept-Language': 'en-US,en;q=0.9,ru;q=0.8',
        'Connection': 'keep-alive',
        'Content-Type': 'application/json',
        'Host': '172.30.0.3:8834',
        'Origin': 'https://172.30.0.3:8834',
        'Referer': 'https://172.30.0.3:8834/',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-origin',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36',
        'X-API-Token': api_token,
        'X-Cookie': f'token={session_token}',
        'sec-ch-ua': '"Google Chrome";v="141", "Not?A_Brand";v="8", "Chromium";v="141"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"'
    }

    try:
        response = requests.put(url, json=payload, headers=headers, verify=False)

        if response.status_code == 200:
            print(f"[SUCCESS] Scan {scan_id} updated successfully!")
            response_data = response.json()
            print(f"Updated scan: {response_data.get('name')}")
            return True
        else:
            print(f"[FAILED] Failed to update scan {scan_id}")
            print(f"Status code: {response.status_code}")
            print(f"Response: {response.text}")
            return False

    except Exception as e:
        print(f"Error updating scan: {e}")
        import traceback
        traceback.print_exc()
        return False


def launch_scan(scan_id, api_token, session_token):
    """
    Launch a scan

    Args:
        scan_id: The scan ID to launch
        api_token: X-API-Token
        session_token: Session token

    Returns:
        bool: True if successful, False otherwise
    """
    url = f"{NESSUS_URL}/scans/{scan_id}/launch"

    headers = {
        'Accept': '*/*',
        'Accept-Encoding': 'gzip, deflate, br, zstd',
        'Accept-Language': 'en-US,en;q=0.9,ru;q=0.8',
        'Connection': 'keep-alive',
        'Content-Length': '0',
        'Content-Type': 'application/json',
        'Host': '172.30.0.3:8834',
        'Origin': 'https://172.30.0.3:8834',
        'Referer': 'https://172.30.0.3:8834/',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-origin',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36',
        'X-API-Token': api_token,
        'X-Cookie': f'token={session_token}',
        'X-KL-kfa-Ajax-Request': 'Ajax_Request',
        'sec-ch-ua': '"Google Chrome";v="141", "Not?A_Brand";v="8", "Chromium";v="141"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"'
    }

    try:
        response = requests.post(url, headers=headers, verify=False)

        if response.status_code == 200:
            print(f"[SUCCESS] Scan {scan_id} launched successfully!")
            print(f"Response: {response.text}")
            return True
        else:
            print(f"[FAILED] Failed to launch scan {scan_id}")
            print(f"Status code: {response.status_code}")
            print(f"Response: {response.text}")
            return False

    except Exception as e:
        print(f"Error launching scan: {e}")
        return False


def print_usage():
    """Print usage instructions"""
    print("Usage:")
    print("  Update and launch scan:")
    print("    python edit_scan.py <scan_id> [options] --launch")
    print()
    print("  Update only (no launch):")
    print("    python edit_scan.py <scan_id> [options]")
    print()
    print("Options:")
    print("  --name <name>              New scan name")
    print("  --description <desc>       New scan description")
    print("  --targets <targets>        New target IPs/hostnames (comma-separated)")
    print("  --launch                   Launch the scan after updating")
    print()
    print("Examples:")
    print("  python edit_scan.py 12 --name \"Updated Scan\" --targets \"192.168.1.1,192.168.1.2\" --launch")
    print("  python edit_scan.py 12 --description \"New description\" --targets \"10.0.0.1\"")
    print("  python edit_scan.py 12 --targets \"172.32.0.1\" --launch")
    print()
    print("Note: To edit SSH credentials, use manage_credentials.py instead")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print_usage()
        sys.exit(1)

    scan_id = sys.argv[1]

    # Check if scan is running
    print(f"Checking scan {scan_id} status...")
    status = get_scan_status(scan_id)

    if status == 'running':
        print(f"[ERROR] Scan {scan_id} is currently running")
        print("Please stop the scan before modifying it")
        sys.exit(1)

    if status is None:
        print(f"[WARNING] Could not determine scan status (scan may not exist)")

    # Parse arguments
    name = None
    description = None
    targets = None
    should_launch = False

    i = 2
    while i < len(sys.argv):
        arg = sys.argv[i]

        if arg == "--name":
            if i + 1 < len(sys.argv):
                name = sys.argv[i + 1]
                i += 2
            else:
                print("Error: --name requires a value")
                sys.exit(1)
        elif arg == "--description":
            if i + 1 < len(sys.argv):
                description = sys.argv[i + 1]
                i += 2
            else:
                print("Error: --description requires a value")
                sys.exit(1)
        elif arg == "--targets":
            if i + 1 < len(sys.argv):
                targets = sys.argv[i + 1]
                i += 2
            else:
                print("Error: --targets requires a value")
                sys.exit(1)
        elif arg == "--launch":
            should_launch = True
            i += 1
        else:
            print(f"Unknown argument: {arg}")
            print_usage()
            sys.exit(1)

    # Check if at least one update parameter was provided
    if name is None and description is None and targets is None:
        print("Error: At least one update parameter must be provided")
        print_usage()
        sys.exit(1)

    # Authenticate
    print(f"Authenticating as {USERNAME}...")
    api_token, session_token = authenticate(USERNAME, PASSWORD)

    if not api_token or not session_token:
        print("Authentication failed. Cannot update scan.")
        sys.exit(1)

    # Update the scan
    success = update_scan(scan_id, api_token, session_token, name, description, targets)

    if not success:
        print("Failed to update scan.")
        sys.exit(1)

    # Launch if requested
    if should_launch:
        print(f"\nLaunching scan {scan_id}...")
        if not launch_scan(scan_id, api_token, session_token):
            sys.exit(1)
