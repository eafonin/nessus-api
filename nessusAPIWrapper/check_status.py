"""Check Nessus server status"""
import urllib3
from tenable.nessus import Nessus

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

nessus = Nessus(
    url='https://172.32.0.209:8834',
    access_key='27f46c288d1b5d229f152128ed219cec3962a811a9090da0a3e8375c53389298',
    secret_key='11a99860b2355d1dc1a91999c096853d1e2ff20a88e30fc5866de82c97005329',
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
