"""Create scan on second scanner using direct API calls with known token"""
import httpx
import json

# Second scanner configuration
NESSUS_URL = 'https://172.30.0.4:8834'
USERNAME = 'nessus'
PASSWORD = 'nessus'
API_TOKEN = '55cd92f0-0ede-40ba-9327-eb003e94235c'
TARGET = '172.32.0.215'

client = httpx.Client(verify=False, timeout=30.0)

try:
    # Authenticate
    print(f"Authenticating with {NESSUS_URL}...")
    auth_resp = client.post(
        f"{NESSUS_URL}/session",
        json={'username': USERNAME, 'password': PASSWORD},
        headers={
            'Content-Type': 'application/json',
            'X-API-Token': API_TOKEN
        }
    )

    if auth_resp.status_code != 200:
        print(f"Authentication failed: {auth_resp.status_code}")
        print(auth_resp.text)
        exit(1)

    token = auth_resp.json().get('token')
    print(f"✓ Authenticated successfully")

    headers = {
        'X-Cookie': f'token={token}',
        'X-API-Token': API_TOKEN,
        'Content-Type': 'application/json'
    }

    # Get templates
    print("\nGetting scan templates...")
    templates_resp = client.get(f"{NESSUS_URL}/editor/scan/templates", headers=headers)
    templates = templates_resp.json().get('templates', [])

    # Find basic template
    basic_template = None
    for template in templates:
        if 'basic' in template.get('name', '').lower() or 'Basic' in template.get('title', ''):
            basic_template = template
            break

    if not basic_template and templates:
        basic_template = templates[0]

    if not basic_template:
        print("No templates found!")
        exit(1)

    print(f"Using template: {basic_template.get('title', basic_template.get('name'))}")

    # Create scan
    print(f"\nCreating scan for target: {TARGET}...")
    scan_data = {
        'uuid': basic_template.get('uuid'),
        'settings': {
            'name': f"Scanner2 Scan - {TARGET}",
            'description': f"Automated scan from second scanner",
            'text_targets': TARGET,
            'scanner_id': '1',
            'folder_id': 3,
            'enabled': False,
            'launch_now': False
        }
    }

    create_resp = client.post(
        f"{NESSUS_URL}/scans",
        json=scan_data,
        headers=headers
    )

    if create_resp.status_code != 200:
        print(f"Failed to create scan: {create_resp.status_code}")
        print(create_resp.text)
        exit(1)

    scan_info = create_resp.json()
    scan_id = scan_info.get('scan', {}).get('id')
    print(f"✓ Scan created with ID: {scan_id}")

    # Launch scan
    print(f"\nLaunching scan...")
    launch_resp = client.post(
        f"{NESSUS_URL}/scans/{scan_id}/launch",
        headers=headers
    )

    if launch_resp.status_code == 200:
        print(f"✓ Scan launched successfully!")
    else:
        print(f"Failed to launch: {launch_resp.status_code}")
        print(launch_resp.text)
        exit(1)

    # Get status
    details_resp = client.get(f"{NESSUS_URL}/scans/{scan_id}", headers=headers)
    scan_details = details_resp.json()
    info = scan_details.get('info', {})

    print(f"\n{'='*60}")
    print(f"SCAN DETAILS:")
    print(f"{'='*60}")
    print(f"  Scan ID: {scan_id}")
    print(f"  Name: {info.get('name')}")
    print(f"  Status: {info.get('status')}")
    print(f"  Targets: {info.get('targets')}")
    print(f"  Scanner: {info.get('scanner_name')}")
    print(f"{'='*60}")
    print(f"\nAccess scan at: {NESSUS_URL}/#/scans/{scan_id}")

except Exception as e:
    print(f"\nError: {e}")
    import traceback
    traceback.print_exc()
    exit(1)
finally:
    client.close()
