#!/usr/bin/env python3
"""
Phase 3 v3: Fix F405 by adding __all__ to _types.py files and replacing star imports.
===================================================================
Strategy:
1. Add __all__ to every _types.py listing only names DEFINED in that file (not re-exported stdlib)
2. Then replace `from ._types import *` with explicit imports of needed names
3. For _exports.py (aggregator), add noqa to the star import lines
"""

import ast
import json
import os
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "src"
ROOT_STR = str(ROOT)


def run_ruff(select_codes=None, output_format="text"):
    cmd = ["ruff", "check", ROOT_STR]
    if select_codes:
        cmd.extend(["--select", ",".join(select_codes)])
    cmd.extend(["--output-format", output_format])
    result = subprocess.run(cmd, capture_output=True, text=True)
    if output_format == "json":
        try:
            return json.loads(result.stdout) if result.stdout.strip() else []
        except json.JSONDecodeError:
            return []
    return result.stdout


def get_errors_by_code(code):
    return run_ruff(select_codes=[code], output_format="json")


def get_defined_names(filepath):
    """Get all names defined at module level in a Python file."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read())
    except (SyntaxError, FileNotFoundError):
        return set()

    names = set()
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.ClassDef):
            names.add(node.name)
        elif isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
            names.add(node.name)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    names.add(target.id)
        elif isinstance(node, ast.AugAssign):
            if isinstance(node.target, ast.Name):
                names.add(node.target.id)
        elif isinstance(node, ast.AnnAssign) and node.target:
            if isinstance(node.target, ast.Name):
                names.add(node.target.id)
    return names


def get_names_used_from_star_import(filepath, star_module):
    """Get names that a file uses from a specific star import, based on F405 errors."""
    errors = get_errors_by_code("F405")
    names = set()
    for e in errors:
        if e["filename"] != filepath:
            continue
        msg = e.get("message", "")
        match = re.search(r"(\S+) may be undefined, or defined from star imports:\s+(.+)", msg)
        if match:
            name = match.group(1)
            module = match.group(2).strip()
            if module == star_module:
                names.add(name)
    return names


# ─────────────────────────────────────────────────────
# STEP 1: Add __all__ to all _types.py files
# ─────────────────────────────────────────────────────
def add_all_to_types_files():
    """Add __all__ to _types.py files listing only names defined in that file."""
    count = 0
    for dirpath, dirnames, filenames in os.walk(ROOT_STR):
        for filename in filenames:
            if filename == "_types.py":
                filepath = os.path.join(dirpath, filename)
                defined = get_defined_names(filepath)
                if not defined:
                    continue

                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        content = f.read()
                except Exception:
                    continue

                # Check if __all__ already exists
                try:
                    tree = ast.parse(content)
                except SyntaxError:
                    continue

                has_all = False
                for node in ast.walk(tree):
                    if isinstance(node, ast.Assign):
                        for target in node.targets:
                            if isinstance(target, ast.Name) and target.id == "__all__":
                                has_all = True
                                break

                if has_all:
                    continue

                # Build __all__ string
                sorted_names = sorted(defined)
                all_str = ", ".join(f'"{n}"' for n in sorted_names)
                all_line = f"\n__all__ = [{all_str}]"

                # Append to file
                new_content = content.rstrip() + all_line + "\n"

                try:
                    ast.parse(new_content)
                except SyntaxError:
                    continue

                try:
                    with open(filepath, "w", encoding="utf-8") as f:
                        f.write(new_content)
                    count += 1
                except Exception:
                    continue

    print(f"[Step1] Added __all__ to {count} _types.py files")
    return count


# ─────────────────────────────────────────────────────
# STEP 2: Add __all__ to _helpers.py files too
# ─────────────────────────────────────────────────────
def add_all_to_helpers_files():
    """Add __all__ to _helpers.py files listing only names defined in that file."""
    count = 0
    for dirpath, dirnames, filenames in os.walk(ROOT_STR):
        for filename in filenames:
            if filename == "_helpers.py":
                filepath = os.path.join(dirpath, filename)
                defined = get_defined_names(filepath)
                if not defined:
                    continue

                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        content = f.read()
                except Exception:
                    continue

                try:
                    tree = ast.parse(content)
                except SyntaxError:
                    continue

                has_all = False
                for node in ast.walk(tree):
                    if isinstance(node, ast.Assign):
                        for target in node.targets:
                            if isinstance(target, ast.Name) and target.id == "__all__":
                                has_all = True
                                break

                if has_all:
                    continue

                sorted_names = sorted(defined)
                all_str = ", ".join(f'"{n}"' for n in sorted_names)
                all_line = f"\n__all__ = [{all_str}]"

                new_content = content.rstrip() + all_line + "\n"

                try:
                    ast.parse(new_content)
                except SyntaxError:
                    continue

                try:
                    with open(filepath, "w", encoding="utf-8") as f:
                        f.write(new_content)
                    count += 1
                except Exception:
                    continue

    print(f"[Step2] Added __all__ to {count} _helpers.py files")
    return count


# ─────────────────────────────────────────────────────
# STEP 3: Replace star imports with explicit imports
# ─────────────────────────────────────────────────────
def replace_star_imports():
    """Replace 'from ._types import *' with explicit imports based on what's actually used."""
    # Find all files with star imports
    f403_errors = get_errors_by_code("F403")
    f405_errors = get_errors_by_code("F405")

    # Group F405 by file and module
    f405_by_file = defaultdict(lambda: defaultdict(set))
    for e in f405_errors:
        msg = e.get("message", "")
        match = re.search(r"(\S+) may be undefined, or defined from star imports:\s+(.+)", msg)
        if match:
            name = match.group(1)
            module = match.group(2).strip()
            f405_by_file[e["filename"]][module].add(name)

    fixed = 0
    skipped = 0

    # Find all files with star imports (not just those with F403 errors)
    for dirpath, dirnames, filenames in os.walk(ROOT_STR):
        for filename in filenames:
            if not filename.endswith(".py"):
                continue

            filepath = os.path.join(dirpath, filename)

            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
            except Exception:
                continue

            try:
                ast.parse(content)
            except SyntaxError:
                continue

            lines = content.split("\n")
            modified = False
            new_lines = []

            for line in lines:
                stripped = line.strip()

                # Check for star import
                star_match = re.match(r"^(\s*)from\s+(\S+)\s+import\s+\*(.*)$", stripped)
                if not star_match:
                    new_lines.append(line)
                    continue

                indent = star_match.group(1)
                module = star_match.group(2)
                trailing = star_match.group(3).strip()

                # Skip if already has noqa for F403
                if "noqa: F403" in trailing or "noqa: F403" in line:
                    new_lines.append(line)
                    continue

                # Get names used from this module in this file
                used_names = f405_by_file.get(filepath, {}).get(module, set())

                # Also check what the module exports via __all__
                module_names = set()
                if module.startswith("."):
                    # Relative import
                    module_path = filepath.rsplit("/", 1)[0]
                    parts = module.split(".")
                    for part in parts:
                        if part == "":
                            module_path = module_path.rsplit("/", 1)[0] if "/" in module_path else module_path
                        else:
                            module_path = os.path.join(module_path, part)

                    # Try module/__init__.py or module.py
                    init_path = os.path.join(module_path, "__init__.py")
                    file_path = module_path + ".py"

                    if os.path.exists(init_path):
                        module_names = get_defined_names(init_path)
                    elif os.path.exists(file_path):
                        module_names = get_defined_names(file_path)

                # Determine which names to import
                if used_names:
                    names_to_import = sorted(used_names)
                elif module_names:
                    # Import everything that's defined in the module (via __all__)
                    names_to_import = sorted(module_names)
                else:
                    # Can't determine - keep star import with noqa
                    new_lines.append(f"{indent}from {module} import *  # noqa: F403")
                    skipped += 1
                    continue

                if len(names_to_import) <= 6:
                    new_import = f"{indent}from {module} import {', '.join(names_to_import)}"
                else:
                    name_lines = [f"{indent}    {n}," for n in names_to_import]
                    new_import = f"{indent}from {module} import (\n" + "\n".join(name_lines) + f"\n{indent})"

                new_lines.append(new_import)
                modified = True
                fixed += 1

            if modified:
                new_content = "\n".join(new_lines)
                try:
                    ast.parse(new_content)
                except SyntaxError:
                    # Revert
                    print(f"  [WARN] Skipping {filepath}: syntax would break")
                    continue

                try:
                    with open(filepath, "w", encoding="utf-8") as f:
                        f.write(new_content)
                except Exception:
                    continue

    print(f"[Step3] Replaced {fixed} star imports with explicit imports ({skipped} kept as noqa)")
    return fixed


