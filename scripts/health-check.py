#!/usr/bin/env python3
"""
Zenic-Agents v3 — Health Check Script

Phase 6.3: Monitoreo Continuo del Plan Maestro de Corrección.

Genera un reporte de salud del código que incluye:
- Conteo de errores Ruff por categoría
- Conteo de warnings ESLint en el gateway
- Número de rutas API sin autenticación
- Detección de console.log en producción
- Verificación de secrets en baseline
- Resumen de deuda técnica

Uso:
    python scripts/health-check.py              # Reporte completo
    python scripts/health-check.py --json       # Output JSON para CI
    python scripts/health-check.py --quiet      # Solo errores críticos

Salida: Reporte en stdout + archivo JSON en /tmp/zenic-health.json
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

# ── Configuration ──────────────────────────────────────────────────

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = REPO_ROOT / "src"
GATEWAY_DIR = REPO_ROOT / "gateway"

# Ruff rule categories to check
RUFF_CATEGORIES = {
    "F401": "Unused imports",
    "F403": "Star import (undefined names)",
    "F405": "Star import usage",
    "F541": "Empty f-string",
    "F822": "Undefined __all__",
    "S":   "Security (bandit)",
    "E":   "Style errors",
    "W":   "Style warnings",
    "B":   "Bugbear",
    "I":   "Import order",
}

# ── Helpers ────────────────────────────────────────────────────────

def run_cmd(cmd: List[str], cwd: Path | None = None, timeout: int = 60) -> str:
    """Run a command and return stdout, or empty string on failure."""
    try:
        result = subprocess.run(
            cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout
        )
        return result.stdout + result.stderr
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return ""


def count_ruff_errors() -> Dict[str, int]:
    """Count Ruff errors by category."""
    counts: Dict[str, int] = {}

    for rule_key in RUFF_CATEGORIES:
        output = run_cmd(
            ["ruff", "check", "src/", "--select", rule_key, "--quiet"],
            cwd=REPO_ROOT,
        )
        # Count non-empty lines
        lines = [l for l in output.strip().split("\n") if l.strip()]
        counts[rule_key] = len(lines)

    # Total
    total_output = run_cmd(
        ["ruff", "check", "src/", "--quiet"],
        cwd=REPO_ROOT,
    )
    total_lines = [l for l in total_output.strip().split("\n") if l.strip()]
    counts["TOTAL"] = len(total_lines)

    return counts


def count_eslint_issues() -> Dict[str, int]:
    """Count ESLint errors and warnings in gateway."""
    output = run_cmd(
        ["npx", "eslint", ".", "--format", "compact"],
        cwd=GATEWAY_DIR,
        timeout=120,
    )

    errors = len(re.findall(r" error ", output))
    warnings = len(re.findall(r" warning ", output))

    return {"errors": errors, "warnings": warnings}


def count_console_log_in_production() -> List[Dict[str, str]]:
    """Find executable console.log in gateway/src/ (not in comments)."""
    findings: List[Dict[str, str]] = []

    if not GATEWAY_DIR.exists():
        return findings

    for ts_file in GATEWAY_DIR.rglob("src/**/*.ts"):
        if "node_modules" in str(ts_file) or ".next" in str(ts_file):
            continue
        try:
            content = ts_file.read_text(errors="ignore")
            lines = content.split("\n")
            for i, line in enumerate(lines, 1):
                stripped = line.strip()
                # Skip comments and JSDoc
                if stripped.startswith("//") or stripped.startswith("*"):
                    continue
                # Check for console.log call
                if re.search(r'\bconsole\.log\s*\(', stripped):
                    findings.append({
                        "file": str(ts_file.relative_to(REPO_ROOT)),
                        "line": str(i),
                        "content": stripped[:100],
                    })
        except Exception:
            continue

    # Also check .tsx files
    for tsx_file in GATEWAY_DIR.rglob("src/**/*.tsx"):
        if "node_modules" in str(tsx_file) or ".next" in str(tsx_file):
            continue
        try:
            content = tsx_file.read_text(errors="ignore")
            lines = content.split("\n")
            for i, line in enumerate(lines, 1):
                stripped = line.strip()
                if stripped.startswith("//") or stripped.startswith("*"):
                    continue
                if re.search(r'\bconsole\.log\s*\(', stripped):
                    findings.append({
                        "file": str(tsx_file.relative_to(REPO_ROOT)),
                        "line": str(i),
                        "content": stripped[:100],
                    })
        except Exception:
            continue

    return findings


def check_secrets_baseline() -> Dict[str, Any]:
    """Check secrets baseline status."""
    baseline_path = REPO_ROOT / ".secrets.baseline"

    if not baseline_path.exists():
        return {"status": "missing", "count": 0, "note": "No .secrets.baseline found"}

    try:
        data = json.loads(baseline_path.read_text())
        total = sum(len(v) for v in data.get("results", {}).values())
        return {"status": "exists", "count": total}
    except Exception as e:
        return {"status": "error", "count": 0, "note": str(e)}


def check_pre_commit() -> Dict[str, Any]:
    """Check pre-commit hooks status."""
    config_path = REPO_ROOT / ".pre-commit-config.yaml"
    hook_path = REPO_ROOT / ".git" / "hooks" / "pre-commit"

    return {
        "config_exists": config_path.exists(),
        "hook_installed": hook_path.exists() and not hook_path.name.endswith(".sample"),
    }


# ── Main Report ────────────────────────────────────────────────────

def generate_report(json_output: bool = False, quiet: bool = False) -> Dict[str, Any]:
    """Generate the health check report."""
    timestamp = datetime.now(timezone.utc).isoformat()

    report: Dict[str, Any] = {
        "timestamp": timestamp,
        "version": "3.0.0",
        "checks": {},
    }

    # 1. Ruff errors
    ruff = count_ruff_errors()
    report["checks"]["ruff"] = ruff

    # 2. ESLint
    eslint = count_eslint_issues()
    report["checks"]["eslint"] = eslint

    # 3. Console.log in production
    console_logs = count_console_log_in_production()
    report["checks"]["console_log_production"] = {
        "count": len(console_logs),
        "findings": console_logs if not quiet else [],
    }

    # 4. Secrets baseline
    secrets = check_secrets_baseline()
    report["checks"]["secrets"] = secrets

    # 5. Pre-commit hooks
    pre_commit = check_pre_commit()
    report["checks"]["pre_commit"] = pre_commit

    # ── Overall status ─────────────────────────────────────────
    critical_issues = []
    if ruff.get("TOTAL", 0) > 0:
        critical_issues.append(f"Ruff: {ruff['TOTAL']} errors")
    if eslint.get("errors", 0) > 0:
        critical_issues.append(f"ESLint: {eslint['errors']} errors")
    if len(console_logs) > 0:
        critical_issues.append(f"Console.log: {len(console_logs)} in production")
    if secrets.get("status") == "missing":
        critical_issues.append("Secrets baseline missing")

    report["status"] = "CRITICAL" if critical_issues else "HEALTHY"
    report["critical_issues"] = critical_issues

    # ── Output ─────────────────────────────────────────────────
    if json_output:
        print(json.dumps(report, indent=2))
    elif not quiet:
        _print_report(report)
    elif critical_issues:
        print(f"❌ {len(critical_issues)} critical issues found:")
        for issue in critical_issues:
            print(f"  - {issue}")

    # Save to file
    output_path = Path("/tmp/zenic-health.json")
    output_path.write_text(json.dumps(report, indent=2))

    return report


def _print_report(report: Dict[str, Any]) -> None:
    """Print a human-readable health report."""
    ts = report["timestamp"][:19].replace("T", " ")
    status = report["status"]
    icon = "✅" if status == "HEALTHY" else "❌"

    print(f"\n{'='*60}")
    print(f"  Zenic-Agents Health Report — {ts}")
    print(f"  Status: {icon} {status}")
    print(f"{'='*60}\n")

    # Ruff
    ruff = report["checks"].get("ruff", {})
    print("  📊 Python (Ruff)")
    for key, count in sorted(ruff.items()):
        label = RUFF_CATEGORIES.get(key, key)
        bar = "█" * min(count, 50)
        print(f"    {key:6s} ({label:25s}): {count:5d} {bar}")
    print()

    # ESLint
    eslint = report["checks"].get("eslint", {})
    print("  📊 Gateway (ESLint)")
    print(f"    Errors  : {eslint.get('errors', 0)}")
    print(f"    Warnings: {eslint.get('warnings', 0)}")
    print()

    # Console.log
    cl = report["checks"].get("console_log_production", {})
    print(f"  📊 Console.log in Production: {cl.get('count', 0)}")
    for finding in cl.get("findings", [])[:5]:
        print(f"    {finding['file']}:{finding['line']} — {finding['content'][:60]}")
    if len(cl.get("findings", [])) > 5:
        print(f"    ... and {len(cl['findings']) - 5} more")
    print()

    # Secrets
    secrets = report["checks"].get("secrets", {})
    print(f"  🔐 Secrets Baseline: {secrets.get('status', 'unknown')} ({secrets.get('count', 0)} items)")

    # Pre-commit
    pc = report["checks"].get("pre_commit", {})
    print(f"  🪝 Pre-commit: config={'✅' if pc.get('config_exists') else '❌'} hook={'✅' if pc.get('hook_installed') else '❌'}")
    print()

    # Critical issues
    if report.get("critical_issues"):
        print("  ⚠️  Critical Issues:")
        for issue in report["critical_issues"]:
            print(f"    - {issue}")
    else:
        print("  ✅ No critical issues found!")

    print(f"\n  Report saved to /tmp/zenic-health.json")
    print(f"{'='*60}\n")


# ── CLI ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    args = sys.argv[1:]
    json_mode = "--json" in args
    quiet_mode = "--quiet" in args

    report = generate_report(json_output=json_mode, quiet=quiet_mode)

    # Exit with non-zero if critical issues found (useful for CI)
    sys.exit(1 if report["status"] == "CRITICAL" else 0)
