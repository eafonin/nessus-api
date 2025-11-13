"""Convert Nessus data to JSON-NL format."""

import json
from typing import List, Dict, Any, Optional

from .parser import parse_nessus_file
from .profiles import get_schema_fields
from .filters import apply_filters


class NessusToJsonNL:
    """Convert Nessus XML to JSON-NL with schemas and filtering."""

    def convert(
        self,
        nessus_data: bytes,
        schema_profile: str = "brief",
        custom_fields: Optional[List[str]] = None,
        filters: Optional[Dict[str, Any]] = None,
        page: int = 1,
        page_size: int = 40
    ) -> str:
        """
        Convert to JSON-NL format.

        Returns multi-line string (JSON-NL).
        """
        # Parse Nessus data
        parsed = parse_nessus_file(nessus_data)
        all_vulns = parsed["vulnerabilities"]
        scan_meta = parsed["scan_metadata"]

        # Determine fields
        if custom_fields:
            fields = custom_fields
            profile = "custom"
        else:
            try:
                fields = get_schema_fields(schema_profile, custom_fields)
                profile = schema_profile
            except ValueError as e:
                raise ValueError(str(e))

        # Apply field projection
        if fields is not None:  # None means "full" schema (all fields)
            all_vulns = [
                self._project_fields(vuln, fields)
                for vuln in all_vulns
            ]

        # Apply filters
        if filters:
            all_vulns = apply_filters(all_vulns, filters)

        # Pagination
        total_vulns = len(all_vulns)
        if page == 0:
            # Return all
            page_vulns = all_vulns
            total_pages = 1
        else:
            # Clamp page_size
            page_size = max(10, min(100, page_size))
            total_pages = (total_vulns + page_size - 1) // page_size if total_vulns > 0 else 1
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            page_vulns = all_vulns[start_idx:end_idx]

        # Build JSON-NL output
        lines = []

        # Line 1: Schema with filters_applied
        lines.append(json.dumps({
            "type": "schema",
            "profile": profile,
            "fields": fields if fields is not None else "all",
            "filters_applied": filters or {},
            "total_vulnerabilities": total_vulns,
            "total_pages": total_pages
        }))

        # Line 2: Scan metadata
        lines.append(json.dumps({
            "type": "scan_metadata",
            **scan_meta
        }))

        # Lines 3+: Vulnerabilities
        for vuln in page_vulns:
            lines.append(json.dumps(vuln))

        # Last line: Pagination (only if not page=0)
        if page != 0:
            lines.append(json.dumps({
                "type": "pagination",
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "next_page": page + 1 if page < total_pages else None
            }))

        return "\n".join(lines)

    def _project_fields(self, vulnerability: Dict, fields: List[str]) -> Dict:
        """Project vulnerability to include only specified fields."""
        # Always include "type" field
        projected = {"type": vulnerability.get("type", "vulnerability")}

        for field in fields:
            if field in vulnerability:
                projected[field] = vulnerability[field]

        return projected
