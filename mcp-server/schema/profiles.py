"""Schema profile definitions for vulnerability output formatting."""


# Four predefined schema profiles
SCHEMAS = {
    "minimal": [
        "host",
        "plugin_id",
        "severity",
        "cve",
        "cvss_score",
        "exploit_available",
    ],
    "summary": [
        # minimal fields +
        "host",
        "plugin_id",
        "severity",
        "cve",
        "cvss_score",
        "exploit_available",
        # 3 additional fields
        "plugin_name",
        "cvss3_base_score",
        "synopsis",
    ],
    "brief": [
        # summary fields +
        "host",
        "plugin_id",
        "severity",
        "cve",
        "cvss_score",
        "exploit_available",
        "plugin_name",
        "cvss3_base_score",
        "synopsis",
        # 2 more fields
        "description",
        "solution",
    ],
    "full": None,  # None means all fields (no filtering)
}


def get_schema_fields(
    profile: str, custom_fields: list[str] | None = None
) -> list[str] | None:
    """
    Get field list for given schema profile or custom fields.

    Args:
        profile: One of "minimal", "summary", "brief", "full"
        custom_fields: Custom field list (mutually exclusive with non-default profile)

    Returns:
        List of field names, or None for full schema (all fields)

    Raises:
        ValueError: If both profile (non-default) and custom_fields are provided
    """
    # Enforce mutual exclusivity (brief is default, so only check if changed)
    if profile != "brief" and custom_fields is not None:
        raise ValueError(
            f"Cannot specify both schema_profile='{profile}' and custom_fields. "
            "Use schema_profile for predefined schemas OR custom_fields for custom schema, not both."
        )

    # Custom fields take precedence if provided
    if custom_fields:
        return custom_fields

    # Validate profile name
    if profile not in SCHEMAS:
        raise ValueError(
            f"Invalid schema profile: {profile}. Must be one of: {list(SCHEMAS.keys())}"
        )

    return SCHEMAS[profile]
