"""
Manage Nessus scan SSH credentials via JSON template
Export credential template or import credentials from JSON file
"""
import sys
from get_api_token import extract_api_token_from_js
import urllib3
import requests
import json
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
        return None


def extract_field_options(field):
    """
    Extract available options from a dropdown/radio field definition

    Args:
        field: Field definition dict

    Returns:
        list: List of option names, or None if not a dropdown field
    """
    if field.get('type') in ['ui_radio', 'radio', 'select']:
        options = field.get('options', [])
        option_names = []
        for opt in options:
            if isinstance(opt, dict):
                option_names.append(opt.get('name'))
            else:
                option_names.append(opt)
        return option_names
    return None


def extract_ssh_credential_template(credentials):
    """
    Extract SSH credential structure and create a template with dynamically discovered options

    Args:
        credentials: The credentials dict from scan config

    Returns:
        dict: SSH credential template with all available fields and options
    """
    template = {
        "_info": "Fill in the fields you want to set. Remove fields you don't want to change.",
    }

    if not credentials or not credentials.get('data'):
        return template

    # Find SSH type definition (not instance - we want the full field definitions)
    ssh_type = None
    for category in credentials.get('data', []):
        if category.get('name') == 'Host':
            for cred_type in category.get('types', []):
                if 'SSH' in cred_type.get('name', ''):
                    ssh_type = cred_type
                    break
            break

    if not ssh_type:
        return template

    # Extract field definitions from type
    inputs = ssh_type.get('inputs', [])

    # Find and process auth_method field
    for field in inputs:
        if field.get('id') == 'auth_method':
            # Extract auth method options
            auth_options = extract_field_options(field)
            template['auth_method'] = field.get('default', 'password')
            if auth_options:
                template['_auth_method_options'] = auth_options

            # Process password authentication fields (most common)
            for opt in field.get('options', []):
                if isinstance(opt, dict) and opt.get('name') == 'password':
                    template['_password_auth_fields'] = {}

                    # Extract all fields for password auth
                    for pwd_field in opt.get('inputs', []):
                        field_id = pwd_field.get('id')
                        field_name = pwd_field.get('name')
                        field_type = pwd_field.get('type')

                        if field_id == 'username':
                            template['username'] = pwd_field.get('default', '')
                            template['_password_auth_fields']['username'] = f"{field_name} (required)"

                        elif field_id == 'password':
                            template['password'] = ''
                            template['_password_auth_fields']['password'] = f"{field_name} (required)"

                        elif field_id == 'elevate_privileges_with':
                            # Extract escalation options dynamically
                            elevate_options = extract_field_options(pwd_field)
                            template['elevate_privileges_with'] = pwd_field.get('default', 'Nothing')
                            if elevate_options:
                                template['_elevate_options'] = elevate_options
                            template['_password_auth_fields']['elevate_privileges_with'] = f"{field_name} (optional)"

                            # Extract common escalation fields from the options
                            template['escalation_password'] = ''
                            template['escalation_account'] = ''

                            # Add hints for escalation fields
                            for elev_opt in pwd_field.get('options', []):
                                if isinstance(elev_opt, dict) and elev_opt.get('name') in ['sudo', 'su', 'pbrun', 'dzdo']:
                                    for elev_field in elev_opt.get('inputs', []):
                                        field_id_elev = elev_field.get('id')
                                        if field_id_elev == 'escalation_password':
                                            hint = elev_field.get('name', 'Escalation password')
                                            template['_password_auth_fields']['escalation_password'] = f"{hint} (optional)"
                                        elif field_id_elev == 'escalation_account':
                                            hint = elev_field.get('hint', 'Account to escalate to')
                                            template['_password_auth_fields']['escalation_account'] = f"{hint} (optional)"
                                    break
                    break

    # Now overlay current values if instance exists
    instances = ssh_type.get('instances', [])
    if instances:
        instance = instances[0]
        current_values = extract_current_ssh_values(instance)
        # Update template with current values (but preserve _options and _fields)
        for key, value in current_values.items():
            if not key.startswith('_'):
                template[key] = value

    return template


