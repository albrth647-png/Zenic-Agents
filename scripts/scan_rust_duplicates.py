#!/usr/bin/env python3
"""
─── Zenic-Agents v3 — Rust Duplicate Type Scanner ─────────────────────
Phase 6.1: CI gate to detect cross-crate type duplication in zenic-v2/.

Scans all Rust source files in zenic-v2/ for duplicate struct/enum
definitions across different crates. Reports cross-crate duplicates
(which are the most dangerous) and intra-crate duplicates.

Exit codes:
  0 — No cross-crate duplicates found (clean)
  1 — Cross-crate duplicates found (blocks merge)
  2 — Only intra-crate duplicates (warning only)

Usage:
  python3 scripts/scan_rust_duplicates.py [--crates-dir zenic-v2/] [--ci]
"""

import os
import re
import sys
from collections import defaultdict
from pathlib import Path


def find_rust_files(crates_dir: str) -> dict[str, list[Path]]:
    """Find all .rs files organized by crate name."""
    crates = {}
    crates_path = Path(crates_dir)

    if not crates_path.exists():
        print(f"Error: {crates_dir} does not exist", file=sys.stderr)
        sys.exit(1)

    for crate_dir in crates_path.iterdir():
        if not crate_dir.is_dir():
            continue
        if crate_dir.name.startswith("_") or crate_dir.name.startswith("."):
            continue
        # Skip archived crates
        if crate_dir.name == "_archived":
            continue

        cargo_toml = crate_dir / "Cargo.toml"
        if not cargo_toml.exists():
            continue

        rs_files = list(crate_dir.rglob("*.rs"))
        if rs_files:
            crates[crate_dir.name] = rs_files

    return crates


def extract_type_definitions(rs_files: list[Path]) -> dict[str, list[str]]:
    """Extract all public struct and enum definitions from Rust files.

    Returns: {type_name: [file_paths]}
    """
    # Match pub struct Name, pub enum Name (with optional generics)
    type_pattern = re.compile(
        r"^\s*pub\s+(?:struct|enum)\s+([A-Z][a-zA-Z0-9_]*)"
    )

    definitions = defaultdict(list)

    for rs_file in rs_files:
        try:
            content = rs_file.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue

        for line in content.splitlines():
            match = type_pattern.match(line)
            if match:
                type_name = match.group(1)
                definitions[type_name].append(str(rs_file))

    return definitions


def find_duplicates(crates_dir: str = "zenic-v2/") -> tuple[dict, dict]:
    """Find cross-crate and intra-crate duplicate type definitions.

    Returns:
        cross_crate: {type_name: [(crate_name, file_path), ...]}
        intra_crate: {type_name: [(crate_name, file_path), ...]}
    """
    crates = find_rust_files(crates_dir)

    # Collect all type definitions per crate
    crate_types: dict[str, dict[str, list[str]]] = {}
    for crate_name, rs_files in crates.items():
        crate_types[crate_name] = extract_type_definitions(rs_files)

    # Find cross-crate duplicates (same type name in different crates)
    cross_crate = defaultdict(list)
    all_types: dict[str, list[tuple[str, str]]] = defaultdict(list)

    for crate_name, types in crate_types.items():
        for type_name, files in types.items():
            for file_path in files:
                all_types[type_name].append((crate_name, file_path))

    for type_name, locations in all_types.items():
        crate_names = set(loc[0] for loc in locations)
        if len(crate_names) > 1:
            cross_crate[type_name] = locations

    # Find intra-crate duplicates (same type name in multiple files within same crate)
    intra_crate = defaultdict(list)
    for crate_name, types in crate_types.items():
        for type_name, files in types.items():
            if len(files) > 1:
                for file_path in files:
                    intra_crate[type_name].append((crate_name, file_path))

    return dict(cross_crate), dict(intra_crate)


def format_report(cross_crate: dict, intra_crate: dict, ci_mode: bool = False) -> str:
    """Format the duplicate type report."""
    lines = []
    lines.append("=" * 70)
    lines.append("Rust Duplicate Type Scan Report")
    lines.append("=" * 70)

    if cross_crate:
        lines.append(f"\n🔴 CROSS-CRATE DUPLICATES: {len(cross_crate)} types")
        lines.append("-" * 50)
        for type_name, locations in sorted(cross_crate.items()):
            lines.append(f"\n  {type_name}:")
            crate_names = set()
            for crate_name, file_path in locations:
                lines.append(f"    → {crate_name}: {file_path}")
                crate_names.add(crate_name)
            lines.append(f"    ⚠ Found in {len(crate_names)} different crates")

    if intra_crate:
        lines.append(f"\n🟡 INTRA-CRATE DUPLICATES: {len(intra_crate)} types")
        lines.append("-" * 50)
        for type_name, locations in sorted(intra_crate.items()):
            lines.append(f"\n  {type_name}:")
            for crate_name, file_path in locations:
                lines.append(f"    → {crate_name}: {file_path}")

    if not cross_crate and not intra_crate:
        lines.append("\n✅ No duplicate type definitions found!")

    lines.append("")
    lines.append("=" * 70)

    if ci_mode:
        if cross_crate:
            lines.append("❌ CI GATE FAILED: Cross-crate duplicates block merge")
        else:
            lines.append("✅ CI GATE PASSED: No cross-crate duplicates")

    return "\n".join(lines)


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Scan Rust crates for duplicate type definitions"
    )
    parser.add_argument(
        "--crates-dir",
        default="zenic-v2/",
        help="Path to the Rust crates directory (default: zenic-v2/)",
    )
    parser.add_argument(
        "--ci",
        action="store_true",
        help="CI mode: exit 1 on cross-crate duplicates",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON",
    )

    args = parser.parse_args()

    cross_crate, intra_crate = find_duplicates(args.crates_dir)

    if args.json:
        import json

        result = {
            "cross_crate_duplicates": {
                k: [{"crate": c, "file": f} for c, f in v]
                for k, v in cross_crate.items()
            },
            "intra_crate_duplicates": {
                k: [{"crate": c, "file": f} for c, f in v]
                for k, v in intra_crate.items()
            },
            "cross_crate_count": len(cross_crate),
            "intra_crate_count": len(intra_crate),
        }
        print(json.dumps(result, indent=2))
    else:
        report = format_report(cross_crate, intra_crate, ci_mode=args.ci)
        print(report)

    if args.ci and cross_crate:
        sys.exit(1)  # Block merge
    elif args.ci and intra_crate and not cross_crate:
        sys.exit(0)  # Warning only, don't block

    sys.exit(0)


if __name__ == "__main__":
    main()
