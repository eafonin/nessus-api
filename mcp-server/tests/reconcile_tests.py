#!/usr/bin/env python3
"""
Test Documentation Reconciliation Script

Compares actual tests in source files against TEST_REPORT.md documentation.
Identifies missing, undocumented, and count mismatches.

Usage:
    python3 reconcile_tests.py           # Full detailed report
    python3 reconcile_tests.py --summary # Summary statistics only
    python3 reconcile_tests.py --fix     # Output corrected header counts
    python3 reconcile_tests.py --stubs   # Generate stub entries for missing tests

Exit codes:
    0 - All tests documented correctly
    1 - Issues found (missing tests or count mismatches)
"""

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

TESTS_DIR = Path(__file__).parent
REPORT_FILE = TESTS_DIR / "TEST_REPORT.md"

# Layer directories
LAYERS = {
    "01": TESTS_DIR / "layer01_infrastructure",
    "02": TESTS_DIR / "layer02_internal",
    "03": TESTS_DIR / "layer03_external_basic",
    "04": TESTS_DIR / "layer04_full_workflow",
}


@dataclass
class TestFile:
    """Represents a test file with counts from source and docs."""

    name: str
    layer: str
    source_tests: list = field(default_factory=list)
    doc_tests: list = field(default_factory=list)
    doc_header_count: int = 0

    @property
    def source_count(self) -> int:
        return len(self.source_tests)

    @property
    def doc_count(self) -> int:
        return len(self.doc_tests)

    @property
    def missing_in_docs(self) -> list:
        """Tests in source but not documented."""
        return [t for t in self.source_tests if t not in self.doc_tests]

    @property
    def extra_in_docs(self) -> list:
        """Tests documented but not in source."""
        return [t for t in self.doc_tests if t not in self.source_tests]

    @property
    def is_ok(self) -> bool:
        return (
            self.source_count == self.doc_count == self.doc_header_count
            and not self.missing_in_docs
            and not self.extra_in_docs
        )


def extract_tests_from_source(filepath: Path) -> list[str]:
    """Extract test function names from a Python test file."""
    tests = []
    content = filepath.read_text()

    # Match test functions - both top-level and inside classes
    # Handles: def test_foo(...) and    def test_foo(...)
    for match in re.finditer(
        r"^\s*(?:async )?def (test_\w+)\s*\(", content, re.MULTILINE
    ):
        tests.append(match.group(1))

    return sorted(set(tests))


def extract_tests_from_docs(
    report_content: str, filename: str
) -> tuple[list[str], int]:
    """Extract documented tests and header count for a file from TEST_REPORT.md."""
    tests = []
    header_count = 0

    # Find header with count: ### test_foo.py (N tests)
    header_pattern = rf"^### {re.escape(filename)}\s*\((\d+) tests?\)"
    header_match = re.search(header_pattern, report_content, re.MULTILINE)
    if header_match:
        header_count = int(header_match.group(1))

    # Find section for this file and extract test names from table
    # Pattern: | `test_name` | ... |
    section_pattern = rf"^### {re.escape(filename)}.*?(?=^### |\Z)"
    section_match = re.search(section_pattern, report_content, re.MULTILINE | re.DOTALL)

    if section_match:
        section = section_match.group(0)
        # Extract test names from table rows
        for match in re.finditer(r"^\|\s*`(test_\w+)`", section, re.MULTILINE):
            tests.append(match.group(1))

    return sorted(set(tests)), header_count


def extract_layer_header_count(report_content: str, layer: str) -> int:
    """Extract test count from layer header."""
    pattern = rf"^## Layer {layer}:.*?\((\d+) tests?\)"
    match = re.search(pattern, report_content, re.MULTILINE)
    return int(match.group(1)) if match else 0


def reconcile() -> dict[str, TestFile]:
    """Run reconciliation and return results."""
    results = {}
    report_content = REPORT_FILE.read_text()

    for layer, layer_dir in LAYERS.items():
        if not layer_dir.exists():
            continue

        for test_file in sorted(layer_dir.glob("test_*.py")):
            filename = test_file.name

            tf = TestFile(name=filename, layer=layer)
            tf.source_tests = extract_tests_from_source(test_file)
            tf.doc_tests, tf.doc_header_count = extract_tests_from_docs(
                report_content, filename
            )

            results[filename] = tf

    return results


