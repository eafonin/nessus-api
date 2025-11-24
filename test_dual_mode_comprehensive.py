#!/usr/bin/env python3
"""
Dual-Mode Nessus Scanner Comprehensive Test Suite

Tests both NORMAL and UPDATE modes for:
1. Internet access via VPN (external IP verification)
2. LAN access to target host (172.32.0.215:22)
3. Web UI access from host machine
4. MCP worker access to management endpoints

Test execution uses debug-scanner extensively for network diagnostics.
"""

import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

# =============================================================================
# Configuration
# =============================================================================

SCANNERS = {
    'Scanner 1': {
        'internal_url': 'https://172.30.0.3:8834',
        'external_url': 'https://localhost:8834',
        'container': 'nessus-pro-1',
        'ip': '172.30.0.3'
    },
    'Scanner 2': {
        'internal_url': 'https://172.30.0.4:8834',
        'external_url': 'https://localhost:8835',
        'container': 'nessus-pro-2',
        'ip': '172.30.0.4'
    }
}

TARGET_HOST = '172.32.0.215'
TARGET_SSH_PORT = 22
EXPECTED_VPN_IP = '62.84.100.88'
VPN_GATEWAY_IP = '172.30.0.2'
DEBUG_CONTAINER = 'debug-scanner'
DOCKER_NETWORK = 'nessus-shared_vpn_net'

# Test results storage
TEST_RESULTS = {
    'timestamp': datetime.now().isoformat(),
    'mode': None,
    'tests': []
}

# =============================================================================
# Helper Functions
# =============================================================================

