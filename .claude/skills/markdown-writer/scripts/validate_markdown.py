#!/usr/bin/env python3
"""
Markdown Validation Script

Validates markdown files against LLM-optimized best practices:
- Single H1 heading
- No skipped heading levels
- Code blocks have language identifiers
- Appropriate document length
- Common pitfalls
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Dict, Tuple


class MarkdownValidator:
    def __init__(self):
        self.issues = []

    def validate_file(self, filepath: Path) -> Dict:
        """Validate a single markdown file."""
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.split('\n')

        result = {
            'file': str(filepath),
            'issues': [],
            'warnings': [],
            'info': []
        }

        # Check 1: Single H1 heading
        h1_count = len(re.findall(r'^# [^#]', content, re.MULTILINE))
        if h1_count == 0:
            result['issues'].append("Missing H1 heading (document title)")
        elif h1_count > 1:
            result['issues'].append(f"Multiple H1 headings found ({h1_count}). Only ONE allowed.")

        # Check 2: Heading hierarchy (no skips)
        headings = re.findall(r'^(#{1,6}) ', content, re.MULTILINE)
        if headings:
            heading_levels = [len(h) for h in headings]
            for i in range(len(heading_levels) - 1):
                current = heading_levels[i]
                next_level = heading_levels[i + 1]
                if next_level > current + 1:
                    result['issues'].append(
                        f"Skipped heading level: H{current} → H{next_level} (around line {i+1})"
                    )

        # Check 3: Code blocks without language identifiers
        code_blocks = re.findall(r'^```(\w*)\n', content, re.MULTILINE)
        empty_code_blocks = [i for i, lang in enumerate(code_blocks) if not lang]
        if empty_code_blocks:
            result['issues'].append(
                f"Found {len(empty_code_blocks)} code block(s) without language identifier"
            )

        # Check 4: Document length
        line_count = len(lines)
        result['info'].append(f"Document length: {line_count} lines")

        if line_count > 1000:
            result['warnings'].append(
                f"Document too long ({line_count} lines). Consider splitting (ideal: 200-1000 lines)"
            )
        elif line_count < 50 and 'README' not in filepath.name:
            result['info'].append(
                f"Document is short ({line_count} lines). This may be fine for simple docs."
            )

        # Check 5: Vague link text
        vague_patterns = [
            r'\[here\]\(',
            r'\[click here\]\(',
            r'\[this\]\(',
            r'\[this document\]\(',
            r'\[click\]\('
        ]
        for pattern in vague_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                result['issues'].append(
                    f"Vague link text found ('{pattern}'). Use descriptive text instead."
                )

        # Check 6: Code/commands without inline code formatting
        # Look for common commands not in backticks
        common_commands = ['npm', 'git', 'docker', 'python', 'pip', 'node']
        for line_num, line in enumerate(lines, 1):
            # Skip code blocks
            if line.strip().startswith('```'):
                continue
            # Skip if already in inline code
            if '`' in line:
                continue
            for cmd in common_commands:
                if re.search(rf'\b{cmd}\s+\w+', line, re.IGNORECASE):
                    result['warnings'].append(
                        f"Line {line_num}: Possible command without backticks: {line.strip()[:60]}"
                    )
                    break

        # Check 7: Missing blank lines around headings
        for i, line in enumerate(lines):
            if re.match(r'^#{1,6} ', line):
                # Check if previous line is not empty (unless it's the first line)
                if i > 0 and lines[i-1].strip() != '':
                    result['warnings'].append(
                        f"Line {i+1}: Missing blank line before heading"
                    )
                # Check if next line is not empty (unless it's the last line)
                if i < len(lines) - 1 and lines[i+1].strip() != '' and not lines[i+1].startswith('#'):
                    result['warnings'].append(
                        f"Line {i+1}: Missing blank line after heading"
                    )

        # Check 8: External links that might should be local
        external_docs = [
            'github.com.*/(README|docs|wiki)',
            'docs\\..*\\.com',
        ]
        for pattern in external_docs:
            matches = re.findall(rf'\[.*?\]\((https?://({pattern}).*?)\)', content)
            if matches:
                result['warnings'].append(
                    f"Found external documentation links. Consider copying locally: {len(matches)} link(s)"
                )

        return result

    def validate_directory(self, directory: Path, exclude_patterns: List[str] = None) -> List[Dict]:
        """Validate all markdown files in directory."""
        if exclude_patterns is None:
            exclude_patterns = ['node_modules', '.git', 'vendor', 'venv', '.claude/skills']

        results = []

        for md_file in directory.rglob('*.md'):
            # Skip excluded directories
            if any(pattern in str(md_file) for pattern in exclude_patterns):
                continue

            result = self.validate_file(md_file)
            results.append(result)

        return results

    def print_results(self, results: List[Dict]):
        """Print validation results in a readable format."""
        total_files = len(results)
        total_issues = sum(len(r['issues']) for r in results)
        total_warnings = sum(len(r['warnings']) for r in results)

        print("=" * 80)
        print(f"MARKDOWN VALIDATION REPORT")
        print("=" * 80)
        print(f"\nScanned {total_files} file(s)")
        print(f"Found {total_issues} issue(s) and {total_warnings} warning(s)\n")

        # Print files with issues
        files_with_issues = [r for r in results if r['issues']]
        if files_with_issues:
            print("\n" + "=" * 80)
            print("ISSUES (Must Fix)")
            print("=" * 80)
            for result in files_with_issues:
                print(f"\n📄 {result['file']}")
                for issue in result['issues']:
                    print(f"   ❌ {issue}")

        # Print files with warnings
        files_with_warnings = [r for r in results if r['warnings']]
        if files_with_warnings:
            print("\n" + "=" * 80)
            print("WARNINGS (Should Fix)")
            print("=" * 80)
            for result in files_with_warnings:
                print(f"\n📄 {result['file']}")
                for warning in result['warnings']:
                    print(f"   ⚠️  {warning}")

        # Print summary
        clean_files = [r for r in results if not r['issues'] and not r['warnings']]
        if clean_files:
            print("\n" + "=" * 80)
            print(f"CLEAN FILES ({len(clean_files)})")
            print("=" * 80)
            for result in clean_files:
                print(f"   ✅ {result['file']}")

        print("\n" + "=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print(f"Total files: {total_files}")
        print(f"Clean files: {len(clean_files)}")
        print(f"Files with issues: {len(files_with_issues)}")
        print(f"Files with warnings: {len(files_with_warnings)}")
        print(f"Total issues: {total_issues}")
        print(f"Total warnings: {total_warnings}")

        if total_issues == 0:
            print("\n✅ No critical issues found!")
        else:
            print(f"\n❌ {total_issues} issue(s) need attention")


def main():
    if len(sys.argv) < 2:
        print("Usage: python validate_markdown.py <directory>")
        print("Example: python validate_markdown.py .")
        sys.exit(1)

    directory = Path(sys.argv[1])
    if not directory.exists():
        print(f"Error: Directory '{directory}' not found")
        sys.exit(1)

    validator = MarkdownValidator()
    results = validator.validate_directory(directory)
    validator.print_results(results)

    # Exit with error code if issues found
    total_issues = sum(len(r['issues']) for r in results)
    sys.exit(0 if total_issues == 0 else 1)


if __name__ == '__main__':
    main()