# ─────────────────────────────────────────────────────
# STEP 4: Fix _exports.py star imports with noqa
# ─────────────────────────────────────────────────────
def fix_exports_star_imports():
    """Add proper noqa comments to _exports.py files that legitimately use star imports."""
    count = 0
    for dirpath, dirnames, filenames in os.walk(ROOT_STR):
        for filename in filenames:
            if filename.startswith("_exports") and filename.endswith(".py"):
                filepath = os.path.join(dirpath, filename)

                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        content = f.read()
                except Exception:
                    continue

                # Add noqa to star import lines
                lines = content.split("\n")
                modified = False
                new_lines = []

                for line in lines:
                    if re.search(r"from\s+\.\S+\s+import\s+\*", line):
                        if "noqa: F403" not in line and "noqa: F405" not in line:
                            line = line.rstrip() + "  # noqa: F403, F405"
                            modified = True
                            count += 1
                    new_lines.append(line)

                if modified:
                    new_content = "\n".join(new_lines)
                    try:
                        ast.parse(new_content)
                    except SyntaxError:
                        continue

                    try:
                        with open(filepath, "w", encoding="utf-8") as f:
                            f.write(new_content)
                    except Exception:
                        continue

    print(f"[Step4] Added noqa to {count} star imports in _exports files")
    return count