def print_summary(results: dict[str, TestFile]):
    """Print summary statistics."""
    print("=" * 70)
    print("TEST DOCUMENTATION RECONCILIATION SUMMARY")
    print("=" * 70)

    total_source = sum(tf.source_count for tf in results.values())
    total_documented = sum(tf.doc_count for tf in results.values())
    total_header = sum(tf.doc_header_count for tf in results.values())

    ok_files = [tf for tf in results.values() if tf.is_ok]
    problem_files = [tf for tf in results.values() if not tf.is_ok]

    print(f"\nFiles analyzed: {len(results)}")
    print(f"Files OK: {len(ok_files)}")
    print(f"Files with issues: {len(problem_files)}")
    print("\nTest counts:")
    print(f"  Source files:     {total_source}")
    print(f"  Documented:       {total_documented}")
    print(f"  Header claims:    {total_header}")
    print(f"  Missing in docs:  {total_source - total_documented}")

    # Per-layer summary
    print("\nPer-layer breakdown:")
    print("-" * 70)
    print(f"{'Layer':<8} {'Source':<10} {'Documented':<12} {'Header':<10} {'Status'}")
    print("-" * 70)

    report_content = REPORT_FILE.read_text()
    for layer in LAYERS:
        layer_files = [tf for tf in results.values() if tf.layer == layer]
        src = sum(tf.source_count for tf in layer_files)
        doc = sum(tf.doc_count for tf in layer_files)
        hdr = extract_layer_header_count(report_content, layer)
        status = "✓" if src == doc == hdr else "✗ MISMATCH"
        print(f"{layer:<8} {src:<10} {doc:<12} {hdr:<10} {status}")


def print_full_report(results: dict[str, TestFile]):
    """Print detailed report of all issues."""
    print_summary(results)

    problem_files = [tf for tf in results.values() if not tf.is_ok]

    if not problem_files:
        print("\n✓ All files are correctly documented!")
        return

    print("\n" + "=" * 70)
    print("DETAILED ISSUES")
    print("=" * 70)

    for tf in sorted(problem_files, key=lambda x: (x.layer, x.name)):
        print(f"\n### {tf.name} (Layer {tf.layer})")
        print(f"    Source: {tf.source_count} tests")
        print(f"    Documented: {tf.doc_count} tests")
        print(f"    Header claims: {tf.doc_header_count} tests")

        if tf.missing_in_docs:
            print(f"\n    MISSING IN DOCS ({len(tf.missing_in_docs)}):")
            for test in tf.missing_in_docs:
                print(f"      - {test}")

        if tf.extra_in_docs:
            print(f"\n    EXTRA IN DOCS (not in source) ({len(tf.extra_in_docs)}):")
            for test in tf.extra_in_docs:
                print(f"      - {test}")


def print_fix_suggestions(results: dict[str, TestFile]):
    """Print suggested fixes for headers."""
    print("=" * 70)
    print("SUGGESTED HEADER FIXES")
    print("=" * 70)

    report_content = REPORT_FILE.read_text()

    # Layer headers
    print("\nLayer headers (update in TEST_REPORT.md and README.MD):")
    print("-" * 70)
    for layer in LAYERS:
        layer_files = [tf for tf in results.values() if tf.layer == layer]
        actual = sum(tf.source_count for tf in layer_files)
        current = extract_layer_header_count(report_content, layer)
        if actual != current:
            print(f"  Layer {layer}: {current} → {actual}")

    # File headers
    print("\nFile headers to update in TEST_REPORT.md:")
    print("-" * 70)
    for tf in sorted(results.values(), key=lambda x: (x.layer, x.name)):
        if tf.source_count != tf.doc_header_count:
            print(
                f"  {tf.name}: ({tf.doc_header_count} tests) → ({tf.source_count} tests)"
            )


def print_missing_stubs(results: dict[str, TestFile]):
    """Print stub documentation for missing tests."""
    print("=" * 70)
    print("STUB DOCUMENTATION FOR MISSING TESTS")
    print("=" * 70)
    print("\nAdd these entries to TEST_REPORT.md:\n")

    for tf in sorted(results.values(), key=lambda x: (x.layer, x.name)):
        if tf.missing_in_docs:
            print(f"\n### {tf.name} - Missing tests ({len(tf.missing_in_docs)}):\n")
            for test in tf.missing_in_docs:
                print(f"| `{test}` | `TODO` | `TODO` | TODO: Add description |")


def main():
    args = sys.argv[1:]

    results = reconcile()

    if "--summary" in args:
        print_summary(results)
    elif "--fix" in args:
        print_fix_suggestions(results)
    elif "--stubs" in args:
        print_missing_stubs(results)
    else:
        print_full_report(results)

    # Exit with error if there are issues
    problem_files = [tf for tf in results.values() if not tf.is_ok]
    sys.exit(1 if problem_files else 0)


if __name__ == "__main__":
    main()