def run_command(cmd: List[str], timeout: int = 30, capture_output: bool = True) -> Tuple[int, str, str]:
    """Run a shell command and return exit code, stdout, stderr."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=capture_output,
            text=True,
            timeout=timeout
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", f"Command timed out after {timeout}s"
    except Exception as e:
        return -1, "", str(e)


def docker_exec(container: str, command: str, timeout: int = 30) -> Tuple[int, str, str]:
    """Execute command inside Docker container."""
    cmd = ['docker', 'exec', container, 'sh', '-c', command]
    return run_command(cmd, timeout)


def record_test(test_name: str, category: str, passed: bool, details: Dict[str, Any]):
    """Record test result."""
    TEST_RESULTS['tests'].append({
        'name': test_name,
        'category': category,
        'passed': passed,
        'timestamp': datetime.now().isoformat(),
        'details': details
    })

    status_icon = "✅" if passed else "❌"
    print(f"  {status_icon} {test_name}: {'PASS' if passed else 'FAIL'}")
    if not passed and 'error' in details:
        print(f"     Error: {details['error']}")


def get_current_mode() -> str:
    """Detect current scanner mode."""
    rc, stdout, stderr = run_command([
        'bash', '-c',
        'cd /home/nessus/docker/nessus-shared && ./switch-mode.sh status | grep "Current Mode:" | awk \'{print $3}\''
    ])

    if rc == 0 and stdout.strip():
        # Remove ANSI color codes
        import re
        mode = re.sub(r'\x1b\[[0-9;]*m', '', stdout.strip())
        return mode
    return 'UNKNOWN'


# =============================================================================
# Test Category 1: Internet Access via VPN
# =============================================================================

def test_vpn_external_ip(container: str, container_name: str):
    """Test external IP matches VPN exit IP."""
    print(f"    Testing {container_name} external IP...")

    rc, stdout, stderr = docker_exec(container, 'curl -s -m 10 https://api.ipify.org', timeout=15)

    if rc == 0 and stdout.strip():
        detected_ip = stdout.strip()
        passed = (detected_ip == EXPECTED_VPN_IP)
        record_test(
            f"{container_name} - VPN External IP",
            "Internet Access",
            passed,
            {
                'expected_ip': EXPECTED_VPN_IP,
                'detected_ip': detected_ip,
                'container': container
            }
        )
    else:
        record_test(
            f"{container_name} - VPN External IP",
            "Internet Access",
            False,
            {
                'expected_ip': EXPECTED_VPN_IP,
                'error': stderr or "No response from ipify.org",
                'container': container
            }
        )


def test_dns_resolution(container: str, container_name: str):
    """Test DNS resolution via VPN gateway."""
    print(f"    Testing {container_name} DNS resolution...")

    rc, stdout, stderr = docker_exec(container, f'nslookup google.com {VPN_GATEWAY_IP}', timeout=10)

    passed = (rc == 0 and 'NXDOMAIN' not in stdout)
    record_test(
        f"{container_name} - DNS Resolution",
        "Internet Access",
        passed,
        {
            'dns_server': VPN_GATEWAY_IP,
            'resolution_output': stdout[:200] if passed else stderr[:200],
            'container': container
        }
    )


def test_routing_table(container: str, container_name: str):
    """Verify routing table configuration."""
    print(f"    Testing {container_name} routing table...")

    rc, stdout, stderr = docker_exec(container, 'ip route show', timeout=5)

    if rc == 0:
        # Check for default via VPN gateway
        has_vpn_default = f'default via {VPN_GATEWAY_IP}' in stdout

        # For Nessus containers, check LAN route; for debug-scanner, only VPN default needed
        if container == DEBUG_CONTAINER:
            # debug-scanner uses default Docker routing (no custom LAN route)
            passed = has_vpn_default
            record_test(
                f"{container_name} - Routing Table",
                "Internet Access",
                passed,
                {
                    'has_vpn_default': has_vpn_default,
                    'routing_table': stdout,
                    'container': container,
                    'note': 'debug-scanner uses default Docker routing'
                }
            )
        else:
            # Nessus scanners should have both VPN default and LAN route
            has_lan_route = '172.32.0.0/24' in stdout
            passed = has_vpn_default and has_lan_route
            record_test(
                f"{container_name} - Routing Table",
                "Internet Access",
                passed,
                {
                    'has_vpn_default': has_vpn_default,
                    'has_lan_route': has_lan_route,
                    'routing_table': stdout,
                    'container': container
                }
            )
    else:
        record_test(
            f"{container_name} - Routing Table",
            "Internet Access",
            False,
            {
                'error': stderr,
                'container': container
            }
        )


def run_internet_access_tests():
    """Run all internet access tests."""
    print("\n" + "="*80)
    print("Category 1: Internet Access via VPN")
    print("="*80)

    # Test debug-scanner (primary network test container)
    test_vpn_external_ip(DEBUG_CONTAINER, "debug-scanner")
    test_dns_resolution(DEBUG_CONTAINER, "debug-scanner")
    test_routing_table(DEBUG_CONTAINER, "debug-scanner")

    # Test Nessus scanner routing tables only (cannot install curl in vendor containers)
    for scanner_name, config in SCANNERS.items():
        test_routing_table(config['container'], scanner_name)


# =============================================================================
# Test Category 2: LAN Access to Target
# =============================================================================

def test_lan_ping(container: str, container_name: str):
    """Test ping to target host."""
    print(f"    Testing {container_name} ping to {TARGET_HOST}...")

    rc, stdout, stderr = docker_exec(container, f'ping -c 3 -W 5 {TARGET_HOST}', timeout=20)

    passed = (rc == 0 and '0% packet loss' in stdout)
    record_test(
        f"{container_name} - LAN Ping",
        "LAN Access",
        passed,
        {
            'target': TARGET_HOST,
            'ping_output': stdout if passed else stderr,
            'container': container
        }
    )


def test_lan_ssh_connectivity(container: str, container_name: str):
    """Test TCP connectivity to SSH port."""
    print(f"    Testing {container_name} SSH connectivity to {TARGET_HOST}:{TARGET_SSH_PORT}...")

    # Use nc (netcat) for port checking
    rc, stdout, stderr = docker_exec(
        container,
        f'nc -zv {TARGET_HOST} {TARGET_SSH_PORT} 2>&1',
        timeout=10
    )

    # nc returns 0 on success and output contains "open"
    passed = (rc == 0 or 'open' in stdout.lower())
    record_test(
        f"{container_name} - SSH Port Connectivity",
        "LAN Access",
        passed,
        {
            'target': f'{TARGET_HOST}:{TARGET_SSH_PORT}',
            'result': stdout.strip() if stdout else stderr.strip(),
            'container': container
        }
    )


def test_lan_route_verification(container: str, container_name: str):
    """Verify LAN traffic does NOT go through VPN."""
    print(f"    Testing {container_name} LAN routing (direct, not via VPN)...")

    # Check route to LAN target
    rc, stdout, stderr = docker_exec(container, f'ip route get {TARGET_HOST}', timeout=5)

    if rc == 0:
        # Should NOT go via VPN gateway for LAN traffic
        goes_via_bridge = '172.30.0.1' in stdout
        not_via_vpn = VPN_GATEWAY_IP not in stdout
        passed = goes_via_bridge and not_via_vpn

        record_test(
            f"{container_name} - LAN Direct Routing",
            "LAN Access",
            passed,
            {
                'target': TARGET_HOST,
                'goes_via_bridge': goes_via_bridge,
                'avoids_vpn': not_via_vpn,
                'route_output': stdout,
                'container': container
            }
        )
    else:
        record_test(
            f"{container_name} - LAN Direct Routing",
            "LAN Access",
            False,
            {
                'error': stderr,
                'container': container
            }
        )


def run_lan_access_tests():
    """Run all LAN access tests."""
    print("\n" + "="*80)
    print(f"Category 2: LAN Access to Target ({TARGET_HOST})")
    print("="*80)

    # Test using debug-scanner (primary network test container)
    test_lan_ping(DEBUG_CONTAINER, "debug-scanner")
    test_lan_ssh_connectivity(DEBUG_CONTAINER, "debug-scanner")
    test_lan_route_verification(DEBUG_CONTAINER, "debug-scanner")

    # Test Nessus scanner LAN routing only (cannot install ping in vendor containers)
    for scanner_name, config in SCANNERS.items():
        test_lan_route_verification(config['container'], scanner_name)


# =============================================================================
# Test Category 3: Web UI Access from Host
# =============================================================================

def test_webui_localhost_access(scanner_name: str, url: str, mode: str):
    """Test Web UI access from host via localhost."""
    print(f"    Testing {scanner_name} WebUI access ({url})...")

    rc, stdout, stderr = run_command(
        ['curl', '-k', '-s', '-m', '10', f'{url}/server/status'],
        timeout=15
    )

    if mode == 'NORMAL':
        # In NORMAL mode, localhost access is EXPECTED TO FAIL due to VPN routing
        if rc == 0 and stdout:
            try:
                data = json.loads(stdout)
                passed = 'status' in data
                record_test(
                    f"{scanner_name} - WebUI Localhost Access (NORMAL mode)",
                    "Web UI Access",
                    passed,
                    {
                        'url': url,
                        'mode': mode,
                        'status_response': data,
                        'note': 'UNEXPECTED SUCCESS - localhost access should fail with VPN routing'
                    }
                )
            except json.JSONDecodeError:
                record_test(
                    f"{scanner_name} - WebUI Localhost Access (NORMAL mode)",
                    "Web UI Access",
                    False,
                    {
                        'url': url,
                        'mode': mode,
                        'error': 'Invalid JSON response',
                        'raw_output': stdout[:200]
                    }
                )
        else:
            # EXPECTED FAILURE - Document as known limitation
            record_test(
                f"{scanner_name} - WebUI Localhost Access (NORMAL mode)",
                "Web UI Access",
                False,
                {
                    'url': url,
                    'mode': mode,
                    'error': stderr or 'Connection timeout/failed',
                    'note': 'EXPECTED FAILURE: VPN split routing prevents Docker port forwarding',
                    'workaround': 'Use internal IPs (172.30.0.3:8834, 172.30.0.4:8834) or SSH tunnel'
                }
            )
    elif mode == 'UPDATE':
        # Should FAIL in UPDATE mode (no port forwarding)
        passed = (rc != 0 or not stdout)
        record_test(
            f"{scanner_name} - WebUI Localhost Access (UPDATE mode)",
            "Web UI Access",
            passed,
            {
                'url': url,
                'mode': mode,
                'accessible': not passed,
                'expected': 'NOT accessible (port forwarding disabled)'
            }
        )


def test_webui_internal_access(scanner_name: str, url: str):
    """Test Web UI access via internal IP from docker network."""
    print(f"    Testing {scanner_name} WebUI internal access ({url})...")

    # Access from debug-scanner container
    rc, stdout, stderr = docker_exec(
        DEBUG_CONTAINER,
        f'curl -k -s -m 10 {url}/server/status',
        timeout=15
    )

    if rc == 0 and stdout:
        try:
            data = json.loads(stdout)
            passed = 'status' in data
            record_test(
                f"{scanner_name} - WebUI Internal Access",
                "Web UI Access",
                passed,
                {
                    'url': url,
                    'status_response': data,
                    'test_from': DEBUG_CONTAINER
                }
            )
        except json.JSONDecodeError:
            record_test(
                f"{scanner_name} - WebUI Internal Access",
                "Web UI Access",
                False,
                {
                    'url': url,
                    'error': 'Invalid JSON response',
                    'raw_output': stdout[:200]
                }
            )
    else:
        record_test(
            f"{scanner_name} - WebUI Internal Access",
            "Web UI Access",
            False,
            {
                'url': url,
                'error': stderr or 'Connection failed'
            }
        )


def run_webui_access_tests(mode: str):
    """Run all Web UI access tests."""
    print("\n" + "="*80)
    print(f"Category 3: Web UI Access from Host (Mode: {mode})")
    print("="*80)

    for scanner_name, config in SCANNERS.items():
        # Test localhost access (mode-dependent)
        test_webui_localhost_access(scanner_name, config['external_url'], mode)

        # Test internal access (should work in both modes)
        test_webui_internal_access(scanner_name, config['internal_url'])


# =============================================================================
# Test Category 4: MCP Worker Access
# =============================================================================

def test_mcp_server_status(scanner_name: str, url: str):
    """Test /server/status endpoint (read-only)."""
    print(f"    Testing {scanner_name} MCP /server/status...")

    rc, stdout, stderr = docker_exec(
        DEBUG_CONTAINER,
        f'curl -k -s -m 10 {url}/server/status',
        timeout=15
    )

    if rc == 0 and stdout:
        try:
            data = json.loads(stdout)
            passed = 'status' in data
            record_test(
                f"{scanner_name} - MCP /server/status",
                "MCP Worker Access",
                passed,
                {
                    'url': url,
                    'endpoint': '/server/status',
                    'response': data
                }
            )
        except json.JSONDecodeError:
            record_test(
                f"{scanner_name} - MCP /server/status",
                "MCP Worker Access",
                False,
                {
                    'url': url,
                    'error': 'Invalid JSON response'
                }
            )
    else:
        record_test(
            f"{scanner_name} - MCP /server/status",
            "MCP Worker Access",
            False,
            {
                'url': url,
                'error': stderr or 'Connection failed'
            }
        )


def test_mcp_server_properties(scanner_name: str, url: str):
    """Test /server/properties endpoint (read-only, may require auth)."""
    print(f"    Testing {scanner_name} MCP /server/properties...")

    rc, stdout, stderr = docker_exec(
        DEBUG_CONTAINER,
        f'curl -k -s -m 10 {url}/server/properties',
        timeout=15
    )

    if rc == 0 and stdout:
        try:
            data = json.loads(stdout)
            # May return authentication error, but connection should succeed
            passed = isinstance(data, dict)
            record_test(
                f"{scanner_name} - MCP /server/properties",
                "MCP Worker Access",
                passed,
                {
                    'url': url,
                    'endpoint': '/server/properties',
                    'response': data
                }
            )
        except json.JSONDecodeError:
            record_test(
                f"{scanner_name} - MCP /server/properties",
                "MCP Worker Access",
                False,
                {
                    'url': url,
                    'error': 'Invalid JSON response'
                }
            )
    else:
        record_test(
            f"{scanner_name} - MCP /server/properties",
            "MCP Worker Access",
            False,
            {
                'url': url,
                'error': stderr or 'Connection failed'
            }
        )


def run_mcp_worker_tests():
    """Run all MCP worker access tests."""
    print("\n" + "="*80)
    print("Category 4: MCP Worker Access (Management Endpoints)")
    print("="*80)

    for scanner_name, config in SCANNERS.items():
        test_mcp_server_status(scanner_name, config['internal_url'])
        test_mcp_server_properties(scanner_name, config['internal_url'])


# =============================================================================
# Main Test Runner
# =============================================================================

def generate_summary():
    """Generate test summary statistics."""
    total_tests = len(TEST_RESULTS['tests'])
    passed_tests = sum(1 for t in TEST_RESULTS['tests'] if t['passed'])
    failed_tests = total_tests - passed_tests

    # Group by category
    categories = {}
    for test in TEST_RESULTS['tests']:
        cat = test['category']
        if cat not in categories:
            categories[cat] = {'passed': 0, 'failed': 0}
        if test['passed']:
            categories[cat]['passed'] += 1
        else:
            categories[cat]['failed'] += 1

    return {
        'total': total_tests,
        'passed': passed_tests,
        'failed': failed_tests,
        'pass_rate': (passed_tests / total_tests * 100) if total_tests > 0 else 0,
        'categories': categories
    }


def print_summary(summary: Dict[str, Any]):
    """Print test summary to console."""
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    print(f"Mode: {TEST_RESULTS['mode']}")
    print(f"Total Tests: {summary['total']}")
    print(f"Passed: {summary['passed']} ✅")
    print(f"Failed: {summary['failed']} ❌")
    print(f"Pass Rate: {summary['pass_rate']:.1f}%")
    print("\nBy Category:")
    for category, stats in summary['categories'].items():
        print(f"  {category}:")
        print(f"    Passed: {stats['passed']} ✅")
        print(f"    Failed: {stats['failed']} ❌")
    print("="*80)


def save_results(output_file: str, summary: Dict[str, Any]):
    """Save test results to JSON file."""
    TEST_RESULTS['summary'] = summary

    with open(output_file, 'w') as f:
        json.dump(TEST_RESULTS, f, indent=2)

    print(f"\nDetailed results saved to: {output_file}")


def main():
    """Main test execution."""
    import argparse

    parser = argparse.ArgumentParser(description='Comprehensive dual-mode scanner tests')
    parser.add_argument('--mode', choices=['auto', 'normal', 'update'], default='auto',
                       help='Test mode (auto-detect by default)')
    parser.add_argument('--output', default='/home/nessus/projects/nessus-api/test_results_{mode}_{timestamp}.json',
                       help='Output JSON file path')
    parser.add_argument('--category', choices=['internet', 'lan', 'webui', 'mcp', 'all'], default='all',
                       help='Test category to run')
    args = parser.parse_args()

    # Detect or use specified mode
    if args.mode == 'auto':
        mode = get_current_mode()
        print(f"Auto-detected mode: {mode}")
    else:
        mode = args.mode.upper()

    TEST_RESULTS['mode'] = mode

    print("\n" + "="*80)
    print(f"DUAL-MODE NESSUS SCANNER TEST SUITE - Mode: {mode}")
    print("="*80)
    print(f"Timestamp: {TEST_RESULTS['timestamp']}")
    print(f"Target Host: {TARGET_HOST}:{TARGET_SSH_PORT}")
    print(f"Expected VPN IP: {EXPECTED_VPN_IP}")
    print("="*80)

    # Run test categories
    if args.category in ['internet', 'all']:
        run_internet_access_tests()

    if args.category in ['lan', 'all']:
        run_lan_access_tests()

    if args.category in ['webui', 'all']:
        run_webui_access_tests(mode)

    if args.category in ['mcp', 'all']:
        run_mcp_worker_tests()

    # Generate summary
    summary = generate_summary()
    print_summary(summary)

    # Save results
    output_file = args.output.format(
        mode=mode.lower(),
        timestamp=datetime.now().strftime('%Y%m%d_%H%M%S')
    )
    save_results(output_file, summary)

    # Exit with appropriate code
    sys.exit(0 if summary['failed'] == 0 else 1)


if __name__ == '__main__':
    main()