def extract_current_ssh_values(instance):
    """
    Extract current SSH credential values from instance

    Args:
        instance: SSH credential instance

    Returns:
        dict: Current values
    """
    values = {}

    def find_value(inputs, field_id):
        """Recursively find a field value by ID"""
        for inp in inputs:
            if inp.get('id') == field_id and 'default' in inp:
                return inp['default']
            if inp.get('type') == 'ui_radio':
                if inp.get('id') == field_id and 'default' in inp:
                    return inp['default']
                for option in inp.get('options', []):
                    if isinstance(option, dict) and option.get('inputs'):
                        result = find_value(option['inputs'], field_id)
                        if result is not None:
                            return result
        return None

    inputs = instance.get('inputs', [])

    # Extract auth method
    auth_method = find_value(inputs, 'auth_method')
    if auth_method:
        values['auth_method'] = auth_method

    # Extract username and password
    username = find_value(inputs, 'username')
    if username:
        values['username'] = username

    # Note: passwords are masked, so we won't get them
    values['password'] = ""

    # Extract privilege escalation
    elevate_method = find_value(inputs, 'elevate_privileges_with')
    if elevate_method:
        values['elevate_privileges_with'] = elevate_method

    escalation_account = find_value(inputs, 'escalation_account')
    if escalation_account:
        values['escalation_account'] = escalation_account

    # Note: escalation password is masked
    values['escalation_password'] = ""

    return values


def export_credentials_template(scan_id, output_file):
    """
    Export SSH credentials template to JSON file

    Args:
        scan_id: The scan ID
        output_file: Output JSON filename

    Returns:
        bool: True if successful
    """
    print(f"Retrieving scan {scan_id} configuration...")
    scan_config = get_scan_details(scan_id)

    if not scan_config:
        return False

    credentials = scan_config.get('credentials', {})
    template = extract_ssh_credential_template(credentials)

    try:
        with open(output_file, 'w') as f:
            json.dump(template, f, indent=2)
        print(f"[SUCCESS] SSH credentials template exported to: {output_file}")
        print(f"\nEdit the file and fill in the credentials, then run:")
        print(f"  python manage_credentials.py {scan_id} {output_file}")
        return True
    except Exception as e:
        print(f"[FAILED] Error writing template: {e}")
        return False


