#!/usr/bin/env python3
"""
Markdown Documentation Analyzer

Analyzes documentation structure to find:
- Orphaned documents (no incoming links)
- Broken internal links
- Document relationship graph
- Oversized documents
- Scattered related content
"""

import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple
from collections import defaultdict


class DocumentationAnalyzer:
    def __init__(self, root_dir: Path):
        self.root_dir = root_dir
        self.all_files: Set[Path] = set()
        self.links: Dict[Path, List[Tuple[str, Path]]] = defaultdict(list)  # source -> [(text, target)]
        self.incoming_links: Dict[Path, List[Path]] = defaultdict(list)  # target -> [sources]
        self.broken_links: Dict[Path, List[str]] = defaultdict(list)  # source -> [broken_link]

    def discover_files(self, exclude_patterns: List[str] = None):
        """Discover all markdown files."""
        if exclude_patterns is None:
            exclude_patterns = ['node_modules', '.git', 'vendor', 'venv', '__pycache__', '.claude/skills']

        for md_file in self.root_dir.rglob('*.md'):
            if any(pattern in str(md_file) for pattern in exclude_patterns):
                continue
            self.all_files.add(md_file)

    def analyze_links(self):
        """Analyze all links in all files."""
        link_pattern = r'\[([^\]]+)\]\(([^)]+)\)'

        for source_file in self.all_files:
            with open(source_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Find all markdown links
            matches = re.finditer(link_pattern, content)
            for match in matches:
                link_text = match.group(1)
                link_target = match.group(2)

                # Skip external links
                if link_target.startswith(('http://', 'https://', 'mailto:', '#')):
                    # Handle internal anchor only
                    if link_target.startswith('#'):
                        # Check if anchor exists in same file
                        anchor = link_target[1:]
                        if not self._anchor_exists(source_file, anchor):
                            self.broken_links[source_file].append(f"#{anchor} (anchor not found)")
                    continue

                # Handle internal file links (may include anchors)
                target_path, anchor = self._resolve_link(source_file, link_target)

                if target_path:
                    # Check if file exists
                    if not target_path.exists():
                        self.broken_links[source_file].append(link_target)
                    else:
                        # Record the link
                        self.links[source_file].append((link_text, target_path))
                        self.incoming_links[target_path].append(source_file)

                        # If anchor specified, check if it exists
                        if anchor and not self._anchor_exists(target_path, anchor):
                            self.broken_links[source_file].append(
                                f"{link_target} (anchor '{anchor}' not found)"
                            )

    def _resolve_link(self, source_file: Path, link_target: str) -> Tuple[Path, str]:
        """Resolve a relative link to absolute path."""
        # Split anchor if present
        if '#' in link_target:
            file_part, anchor = link_target.split('#', 1)
        else:
            file_part, anchor = link_target, None

        if not file_part:  # Just an anchor
            return None, anchor

        # Resolve relative path
        source_dir = source_file.parent
        target_path = (source_dir / file_part).resolve()

        return target_path, anchor

    def _anchor_exists(self, file_path: Path, anchor: str) -> bool:
        """Check if anchor (heading) exists in file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Find all headings
            headings = re.findall(r'^#{1,6}\s+(.+)$', content, re.MULTILINE)

            # Convert headings to anchor format
            for heading in headings:
                # GitHub-style anchor generation
                heading_anchor = heading.lower()
                heading_anchor = re.sub(r'[^\w\s-]', '', heading_anchor)
                heading_anchor = re.sub(r'[\s]+', '-', heading_anchor)

                if heading_anchor == anchor:
                    return True

            return False
        except Exception:
            return False

    def find_orphaned_documents(self) -> List[Path]:
        """Find documents with no incoming links."""
        orphaned = []

        for doc in self.all_files:
            # README files and index files are typically entry points
            if doc.name.lower() in ['readme.md', 'index.md']:
                continue

            # Check if has incoming links
            if doc not in self.incoming_links or len(self.incoming_links[doc]) == 0:
                orphaned.append(doc)

        return orphaned

    def find_oversized_documents(self, threshold: int = 1000) -> List[Tuple[Path, int]]:
        """Find documents exceeding line threshold."""
        oversized = []

        for doc in self.all_files:
            with open(doc, 'r', encoding='utf-8') as f:
                line_count = len(f.readlines())

            if line_count > threshold:
                oversized.append((doc, line_count))

        return sorted(oversized, key=lambda x: x[1], reverse=True)

    def generate_document_map(self) -> Dict:
        """Generate a map of document relationships."""
        doc_map = {}

        for doc in self.all_files:
            relative_path = doc.relative_to(self.root_dir)
            doc_map[str(relative_path)] = {
                'outgoing_links': len(self.links[doc]),
                'incoming_links': len(self.incoming_links[doc]),
                'linked_from': [str(f.relative_to(self.root_dir)) for f in self.incoming_links[doc]],
                'links_to': [str(t.relative_to(self.root_dir)) for _, t in self.links[doc]],
            }

        return doc_map

    def print_report(self):
        """Print comprehensive analysis report."""
        print("=" * 80)
        print("DOCUMENTATION STRUCTURE ANALYSIS")
        print("=" * 80)
        print(f"\nAnalyzing: {self.root_dir}")
        print(f"Total markdown files: {len(self.all_files)}\n")

        # Broken links
        if self.broken_links:
            print("=" * 80)
            print(f"BROKEN LINKS ({sum(len(v) for v in self.broken_links.values())} total)")
            print("=" * 80)
            for source, targets in self.broken_links.items():
                rel_path = source.relative_to(self.root_dir)
                print(f"\n📄 {rel_path}")
                for target in targets:
                    print(f"   ❌ {target}")
        else:
            print("✅ No broken links found!\n")

        # Orphaned documents
        orphaned = self.find_orphaned_documents()
        if orphaned:
            print("\n" + "=" * 80)
            print(f"ORPHANED DOCUMENTS ({len(orphaned)} files)")
            print("=" * 80)
            print("These documents have no incoming links:\n")
            for doc in sorted(orphaned):
                rel_path = doc.relative_to(self.root_dir)
                print(f"   🔗 {rel_path}")
            print("\n💡 Recommendation: Link these from related documents or main README")
        else:
            print("\n✅ No orphaned documents found!")

        # Oversized documents
        oversized = self.find_oversized_documents()
        if oversized:
            print("\n" + "=" * 80)
            print(f"OVERSIZED DOCUMENTS ({len(oversized)} files)")
            print("=" * 80)
            print("These documents exceed 1000 lines:\n")
            for doc, lines in oversized:
                rel_path = doc.relative_to(self.root_dir)
                print(f"   📏 {rel_path}: {lines} lines")
            print("\n💡 Recommendation: Consider splitting into multiple focused documents")
        else:
            print("\n✅ No oversized documents found!")

        # Document connectivity
        print("\n" + "=" * 80)
        print("DOCUMENT CONNECTIVITY")
        print("=" * 80)

        # Most linked documents
        most_linked = sorted(
            [(doc, len(sources)) for doc, sources in self.incoming_links.items()],
            key=lambda x: x[1],
            reverse=True
        )[:5]

        if most_linked:
            print("\nMost referenced documents:")
            for doc, count in most_linked:
                rel_path = doc.relative_to(self.root_dir)
                print(f"   📊 {rel_path}: {count} incoming links")

        # Documents with most outgoing links (potential hubs)
        most_outgoing = sorted(
            [(doc, len(targets)) for doc, targets in self.links.items()],
            key=lambda x: x[1],
            reverse=True
        )[:5]

        if most_outgoing:
            print("\nPotential navigation hubs (most outgoing links):")
            for doc, count in most_outgoing:
                rel_path = doc.relative_to(self.root_dir)
                print(f"   🗺️  {rel_path}: {count} outgoing links")

        # Summary
        print("\n" + "=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print(f"Total files: {len(self.all_files)}")
        print(f"Orphaned files: {len(orphaned)}")
        print(f"Oversized files: {len(oversized)}")
        print(f"Broken links: {sum(len(v) for v in self.broken_links.values())}")
        print(f"Total internal links: {sum(len(v) for v in self.links.values())}")

        # Health score
        total_issues = len(orphaned) + len(oversized) + sum(len(v) for v in self.broken_links.values())
        if total_issues == 0:
            print("\n✅ Documentation structure is healthy!")
        elif total_issues < 5:
            print(f"\n⚠️  Minor issues found ({total_issues}). Quick fixes recommended.")
        else:
            print(f"\n❌ {total_issues} issues found. Documentation needs attention.")


def main():
    if len(sys.argv) < 2:
        print("Usage: python analyze_docs.py <directory>")
        print("Example: python analyze_docs.py .")
        sys.exit(1)

    directory = Path(sys.argv[1]).resolve()
    if not directory.exists():
        print(f"Error: Directory '{directory}' not found")
        sys.exit(1)

    analyzer = DocumentationAnalyzer(directory)

    print("Discovering markdown files...")
    analyzer.discover_files()

    print("Analyzing links and structure...")
    analyzer.analyze_links()

    print("\n")
    analyzer.print_report()


if __name__ == '__main__':
    main()
