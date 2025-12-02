"""Unit tests for IP address and CIDR matching utilities."""

import ipaddress

from core.ip_utils import _ip_or_network_match, parse_target, targets_match


class TestParseTarget:
    """Tests for parse_target function."""

    def test_parse_ipv4_address(self):
        """Test parsing a simple IPv4 address."""
        result = parse_target("192.168.1.1")
        assert result == ipaddress.ip_address("192.168.1.1")
        assert isinstance(result, ipaddress.IPv4Address)

    def test_parse_ipv4_cidr(self):
        """Test parsing IPv4 CIDR notation."""
        result = parse_target("10.0.0.0/8")
        assert result == ipaddress.ip_network("10.0.0.0/8")
        assert isinstance(result, ipaddress.IPv4Network)

    def test_parse_ipv4_cidr_non_strict(self):
        """Test parsing CIDR with host bits set (non-strict mode)."""
        # "192.168.1.5/24" should be normalized to "192.168.1.0/24"
        result = parse_target("192.168.1.5/24")
        assert result == ipaddress.ip_network("192.168.1.0/24")

    def test_parse_ipv6_address(self):
        """Test parsing IPv6 address."""
        result = parse_target("::1")
        assert result == ipaddress.ip_address("::1")
        assert isinstance(result, ipaddress.IPv6Address)

    def test_parse_ipv6_cidr(self):
        """Test parsing IPv6 CIDR."""
        result = parse_target("2001:db8::/32")
        assert result == ipaddress.ip_network("2001:db8::/32")
        assert isinstance(result, ipaddress.IPv6Network)

    def test_parse_hostname_returns_none(self):
        """Test that hostnames return None (can't do CIDR matching)."""
        assert parse_target("scan-target.local") is None
        assert parse_target("example.com") is None
        assert parse_target("my-server-01") is None

    def test_parse_invalid_returns_none(self):
        """Test that invalid input returns None."""
        assert parse_target("not-an-ip") is None
        assert parse_target("999.999.999.999") is None
        assert parse_target("192.168.1.1/99") is None  # Invalid prefix length

    def test_parse_empty_returns_none(self):
        """Test that empty string returns None."""
        assert parse_target("") is None
        assert parse_target("   ") is None

    def test_parse_whitespace_trimmed(self):
        """Test that whitespace is trimmed."""
        result = parse_target("  192.168.1.1  ")
        assert result == ipaddress.ip_address("192.168.1.1")


class TestIPOrNetworkMatch:
    """Tests for _ip_or_network_match helper function."""

    def test_ip_equals_ip(self):
        """Test exact IP match."""
        ip1 = ipaddress.ip_address("192.168.1.1")
        ip2 = ipaddress.ip_address("192.168.1.1")
        assert _ip_or_network_match(ip1, ip2) is True

    def test_ip_not_equals_ip(self):
        """Test non-matching IPs."""
        ip1 = ipaddress.ip_address("192.168.1.1")
        ip2 = ipaddress.ip_address("192.168.1.2")
        assert _ip_or_network_match(ip1, ip2) is False

    def test_ip_in_network(self):
        """Test IP within network."""
        ip = ipaddress.ip_address("10.0.0.5")
        network = ipaddress.ip_network("10.0.0.0/24")
        assert _ip_or_network_match(ip, network) is True

    def test_ip_not_in_network(self):
        """Test IP not within network."""
        ip = ipaddress.ip_address("192.168.1.1")
        network = ipaddress.ip_network("10.0.0.0/24")
        assert _ip_or_network_match(ip, network) is False

    def test_network_contains_ip(self):
        """Test network contains IP (reversed order)."""
        network = ipaddress.ip_network("10.0.0.0/24")
        ip = ipaddress.ip_address("10.0.0.5")
        assert _ip_or_network_match(network, ip) is True

    def test_networks_overlap(self):
        """Test overlapping networks."""
        net1 = ipaddress.ip_network("10.0.0.0/24")
        net2 = ipaddress.ip_network("10.0.0.0/16")
        assert _ip_or_network_match(net1, net2) is True

    def test_networks_no_overlap(self):
        """Test non-overlapping networks."""
        net1 = ipaddress.ip_network("10.0.0.0/24")
        net2 = ipaddress.ip_network("192.168.0.0/24")
        assert _ip_or_network_match(net1, net2) is False


