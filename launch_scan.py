"""
Launch Nessus scans by simulating web UI button press
Bypasses API license restrictions by using direct HTTP requests
"""
import sys
import urllib3
import requests
from tenable.nessus import Nessus

# Disable SSL warnings for localhost/self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Nessus configuration
NESSUS_URL = 'https://localhost:8834'
ACCESS_KEY = 'abc04cab03684de788ba0c4614eaba6302d3fe26852da06040eac3879547e405'
SECRET_KEY = '06332ecfd4bc633667be4e20e139c9451a848c580da988c69679fde16ce9c837'
STATIC_API_TOKEN = 'af824aba-e642-4e63-a49b-0810542ad8a5'

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
        'Host': 'localhost:8834',
        'Origin': 'https://localhost:8834',
        'Referer': 'https://localhost:8834/',
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
            # Extract session token from response body
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


def list_scans():
    """List all available scans using API"""
    nessus = Nessus(
        url=NESSUS_URL,
        access_key=ACCESS_KEY,
        secret_key=SECRET_KEY,
        ssl_verify=False
    )

    try:
        scans_data = nessus.scans.list()

        print("=" * 80)
        print("AVAILABLE SCANS")
        print("=" * 80)

        if 'scans' in scans_data and scans_data['scans']:
            for scan in scans_data['scans']:
                scan_id = scan.get('id')
                name = scan.get('name')
                status = scan.get('status')
                print(f"ID: {scan_id:4} | Status: {status:12} | Name: {name}")
        else:
            print("No scans found.")

    except Exception as e:
        print(f"Error listing scans: {e}")
        sys.exit(1)


def launch_scan(scan_id, api_token, cookie_token):
    """
    Launch a scan by simulating web UI button press

    Args:
        scan_id: The scan ID to launch
        api_token: X-API-Token from browser (copy from dev tools)
        cookie_token: X-Cookie token value from browser (copy from dev tools)
    """
    url = f"{NESSUS_URL}/scans/{scan_id}/launch"

    headers = {
        'Accept': '*/*',
        'Accept-Encoding': 'gzip, deflate, br, zstd',
        'Accept-Language': 'en-US,en;q=0.9,ru;q=0.8',
        'Connection': 'keep-alive',
        'Content-Length': '0',
        'Content-Type': 'application/json',
        'Host': 'localhost:8834',
        'Origin': 'https://localhost:8834',
        'Referer': 'https://localhost:8834/',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-origin',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36',
        'X-API-Token': api_token,
        'X-Cookie': f'token={cookie_token}',
        'X-KL-kfa-Ajax-Request': 'Ajax_Request',
        'sec-ch-ua': '"Google Chrome";v="141", "Not?A_Brand";v="8", "Chromium";v="141"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"'
    }

    try:
        response = requests.post(url, headers=headers, verify=False)

        if response.status_code == 200:
            print(f"[SUCCESS] Scan {scan_id} launched successfully!")
            print(f"Response: {response.text}")
        else:
            print(f"[FAILED] Failed to launch scan {scan_id}")
            print(f"Status code: {response.status_code}")
            print(f"Response: {response.text}")

    except Exception as e:
        print(f"Error launching scan: {e}")
        sys.exit(1)


def stop_scan(scan_id, api_token, cookie_token):
    """
    Stop a running scan by simulating web UI button press

    Args:
        scan_id: The scan ID to stop
        api_token: X-API-Token from browser or authentication
        cookie_token: X-Cookie token value from browser or authentication
    """
    url = f"{NESSUS_URL}/scans/{scan_id}/stop"

    headers = {
        'Accept': '*/*',
        'Accept-Encoding': 'gzip, deflate, br, zstd',
        'Accept-Language': 'en-US,en;q=0.9,ru;q=0.8',
        'Connection': 'keep-alive',
        'Content-Length': '0',
        'Content-Type': 'application/json',
        'Host': 'localhost:8834',
        'Origin': 'https://localhost:8834',
        'Referer': 'https://localhost:8834/',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-origin',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36',
        'X-API-Token': api_token,
        'X-Cookie': f'token={cookie_token}',
        'X-KL-kfa-Ajax-Request': 'Ajax_Request',
        'sec-ch-ua': '"Google Chrome";v="141", "Not?A_Brand";v="8", "Chromium";v="141"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"'
    }

    try:
        response = requests.post(url, headers=headers, verify=False)

        if response.status_code == 200:
            print(f"[SUCCESS] Scan {scan_id} stopped successfully!")
            if response.text:
                print(f"Response: {response.text}")
        else:
            print(f"[FAILED] Failed to stop scan {scan_id}")
            print(f"Status code: {response.status_code}")
            print(f"Response: {response.text}")

    except Exception as e:
        print(f"Error stopping scan: {e}")


