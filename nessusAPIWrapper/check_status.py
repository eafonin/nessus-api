"""Check Nessus server status"""
import urllib3
from tenable.nessus import Nessus

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

nessus = Nessus(
    url='https://172.30.0.3:8834',
    access_key='dca6c2f38119ba7eb2f40ddec670f680d7d1fb3cf8cf1f93ffdc7f8d7165b044',
    secret_key='45b6a702ceb4005b933cee1bd9b09cea96a82a1da68977cf4982c31ea8c83d79',
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
