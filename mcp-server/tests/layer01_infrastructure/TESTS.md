# Layer 01: Infrastructure Tests

[← Test Suite](../README.MD) | [Layer README](README.MD)

---

## Overview

Tests that verify external dependencies are accessible before running any other tests.

- **Test Count**: 25 tests
- **Duration**: <1 second
- **Marker**: `@pytest.mark.layer01`

---

## test_nessus_connectivity.py (10 tests)

| Test | Arguments | Returns | Description |
|------|-----------|---------|-------------|
| `test_dns_resolution` | `hostname` from NESSUS_URL env | `ip_address: str` | Verifies Nessus hostname resolves. Pass: non-empty IP. |
| `test_tcp_port_connectivity` | `hostname`, `port=8834` | `result: int` (0=success) | Verifies TCP port 8834 is open. Pass: returns 0. |
| `test_https_reachable` | `NESSUS_URL/server/status` | `status_code: int` | Verifies HTTPS endpoint responds. Pass: status 200. |
| `test_server_status_ready` | `NESSUS_URL/server/status` | `{"status": "ready"}` | Verifies Nessus reports ready. Pass: status == "ready". |
| `test_ssl_bypass_works` | `NESSUS_URL/server/status`, `verify=False` | `status_code: 200` | Verifies SSL bypass works. Pass: status 200. |
| `test_self_signed_cert_detected` | `NESSUS_URL/server/status`, `verify=True` | `ConnectError` or success | Verifies self-signed cert detected. Pass: raises ConnectError or succeeds. |
| `test_server_status_endpoint` | `NESSUS_URL/server/status` | `status_code: 200` | Verifies /server/status accessible. Pass: status 200. |
| `test_server_properties_endpoint` | `NESSUS_URL/server/properties` | `status_code: 200` | Verifies /server/properties accessible. Pass: status 200. |
| `test_authentication_endpoint_accessible` | `NESSUS_URL/session`, invalid creds | `status_code: 200\|401\|403` | Verifies /session responds. Pass: status in [200, 401, 403]. |
| `test_server_properties_retrievable` | `NESSUS_URL/server/properties` | `{"nessus_type": ...}` | Verifies properties contain nessus_type. Pass: key exists. |

---

## test_redis_connectivity.py (6 tests)

| Test | Arguments | Returns | Description |
|------|-----------|---------|-------------|
| `test_dns_resolution` | `REDIS_HOST` env | `ip_address: str` | Verifies Redis hostname resolves. Pass: non-empty IP. |
| `test_tcp_port_connectivity` | `REDIS_HOST`, `REDIS_PORT=6379` | `result: int` (0=success) | Verifies Redis port is open. Pass: connect_ex returns 0. |
| `test_ping` | Redis client fixture | `True` | Verifies PING works. Pass: returns True. |
| `test_set_get` | `key`, `value` | `value: str` | Verifies SET/GET work. Pass: get returns set value. |
| `test_list_operations` | `key`, items list | `length: 2`, `item` | Verifies LPUSH/LLEN/RPOP. Pass: length=2, rpop returns item. |
| `test_info_command` | Redis client | `{"redis_version": ...}` | Verifies INFO returns server info. Pass: has required keys. |

---

## test_both_scanners.py (5 tests)

> Note: `test_scanner_reachable` and `test_scanner_ready` are parameterized, running once per scanner (×2).

| Test | Arguments | Returns | Description |
|------|-----------|---------|-------------|
| `test_scanner_reachable` | `url` param from fixture (×2 scanners) | `status_code: 200` | Verifies scanner HTTPS reachable. Pass: status 200. |
| `test_scanner_ready` | Scanner `/server/status` (×2 scanners) | `{"status": "ready"}` | Verifies scanner reports ready. Pass: status == "ready". |
| `test_scanners_have_different_uuids` | Both scanners | `uuids: list[str]` | Verifies unique UUIDs. Pass: all UUIDs unique. |

---

## test_target_accounts.py (4 tests)

| Test | Arguments | Returns | Description |
|------|-----------|---------|-------------|
| `test_scan_target_ssh_port` | `SCAN_TARGET_IP`, port 22 | `bool` | Verifies scan-target SSH port open. Pass: port open. |
| `test_external_host_ssh_port` | `EXTERNAL_HOST_IP`, port 22 | `bool` | Verifies external host SSH port open. Pass: port open. |
| `test_scan_target_accepts_connections` | `SCAN_TARGET_IP:22` | `banner: str` | Verifies SSH banner received. Pass: "SSH" in banner. |
| `test_credentials_documented` | Credential structure | `credentials: dict` | Documents test credentials. Pass: has required structure. |

---

## See Also

- [Layer 02: Internal Tests](../layer02_internal/TESTS.md)
- [Testing Guide](../../docs/TESTING.md)