def stop_all_scans():
    """Stop all running scans"""
    print(f"Authenticating as {USERNAME}...")
    api_token, session_token = authenticate(USERNAME, PASSWORD)

    if not api_token or not session_token:
        print("Authentication failed. Cannot stop scans.")
        sys.exit(1)

    # Get list of scans
    nessus = Nessus(
        url=NESSUS_URL,
        access_key=ACCESS_KEY,
        secret_key=SECRET_KEY,
        ssl_verify=False
    )

    try:
        scans_data = nessus.scans.list()

        if 'scans' in scans_data and scans_data['scans']:
            running_scans = [s for s in scans_data['scans'] if s.get('status') == 'running']

            if running_scans:
                print(f"\nFound {len(running_scans)} running scan(s). Stopping...")
                for scan in running_scans:
                    scan_id = scan.get('id')
                    name = scan.get('name')
                    print(f"\nStopping scan {scan_id}: {name}")
                    stop_scan(scan_id, api_token, session_token)
            else:
                print("\nNo running scans found.")
        else:
            print("\nNo scans found.")

    except Exception as e:
        print(f"Error listing scans: {e}")
        sys.exit(1)


def print_usage():
    """Print usage instructions"""
    print("Usage:")
    print("  List scans:")
    print("    python launch_scan.py")
    print("    python launch_scan.py list")
    print()
    print("  Launch scan (auto-login):")
    print("    python launch_scan.py launch <scan_id>")
    print()
    print("  Stop scan (auto-login):")
    print("    python launch_scan.py stop <scan_id>")
    print()
    print("  Stop all running scans:")
    print("    python launch_scan.py stop-all")
    print()
    print("  Launch scan (manual tokens):")
    print("    python launch_scan.py launch <scan_id> <X-API-Token> <cookie_token>")
    print()
    print("Examples:")
    print("    python launch_scan.py launch 24")
    print("    python launch_scan.py stop 18")
    print("    python launch_scan.py stop-all")


if __name__ == "__main__":
    if len(sys.argv) == 1:
        # No arguments - list scans
        list_scans()
    elif len(sys.argv) == 2:
        command = sys.argv[1]

        if command == "list":
            list_scans()
        elif command == "stop-all":
            stop_all_scans()
        else:
            # Backward compatibility: assume it's a scan ID to launch
            scan_id = command
            print(f"Authenticating as {USERNAME}...")
            api_token, session_token = authenticate(USERNAME, PASSWORD)

            if api_token and session_token:
                launch_scan(scan_id, api_token, session_token)
            else:
                print("Authentication failed. Cannot launch scan.")
                sys.exit(1)
    elif len(sys.argv) == 3:
        command = sys.argv[1]
        scan_id = sys.argv[2]

        if command == "launch":
            print(f"Authenticating as {USERNAME}...")
            api_token, session_token = authenticate(USERNAME, PASSWORD)

            if api_token and session_token:
                launch_scan(scan_id, api_token, session_token)
            else:
                print("Authentication failed. Cannot launch scan.")
                sys.exit(1)
        elif command == "stop":
            print(f"Authenticating as {USERNAME}...")
            api_token, session_token = authenticate(USERNAME, PASSWORD)

            if api_token and session_token:
                stop_scan(scan_id, api_token, session_token)
            else:
                print("Authentication failed. Cannot stop scan.")
                sys.exit(1)
        else:
            print_usage()
            sys.exit(1)
    elif len(sys.argv) == 5:
        # Launch/stop scan with provided tokens
        command = sys.argv[1]
        scan_id = sys.argv[2]
        api_token = sys.argv[3]
        cookie_token = sys.argv[4]

        if command == "launch":
            launch_scan(scan_id, api_token, cookie_token)
        elif command == "stop":
            stop_scan(scan_id, api_token, cookie_token)
        else:
            print_usage()
            sys.exit(1)
    else:
        # Invalid arguments
        print_usage()
        sys.exit(1)
