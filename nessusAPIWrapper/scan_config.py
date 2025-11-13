"""
Display detailed scan configuration including credentials, targets, and parameters
Usage: python scan_config.py [scan_name_or_id]
"""
import sys
import urllib3
from tenable.nessus import Nessus
import json

# Disable SSL warnings for localhost/self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Initialize Nessus client
nessus = Nessus(
    url='https://172.32.0.209:8834',
    access_key='27f46c288d1b5d229f152128ed219cec3962a811a9090da0a3e8375c53389298',
    secret_key='11a99860b2355d1dc1a91999c096853d1e2ff20a88e30fc5866de82c97005329',
    ssl_verify=False
)


def find_scan_by_name_or_id(search_term):
    """Find a scan by name or ID"""
    scans_data = nessus.scans.list()

    # Try to match by ID first if search_term is numeric
    if search_term.isdigit():
        scan_id = int(search_term)
        for scan in scans_data.get('scans', []):
            if scan['id'] == scan_id:
                return scan

    # Match by name (case-insensitive partial match)
    search_lower = search_term.lower()
    for scan in scans_data.get('scans', []):
        if search_lower in scan['name'].lower():
            return scan

    return None


def mask_sensitive(key, value):
    """Mask sensitive credential fields"""
    sensitive_keys = ['password', 'private_key', 'passphrase', 'secret', 'key_file']
    if any(sk in key.lower() for sk in sensitive_keys) and value:
        return "***REDACTED***"
    return value


def extract_input_values(inputs_list, prefix=""):
    """Recursively extract values from nested input structure"""
    result = {}

    for input_item in inputs_list:
        input_id = input_item.get('id')
        input_name = input_item.get('name')
        default_value = input_item.get('default', '')

        if default_value:
            full_name = f"{prefix}{input_name}" if prefix else input_name
            result[full_name] = {
                'id': input_id,
                'value': default_value,
                'type': input_item.get('type')
            }

        # Handle nested ui_radio options
        if input_item.get('type') in ['ui_radio', 'radio']:
            selected_option = input_item.get('default')
            options = input_item.get('options', [])

            # Find the selected option and recurse
            for option in options:
                option_name = option if isinstance(option, str) else option.get('name')
                if option_name == selected_option and isinstance(option, dict):
                    nested_inputs = option.get('inputs')
                    if nested_inputs:
                        nested_prefix = f"{input_name} > "
                        result.update(extract_input_values(nested_inputs, nested_prefix))

    return result


def display_credentials(credentials_data):
    """Parse and display configured credentials"""
    found_creds = False

    for category in credentials_data.get('data', []):
        category_name = category.get('name')

        for cred_type in category.get('types', []):
            type_name = cred_type.get('name')
            instances = cred_type.get('instances', [])

            if instances:
                found_creds = True
                print(f"\n[{category_name.upper()} - {type_name}]")

                for idx, instance in enumerate(instances, 1):
                    # Show summary if available
                    summary = instance.get('summary')
                    if summary:
                        print(f"  Instance #{idx}: {summary}")
                    else:
                        print(f"  Instance #{idx}:")

                    # Extract values from the nested inputs structure
                    instance_inputs = instance.get('inputs', [])
                    values = extract_input_values(instance_inputs)

                    # Display extracted values
                    for name, data in values.items():
                        display_value = mask_sensitive(data['id'], data['value'])
                        print(f"    {name}: {display_value}")

    if not found_creds:
        print("  No credentials configured")


