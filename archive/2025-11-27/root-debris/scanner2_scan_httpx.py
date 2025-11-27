"""Create and launch a scan on the second Nessus scanner using httpx"""
import httpx
import json
import time

# Second scanner configuration
NESSUS_URL = 'https://172.30.0.4:8834'
USERNAME = 'nessus'
PASSWORD = 'nessus'
TARGET = '172.32.0.215'

def main():
    print(f"Connecting to Nessus scanner at {NESSUS_URL}...")

    # Create httpx client with SSL verification disabled
    client = httpx.Client(verify=False, timeout=30.0)

    # Authenticate
    print("Authenticating...")
    auth_resp = client.post(
        f"{NESSUS_URL}/session",
        json={'username': USERNAME, 'password': PASSWORD},
        headers={'Content-Type': 'application/json'}
    )

    if auth_resp.status_code != 200:
        print(f"Authentication failed: {auth_resp.status_code}")
        print(auth_resp.text)
        return

    token = auth_resp.json().get('token')
    print("✓ Authenticated successfully")

    # Set up headers with token
    headers = {
        'X-Cookie': f'token={token}',
        'Content-Type': 'application/json'
    }

    # Check scanner status
    print("\nChecking scanner status...")
    status_resp = client.get(f"{NESSUS_URL}/server/status", headers=headers)
    status = status_resp.json()
    print(f"  Status: {status.get('status')}")
    print(f"  Feed status: {status.get('detailed_status', {}).get('feed_status', {}).get('status')}")

    # List available scanners
    print("\nAvailable scanners:")
    scanners_resp = client.get(f"{NESSUS_URL}/scanners", headers=headers)
    scanners = scanners_resp.json().get('scanners', [])
    for scanner in scanners:
        print(f"  - {scanner.get('name')} (ID: {scanner.get('id')}, Status: {scanner.get('status')})")
        if scanner.get('loaded_plugin_set'):
            print(f"    Plugin Set: {scanner.get('loaded_plugin_set')}")

    # Get templates
    print("\nGetting scan templates...")
    templates_resp = client.get(f"{NESSUS_URL}/editor/scan/templates", headers=headers)
    templates = templates_resp.json().get('templates', [])

    # Find Basic Network Scan template
    basic_template = None
    for template in templates:
        if 'basic' in template.get('name', '').lower():
            basic_template = template
            break

    if not basic_template:
        # Use first available template
        basic_template = templates[0] if templates else None

    if not basic_template:
        print("No templates available")
        return

    print(f"  Using template: {basic_template.get('title', basic_template.get('name'))}")

    # Create scan
    print(f"\nCreating scan for target: {TARGET}")
    scan_data = {
        'uuid': basic_template.get('uuid'),
        'settings': {
            'name': f"Scanner2 Scan - {TARGET}",
            'description': f"Automated scan from second scanner",
            'text_targets': TARGET,
            'scanner_id': '1',  # Default local scanner
            'folder_id': 3,  # My Scans folder
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
        return

    scan_info = create_resp.json()
    scan_id = scan_info.get('scan', {}).get('id')
    print(f"✓ Scan created with ID: {scan_id}")

    # Launch the scan
    print(f"\nLaunching scan {scan_id}...")
    launch_resp = client.post(
        f"{NESSUS_URL}/scans/{scan_id}/launch",
        headers=headers
    )

    if launch_resp.status_code == 200:
        print("✓ Scan launched successfully")
    else:
        print(f"Failed to launch scan: {launch_resp.status_code}")
        print(launch_resp.text)
        return

    # Check scan status
    time.sleep(2)
    details_resp = client.get(f"{NESSUS_URL}/scans/{scan_id}", headers=headers)
    scan_details = details_resp.json()
    info = scan_details.get('info', {})

    print(f"\nScan Status:")
    print(f"  Name: {info.get('name')}")
    print(f"  Status: {info.get('status')}")
    print(f"  Targets: {info.get('targets')}")
    print(f"  Scanner: {info.get('scanner_name')}")

    print(f"\nScan is running. You can check progress at:")
    print(f"  {NESSUS_URL}/#/scans/{scan_id}")

    client.close()

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
