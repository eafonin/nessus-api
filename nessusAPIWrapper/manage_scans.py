"""
Create and delete Nessus scans via web UI simulation
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
NESSUS_URL = 'https://172.32.0.209:8834'
ACCESS_KEY = '4a4538d310e4a0b1f4a9ed5765913cf60c25380e303aceaeda867e8dd3f57071'
SECRET_KEY = 'fe25d148200608e2970944cde3b38862d8ecae9092950620d151b0a7f72041b9'
# Fetch X-API-Token dynamically from Nessus Web UI
STATIC_API_TOKEN = extract_api_token_from_js()
if not STATIC_API_TOKEN:
    print("Error: Failed to fetch X-API-Token from Nessus Web UI", file=sys.stderr)
    sys.exit(1)

# Credentials
USERNAME = 'nessus'
PASSWORD = 'nessus'

# Known template UUIDs (Advanced Scan template)
ADVANCED_SCAN_TEMPLATE = 'ad629e16-03b6-8c1d-cef6-ef8c9dd3c658d24bd260ef5f9e66'


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
        'Host': '172.32.0.209:8834',
        'Origin': 'https://172.32.0.209:8834',
        'Referer': 'https://172.32.0.209:8834/',
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
                return None, None
        else:
            print(f"[AUTH FAILED] Status code: {response.status_code}")
            return None, None

    except Exception as e:
        print(f"Error during authentication: {e}")
        return None, None


def get_template_config(template_uuid, api_token, session_token):
    """
    Get template configuration from Nessus

    Args:
        template_uuid: Template UUID
        api_token: X-API-Token
        session_token: Session token

    Returns:
        dict: Template configuration or None
    """
    url = f"{NESSUS_URL}/editor/scan/templates/{template_uuid}"

    headers = {
        'Accept': '*/*',
        'Accept-Encoding': 'gzip, deflate, br, zstd',
        'Accept-Language': 'en-US,en;q=0.9,ru;q=0.8',
        'Connection': 'keep-alive',
        'Content-Type': 'application/json',
        'Host': '172.32.0.209:8834',
        'Referer': 'https://172.32.0.209:8834/',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-origin',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36',
        'X-API-Token': api_token,
        'X-API-Version': '2',
        'X-Cookie': f'token={session_token}',
        'sec-ch-ua': '"Google Chrome";v="141", "Not?A_Brand";v="8", "Chromium";v="141"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"'
    }

    try:
        response = requests.get(url, headers=headers, verify=False)

        if response.status_code == 200:
            return response.json()
        else:
            print(f"[FAILED] Failed to get template configuration")
            print(f"Status code: {response.status_code}")
            return None

    except Exception as e:
        print(f"Error getting template: {e}")
        return None


def extract_settings_from_template(template_config):
    """
    Extract flat settings dict from template configuration

    Args:
        template_config: Template configuration

    Returns:
        dict: Flat settings dictionary with defaults
    """
    settings = {}

    # Process each settings section
    for section_name, section_data in template_config.get('settings', {}).items():
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
                    for key in ['enabled', 'rrules', 'timezone', 'starttime', 'agent_scan_launch_type']:
                        if key in group and group[key] is not None:
                            settings[key] = group[key]

                    for key in ['emails', 'filters', 'filter_type']:
                        if key in group and group[key] is not None:
                            settings[key] = group[key]

    return settings


def init_ssh_credentials(scan_id, api_token, session_token):
    """
    Initialize scan with dummy SSH credentials so they can be updated later

    Args:
        scan_id: The scan ID
        api_token: X-API-Token
        session_token: Session token

    Returns:
        bool: True if successful
    """
    try:
        # Get scan via API to retrieve full config
        nessus = Nessus(
            url=NESSUS_URL,
            access_key=ACCESS_KEY,
            secret_key=SECRET_KEY,
            ssl_verify=False
        )

        scan_config = nessus.editor.details('scan', scan_id)
        credentials = scan_config.get('credentials', {})

        # Find SSH type
        ssh_type = None
        for category in credentials.get('data', []):
            if category.get('name') == 'Host':
                for cred_type in category.get('types', []):
                    if 'SSH' in cred_type.get('name', ''):
                        ssh_type = cred_type
                        break
                break

        if not ssh_type:
            print("[WARNING] Could not find SSH credential type")
            return False

        # Get the full SSH type definition (inputs) and use it as a template
        # We'll create an instance from the type's inputs structure
        type_inputs = ssh_type.get('inputs', [])

        # Find auth_method field
        auth_method_field = None
        for field in type_inputs:
            if field.get('id') == 'auth_method':
                auth_method_field = field
                break

        if not auth_method_field:
            print("[WARNING] Could not find auth_method field in SSH type")
            return False

        # Create instance using the full structure from the type definition
        # but with default values set to placeholder
        dummy_instance = {
            "summary": "User: PLACEHOLDER, Auth method: password",
            "inputs": [auth_method_field.copy()]
        }

        # Set default to password and add placeholder username/password
        for opt in dummy_instance['inputs'][0].get('options', []):
            if isinstance(opt, dict) and opt.get('name') == 'password':
                # Set defaults for password auth
                for inp in opt.get('inputs', []):
                    if inp.get('id') == 'username':
                        inp['default'] = 'PLACEHOLDER'
                    elif inp.get('id') == 'password':
                        inp['default'] = 'PLACEHOLDER'
                    elif inp.get('id') == 'elevate_privileges_with':
                        inp['default'] = 'Nothing'

        # Set auth method default
        dummy_instance['inputs'][0]['default'] = 'password'

        ssh_type['instances'] = [dummy_instance]

        # Build update payload
        payload = {
            'uuid': scan_config.get('uuid'),
            'settings': {},
            'credentials': credentials,
            'plugins': scan_config.get('plugins', {})
        }

        # Extract settings
        for section_name, section_data in scan_config.get('settings', {}).items():
            if isinstance(section_data, dict):
                inputs = section_data.get('inputs')
                if inputs:
                    for input_item in inputs:
                        input_id = input_item.get('id')
                        default_value = input_item.get('default')
                        if input_id and default_value is not None:
                            payload['settings'][input_id] = default_value

        # PUT request
        url = f"{NESSUS_URL}/scans/{scan_id}"
        headers = {
            'Content-Type': 'application/json',
            'X-API-Token': api_token,
            'X-Cookie': f'token={session_token}'
        }

        response = requests.put(url, json=payload, headers=headers, verify=False)

        if response.status_code == 200:
            print("[SUCCESS] SSH credentials structure initialized")
            # Verify it saved
            verify_config = nessus.editor.details('scan', scan_id)
            verify_creds = verify_config.get('credentials', {})
            for cat in verify_creds.get('data', []):
                if cat.get('name') == 'Host':
                    for ct in cat.get('types', []):
                        if 'SSH' in ct.get('name', ''):
                            inst_count = len(ct.get('instances', []))
                            if inst_count > 0:
                                print(f"[VERIFIED] {inst_count} SSH credential instance(s) saved")
                            else:
                                print("[WARNING] SSH instance was not saved (Nessus may have rejected it)")
                            break
                    break
            return True
        else:
            print(f"[WARNING] Could not initialize SSH credentials: {response.status_code}")
            print(f"Response: {response.text}")
            return False

    except Exception as e:
        print(f"[WARNING] Error initializing SSH credentials: {e}")
        return False


def create_scan(api_token, session_token, name, targets, description="", template_uuid=None):
    """
    Create a new scan

    Args:
        api_token: X-API-Token
        session_token: Session token
        name: Scan name
        targets: Target IPs/hostnames
        description: Scan description (optional)
        template_uuid: Template UUID (optional, defaults to Advanced Scan)

    Returns:
        dict: Created scan info or None on failure
    """
    if template_uuid is None:
        template_uuid = ADVANCED_SCAN_TEMPLATE

    print(f"Fetching template configuration...")
    template_config = get_template_config(template_uuid, api_token, session_token)

    if not template_config:
        return None

    # Extract default settings from template
    settings = extract_settings_from_template(template_config)

    # Override with user-provided values
    settings['name'] = name
    settings['text_targets'] = targets
    if description:
        settings['description'] = description

    # Ensure required fields
    if 'folder_id' not in settings:
        settings['folder_id'] = 3  # My Scans folder
    if 'scanner_id' not in settings:
        settings['scanner_id'] = '1'  # Local scanner
    settings['launch_now'] = False
    settings['enabled'] = False

    # Build payload with dummy SSH credentials
    payload = {
        'uuid': template_config.get('uuid'),
        'settings': settings,
        'credentials': {
            'add': {
                'Host': {
                    'SSH': [
                        {
                            'auth_method': 'password',
                            'username': 'PLACEHOLDER',
                            'password': 'PLACEHOLDER',
                            'elevate_privileges_with': 'Nothing',
                            'custom_password_prompt': '',
                            'target_priority_list': ''
                        }
                    ]
                }
            },
            'edit': {},
            'delete': []
        },
        'plugins': template_config.get('plugins', {})
    }

    # Make POST request to create scan
    url = f"{NESSUS_URL}/scans"

    headers = {
        'Accept': '*/*',
        'Accept-Encoding': 'gzip, deflate, br, zstd',
        'Accept-Language': 'en-US,en;q=0.9,ru;q=0.8',
        'Connection': 'keep-alive',
        'Content-Type': 'application/json',
        'Host': '172.32.0.209:8834',
        'Origin': 'https://172.32.0.209:8834',
        'Referer': 'https://172.32.0.209:8834/',
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
        response = requests.post(url, json=payload, headers=headers, verify=False)

        if response.status_code == 200:
            scan_info = response.json()
            scan_id = scan_info.get('scan', {}).get('id')
            print(f"[SUCCESS] Scan created successfully!")
            print(f"Scan ID: {scan_id}")
            print(f"Scan Name: {scan_info.get('scan', {}).get('name')}")
            print(f"[INFO] Dummy SSH credentials added (username/password: PLACEHOLDER)")
            print(f"[INFO] Use 'python manage_credentials.py {scan_id}' to update SSH credentials")

            return scan_info
        else:
            print(f"[FAILED] Failed to create scan")
            print(f"Status code: {response.status_code}")
            print(f"Response: {response.text}")
            return None

    except Exception as e:
        print(f"Error creating scan: {e}")
        import traceback
        traceback.print_exc()
        return None


def move_to_trash(scan_id, api_token, session_token):
    """
    Move scan to trash folder

    Args:
        scan_id: Scan ID
        api_token: X-API-Token
        session_token: Session token

    Returns:
        bool: True if successful
    """
    url = f"{NESSUS_URL}/scans/{scan_id}/folder"

    headers = {
        'Accept': '*/*',
        'Accept-Encoding': 'gzip, deflate, br, zstd',
        'Accept-Language': 'en-US,en;q=0.9,ru;q=0.8',
        'Connection': 'keep-alive',
        'Content-Type': 'application/json',
        'Host': '172.32.0.209:8834',
        'Origin': 'https://172.32.0.209:8834',
        'Referer': 'https://172.32.0.209:8834/',
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

    payload = {'folder_id': 2}  # 2 = Trash folder

    try:
        response = requests.put(url, json=payload, headers=headers, verify=False)

        if response.status_code == 200:
            print(f"[SUCCESS] Scan {scan_id} moved to trash")
            return True
        else:
            print(f"[FAILED] Failed to move scan {scan_id} to trash")
            print(f"Status code: {response.status_code}")
            return False

    except Exception as e:
        print(f"Error moving scan to trash: {e}")
        return False


def empty_trash(api_token, session_token):
    """
    Empty trash folder (permanently delete all scans in trash)

    Args:
        api_token: X-API-Token
        session_token: Session token

    Returns:
        bool: True if successful
    """
    # First, get list of scans in trash
    nessus = Nessus(
        url=NESSUS_URL,
        access_key=ACCESS_KEY,
        secret_key=SECRET_KEY,
        ssl_verify=False
    )

    try:
        scans_data = nessus.scans.list()
        trash_scans = [str(s['id']) for s in scans_data.get('scans', []) if s.get('folder_id') == 2]

        if not trash_scans:
            print("[INFO] Trash is already empty")
            return True

        print(f"[INFO] Found {len(trash_scans)} scan(s) in trash")

    except Exception as e:
        print(f"Error listing scans: {e}")
        return False

    url = f"{NESSUS_URL}/scans"

    headers = {
        'Accept': '*/*',
        'Accept-Encoding': 'gzip, deflate, br, zstd',
        'Accept-Language': 'en-US,en;q=0.9,ru;q=0.8',
        'Connection': 'keep-alive',
        'Content-Type': 'application/json',
        'Host': '172.32.0.209:8834',
        'Origin': 'https://172.32.0.209:8834',
        'Referer': 'https://172.32.0.209:8834/',
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

    payload = {'ids': trash_scans}

    try:
        response = requests.delete(url, json=payload, headers=headers, verify=False)

        if response.status_code == 200:
            print(f"[SUCCESS] Trash emptied ({len(trash_scans)} scan(s) deleted)")
            return True
        else:
            print(f"[FAILED] Failed to empty trash")
            print(f"Status code: {response.status_code}")
            print(f"Response: {response.text}")
            return False

    except Exception as e:
        print(f"Error emptying trash: {e}")
        return False


def delete_scan_permanent(scan_ids, api_token, session_token):
    """
    Permanently delete scan(s) using bulk delete

    Args:
        scan_ids: List of scan IDs or single scan ID
        api_token: X-API-Token
        session_token: Session token

    Returns:
        bool: True if successful
    """
    # Convert single ID to list
    if not isinstance(scan_ids, list):
        scan_ids = [str(scan_ids)]
    else:
        scan_ids = [str(sid) for sid in scan_ids]

    url = f"{NESSUS_URL}/scans"

    headers = {
        'Accept': '*/*',
        'Accept-Encoding': 'gzip, deflate, br, zstd',
        'Accept-Language': 'en-US,en;q=0.9,ru;q=0.8',
        'Connection': 'keep-alive',
        'Content-Type': 'application/json',
        'Host': '172.32.0.209:8834',
        'Origin': 'https://172.32.0.209:8834',
        'Referer': 'https://172.32.0.209:8834/',
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

    payload = {'ids': scan_ids}

    try:
        response = requests.delete(url, json=payload, headers=headers, verify=False)

        if response.status_code == 200:
            print(f"[SUCCESS] {len(scan_ids)} scan(s) deleted permanently")
            return True
        else:
            print(f"[FAILED] Failed to delete scan(s)")
            print(f"Status code: {response.status_code}")
            print(f"Response: {response.text}")
            return False

    except Exception as e:
        print(f"Error deleting scan(s): {e}")
        return False


def delete_scan(scan_id, api_token, session_token):
    """
    Delete a scan - fully automated with just scan ID

    Args:
        scan_id: Scan ID
        api_token: X-API-Token
        session_token: Session token

    Returns:
        bool: True if successful
    """
    # Move to trash first
    if not move_to_trash(scan_id, api_token, session_token):
        return False

    # Then permanently delete it
    return delete_scan_permanent([scan_id], api_token, session_token)


def print_usage():
    """Print usage instructions"""
    print("Usage:")
    print("  Create scan:")
    print("    python manage_scans.py create <name> <targets> [description]")
    print()
    print("  Delete scan:")
    print("    python manage_scans.py delete <scan_id>")
    print()
    print("  Empty trash:")
    print("    python manage_scans.py empty-trash")
    print()
    print("Examples:")
    print('  python manage_scans.py create "My Scan" "192.168.1.1,192.168.1.2"')
    print('  python manage_scans.py create "Test Scan" "10.0.0.1" "Testing description"')
    print("  python manage_scans.py delete 25")
    print("  python manage_scans.py empty-trash")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(1)

    command = sys.argv[1]

    # Authenticate
    print(f"Authenticating as {USERNAME}...")
    api_token, session_token = authenticate(USERNAME, PASSWORD)

    if not api_token or not session_token:
        print("Authentication failed.")
        sys.exit(1)

    if command == "create":
        if len(sys.argv) < 4:
            print("Error: create requires name and targets")
            print_usage()
            sys.exit(1)

        name = sys.argv[2]
        targets = sys.argv[3]
        description = sys.argv[4] if len(sys.argv) > 4 else ""

        result = create_scan(api_token, session_token, name, targets, description)
        if not result:
            sys.exit(1)

    elif command == "delete":
        if len(sys.argv) < 3:
            print("Error: delete requires scan_id")
            print_usage()
            sys.exit(1)

        scan_id = sys.argv[2]
        if not delete_scan(scan_id, api_token, session_token):
            sys.exit(1)

    elif command == "empty-trash":
        if not empty_trash(api_token, session_token):
            sys.exit(1)

    else:
        print(f"Unknown command: {command}")
        print_usage()
        sys.exit(1)
