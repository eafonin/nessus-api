"""
List all scans from Nessus Essentials
"""
import urllib3
from tenable.nessus import Nessus

# Disable SSL warnings for localhost/self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Initialize Nessus client
nessus = Nessus(
    url='https://localhost:8834',
    access_key='abc04cab03684de788ba0c4614eaba6302d3fe26852da06040eac3879547e405',
    secret_key='06332ecfd4bc633667be4e20e139c9451a848c580da988c69679fde16ce9c837',
    ssl_verify=False  # Required for localhost/self-signed certs
)

# Get list of scans
try:
    scans_data = nessus.scans.list()

    print("=" * 80)
    print("MY SCANS")
    print("=" * 80)

    if 'scans' in scans_data and scans_data['scans']:
        for scan in scans_data['scans']:
            print(f"\nScan ID: {scan.get('id')}")
            print(f"  Name: {scan.get('name')}")
            print(f"  Status: {scan.get('status')}")
            print(f"  Folder: {scan.get('folder_id')}")
            print(f"  Enabled: {scan.get('enabled')}")
            print(f"  Last Modified: {scan.get('last_modification_date')}")
            if scan.get('uuid'):
                print(f"  UUID: {scan.get('uuid')}")
    else:
        print("\nNo scans found.")

    # Also show folders if available
    if 'folders' in scans_data and scans_data['folders']:
        print("\n" + "=" * 80)
        print("FOLDERS")
        print("=" * 80)
        for folder in scans_data['folders']:
            print(f"Folder ID: {folder.get('id')} - Name: {folder.get('name')}")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