class TestTargetsMatch:
    """Tests for targets_match function - main entry point."""

    # =========================================================================
    # Basic IP vs IP cases
    # =========================================================================
    def test_ip_exact_match(self):
        """Test exact IP match."""
        assert targets_match("192.168.1.1", "192.168.1.1") is True

    def test_ip_no_match(self):
        """Test non-matching IPs."""
        assert targets_match("192.168.1.1", "192.168.1.2") is False

    # =========================================================================
    # IP vs CIDR cases (search hit scenarios)
    # =========================================================================
    def test_ip_in_cidr_hit(self):
        """SEARCH HIT: Query IP is within stored subnet."""
        assert targets_match("10.0.0.5", "10.0.0.0/24") is True

    def test_ip_in_large_cidr_hit(self):
        """SEARCH HIT: Query IP in large /8 network."""
        assert targets_match("10.50.100.200", "10.0.0.0/8") is True

    def test_ip_at_network_boundary_hit(self):
        """SEARCH HIT: Query IP at network address."""
        assert targets_match("192.168.1.0", "192.168.1.0/24") is True

    def test_ip_at_broadcast_boundary_hit(self):
        """SEARCH HIT: Query IP at broadcast address."""
        assert targets_match("192.168.1.255", "192.168.1.0/24") is True

    # =========================================================================
    # IP vs CIDR cases (search miss scenarios)
    # =========================================================================
    def test_ip_not_in_cidr_miss(self):
        """SEARCH MISS: Query IP is outside stored subnet."""
        assert targets_match("192.168.1.1", "10.0.0.0/24") is False

    def test_ip_adjacent_cidr_miss(self):
        """SEARCH MISS: Query IP is just outside CIDR boundary."""
        assert targets_match("10.0.1.0", "10.0.0.0/24") is False  # First IP of next /24

    def test_ip_different_network_miss(self):
        """SEARCH MISS: Query IP is in completely different network."""
        assert targets_match("172.16.0.1", "192.168.0.0/16") is False

    # =========================================================================
    # CIDR vs IP cases (search hit scenarios)
    # =========================================================================
    def test_cidr_contains_ip_hit(self):
        """SEARCH HIT: Query subnet contains stored IP."""
        assert targets_match("10.0.0.0/24", "10.0.0.5") is True

    def test_large_cidr_contains_ip_hit(self):
        """SEARCH HIT: Query /8 network contains stored IP."""
        assert targets_match("10.0.0.0/8", "10.100.200.50") is True

    # =========================================================================
    # CIDR vs IP cases (search miss scenarios)
    # =========================================================================
    def test_cidr_not_contains_ip_miss(self):
        """SEARCH MISS: Query subnet doesn't contain stored IP."""
        assert targets_match("10.0.0.0/24", "192.168.1.1") is False

    # =========================================================================
    # CIDR vs CIDR cases (search hit scenarios)
    # =========================================================================
    def test_cidr_overlap_subset_hit(self):
        """SEARCH HIT: Query subnet is subset of stored subnet."""
        assert targets_match("10.0.0.0/24", "10.0.0.0/16") is True

    def test_cidr_overlap_superset_hit(self):
        """SEARCH HIT: Query subnet is superset of stored subnet."""
        assert targets_match("10.0.0.0/16", "10.0.0.0/24") is True

    def test_cidr_exact_match_hit(self):
        """SEARCH HIT: Exact CIDR match."""
        assert targets_match("192.168.1.0/24", "192.168.1.0/24") is True

    def test_cidr_partial_overlap_hit(self):
        """SEARCH HIT: Partially overlapping CIDRs."""
        # Both share 10.0.0.0/25
        assert targets_match("10.0.0.0/24", "10.0.0.0/25") is True

    # =========================================================================
    # CIDR vs CIDR cases (search miss scenarios)
    # =========================================================================
    def test_cidr_no_overlap_miss(self):
        """SEARCH MISS: Non-overlapping CIDRs."""
        assert targets_match("10.0.0.0/24", "192.168.0.0/24") is False

    def test_cidr_adjacent_no_overlap_miss(self):
        """SEARCH MISS: Adjacent but non-overlapping CIDRs."""
        assert targets_match("10.0.0.0/24", "10.0.1.0/24") is False

    # =========================================================================
    # Multiple targets (comma-separated) - search hit scenarios
    # =========================================================================
    def test_multiple_targets_match_first_hit(self):
        """SEARCH HIT: Query matches first of multiple targets."""
        assert targets_match("192.168.1.1", "192.168.1.1,10.0.0.0/8") is True

    def test_multiple_targets_match_second_hit(self):
        """SEARCH HIT: Query matches second of multiple targets."""
        assert targets_match("10.0.0.5", "192.168.1.1,10.0.0.0/8") is True

    def test_multiple_targets_match_cidr_in_list_hit(self):
        """SEARCH HIT: Query IP matches CIDR in target list."""
        assert (
            targets_match("172.16.0.50", "192.168.1.1,172.16.0.0/16,10.0.0.1") is True
        )

    def test_multiple_targets_cidr_query_hit(self):
        """SEARCH HIT: Query CIDR contains one of the stored IPs."""
        assert targets_match("10.0.0.0/24", "192.168.1.1,10.0.0.50,172.16.0.1") is True

    # =========================================================================
    # Multiple targets (comma-separated) - search miss scenarios
    # =========================================================================
    def test_multiple_targets_no_match_miss(self):
        """SEARCH MISS: Query doesn't match any of multiple targets."""
        assert targets_match("8.8.8.8", "192.168.1.1,10.0.0.0/24,172.16.0.1") is False

    def test_multiple_targets_cidr_no_overlap_miss(self):
        """SEARCH MISS: Query CIDR doesn't overlap any stored targets."""
        assert targets_match("8.8.8.0/24", "192.168.1.1,10.0.0.0/24") is False

    # =========================================================================
    # Hostname cases
    # =========================================================================
    def test_hostname_exact_match_hit(self):
        """SEARCH HIT: Hostname exact match (case-insensitive)."""
        assert targets_match("scan-target", "scan-target") is True

    def test_hostname_case_insensitive_hit(self):
        """SEARCH HIT: Hostname match is case-insensitive."""
        assert targets_match("SCAN-TARGET", "scan-target") is True
        assert targets_match("scan-target", "SCAN-TARGET") is True

    def test_hostname_in_list_hit(self):
        """SEARCH HIT: Hostname matches one in target list."""
        assert targets_match("server1", "192.168.1.1,server1,10.0.0.1") is True

    def test_hostname_no_match_miss(self):
        """SEARCH MISS: Hostname doesn't match."""
        assert targets_match("server1", "server2") is False

    def test_hostname_vs_ip_miss(self):
        """SEARCH MISS: Hostname query can't match IP targets."""
        assert targets_match("scan-target", "192.168.1.1") is False

    def test_ip_vs_hostname_miss(self):
        """SEARCH MISS: IP query can't match hostname targets."""
        assert targets_match("192.168.1.1", "scan-target") is False

    # =========================================================================
    # Edge cases
    # =========================================================================
    def test_empty_query_miss(self):
        """SEARCH MISS: Empty query never matches."""
        assert targets_match("", "192.168.1.1") is False

    def test_empty_stored_targets_miss(self):
        """SEARCH MISS: Empty stored targets never match."""
        assert targets_match("192.168.1.1", "") is False

    def test_both_empty_miss(self):
        """SEARCH MISS: Both empty never matches."""
        assert targets_match("", "") is False

    def test_whitespace_handling(self):
        """Test whitespace in comma-separated targets is handled."""
        assert (
            targets_match("10.0.0.5", "192.168.1.1, 10.0.0.0/24 , 172.16.0.1") is True
        )

    def test_empty_entries_in_list(self):
        """Test empty entries in comma-separated list are skipped."""
        assert targets_match("10.0.0.5", "192.168.1.1,,10.0.0.0/24,") is True