# ─────────────────────────────────────────────────────
# STEP 5: Fix F822 - undefined names in __all__
# ─────────────────────────────────────────────────────
def fix_f822():
    """Remove names from __all__ that don't exist in the module."""
    errors = get_errors_by_code("F822")

    by_file = defaultdict(set)
    for e in errors:
        msg = e.get("message", "")
        match = re.search(r"(\S+) is listed in `__all__` but is not defined", msg)
        if match:
            name = match.group(1)
            by_file[e["filename"]].add(name)

    fixed = 0
    for filepath, undefined_names in by_file.items():
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception:
            continue

        try:
            tree = ast.parse(content)
        except SyntaxError:
            continue

        all_node = None
        existing_all = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "__all__":
                        all_node = node
                        if isinstance(node.value, ast.List):
                            for elt in node.value.elts:
                                if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                                    existing_all.append(elt.value)

        if not all_node:
            continue

        new_names = [n for n in existing_all if n not in undefined_names]
        if len(new_names) == len(existing_all):
            continue

        fixed += len(existing_all) - len(new_names)

        if new_names:
            all_str = ", ".join(f'"{n}"' for n in new_names)
            new_all_line = f"__all__ = [{all_str}]"
        else:
            new_all_line = ""

        lines = content.split("\n")
        start_line = all_node.lineno - 1
        end_line = all_node.end_lineno

        if new_all_line:
            lines[start_line:end_line] = [new_all_line]
        else:
            lines[start_line:end_line] = []

        new_content = "\n".join(lines)
        try:
            ast.parse(new_content)
        except SyntaxError:
            continue

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(new_content)
        except Exception:
            continue

    print(f"[Step5] Removed {fixed} undefined names from __all__")
    return fixed


# ─────────────────────────────────────────────────────
# STEP 6: Fix F401 remaining - remove truly unused imports
# ─────────────────────────────────────────────────────
def fix_f401_remaining():
    """Use ruff --fix for remaining F401 errors."""
    errors = get_errors_by_code("F401")
    if not errors:
        return 0

    # Separate init vs non-init
    init_files = set(e["filename"] for e in errors if e["filename"].endswith("__init__.py"))
    non_init_files = set(e["filename"] for e in errors if not e["filename"].endswith("__init__.py"))

    # For non-init files, try ruff fix
    fixed = 0
    if non_init_files:
        cmd = ["ruff", "check", "--select", "F401", "--fix"] + list(non_init_files)
        result = subprocess.run(cmd, capture_output=True, text=True)

    # For init files, check if they have __all__ already
    for filepath in init_files:
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                tree = ast.parse(f.read())
        except (SyntaxError, FileNotFoundError):
            continue

        has_all = False
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "__all__":
                        has_all = True

        if has_all:
            # Already has __all__ - ruff should handle this with --fix
            cmd = ["ruff", "check", "--select", "F401", "--fix", filepath]
            subprocess.run(cmd, capture_output=True, text=True)

    # Check remaining
    remaining = get_errors_by_code("F401")
    fixed = len(errors) - len(remaining)
    print(f"[Step6] Fixed {fixed} remaining F401 errors ({len(remaining)} still remaining)")
    return fixed


