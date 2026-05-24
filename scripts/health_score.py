#!/usr/bin/env python3
"""
─── Zenic-Agents v3 — Health Score Calculator ────────────────────────
Phase 6.3: Integrates multiple quality metrics into a single
health score for the project. Used by the weekly health report
and CI pipeline.

Metrics (weighted):
  - Ruff errors (30%): Fewer = better. Target: 0.
  - API auth coverage (25%): % of mutating routes with auth. Target: 100%.
  - Security secrets (20%): New secrets detected. Target: 0.
  - Rust cross-crate dupes (15%): Fewer = better. Target: 0.
  - Test coverage (10%): % coverage. Target: 80%+.

Score: 0-100 (100 = perfect health)

Usage:
  python3 scripts/health_score.py [--json] [--ci]
  python3 scripts/health_score.py --ruff-errors 5 --auth-coverage 0.95 --secrets 0 --rust-dupes 3 --coverage 0.65
"""

import json
import subprocess
import sys
import os
from pathlib import Path


def count_ruff_errors(src_dir: str = "src/") -> int:
    """Count total Ruff errors in Python source."""
    try:
        result = subprocess.run(
            ["ruff", "check", src_dir, "--quiet"],
            capture_output=True, text=True, timeout=120
        )
        # Count non-empty output lines
        lines = [l for l in result.stdout.strip().splitlines() if l.strip()]
        return len(lines)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return -1  # Unable to run


def count_api_auth_coverage(gateway_dir: str = "gateway/src/app/api/") -> dict:
    """Count API routes and check how many have auth calls.

    Returns: {
        total_mutating: int,
        authenticated_mutating: int,
        total_get: int,
        authenticated_get: int,
        coverage_mutating: float,
        coverage_get: float,
    }
    """
    gateway_path = Path(gateway_dir)
    if not gateway_path.exists():
        return {
            "total_mutating": 0,
            "authenticated_mutating": 0,
            "total_get": 0,
            "authenticated_get": 0,
            "coverage_mutating": 1.0,
            "coverage_get": 1.0,
        }

    auth_patterns = [
        "requireAuth",
        "requireAuthAndPermission",
        "getAuthUser",
        "requireTenantAuth",
    ]

    mutating_methods = ["POST", "PUT", "DELETE", "PATCH"]
    get_methods = ["GET"]

    stats = {
        "total_mutating": 0,
        "authenticated_mutating": 0,
        "total_get": 0,
        "authenticated_get": 0,
    }

    # Find all route.ts files
    for route_file in gateway_path.rglob("route.ts"):
        try:
            content = route_file.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue

        # Skip test files
        if "__tests__" in str(route_file) or ".test." in str(route_file):
            continue

        has_auth = any(pattern in content for pattern in auth_patterns)

        for method in mutating_methods:
            # Look for export async function METHOD or export const METHOD
            pattern = rf"export\s+(?:async\s+)?(?:function\s+)?{method}\b"
            if re_search_safe(pattern, content):
                stats["total_mutating"] += 1
                if has_auth:
                    stats["authenticated_mutating"] += 1

        for method in get_methods:
            pattern = rf"export\s+(?:async\s+)?(?:function\s+)?{method}\b"
            if re_search_safe(pattern, content):
                stats["total_get"] += 1
                if has_auth:
                    stats["authenticated_get"] += 1

    stats["coverage_mutating"] = (
        stats["authenticated_mutating"] / stats["total_mutating"]
        if stats["total_mutating"] > 0
        else 1.0
    )
    stats["coverage_get"] = (
        stats["authenticated_get"] / stats["total_get"]
        if stats["total_get"] > 0
        else 1.0
    )

    return stats


def re_search_safe(pattern: str, text: str) -> bool:
    """Safe regex search."""
    import re
    try:
        return bool(re.search(pattern, text))
    except re.error:
        return False


def count_secrets(baseline_file: str = ".secrets.baseline") -> int:
    """Count potential secrets in baseline."""
    try:
        with open(baseline_file, "r") as f:
            data = json.load(f)
        return sum(len(v) for v in data.get("results", {}).values())
    except (FileNotFoundError, json.JSONDecodeError):
        return -1


def count_rust_cross_crate_dupes(crates_dir: str = "zenic-v2/") -> int:
    """Count cross-crate duplicate Rust types."""
    script_path = Path("scripts/scan_rust_duplicates.py")
    if not script_path.exists():
        return -1

    try:
        result = subprocess.run(
            ["python3", str(script_path), "--crates-dir", crates_dir, "--json"],
            capture_output=True, text=True, timeout=60
        )
        data = json.loads(result.stdout)
        return data.get("cross_crate_count", 0)
    except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
        return -1


