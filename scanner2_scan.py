"""Create and launch a scan on the second Nessus scanner"""
import urllib3
from tenable.nessus import Nessus
import time

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Second scanner configuration
NESSUS_URL = 'https://172.30.0.4:8834'
USERNAME = 'nessus'
PASSWORD = 'nessus'
TARGET = '172.32.0.215'

def main():
    print(f"Connecting to Nessus scanner at {NESSUS_URL}...")

    # Connect to Nessus
    nessus = Nessus(
        url=NESSUS_URL,
        username=USERNAME,
        password=PASSWORD,
        ssl_verify=False
    )

    print("✓ Connected successfully")

    # Check scanner status
    print("\nChecking scanner status...")
    status = nessus.server.status()
    print(f"  Status: {status.get('status')}")
    print(f"  Feed status: {status.get('detailed_status', {}).get('feed_status', {}).get('status')}")

    # List available scanners
    print("\nAvailable scanners:")
    scanners = nessus.scanners.list()
    for scanner in scanners.get('scanners', []):
        print(f"  - {scanner.get('name')} (ID: {scanner.get('id')}, Status: {scanner.get('status')})")
        if scanner.get('loaded_plugin_set'):
            print(f"    Plugin Set: {scanner.get('loaded_plugin_set')}")

    # Create scan
    print(f"\nCreating scan for target: {TARGET}")
    scan = nessus.scans.create(
        name=f"Scanner2 Scan - {TARGET}",
        description=f"Automated scan from second scanner",
        targets=[TARGET],
        template='basic'  # Using basic network scan template
    )

    scan_id = scan.get('scan', {}).get('id')
    print(f"✓ Scan created with ID: {scan_id}")

    # Launch the scan
    print(f"\nLaunching scan {scan_id}...")
    nessus.scans.launch(scan_id)
    print("✓ Scan launched successfully")

    # Check scan status
    time.sleep(2)
    scan_details = nessus.scans.details(scan_id)
    print(f"\nScan Status:")
    print(f"  Name: {scan_details.get('info', {}).get('name')}")
    print(f"  Status: {scan_details.get('info', {}).get('status')}")
    print(f"  Targets: {scan_details.get('info', {}).get('targets')}")
    print(f"  Scanner: {scan_details.get('info', {}).get('scanner_name')}")

    print(f"\nScan is running. You can check progress at:")
    print(f"  {NESSUS_URL}/#/scans/{scan_id}")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
