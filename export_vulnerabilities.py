"""
Export vulnerability data from a Nessus scan
Usage: python export_vulnerabilities.py <scan_id_or_name> [options]
"""
import sys
import urllib3
from tenable.nessus import Nessus
import json
import csv
from datetime import datetime

# Disable SSL warnings for localhost/self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Initialize Nessus client
nessus = Nessus(
    url='https://localhost:8834',
    access_key='abc04cab03684de788ba0c4614eaba6302d3fe26852da06040eac3879547e405',
    secret_key='06332ecfd4bc633667be4e20e139c9451a848c580da988c69679fde16ce9c837',
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


def get_vulnerability_details(scan_id, plugin_id, host_id=None):
    """Get detailed information about a specific vulnerability"""
    try:
        if host_id:
            details = nessus.scans.plugin_output(scan_id, host_id, plugin_id)
            return details
        return None
    except Exception as e:
        return None


def export_to_json(scan_id, scan_name, output_file=None):
    """Export vulnerability data to JSON format"""
    print(f"[*] Exporting vulnerability data to JSON...")

    details = nessus.scans.details(scan_id)

    if not output_file:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f"vulns_{scan_name.replace(' ', '_')}_{timestamp}.json"

    export_data = {
        'scan_info': {
            'scan_id': scan_id,
            'scan_name': scan_name,
            'status': details['info'].get('status'),
            'targets': details['info'].get('targets'),
            'scan_start': details['info'].get('scan_start'),
            'scan_end': details['info'].get('scan_end'),
            'policy': details['info'].get('policy'),
            'export_date': datetime.now().isoformat()
        },
        'vulnerabilities': details.get('vulnerabilities', []),
        'hosts': details.get('hosts', []),
        'remediations': details.get('remediations', {})
    }

    with open(output_file, 'w') as f:
        json.dump(export_data, f, indent=2)

    print(f"[+] JSON export saved to: {output_file}")
    return output_file


def export_to_csv(scan_id, scan_name, output_file=None):
    """Export vulnerability data to CSV format"""
    print(f"[*] Exporting vulnerability data to CSV...")

    details = nessus.scans.details(scan_id)

    if not output_file:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f"vulns_{scan_name.replace(' ', '_')}_{timestamp}.csv"

    vulnerabilities = details.get('vulnerabilities', [])

    if not vulnerabilities:
        print("[!] No vulnerabilities found in scan")
        return None

    # CSV headers
    fieldnames = [
        'plugin_id', 'plugin_name', 'plugin_family', 'severity',
        'severity_name', 'count', 'cvss_score', 'vpr_score',
        'epss_score', 'cpe'
    ]

    severity_map = {
        0: 'Info',
        1: 'Low',
        2: 'Medium',
        3: 'High',
        4: 'Critical'
    }

    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for vuln in vulnerabilities:
            row = {
                'plugin_id': vuln.get('plugin_id'),
                'plugin_name': vuln.get('plugin_name'),
                'plugin_family': vuln.get('plugin_family'),
                'severity': vuln.get('severity'),
                'severity_name': severity_map.get(vuln.get('severity'), 'Unknown'),
                'count': vuln.get('count'),
                'cvss_score': vuln.get('score') or '',
                'vpr_score': vuln.get('vpr_score') or '',
                'epss_score': vuln.get('epss_score') or '',
                'cpe': vuln.get('cpe') or ''
            }
            writer.writerow(row)

    print(f"[+] CSV export saved to: {output_file}")
    return output_file


def export_scan_file(scan_id, scan_name, format='nessus', output_file=None):
    """Export full scan in native Nessus format (nessus, csv, html, pdf)"""
    print(f"[*] Exporting scan in {format.upper()} format...")
    print(f"[*] This may take a while for large scans...")

    if not output_file:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        ext_map = {
            'nessus': 'nessus',
            'csv': 'csv',
            'html': 'html',
            'pdf': 'pdf',
            'db': 'db'
        }
        ext = ext_map.get(format, format)
        output_file = f"scan_{scan_name.replace(' ', '_')}_{timestamp}.{ext}"

    try:
        # Export scan
        with open(output_file, 'wb') as f:
            nessus.scans.export_scan(scan_id, fobj=f, format=format)

        print(f"[+] {format.upper()} export saved to: {output_file}")
        return output_file

    except Exception as e:
        print(f"[!] Error exporting scan: {e}")
        import traceback
        traceback.print_exc()
        return None


def display_vulnerability_summary(scan_id, scan_name):
    """Display a summary of vulnerabilities"""
    details = nessus.scans.details(scan_id)
    vulnerabilities = details.get('vulnerabilities', [])
    hosts = details.get('hosts', [])

    print("\n" + "=" * 70)
    print(f"VULNERABILITY SUMMARY: {scan_name}")
    print("=" * 70)

    # Scan info
    info = details['info']
    print(f"\n[SCAN INFORMATION]")
    print(f"  Scan ID: {scan_id}")
    print(f"  Status: {info.get('status')}")
    print(f"  Targets: {info.get('targets')}")
    print(f"  Policy: {info.get('policy')}")
    if info.get('scan_start'):
        print(f"  Scan Start: {datetime.fromtimestamp(info['scan_start'])}")
    if info.get('scan_end'):
        print(f"  Scan End: {datetime.fromtimestamp(info['scan_end'])}")

    # Host summary
    print(f"\n[HOST SUMMARY]")
    print(f"  Total Hosts: {len(hosts)}")
    for host in hosts:
        print(f"    - {host.get('hostname', 'Unknown')} ({host.get('host_ip', 'N/A')})")
        print(f"      Critical: {host.get('critical', 0)}, High: {host.get('high', 0)}, "
              f"Medium: {host.get('medium', 0)}, Low: {host.get('low', 0)}, Info: {host.get('info', 0)}")

    # Vulnerability summary by severity
    severity_counts = {0: 0, 1: 0, 2: 0, 3: 0, 4: 0}
    for vuln in vulnerabilities:
        sev = vuln.get('severity', 0)
        severity_counts[sev] = severity_counts.get(sev, 0) + vuln.get('count', 1)

    severity_names = {0: 'Info', 1: 'Low', 2: 'Medium', 3: 'High', 4: 'Critical'}

    print(f"\n[VULNERABILITY SUMMARY]")
    print(f"  Total Unique Vulnerabilities: {len(vulnerabilities)}")
    for sev in [4, 3, 2, 1, 0]:
        print(f"  {severity_names[sev]:8s}: {severity_counts[sev]:5d}")

    # Top 10 critical/high vulnerabilities
    critical_high = [v for v in vulnerabilities if v.get('severity', 0) >= 3]
    if critical_high:
        print(f"\n[TOP CRITICAL/HIGH VULNERABILITIES]")
        critical_high.sort(key=lambda x: (x.get('severity', 0), x.get('count', 0)), reverse=True)

        for i, vuln in enumerate(critical_high[:10], 1):
            sev_name = severity_names.get(vuln.get('severity'), 'Unknown')
            print(f"\n  {i}. [{sev_name}] {vuln.get('plugin_name')}")
            print(f"     Plugin ID: {vuln.get('plugin_id')}")
            print(f"     Count: {vuln.get('count')} occurrence(s)")
            if vuln.get('score'):
                print(f"     CVSS Score: {vuln.get('score')}")

    print("\n" + "=" * 70)


def main():
    if len(sys.argv) < 2:
        print("=" * 70)
        print("NESSUS VULNERABILITY EXPORTER")
        print("=" * 70)
        print("\nUsage: python export_vulnerabilities.py <scan_id_or_name> [format]")
        print("\nFormats:")
        print("  json      - Export vulnerability list to JSON (default)")
        print("  csv       - Export vulnerability list to CSV")
        print("  nessus    - Export full scan in .nessus format")
        print("  html      - Export full scan as HTML report")
        print("  pdf       - Export full scan as PDF report")
        print("  all       - Export in all formats")
        print("\nExamples:")
        print("  python export_vulnerabilities.py 12")
        print("  python export_vulnerabilities.py '172.32.0.209' csv")
        print("  python export_vulnerabilities.py 'Basic Network' all")
        print("\n" + "=" * 70)

        # Show available scans
        print("\nAvailable scans:")
        scans_data = nessus.scans.list()
        for s in scans_data.get('scans', []):
            status_icon = {
                'completed': '[OK]',
                'running': '[>>]',
                'canceled': '[XX]'
            }.get(s['status'], '[ ]')
            print(f"  {status_icon} ID: {s['id']:3d} - {s['name']:40s} [{s['status']}]")

        sys.exit(1)

    search_term = sys.argv[1]
    export_format = sys.argv[2].lower() if len(sys.argv) > 2 else 'json'

    print("=" * 70)
    print("NESSUS VULNERABILITY EXPORTER")
    print("=" * 70)
    print(f"\n[*] Searching for scan: '{search_term}'...")

    scan = find_scan_by_name_or_id(search_term)

    if not scan:
        print(f"[!] Scan '{search_term}' not found")
        print("\n[*] Available scans:")
        scans_data = nessus.scans.list()
        for s in scans_data.get('scans', []):
            print(f"  ID: {s['id']} - Name: {s['name']}")
        sys.exit(1)

    scan_id = scan['id']
    scan_name = scan['name']

    print(f"[+] Found scan: {scan_name} (ID: {scan_id})")
    print(f"[*] Status: {scan['status']}")

    if scan['status'] not in ['completed', 'canceled']:
        print(f"[!] Warning: Scan status is '{scan['status']}', export may be incomplete")

    print()

    # Display summary
    display_vulnerability_summary(scan_id, scan_name)

    # Export based on format
    print(f"\n[*] Export format: {export_format.upper()}")

    exported_files = []

    if export_format == 'all':
        exported_files.append(export_to_json(scan_id, scan_name))
        exported_files.append(export_to_csv(scan_id, scan_name))
        exported_files.append(export_scan_file(scan_id, scan_name, 'nessus'))
        exported_files.append(export_scan_file(scan_id, scan_name, 'html'))
        exported_files.append(export_scan_file(scan_id, scan_name, 'csv'))
    elif export_format == 'json':
        exported_files.append(export_to_json(scan_id, scan_name))
    elif export_format == 'csv':
        exported_files.append(export_to_csv(scan_id, scan_name))
    elif export_format in ['nessus', 'html', 'pdf']:
        exported_files.append(export_scan_file(scan_id, scan_name, export_format))
    else:
        print(f"[!] Unknown format: {export_format}")
        print("[*] Supported formats: json, csv, nessus, html, pdf, all")
        sys.exit(1)

    # Summary
    print("\n" + "=" * 70)
    print("[+] EXPORT COMPLETE")
    print("=" * 70)
    print("\nExported files:")
    for f in exported_files:
        if f:
            print(f"  - {f}")
    print()


if __name__ == '__main__':
    main()
