"""Generic filtering engine."""

from typing import List, Dict, Any


def apply_filters(vulns: List[Dict], filters: Dict[str, Any]) -> List[Dict]:
    """
    Apply filters to vulnerability list.

    AND logic: all filters must match.
    """
    if not filters:
        return vulns

    return [v for v in vulns if matches_all_filters(v, filters)]


def matches_all_filters(vuln: Dict[str, Any], filters: Dict[str, Any]) -> bool:
    """Check if vulnerability matches all filters."""
    for field, filter_value in filters.items():
        if field not in vuln:
            return False

        vuln_value = vuln[field]

        # String filter (case-insensitive substring)
        if isinstance(vuln_value, str) and isinstance(filter_value, str):
            if filter_value.lower() not in vuln_value.lower():
                return False

        # Number filter with operators (e.g., ">7.0", ">=5", "<10")
        elif isinstance(filter_value, str) and len(filter_value) > 0 and filter_value[0] in "<>=":
            try:
                num_value = float(vuln_value)
                if not compare_number(num_value, filter_value):
                    return False
            except (ValueError, TypeError):
                return False

        # Boolean filter (exact match)
        elif isinstance(filter_value, bool):
            if bool(vuln_value) != filter_value:
                return False

        # List filter (any element contains substring)
        elif isinstance(vuln_value, list):
            filter_str = str(filter_value).lower()
            found = any(filter_str in str(item).lower() for item in vuln_value)
            if not found:
                return False

        # Exact match for other types
        else:
            if vuln_value != filter_value:
                return False

    return True


def compare_number(value: float, operator_str: str) -> bool:
    """Compare number with operator string like '>7.0'."""
    if operator_str.startswith(">="):
        return value >= float(operator_str[2:])
    elif operator_str.startswith("<="):
        return value <= float(operator_str[2:])
    elif operator_str.startswith(">"):
        return value > float(operator_str[1:])
    elif operator_str.startswith("<"):
        return value < float(operator_str[1:])
    elif operator_str.startswith("="):
        return value == float(operator_str[1:])
    return False