def build_ssh_credential_instance(template_data, existing_instance=None):
    """
    Build SSH credential instance from template data

    Args:
        template_data: The filled template data
        existing_instance: Existing instance structure (if any)

    Returns:
        dict: SSH credential instance
    """
    auth_method = template_data.get('auth_method', 'password')

    if existing_instance:
        # Update existing instance
        instance = existing_instance

        def update_value(inputs, field_id, new_value, depth=0, active_auth_method=None):
            """Recursively update a field value"""
            if new_value is None or new_value == "":
                return False
            for inp in inputs:
                if inp.get('id') == field_id:
                    inp['default'] = new_value
                    return True
                if inp.get('type') == 'ui_radio':
                    # For auth_method, only search in the active option
                    if inp.get('id') == 'auth_method' and active_auth_method:
                        for option in inp.get('options', []):
                            if isinstance(option, dict) and option.get('name') == active_auth_method and option.get('inputs'):
                                if update_value(option['inputs'], field_id, new_value, depth+1, active_auth_method):
                                    return True
                    else:
                        # For other ui_radio fields, search all options
                        for option in inp.get('options', []):
                            if isinstance(option, dict) and option.get('inputs'):
                                if update_value(option['inputs'], field_id, new_value, depth+1, active_auth_method):
                                    return True
            return False

        inputs = instance.get('inputs', [])

        # Get the active auth method
        active_auth_method = template_data.get('auth_method', 'password')

        # Update username
        if template_data.get('username'):
            update_value(inputs, 'username', template_data['username'], active_auth_method=active_auth_method)

        # Update password
        if template_data.get('password'):
            update_value(inputs, 'password', template_data['password'], active_auth_method=active_auth_method)

        # Update escalation method
        if template_data.get('elevate_privileges_with'):
            update_value(inputs, 'elevate_privileges_with', template_data['elevate_privileges_with'], active_auth_method=active_auth_method)

        # Update escalation password
        if template_data.get('escalation_password'):
            update_value(inputs, 'escalation_password', template_data['escalation_password'], active_auth_method=active_auth_method)

        # Update escalation account
        if template_data.get('escalation_account'):
            update_value(inputs, 'escalation_account', template_data['escalation_account'], active_auth_method=active_auth_method)

        # Update summary to reflect new username
        username = template_data.get('username', 'PLACEHOLDER')
        auth_method = template_data.get('auth_method', 'password')
        instance['summary'] = f"User: {username}, Auth method: {auth_method}"

        return instance
    else:
        # Create new instance from scratch
        print("[INFO] No existing SSH credentials - creating new instance")

        auth_method = template_data.get('auth_method', 'password')
        username = template_data.get('username', '')
        password = template_data.get('password', '')
        elevate_priv = template_data.get('elevate_privileges_with', 'Nothing')
        escalation_password = template_data.get('escalation_password', '')
        escalation_account = template_data.get('escalation_account', '')

        # Build instance structure based on auth_method
        instance = {
            "summary": f"User: {username}, Auth method: {auth_method}",
            "inputs": [
                {
                    "id": "auth_method",
                    "name": "Authentication method",
                    "type": "ui_radio",
                    "default": auth_method,
                    "options": [
                        {
                            "name": "certificate",
                            "inputs": []  # Minimal structure
                        },
                        {
                            "name": "Kerberos",
                            "inputs": []  # Minimal structure
                        },
                        {
                            "name": "password",
                            "inputs": [
                                {
                                    "id": "username",
                                    "name": "Username",
                                    "type": "entry",
                                    "default": username,
                                    "placeholder": "root",
                                    "required": True
                                },
                                {
                                    "id": "password",
                                    "name": "Password (unsafe!)",
                                    "type": "password",
                                    "default": password,
                                    "required": True
                                },
                                {
                                    "id": "elevate_privileges_with",
                                    "name": "Elevate privileges with",
                                    "type": "ui_radio",
                                    "default": elevate_priv,
                                    "options": [
                                        {"name": "Nothing", "inputs": None},
                                        {"name": ".k5login", "inputs": []},
                                        {"name": "Cisco 'enable'", "inputs": []},
                                        {"name": "dzdo", "inputs": []},
                                        {"name": "pbrun", "inputs": []},
                                        {"name": "su", "inputs": []},
                                        {"name": "su+sudo", "inputs": []},
                                        {
                                            "name": "sudo",
                                            "inputs": [
                                                {
                                                    "id": "escalation_account",
                                                    "name": "sudo user",
                                                    "type": "entry",
                                                    "default": escalation_account if escalation_account else "",
                                                    "placeholder": "root",
                                                    "required": False
                                                },
                                                {
                                                    "id": "escalation_password",
                                                    "name": "sudo password",
                                                    "type": "password",
                                                    "default": escalation_password if escalation_password else "",
                                                    "required": False
                                                }
                                            ]
                                        },
                                        {"name": "Checkpoint Gaia 'expert'", "inputs": []}
                                    ]
                                }
                            ]
                        },
                        {
                            "name": "public key",
                            "inputs": []  # Minimal structure
                        }
                    ]
                }
            ]
        }

        return instance


