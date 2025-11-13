"""
Export DETAILED vulnerability data from a Nessus scan (with full plugin info)
Usage: python export_vulnerabilities_detailed.py <scan_id_or_name> [format]
"""
import sys
import urllib3
from tenable.nessus import Nessus
import json
from datetime import datetime

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

    if search_term.isdigit():
        scan_id = int(search_term)
        for scan in scans_data.get('scans', []):
            if scan['id'] == scan_id:
                return scan

    search_lower = search_term.lower()
    for scan in scans_data.get('scans', []):
        if search_lower in scan['name'].lower():
            return scan

    return None


def get_detailed_plugin_info(scan_id, host_id, plugin_id):
    """Get full plugin details for a specific vulnerability"""
    try:
        return nessus.scans.plugin_output(scan_id, host_id, plugin_id)
    except Exception as e:
        print(f"[!] Error fetching plugin {plugin_id} for host {host_id}: {e}")
        return None


def export_detailed_json(scan_id, scan_name, output_file=None):
    """Export vulnerability data with FULL plugin details"""
    print(f"[*] Fetching detailed vulnerability data...")
    print(f"[*] This will take longer as it fetches complete plugin information...")

    details = nessus.scans.details(scan_id)
    hosts = details.get('hosts', [])
    vulnerabilities = details.get('vulnerabilities', [])

    if not output_file:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f"vulns_detailed_{scan_name.replace(' ', '_')}_{timestamp}.json"

    # Build detailed vulnerability database
    detailed_vulns = []
    total_vulns = sum(v.get('count', 1) for v in vulnerabilities)
    processed = 0

    print(f"[*] Processing {len(vulnerabilities)} unique vulnerabilities across {len(hosts)} host(s)...")

    for vuln in vulnerabilities:
        plugin_id = vuln.get('plugin_id')
        plugin_name = vuln.get('plugin_name')

        print(f"[*] [{processed+1}/{len(vulnerabilities)}] Fetching details for: {plugin_name} (Plugin {plugin_id})")

        # Get detailed info from each affected host
        vuln_details = {
            'plugin_id': plugin_id,
            'plugin_name': plugin_name,
            'plugin_family': vuln.get('plugin_family'),
            'severity': vuln.get('severity'),
            'count': vuln.get('count'),
            'cvss_score': vuln.get('score'),
            'vpr_score': vuln.get('vpr_score'),
            'epss_score': vuln.get('epss_score'),
            'affected_hosts': []
        }

        # Fetch detailed plugin output for each host
        for host in hosts:
            host_id = host.get('host_id')

            plugin_info = get_detailed_plugin_info(scan_id, host_id, plugin_id)

            if plugin_info and plugin_info.get('outputs'):
                # Extract first output (contains the detailed info)
                output = plugin_info['outputs'][0] if plugin_info['outputs'] else {}

                host_detail = {
                    'host_id': host_id,
                    'hostname': host.get('hostname'),
                    'host_ip': host.get('host_ip', ''),
                    'plugin_output': output.get('plugin_output', ''),
                    'severity': output.get('severity', 0),
                    'port': output.get('port', 0),
                    'protocol': output.get('protocol', ''),
                    'service_name': output.get('svc_name', '')
                }

                # Extract detailed plugin information from 'info' section
                if 'info' in plugin_info:
                    info = plugin_info['info']
                    if 'plugindescription' in info:
                        pd = info['plugindescription']
                        attrs = pd.get('pluginattributes', {})

                        # Extract risk information
                        risk_info = attrs.get('risk_information', {})
                        host_detail.update({
                            'risk_factor': risk_info.get('risk_factor'),
                            'cvss_base_score': risk_info.get('cvss_base_score'),
                            'cvss_vector': risk_info.get('cvss_vector'),
                            'cvss_temporal_score': risk_info.get('cvss_temporal_score'),
                            'cvss_temporal_vector': risk_info.get('cvss_temporal_vector'),
                            'cvss3_base_score': risk_info.get('cvss3_base_score'),
                            'cvss3_vector': risk_info.get('cvss3_vector'),
                            'cvss3_temporal_score': risk_info.get('cvss3_temporal_score'),
                            'cvss3_temporal_vector': risk_info.get('cvss3_temporal_vector'),
                            'cvss3_impact_score': attrs.get('cvssV3_impactScore'),
                        })

                        # Extract vulnerability information
                        vuln_info = attrs.get('vuln_information', {})
                        host_detail.update({
                            'exploit_available': vuln_info.get('exploit_available'),
                            'exploitability_ease': vuln_info.get('exploitability_ease'),
                            'exploit_code_maturity': attrs.get('exploit_code_maturity'),
                            'patch_publication_date': vuln_info.get('patch_publication_date'),
                            'vuln_publication_date': vuln_info.get('vuln_publication_date'),
                            'cpe': vuln_info.get('cpe'),
                            'age_of_vuln': attrs.get('age_of_vuln'),
                        })

                        # Extract plugin information
                        plugin_info_data = attrs.get('plugin_information', {})
                        host_detail.update({
                            'plugin_publication_date': plugin_info_data.get('plugin_publication_date'),
                            'plugin_modification_date': plugin_info_data.get('plugin_modification_date'),
                            'plugin_type': plugin_info_data.get('plugin_type'),
                            'plugin_version': plugin_info_data.get('plugin_version'),
                        })

                        # Extract references
                        ref_info = attrs.get('ref_information', {})
                        refs = ref_info.get('ref', [])
                        cve_list = []
                        xref_list = []
                        bid_list = []

                        for ref in refs:
                            ref_name = ref.get('name', '').lower()
                            values = ref.get('values', {}).get('value', [])

                            if ref_name == 'cve':
                                cve_list.extend(values)
                            elif ref_name == 'bid':
                                bid_list.extend(values)
                            else:
                                xref_list.extend([f"{ref_name.upper()}:{v}" for v in values])

                        host_detail.update({
                            'cve': cve_list,
                            'bid': bid_list,
                            'xref': xref_list,
                        })

                        # Extract descriptive text
                        host_detail.update({
                            'description': attrs.get('description'),
                            'solution': attrs.get('solution'),
                            'synopsis': attrs.get('synopsis'),
                            'see_also': attrs.get('see_also', []),
                            'fname': attrs.get('fname'),
                            'cvss_score_source': attrs.get('cvss_score_source'),
                            'threat_intensity_last_28': attrs.get('threat_intensity_last_28'),
                            'threat_recency': attrs.get('threat_recency'),
                            'threat_sources_last_28': attrs.get('threat_sources_last_28'),
                            'product_coverage': attrs.get('product_coverage'),
                            'generated_plugin': attrs.get('generated_plugin'),
                        })

                        # Add any USN references (Ubuntu Security Notices)
                        if 'usn' in attrs:
                            host_detail['usn'] = attrs['usn']

                vuln_details['affected_hosts'].append(host_detail)

        detailed_vulns.append(vuln_details)
        processed += 1

    # Build final export structure
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
        'hosts_summary': hosts,
        'vulnerabilities': detailed_vulns,
        'total_unique_vulnerabilities': len(vulnerabilities),
        'total_vulnerability_instances': total_vulns
    }

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(export_data, f, indent=2, ensure_ascii=False)

    print(f"[+] Detailed JSON export saved to: {output_file}")
    print(f"[+] Exported {len(detailed_vulns)} vulnerabilities with full details")

    return output_file


