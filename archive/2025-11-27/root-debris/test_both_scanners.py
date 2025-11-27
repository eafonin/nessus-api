"""Test both scanners step by step with detailed output"""
import httpx
import re
import time

# Scanner configurations
SCANNERS = {
    'Scanner 1': {
        'url': 'https://172.30.0.3:8834',
        'ip': '172.30.0.3',
        'username': 'nessus',
        'password': 'nessus'
    },
    'Scanner 2': {
        'url': 'https://172.30.0.4:8834',
        'ip': '172.30.0.4',
        'username': 'nessus',
        'password': 'nessus'
    }
}

TARGET = '172.32.0.215'
BASIC_TEMPLATE_UUID = '731a8e52-3ea6-a291-ec0a-d2ff0619c19d7bd788d6be818b65'

def print_header(text):
    print("\n" + "="*70)
    print(text)
    print("="*70)

def print_step(step, text):
    print(f"\n[STEP {step}] {text}")
    print("-" * 70)

def extract_token(url):
    """Extract X-API-Token from nessus6.js"""
    client = httpx.Client(verify=False, timeout=10.0)
    try:
        response = client.get(f'{url}/nessus6.js')
        pattern = r'getApiToken[^}]+?return[\'"]([A-F0-9-]{30,})[\'"]'
        match = re.search(pattern, response.text, re.IGNORECASE)
        if match:
            return match.group(1)
        return None
    finally:
        client.close()

def authenticate(url, username, password, api_token):
    """Authenticate and get session token"""
    client = httpx.Client(verify=False, timeout=10.0)
    try:
        response = client.post(
            f'{url}/session',
            json={'username': username, 'password': password},
            headers={'Content-Type': 'application/json', 'X-API-Token': api_token}
        )
        if response.status_code == 200:
            return response.json().get('token')
        return None
    finally:
        client.close()

def create_scan(url, api_token, session_token, scanner_name, target):
    """Create a scan"""
    client = httpx.Client(verify=False, timeout=30.0)
    try:
        headers = {
            'X-Cookie': f'token={session_token}',
            'X-API-Token': api_token,
            'Content-Type': 'application/json'
        }

        scan_data = {
            'uuid': BASIC_TEMPLATE_UUID,
            'settings': {
                'name': f'{scanner_name} Test - {target} ({int(time.time())})',
                'description': f'Test scan from {scanner_name}',
                'text_targets': target,
                'scanner_id': '1',
                'folder_id': 3
            }
        }

        response = client.post(f'{url}/scans', json=scan_data, headers=headers)
        if response.status_code == 200:
            return response.json()['scan']
        return None
    finally:
        client.close()

def launch_scan(url, api_token, session_token, scan_id):
    """Launch a scan"""
    client = httpx.Client(verify=False, timeout=10.0)
    try:
        headers = {
            'X-Cookie': f'token={session_token}',
            'X-API-Token': api_token
        }
        response = client.post(f'{url}/scans/{scan_id}/launch', headers=headers)
        return response.status_code == 200
    finally:
        client.close()

def get_scan_status(url, api_token, session_token, scan_id):
    """Get scan status"""
    client = httpx.Client(verify=False, timeout=10.0)
    try:
        headers = {
            'X-Cookie': f'token={session_token}',
            'X-API-Token': api_token
        }
        response = client.get(f'{url}/scans/{scan_id}', headers=headers)
        if response.status_code == 200:
            return response.json().get('info', {})
        return None
    finally:
        client.close()

# Main test flow
print_header("TESTING BOTH NESSUS SCANNERS")

results = {}

# STEP 1: Extract X-API-Tokens
print_step(1, "EXTRACTING X-API-TOKENS FROM WEB UI")
for name, config in SCANNERS.items():
    print(f"\n{name} ({config['ip']}:8834):")
    token = extract_token(config['url'])
    if token:
        config['api_token'] = token
        print(f"  ✓ X-API-Token extracted: {token}")
    else:
        print(f"  ✗ Failed to extract token")
        exit(1)

# STEP 2: Authenticate
print_step(2, "AUTHENTICATING WITH CREDENTIALS")
for name, config in SCANNERS.items():
    print(f"\n{name} ({config['ip']}:8834):")
    print(f"  Username: {config['username']}")
    print(f"  Password: {config['password']}")
    session_token = authenticate(
        config['url'],
        config['username'],
        config['password'],
        config['api_token']
    )
    if session_token:
        config['session_token'] = session_token
        print(f"  ✓ Authentication successful")
        print(f"  Session Token: {session_token[:20]}...")
    else:
        print(f"  ✗ Authentication failed")
        exit(1)

# STEP 3: Create scans
print_step(3, f"CREATING SCANS FOR TARGET: {TARGET}")
for name, config in SCANNERS.items():
    print(f"\n{name} ({config['ip']}:8834):")
    scan = create_scan(
        config['url'],
        config['api_token'],
        config['session_token'],
        name,
        TARGET
    )
    if scan:
        config['scan_id'] = scan['id']
        config['scan_name'] = scan['name']
        print(f"  ✓ Scan created successfully")
        print(f"  Scan ID: {scan['id']}")
        print(f"  Scan Name: {scan['name']}")
    else:
        print(f"  ✗ Failed to create scan")
        exit(1)

# STEP 4: Launch scans
print_step(4, "LAUNCHING SCANS")
for name, config in SCANNERS.items():
    print(f"\n{name} ({config['ip']}:8834):")
    print(f"  Scan ID: {config['scan_id']}")
    success = launch_scan(
        config['url'],
        config['api_token'],
        config['session_token'],
        config['scan_id']
    )
    if success:
        print(f"  ✓ Scan launched successfully")
    else:
        print(f"  ✗ Failed to launch scan")
        exit(1)

# STEP 5: Check initial status
print_step(5, "CHECKING SCAN STATUS")
time.sleep(2)  # Wait a moment for scans to initialize
for name, config in SCANNERS.items():
    print(f"\n{name} ({config['ip']}:8834):")
    status = get_scan_status(
        config['url'],
        config['api_token'],
        config['session_token'],
        config['scan_id']
    )
    if status:
        print(f"  Scan Name: {status.get('name', 'N/A')}")
        print(f"  Status: {status.get('status', 'N/A')}")
        print(f"  Scanner: {status.get('scanner_name', 'N/A')}")
        print(f"  Targets: {status.get('targets', 'N/A')}")
        print(f"  Progress: {status.get('progress', 0)}%")
    else:
        print(f"  ✗ Failed to get status")

# Summary
print_header("TEST SUMMARY")
for name, config in SCANNERS.items():
    print(f"\n{name} ({config['ip']}:8834):")
    print(f"  Scan ID: {config['scan_id']}")
    print(f"  Scan Name: {config['scan_name']}")
    print(f"  Web UI: {config['url']}/#/scans/{config['scan_id']}")

print("\n" + "="*70)
print("✓ Both scanners tested successfully!")
print("="*70)