def display_scan_config(scan_id, scan_name):
    """Display detailed scan configuration from editor API"""
    try:
        # Get configuration from editor API
        config = nessus.editor.details('scan', scan_id)

        print("=" * 80)
        print(f"SCAN CONFIGURATION: {scan_name}")
        print("=" * 80)

        # Basic Information
        print("\n[BASIC INFORMATION]")
        print(f"  Scan ID: {scan_id}")
        print(f"  Name: {config.get('name')}")
        print(f"  UUID: {config.get('uuid')}")
        print(f"  Owner: {config.get('owner')}")
        print(f"  Policy Template: {config.get('title')}")

        # Settings
        settings = config.get('settings', {})
        if settings:
            print("\n[SCAN SETTINGS]")
            print(f"  Name: {settings.get('name', 'N/A')}")
            print(f"  Description: {settings.get('description', 'N/A')}")
            print(f"  Folder ID: {settings.get('folder_id')}")
            print(f"  Scanner ID: {settings.get('scanner_id')}")
            print(f"  Policy ID: {settings.get('policy_id')}")
            print(f"  Enabled: {settings.get('enabled', False)}")
            print(f"  Launch: {settings.get('launch', 'N/A')}")

            # Target information
            print("\n[TARGETS]")
            text_targets = settings.get('text_targets', '')
            file_targets = settings.get('file_targets', '')

            if text_targets:
                print(f"  IP/Hostname Targets: {text_targets}")
            if file_targets:
                print(f"  File Targets: {file_targets}")
            if not text_targets and not file_targets:
                print("  No targets configured")

            # Schedule
            if settings.get('enabled'):
                print("\n[SCHEDULE]")
                print(f"  Scheduled: Yes")
                rrules = settings.get('rrules', {})
                print(f"  Frequency: {rrules.get('freq', 'N/A')}")
                print(f"  Interval: {rrules.get('interval', 'N/A')}")
                if rrules.get('byweekday'):
                    print(f"  By Weekday: {rrules.get('byweekday')}")
                if rrules.get('bymonthday'):
                    print(f"  By Month Day: {rrules.get('bymonthday')}")
                print(f"  Start Time: {settings.get('starttime', 'N/A')}")
                print(f"  Timezone: {settings.get('timezone', 'N/A')}")

            # Advanced settings
            print("\n[ADVANCED SETTINGS]")
            if settings.get('max_scan_time'):
                print(f"  Max Scan Time: {settings.get('max_scan_time')} seconds")
            if settings.get('scan_time_window'):
                print(f"  Scan Time Window: {settings.get('scan_time_window')}")

            # Network discovery settings
            print(f"  Auto Mitigation: {settings.get('auto_mitigation', 'N/A')}")
            print(f"  Auto Mitigation Default: {settings.get('auto_mitigation_default', 'N/A')}")

            # Port scan settings
            if settings.get('portscan_range'):
                print(f"  Port Scan Range: {settings.get('portscan_range')}")

        # Credentials
        print("\n[CREDENTIALS]")
        credentials = config.get('credentials', {})
        if credentials:
            display_credentials(credentials)
        else:
            print("  No credentials configured")

        # Plugins summary
        plugins = config.get('plugins', {})
        if plugins:
            print("\n[PLUGINS]")
            enabled_count = sum(1 for fam in plugins.values()
                                if fam.get('status') == 'enabled')
            print(f"  Total Plugin Families: {len(plugins)}")
            print(f"  Enabled Families: {enabled_count}")

        # Output option to save full config
        print("\n" + "=" * 80)
        print("Tip: Full config saved to scan_config_debug.json for inspection")

        # Save full config for debugging
        with open('scan_config_debug.json', 'w') as f:
            json.dump(config, f, indent=2)

    except Exception as e:
        print(f"Error retrieving scan configuration: {e}")
        import traceback
        traceback.print_exc()


def main():
    # Get scan name/ID from command line or use default
    if len(sys.argv) > 1:
        search_term = ' '.join(sys.argv[1:])
    else:
        search_term = "172.32.0.209_authed"  # Default for testing
        print(f"No scan specified, using default: {search_term}")

    print(f"\nSearching for scan: '{search_term}'...")

    # Find the scan
    scan = find_scan_by_name_or_id(search_term)

    if not scan:
        print(f"ERROR: Scan '{search_term}' not found")
        print("\nAvailable scans:")
        scans_data = nessus.scans.list()
        for s in scans_data.get('scans', []):
            print(f"  ID: {s['id']} - Name: {s['name']}")
        sys.exit(1)

    print(f"Found scan: {scan['name']} (ID: {scan['id']})\n")

    # Display configuration
    display_scan_config(scan['id'], scan['name'])


if __name__ == '__main__':
    main()