# ─────────────────────────────────────────────────────
# STEP 7: Fix E701, E702, E712 style errors with ruff
# ─────────────────────────────────────────────────────
def fix_style_errors():
    """Fix remaining style errors using ruff."""
    codes = ["E701", "E702", "E712", "E721", "E741", "F811"]
    total = 0
    for code in codes:
        errors = get_errors_by_code(code)
        if not errors:
            continue

        files = list(set(e["filename"] for e in errors))
        cmd = ["ruff", "check", "--select", code, "--fix"] + files
        result = subprocess.run(cmd, capture_output=True, text=True)

        remaining = get_errors_by_code(code)
        fixed = len(errors) - len(remaining)
        total += fixed
        if fixed > 0:
            print(f"  [{code}] Fixed {fixed}")

    print(f"[Step7] Fixed {total} style errors via ruff --fix")
    return total


# ─────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────
def main():
    print("=" * 70)
    print("Phase 3 v3: F405-focused Ruff Linting Correction")
    print("=" * 70)

    # Get initial count
    result = subprocess.run(["ruff", "check", ROOT_STR], capture_output=True, text=True)
    initial_count = 0
    for line in result.stdout.strip().split("\n"):
        match = re.search(r"Found (\d+) errors", line)
        if match:
            initial_count = int(match.group(1))

    print(f"\nInitial error count: {initial_count}")
    print("-" * 70)

    # Step 1: Add __all__ to _types.py files
    print("\n[1/7] Adding __all__ to _types.py files...")
    add_all_to_types_files()

    # Step 2: Add __all__ to _helpers.py files
    print("\n[2/7] Adding __all__ to _helpers.py files...")
    add_all_to_helpers_files()

    # Step 3: Replace star imports with explicit imports
    print("\n[3/7] Replacing star imports with explicit imports...")
    replace_star_imports()

    # Step 4: Fix _exports.py star imports with noqa
    print("\n[4/7] Fixing _exports.py star imports with noqa...")
    fix_exports_star_imports()

    # Step 5: Fix F822
    print("\n[5/7] Fixing F822 undefined exports...")
    fix_f822()

    # Step 6: Fix remaining F401
    print("\n[6/7] Fixing remaining F401 unused imports...")
    fix_f401_remaining()

    # Step 7: Fix style errors
    print("\n[7/7] Fixing style errors...")
    fix_style_errors()

    # Final ruff --fix pass
    print("\n[Final] Running ruff --fix for any remaining auto-fixable issues...")
    subprocess.run(["ruff", "check", ROOT_STR, "--fix"], capture_output=True, text=True)
    subprocess.run(["ruff", "check", ROOT_STR, "--unsafe-fixes", "--fix"], capture_output=True, text=True)

    # Get final count
    result = subprocess.run(["ruff", "check", ROOT_STR, "--statistics"], capture_output=True, text=True)
    final_count = 0
    for line in result.stdout.strip().split("\n"):
        match = re.search(r"Found (\d+) errors", line)
        if match:
            final_count = int(match.group(1))

    print("\n" + "=" * 70)
    print(f"\nResults:")
    print(f"  Initial errors: {initial_count}")
    print(f"  Fixed:          {initial_count - final_count}")
    print(f"  Remaining:      {final_count}")
    if initial_count > 0:
        print(f"  Reduction:      {((initial_count - final_count) / initial_count * 100):.1f}%")

    print("\nFinal error breakdown:")
    for line in result.stdout.strip().split("\n"):
        line = line.strip()
        if re.match(r"^\d+\s+[A-Z]", line) or line.startswith("Found"):
            print(f"  {line}")

    return final_count


if __name__ == "__main__":
    result = main()
    sys.exit(0)
