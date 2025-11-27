"""Monitor scan progress and export results"""
import httpx
import time
import xml.etree.ElementTree as ET

# Scanner configurations
SCANNERS = [
    {
        'name': 'Scanner 1',
        'url': 'https://172.30.0.3:8834',
        'scan_id': 42,
        'token': '10122c68-27f6-419d-82b7-99fdfc82610d',
        'session': None
    },
    {
        'name': 'Scanner 2',
        'url': 'https://172.30.0.5:8834',
        'scan_id': 5,
        'token': '778F4A9C-D797-4817-B110-EC427B724486',
        'session': None
    }
]

USERNAME = 'nessus'
PASSWORD = 'nessus'

def authenticate(scanner):
    """Get session token"""
    client = httpx.Client(verify=False, timeout=10.0)
    try:
        response = client.post(
            f"{scanner['url']}/session",
            json={'username': USERNAME, 'password': PASSWORD},
            headers={'X-API-Token': scanner['token']}
        )
        if response.status_code == 200:
            scanner['session'] = response.json()['token']
            print(f"  ✓ {scanner['name']} authenticated")
            return True
        return False
    finally:
        client.close()

def get_status(scanner):
    """Get scan status"""
    client = httpx.Client(verify=False, timeout=10.0)
    try:
        response = client.get(
            f"{scanner['url']}/scans/{scanner['scan_id']}",
            headers={
                'X-Cookie': f'token={scanner["session"]}',
                'X-API-Token': scanner['token']
            }
        )
        if response.status_code == 200:
            data = response.json()
            info = data.get('info', {})
            return {
                'status': info.get('status', 'unknown'),
                'progress': info.get('scanner_progress', 0),
                'name': info.get('name', 'N/A')
            }
        return None
    finally:
        client.close()

def export_scan(scanner):
    """Export scan results"""
    client = httpx.Client(verify=False, timeout=30.0)
    try:
        # Request export
        response = client.post(
            f"{scanner['url']}/scans/{scanner['scan_id']}/export",
            json={'format': 'nessus'},
            headers={
                'X-Cookie': f'token={scanner["session"]}',
                'X-API-Token': scanner['token']
            }
        )
        if response.status_code != 200:
            return None
        
        file_id = response.json()['file']
        
        # Poll for export completion
        for _ in range(30):
            time.sleep(2)
            status_response = client.get(
                f"{scanner['url']}/scans/{scanner['scan_id']}/export/{file_id}/status",
                headers={
                    'X-Cookie': f'token={scanner["session"]}',
                    'X-API-Token': scanner['token']
                }
            )
            if status_response.json().get('status') == 'ready':
                break
        
        # Download export
        download_response = client.get(
            f"{scanner['url']}/scans/{scanner['scan_id']}/export/{file_id}/download",
            headers={
                'X-Cookie': f'token={scanner["session"]}',
                'X-API-Token': scanner['token']
            }
        )
        
        if download_response.status_code == 200:
            return download_response.content
        return None
    finally:
        client.close()

def parse_results(xml_data):
    """Parse .nessus XML and count vulnerabilities"""
    try:
        root = ET.fromstring(xml_data)
        vulns = {'critical': 0, 'high': 0, 'medium': 0, 'low': 0, 'info': 0}
        findings = []
        
        for item in root.findall('.//ReportItem'):
            severity = int(item.get('severity', 0))
            plugin_name = item.find('pluginName')
            
            if severity == 4:
                vulns['critical'] += 1
            elif severity == 3:
                vulns['high'] += 1
            elif severity == 2:
                vulns['medium'] += 1
            elif severity == 1:
                vulns['low'] += 1
            else:
                vulns['info'] += 1
            
            if plugin_name is not None and len(findings) < 10:
                findings.append(plugin_name.text)
        
        return vulns, findings
    except:
        return None, None

def main():
    print("\n" + "="*80)
    print("MONITORING SCAN PROGRESS AND EXPORTING RESULTS")
    print("="*80 + "\n")
    
    # Authenticate
    print("[STEP 1] Authenticating...")
    print("-" * 80)
    for scanner in SCANNERS:
        authenticate(scanner)
    print()
    
    # Monitor progress
    print("[STEP 2] Monitoring scan progress (checking every 15 seconds)...")
    print("-" * 80)
    
    completed = {s['name']: False for s in SCANNERS}
    last_progress = {s['name']: -1 for s in SCANNERS}
    
    max_wait = 900  # 15 minutes
    elapsed = 0
    
    while elapsed < max_wait and not all(completed.values()):
        time.sleep(15)
        elapsed += 15
        
        for scanner in SCANNERS:
            if completed[scanner['name']]:
                continue
                
            status = get_status(scanner)
            if status:
                if status['progress'] != last_progress[scanner['name']]:
                    print(f"  [{elapsed:4d}s] {scanner['name']:10s} | Status: {status['status']:10s} | Progress: {status['progress']:3d}%")
                    last_progress[scanner['name']] = status['progress']
                
                if status['status'] == 'completed':
                    completed[scanner['name']] = True
                    print(f"    ✓ {scanner['name']} completed after {elapsed}s\n")
    
    if not all(completed.values()):
        print(f"\n⚠ Not all scans completed in {max_wait}s")
        return 1
    
    print()
    
    # Export results
    print("[STEP 3] Exporting scan results...")
    print("-" * 80)
    
    results = []
    for scanner in SCANNERS:
        print(f"\n{scanner['name']}:")
        print(f"  Exporting scan {scanner['scan_id']}...")
        
        xml_data = export_scan(scanner)
        if xml_data:
            # Save to file
            filename = f"/tmp/{scanner['name'].replace(' ', '_').lower()}_scan_{scanner['scan_id']}.nessus"
            with open(filename, 'wb') as f:
                f.write(xml_data)
            
            print(f"  ✓ Exported {len(xml_data):,} bytes")
            print(f"  ✓ Saved to: {filename}")
            
            # Parse results
            vulns, findings = parse_results(xml_data)
            if vulns:
                results.append((scanner['name'], vulns, findings, filename))
        else:
            print(f"  ✗ Export failed")
    
    print()
    
    # Show results summary
    print("="*80)
    print("FINAL RESULTS SUMMARY")
    print("="*80 + "\n")
    
    for name, vulns, findings, filename in results:
        total = sum(vulns.values())
        print(f"{name}:")
        print(f"  Total Findings: {total}")
        print(f"  Critical: {vulns['critical']} | High: {vulns['high']} | Medium: {vulns['medium']} | Low: {vulns['low']} | Info: {vulns['info']}")
        print(f"  Results File: {filename}")
        
        if findings:
            print(f"\n  Sample Findings (first 10):")
            for i, finding in enumerate(findings[:10], 1):
                print(f"    {i}. {finding}")
        print()
    
    print("="*80)
    print(f"✅ SUCCESSFULLY TESTED {len(results)} SCANNERS")
    print("="*80 + "\n")
    
    return 0

if __name__ == '__main__':
    exit(main())