def import_credentials_from_template(scan_id, api_token, session_token, template_file):
    """
    Import SSH credentials from JSON template

    Args:
        scan_id: The scan ID
        api_token: X-API-Token
        session_token: Session token
        template_file: Input JSON filename

    Returns:
        bool: True if successful
    """
    # Load template
    try:
        with open(template_file, 'r') as f:
            template_data = json.load(f)
    except Exception as e:
        print(f"[FAILED] Error reading template file: {e}")
        return False

    # Get current scan config
    print(f"Retrieving scan {scan_id} configuration...")
    scan_config = get_scan_details(scan_id)

    if not scan_config:
        return False

    credentials = scan_config.get('credentials', {})

    # Find SSH credentials
    host_category = None
    for category in credentials.get('data', []):
        if category.get('name') == 'Host':
            host_category = category
            break

    if not host_category:
        print("[FAILED] Host credentials category not found")
        return False

    ssh_type = None
    for cred_type in host_category.get('types', []):
        if 'SSH' in cred_type.get('name', ''):
            ssh_type = cred_type
            break

    if not ssh_type:
        print("[FAILED] SSH credential type not found")
        return False

    instances = ssh_type.get('instances', [])

    # Update or create the instance
    if instances:
        # Update existing instance
        updated_instance = build_ssh_credential_instance(template_data, instances[0])
    else:
        # Create new instance from scratch
        updated_instance = build_ssh_credential_instance(template_data, None)

    if not updated_instance:
        return False

    # Build update payload using add/delete format
    # Extract the simple credential values for the edit structure
    cred_values = {
        'auth_method': template_data.get('auth_method', 'password'),
        'username': template_data.get('username', ''),
        'password': template_data.get('password', ''),
        'elevate_privileges_with': template_data.get('elevate_privileges_with', 'Nothing'),
        'custom_password_prompt': '',
        'target_priority_list': ''
    }

    # Add optional escalation fields if provided
    if template_data.get('escalation_password'):
        cred_values['escalation_password'] = template_data['escalation_password']
    if template_data.get('escalation_account'):
        cred_values['escalation_account'] = template_data['escalation_account']

    # Delete existing SSH instances and add new one
    # Get existing instance IDs to delete
    ssh_instance_ids = []
    for inst in instances:
        inst_id = inst.get('id')
        if inst_id:
            ssh_instance_ids.append(inst_id)

    payload = {
        'uuid': scan_config.get('uuid'),
        'settings': {},
        'credentials': {
            'add': {
                'Host': {
                    'SSH': [cred_values]
                }
            },
            'edit': {},
            'delete': ssh_instance_ids if ssh_instance_ids else []
        },
        'plugins': scan_config.get('plugins', {})
    }

    # Extract settings (needed for update)
    for section_name, section_data in scan_config.get('settings', {}).items():
        if isinstance(section_data, dict):
            inputs = section_data.get('inputs')
            if inputs:
                for input_item in inputs:
                    input_id = input_item.get('id')
                    default_value = input_item.get('default')
                    if input_id and default_value is not None:
                        payload['settings'][input_id] = default_value

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
            print(f"[SUCCESS] SSH credentials updated for scan {scan_id}")
            return True
        else:
            print(f"[FAILED] Failed to update credentials")
            print(f"Status code: {response.status_code}")
            print(f"Response: {response.text}")
            return False

    except Exception as e:
        print(f"Error updating credentials: {e}")
        import traceback
        traceback.print_exc()
        return False


def print_usage():
    """Print usage instructions"""
    print("Usage:")
    print("  Export SSH credentials template:")
    print("    python manage_credentials.py <scan_id>")
    print()
    print("  Import SSH credentials from template:")
    print("    python manage_credentials.py <scan_id> <json_file>")
    print()
    print("Examples:")
    print("  python manage_credentials.py 12")
    print("    -> Creates scan_12_ssh_credentials.json with template")
    print()
    print("  python manage_credentials.py 12 scan_12_ssh_credentials.json")
    print("    -> Updates scan 12 with credentials from JSON file")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(1)

    scan_id = sys.argv[1]

    # Check if scan is running
    print(f"Checking scan {scan_id} status...")
    status = get_scan_status(scan_id)

    if status == 'running':
        print(f"[ERROR] Scan {scan_id} is currently running")
        print("Please stop the scan before modifying credentials")
        sys.exit(1)

    if status is None:
        print(f"[WARNING] Could not determine scan status (scan may not exist)")

    if len(sys.argv) == 2:
        # Export mode
        output_file = f"scan_{scan_id}_ssh_credentials.json"
        if not export_credentials_template(scan_id, output_file):
            sys.exit(1)
    elif len(sys.argv) == 3:
        # Import mode
        template_file = sys.argv[2]

        # Authenticate
        print(f"Authenticating as {USERNAME}...")
        api_token, session_token = authenticate(USERNAME, PASSWORD)

        if not api_token or not session_token:
            print("Authentication failed. Cannot update credentials.")
            sys.exit(1)

        # Import credentials
        if not import_credentials_from_template(scan_id, api_token, session_token, template_file):
            sys.exit(1)
    else:
        print_usage()
        sys.exit(1)