def calculate_health_score(
    ruff_errors: int = 0,
    auth_coverage_mutating: float = 1.0,
    secrets_count: int = 0,
    rust_dupes: int = 0,
    test_coverage: float = 0.0,
) -> dict:
    """Calculate weighted health score (0-100).

    Weights:
      Ruff errors: 30% (0 errors = 100, 100+ errors = 0)
      Auth coverage: 25% (100% = 100, 0% = 0)
      Secrets: 20% (0 secrets = 100, 5+ new = 0)
      Rust dupes: 15% (0 dupes = 100, 10+ = 0)
      Test coverage: 10% (80%+ = 100, 0% = 0)
    """
    # Ruff score: penalize linearly, floor at 0
    ruff_score = max(0, 100 - ruff_errors)

    # Auth coverage: linear
    auth_score = auth_coverage_mutating * 100

    # Secrets: penalize heavily
    secrets_score = max(0, 100 - (secrets_count * 20))

    # Rust dupes: penalize
    rust_score = max(0, 100 - (rust_dupes * 10))

    # Test coverage: reward up to 80%
    test_score = min(100, (test_coverage / 0.80) * 100) if test_coverage > 0 else 0

    weights = {
        "ruff": 0.30,
        "auth": 0.25,
        "secrets": 0.20,
        "rust_dupes": 0.15,
        "test_coverage": 0.10,
    }

    overall = (
        ruff_score * weights["ruff"]
        + auth_score * weights["auth"]
        + secrets_score * weights["secrets"]
        + rust_score * weights["rust_dupes"]
        + test_score * weights["test_coverage"]
    )

    return {
        "overall_score": round(overall, 1),
        "grade": score_to_grade(overall),
        "components": {
            "ruff_errors": {"value": ruff_errors, "score": round(ruff_score, 1), "weight": weights["ruff"]},
            "auth_coverage": {"value": round(auth_coverage_mutating, 3), "score": round(auth_score, 1), "weight": weights["auth"]},
            "secrets": {"value": secrets_count, "score": round(secrets_score, 1), "weight": weights["secrets"]},
            "rust_dupes": {"value": rust_dupes, "score": round(rust_score, 1), "weight": weights["rust_dupes"]},
            "test_coverage": {"value": round(test_coverage, 3), "score": round(test_score, 1), "weight": weights["test_coverage"]},
        },
    }


def score_to_grade(score: float) -> str:
    """Convert numeric score to letter grade."""
    if score >= 90:
        return "A"
    elif score >= 80:
        return "B"
    elif score >= 70:
        return "C"
    elif score >= 60:
        return "D"
    else:
        return "F"


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Zenic-Agents Health Score Calculator")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--ci", action="store_true", help="CI mode: fail on low score")
    parser.add_argument("--threshold", type=float, default=70.0,
                        help="Minimum health score for CI (default: 70)")
    # Manual override options
    parser.add_argument("--ruff-errors", type=int, default=None)
    parser.add_argument("--auth-coverage", type=float, default=None)
    parser.add_argument("--secrets", type=int, default=None)
    parser.add_argument("--rust-dupes", type=int, default=None)
    parser.add_argument("--coverage", type=float, default=None)
    # Skip slow checks
    parser.add_argument("--skip-slow", action="store_true",
                        help="Skip ruff and rust-dupe scans (use with --manual overrides)")

    args = parser.parse_args()

    # Collect metrics
    if args.skip_slow and all(v is None for v in [
        args.ruff_errors, args.auth_coverage, args.secrets,
        args.rust_dupes, args.coverage
    ]):
        print("Warning: --skip-slow requires manual overrides", file=sys.stderr)
        sys.exit(1)

    ruff_errors = args.ruff_errors if args.ruff_errors is not None else (
        0 if args.skip_slow else count_ruff_errors()
    )

    if args.auth_coverage is not None:
        auth_coverage = args.auth_coverage
    else:
        auth_stats = count_api_auth_coverage()
        auth_coverage = auth_stats["coverage_mutating"]

    secrets_count = args.secrets if args.secrets is not None else count_secrets()
    rust_dupes = args.rust_dupes if args.rust_dupes is not None else (
        0 if args.skip_slow else count_rust_cross_crate_dupes()
    )
    test_coverage = args.coverage if args.coverage is not None else 0.0

    result = calculate_health_score(
        ruff_errors=ruff_errors,
        auth_coverage_mutating=auth_coverage,
        secrets_count=secrets_count,
        rust_dupes=rust_dupes,
        test_coverage=test_coverage,
    )

    # Add raw metrics
    result["metrics"] = {
        "ruff_errors": ruff_errors,
        "auth_coverage": auth_coverage,
        "secrets_count": secrets_count,
        "rust_cross_crate_dupes": rust_dupes,
        "test_coverage": test_coverage,
    }

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print("\n" + "=" * 60)
        print(f"  ZENIC-AGENTS HEALTH SCORE: {result['overall_score']}/100 ({result['grade']})")
        print("=" * 60)
        for component, data in result["components"].items():
            print(f"  {component:20s}: {data['score']:5.1f}/100 (weight: {data['weight']:.0%})")
        print("=" * 60)

        if args.ci:
            if result["overall_score"] < args.threshold:
                print(f"\n❌ CI GATE FAILED: Score {result['overall_score']} < threshold {args.threshold}")
                sys.exit(1)
            else:
                print(f"\n✅ CI GATE PASSED: Score {result['overall_score']} >= threshold {args.threshold}")


if __name__ == "__main__":
    main()