class TestRealWorldScenarios:
    """Real-world scenarios based on the use case discussion."""

    def test_scenario_scan_target_172_30_0_9(self):
        """
        Real scenario: Searching for historical scans of 172.30.0.9.
        This IP was used in authenticated scans in the discussion.
        """
        # Scan had target "172.30.0.9"
        assert targets_match("172.30.0.9", "172.30.0.9") is True

        # Search by subnet that contains it
        assert targets_match("172.30.0.0/24", "172.30.0.9") is True

        # Search for different IP in same subnet - no match (different IP)
        assert targets_match("172.30.0.10", "172.30.0.9") is False

    def test_scenario_large_network_scan(self):
        """
        Scenario: Network scan of 10.0.0.0/8, searching for specific hosts.
        As discussed: scan found 10.0.0.1, 10.0.0.2 but targets was 10.0.0.0/8.
        """
        stored_target = "10.0.0.0/8"

        # Searching for hosts that were scanned
        assert targets_match("10.0.0.1", stored_target) is True
        assert targets_match("10.0.0.2", stored_target) is True

        # Searching for hosts that weren't found but were in target range
        assert targets_match("10.0.0.3", stored_target) is True  # Within /8

        # Searching for hosts outside target range
        assert targets_match("192.168.1.1", stored_target) is False

    def test_scenario_multiple_network_scan(self):
        """
        Scenario: Scan targeting multiple networks/hosts.
        """
        stored_targets = "192.168.1.0/24,10.0.0.0/16,172.16.5.100"

        # Matches in first network
        assert targets_match("192.168.1.50", stored_targets) is True

        # Matches in second network
        assert targets_match("10.0.100.200", stored_targets) is True

        # Matches exact IP
        assert targets_match("172.16.5.100", stored_targets) is True

        # No match
        assert targets_match("8.8.8.8", stored_targets) is False

    def test_scenario_subnet_search_for_specific_scans(self):
        """
        Scenario: "Show me all scans that included 10.0.x.x networks"
        """
        # Various historical scan targets
        assert targets_match("10.0.0.0/16", "10.0.0.0/24") is True
        assert targets_match("10.0.0.0/16", "10.0.5.100") is True
        assert targets_match("10.0.0.0/16", "10.0.0.0/8") is True  # Overlapping
        assert targets_match("10.0.0.0/16", "192.168.1.0/24") is False
