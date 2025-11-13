"""Generate new Nessus API keys using username/password authentication"""
import urllib3
import requests
import json

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

NESSUS_URL = 'https://172.32.0.209:8834'
USERNAME = 'nessus'
PASSWORD = 'nessus'
# Fetch X-API-Token dynamically from Nessus Web UI
STATIC_API_TOKEN = extract_api_token_from_js()
if not STATIC_API_TOKEN:
    print("Error: Failed to fetch X-API-Token from Nessus Web UI", file=sys.stderr)
    sys.exit(1)

def authenticate():
    """Authenticate and get session token"""
    url = f"{NESSUS_URL}/session"
    headers = {
        'Accept': '*/*',
        'Content-Type': 'application/json',
        'X-API-Token': STATIC_API_TOKEN
    }
    payload = {
        'username': USERNAME,
        'password': PASSWORD
    }

    response = requests.post(url, json=payload, headers=headers, verify=False)
    if response.status_code == 200:
        return response.json().get('token')
    return None

def generate_api_keys(session_token):
    """Generate new API access/secret keys"""
    url = f"{NESSUS_URL}/session/keys"
    headers = {
        'Accept': '*/*',
        'Content-Type': 'application/json',
        'X-API-Token': STATIC_API_TOKEN,
        'X-Cookie': f'token={session_token}'
    }

    response = requests.put(url, headers=headers, verify=False)
    if response.status_code == 200:
        return response.json()
    return None

if __name__ == "__main__":
    print(f"Authenticating with {NESSUS_URL}...")
    session_token = authenticate()

    if not session_token:
        print("Authentication failed")
        exit(1)

    print("Generating new API keys...")
    keys = generate_api_keys(session_token)

    if keys:
        print("\n" + "="*70)
        print("NEW API KEYS GENERATED")
        print("="*70)
        print(f"\nACCESS_KEY = '{keys.get('accessKey')}'")
        print(f"SECRET_KEY = '{keys.get('secretKey')}'")
        print("\n" + "="*70)
        print("\nUpdate these values in your nessusAPIWrapper scripts")
    else:
        print("Failed to generate API keys")
        exit(1)