def display_summary(scan_id, scan_name):
    """Display vulnerability summary"""
    details = nessus.scans.details(scan_id)
    vulnerabilities = details.get('vulnerabilities', [])
    hosts = details.get('hosts', [])

    print("\n" + "=" * 70)
    print(f"SCAN: {scan_name} (ID: {scan_id})")
    print("=" * 70)

    info = details['info']
    print(f"\nStatus: {info.get('status')}")
    print(f"Targets: {info.get('targets')}")
    print(f"Policy: {info.get('policy')}")

    severity_counts = {0: 0, 1: 0, 2: 0, 3: 0, 4: 0}
    for vuln in vulnerabilities:
        sev = vuln.get('severity', 0)
        severity_counts[sev] = severity_counts.get(sev, 0) + vuln.get('count', 1)

    severity_names = {0: 'Info', 1: 'Low', 2: 'Medium', 3: 'High', 4: 'Critical'}

    print(f"\nVulnerabilities:")
    print(f"  Total Unique: {len(vulnerabilities)}")
    for sev in [4, 3, 2, 1, 0]:
        print(f"  {severity_names[sev]:8s}: {severity_counts[sev]:5d}")

    print(f"\nHosts: {len(hosts)}")
    print("=" * 70 + "\n")


def main():
    if len(sys.argv) < 2:
        print("=" * 70)
        print("NESSUS DETAILED VULNERABILITY EXPORTER")
        print("=" * 70)
        print("\nExports complete vulnerability details including:")
        print("  - Full plugin descriptions")
        print("  - CVE information")
        print("  - CVSS scores and vectors")
        print("  - Exploit availability")
        print("  - Solution/remediation info")
        print("  - Plugin output per host")
        print("\nUsage: python export_vulnerabilities_detailed.py <scan_id_or_name>")
        print("\nExamples:")
        print("  python export_vulnerabilities_detailed.py 24")
        print("  python export_vulnerabilities_detailed.py '172.32.0.215'")
        print("\n" + "=" * 70)

        print("\nAvailable scans:")
        scans_data = nessus.scans.list()
        for s in scans_data.get('scans', []):
            status_icon = {'completed': '[OK]', 'running': '[>>]', 'canceled': '[XX]'}.get(s['status'], '[ ]')
            print(f"  {status_icon} ID: {s['id']:3d} - {s['name']:40s} [{s['status']}]")

        sys.exit(1)

    search_term = sys.argv[1]

    print("=" * 70)
    print("NESSUS DETAILED VULNERABILITY EXPORTER")
    print("=" * 70)
    print(f"\n[*] Searching for scan: '{search_term}'...")

    scan = find_scan_by_name_or_id(search_term)

    if not scan:
        print(f"[!] Scan '{search_term}' not found")
        sys.exit(1)

    scan_id = scan['id']
    scan_name = scan['name']

    print(f"[+] Found scan: {scan_name} (ID: {scan_id})")

    # Display summary
    display_summary(scan_id, scan_name)

    # Export detailed data
    exported_file = export_detailed_json(scan_id, scan_name)

    print("\n" + "=" * 70)
    print("[+] EXPORT COMPLETE")
    print("=" * 70)
    print(f"\nExported file: {exported_file}")
    print("\nThis file contains:")
    print("  - Complete plugin descriptions")
    print("  - CVE references")
    print("  - CVSS v2 and v3 scores")
    print("  - Exploit information")
    print("  - Remediation steps")
    print("  - Per-host plugin output")
    print()


if __name__ == '__main__':
    main()
