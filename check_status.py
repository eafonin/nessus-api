"""Check Nessus server status"""
import urllib3
from tenable.nessus import Nessus

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

nessus = Nessus(
    url='https://localhost:8834',
    access_key='abc04cab03684de788ba0c4614eaba6302d3fe26852da06040eac3879547e405',
    secret_key='06332ecfd4bc633667be4e20e139c9451a848c580da988c69679fde16ce9c837',
    ssl_verify=False
)

try:
    status = nessus.server.status()
    print("Server Status:")
    print(f"  Status: {status.get('status')}")
    print(f"  Progress: {status.get('progress', 'N/A')}")
    print(f"  Must Destroy Session: {status.get('must_destroy_session', 'N/A')}")
    print(f"\nFull status:")
    for k, v in status.items():
        print(f"  {k}: {v}")
except Exception as e:
    print(f"Error: {e}")
