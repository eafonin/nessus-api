"""IP address and CIDR matching utilities for target filtering."""

import ipaddress
from typing import Union

# Type alias for IP address or network objects
IPorNetwork = Union[
    ipaddress.IPv4Address,
    ipaddress.IPv6Address,
    ipaddress.IPv4Network,
    ipaddress.IPv6Network,
]


def parse_target(target_str: str) -> IPorNetwork | None:
    """
    Parse an IP address or CIDR string into an ipaddress object.

    Args:
        target_str: IP address (e.g., "192.168.1.1") or CIDR (e.g., "192.168.1.0/24")

    Returns:
        IPv4Address/IPv6Address for IPs, IPv4Network/IPv6Network for CIDRs,
        None for hostnames or invalid input.
    """
    target_str = target_str.strip()
    if not target_str:
        return None

    try:
        if "/" in target_str:
            # CIDR notation - use strict=False to allow host bits
            # e.g., "192.168.1.5/24" -> "192.168.1.0/24"
            return ipaddress.ip_network(target_str, strict=False)
        else:
            return ipaddress.ip_address(target_str)
    except ValueError:
        # Not a valid IP or CIDR (probably a hostname)
        return None


def _ip_or_network_match(a: IPorNetwork, b: IPorNetwork) -> bool:
    """
    Check if two IP/Network objects match or overlap.

    Handles four cases:
    - IP == IP: exact match
    - IP in Network: containment check
    - Network contains IP: containment check
    - Network overlaps Network: overlap check

    Args:
        a: First IP address or network
        b: Second IP address or network

    Returns:
        True if they match/overlap, False otherwise.
    """
    a_is_net = isinstance(a, (ipaddress.IPv4Network, ipaddress.IPv6Network))
    b_is_net = isinstance(b, (ipaddress.IPv4Network, ipaddress.IPv6Network))

    if not a_is_net and not b_is_net:
        # Both are IP addresses - exact match
        return a == b
    elif not a_is_net and b_is_net:
        # a is IP, b is Network - check if IP is in network
        return a in b
    elif a_is_net and not b_is_net:
        # a is Network, b is IP - check if IP is in network
        return b in a
    else:
        # Both are networks - check overlap
        return a.overlaps(b)


def targets_match(query: str, stored_targets: str) -> bool:
    """
    Check if query matches any of the stored targets (CIDR-aware).

    This function handles:
    - IP vs IP: exact match
    - IP vs CIDR: IP within network
    - CIDR vs IP: network contains IP
    - CIDR vs CIDR: networks overlap
    - Hostname vs hostname: case-insensitive string match

    Args:
        query: Search query - single IP (e.g., "10.0.0.5") or CIDR (e.g., "10.0.0.0/24")
        stored_targets: Comma-separated targets from scan payload
                       (e.g., "192.168.1.1,10.0.0.0/8,hostname.local")

    Returns:
        True if query matches ANY of the stored targets, False otherwise.

    Examples:
        >>> targets_match("10.0.0.5", "10.0.0.0/24")
        True  # IP within network

        >>> targets_match("10.0.0.0/24", "10.0.0.5")
        True  # Network contains IP

        >>> targets_match("10.0.0.0/24", "10.0.0.0/16")
        True  # Networks overlap

        >>> targets_match("192.168.1.1", "10.0.0.0/8")
        False  # No overlap

        >>> targets_match("scan-target", "scan-target,192.168.1.1")
        True  # Hostname exact match (case-insensitive)
    """
    if not query or not stored_targets:
        return False

    query = query.strip()
    query_parsed = parse_target(query)

    # Iterate through comma-separated targets
    for target in stored_targets.split(","):
        target = target.strip()
        if not target:
            continue

        target_parsed = parse_target(target)

        # Case 1: Both are unparseable (hostnames) - string match
        if query_parsed is None and target_parsed is None:
            if query.lower() == target.lower():
                return True
            continue

        # Case 2: Query is hostname, target is IP/CIDR - no match possible
        if query_parsed is None:
            continue

        # Case 3: Query is IP/CIDR, target is hostname - no match possible
        if target_parsed is None:
            continue

        # Case 4: Both are parsed IP/CIDR - CIDR-aware matching
        if _ip_or_network_match(query_parsed, target_parsed):
            return True

    return False
