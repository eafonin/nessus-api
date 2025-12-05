# Layer 01: Infrastructure Tests

[← Test Suite](../README.MD)

---

## Purpose

Verify all external services are accessible before running any other tests. These tests should pass before proceeding to higher layers.

**Duration**: <1 second
**Marker**: `@pytest.mark.layer01`

---

## Tests

| Test File | What it checks |
|-----------|----------------|
| `test_nessus_connectivity.py` | Nessus WebUI reachable, SSL works, auth endpoints respond |
| `test_redis_connectivity.py` | Redis server accessible, basic SET/GET operations |
| `test_target_accounts.py` | SSH test accounts accessible on scan targets |
| `test_both_scanners.py` | Both scanner instances (scanner1, scanner2) responding |

---

## Running

```bash
# Run all layer01 tests
pytest tests/layer01_infrastructure/ -v

# Run by marker
pytest -m layer01 -v

# Run single test
pytest tests/layer01_infrastructure/test_nessus_connectivity.py -v
```

---

## If Tests Fail

### Nessus connectivity fails

1. Check container running: `docker ps | grep nessus`
2. Check port accessible: `curl -k https://vpn-gateway:8834/server/status`
3. Verify credentials in config

### Redis connectivity fails

1. Check container: `docker ps | grep redis`
2. Test connection: `docker compose exec redis redis-cli ping`

### Target account tests fail

1. Verify scan-target container running
2. Test SSH manually: `ssh testauth_nosudo@172.30.0.9`
3. Check user passwords match expected

### Both scanners fails

1. Check both scanner containers are running
2. Verify scanner pool configuration in `config/scanners.yaml`

---

## Dependencies

- Docker containers running
- Network connectivity to Docker networks
- Nessus scanner(s) initialized and licensed

---

## See Also

- [Layer 02: Internal](../layer02_internal/README.MD)
- [Testing Guide](../../docs/TESTING.md)
