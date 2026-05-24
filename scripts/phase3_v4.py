#!/usr/bin/env python3
"""
Phase 3 v4: AST-based star import replacement
==============================================
For each file with `from x import *`:
1. Find all star import modules
2. Parse those modules to find their __all__ or defined names
3. Find all names used in the importing file that come from those modules
4. Replace star imports with explicit imports
5. Add noqa for _exports.py aggregator files
"""

import ast
import os
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "src"
ROOT_STR = str(ROOT)


def resolve_module_path(import_module, from_file):
    """Resolve a relative import module to a file path."""
    base_dir = os.path.dirname(from_file)

    # Handle relative imports
    parts = import_module.split(".")
    level = 0
    while level < len(parts) and parts[level] == "":
        level += 1

    # Go up `level - 1` directories (level=1 means same dir)
    for _ in range(max(0, level - 1)):
        base_dir = os.path.dirname(base_dir)

    # Navigate to the module
    for part in parts[level:]:
        if part:
            base_dir = os.path.join(base_dir, part)

    # Check __init__.py or module.py
    init_path = os.path.join(base_dir, "__init__.py")
    file_path = base_dir + ".py"

    if os.path.exists(init_path):
        return init_path
    elif os.path.exists(file_path):
        return file_path
    return None


def get_module_exports(filepath):
    """Get names exported by a module (from __all__ or defined names)."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read())
    except (SyntaxError, FileNotFoundError):
        return set()

    # Check for __all__
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "__all__":
                    if isinstance(node.value, ast.List):
                        names = set()
                        for elt in node.value.elts:
                            if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                                names.add(elt.value)
                        return names

    # No __all__ - return defined names
    names = set()
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.ClassDef):
            names.add(node.name)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            names.add(node.name)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    names.add(target.id)
    return names


def get_names_used_in_file(filepath):
    """Get all Name nodes used in a file (variables, functions, classes referenced)."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read())
    except (SyntaxError, FileNotFoundError):
        return set()

    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            names.add(node.id)
        elif isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
            names.add(node.value.id)
    return names


def get_locally_defined_names(filepath):
    """Get names defined in this file (including via imports)."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read())
    except (SyntaxError, FileNotFoundError):
        return set()

    names = set()
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.asname or alias.name.split(".")[-1])
        elif isinstance(node, ast.ImportFrom):
            if node.names and node.names[0].name != "*":
                for alias in node.names:
                    names.add(alias.asname or alias.name)
        elif isinstance(node, ast.ClassDef):
            names.add(node.name)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            names.add(node.name)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    names.add(target.id)
        elif isinstance(node, ast.For):
            if isinstance(node.target, ast.Name):
                names.add(node.target.id)
        elif isinstance(node, ast.With):
            for item in node.items:
                if item.optional_vars and isinstance(item.optional_vars, ast.Name):
                    names.add(item.optional_vars.id)
    return names


def replace_star_imports_in_file(filepath):
    """Replace star imports with explicit imports in a single file."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception:
        return 0

    try:
        ast.parse(content)
    except SyntaxError:
        return 0

    # Find star imports
    lines = content.split("\n")
    star_imports = []  # (line_index, indent, module, trailing)

    for i, line in enumerate(lines):
        stripped = line.strip()
        star_match = re.match(r"^(\s*)from\s+(\S+)\s+import\s+\*(.*)$", stripped)
        if star_match:
            indent = star_match.group(1)
            module = star_match.group(2)
            trailing = star_match.group(3).strip()
            star_imports.append((i, indent, module, trailing))

    if not star_imports:
        return 0

    # Get names used in this file
    used_names = get_names_used_in_file(filepath)
    locally_defined = get_locally_defined_names(filepath)
    needed_names = used_names - locally_defined

    # For each star import, find what names come from it
    replacements = []
    for line_idx, indent, module, trailing in star_imports:
        # Resolve the module path
        module_path = resolve_module_path(module, filepath)

        if module_path is None:
            # Can't resolve - keep with noqa
            replacements.append((line_idx, None, f"{indent}from {module} import *  # noqa: F403, F405"))
            continue

        # Get module exports
        module_exports = get_module_exports(module_path)

        # Find which exported names are actually needed
        imported_names = module_exports & needed_names

        if imported_names:
            sorted_names = sorted(imported_names)
            if len(sorted_names) <= 5:
                new_import = f"{indent}from {module} import {', '.join(sorted_names)}"
            else:
                name_lines = [f"{indent}    {n}," for n in sorted_names]
                new_import = f"{indent}from {module} import (\n" + "\n".join(name_lines) + f"\n{indent})"
            replacements.append((line_idx, sorted_names, new_import))
        else:
            # No names needed from this module - remove the import
            replacements.append((line_idx, [], None))

    # Apply replacements in reverse order
    fixed = 0
    for line_idx, names, new_line in reversed(replacements):
        if new_line is None:
            # Remove the line entirely
            lines[line_idx:line_idx + 1] = []
        else:
            lines[line_idx] = new_line
        fixed += 1

    new_content = "\n".join(lines)

    # Verify syntax
    try:
        ast.parse(new_content)
    except SyntaxError:
        return 0

    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(new_content)
    except Exception:
        return 0

    return fixed


def fix_exports_files():
    """Handle _exports.py files specially - add noqa instead of replacing."""
    count = 0
    for dirpath, dirnames, filenames in os.walk(ROOT_STR):
        for filename in filenames:
            if "_exports" in filename and filename.endswith(".py"):
                filepath = os.path.join(dirpath, filename)

                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        content = f.read()
                except Exception:
                    continue

                modified = False
                lines = content.split("\n")
                new_lines = []

                for line in lines:
                    if re.search(r"from\s+\S+\s+import\s+\*", line):
                        if "noqa: F403" not in line:
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

    print(f"  Added noqa to {count} star imports in _exports files")
    return count


def fix_init_star_imports():
    """Handle __init__.py star imports - add noqa for re-export patterns."""
    count = 0
    for dirpath, dirnames, filenames in os.walk(ROOT_STR):
        for filename in filenames:
            if filename == "__init__.py":
                filepath = os.path.join(dirpath, filename)

                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        content = f.read()
                except Exception:
                    continue

                # Check if file has __all__ (legitimate re-export pattern)
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

                if not has_all:
                    continue

                modified = False
                lines = content.split("\n")
                new_lines = []

                for line in lines:
                    if re.search(r"from\s+\S+\s+import\s+\*", line):
                        if "noqa: F403" not in line:
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

    print(f"  Added noqa to {count} star imports in __init__.py files with __all__")
    return count


def fix_mixin_star_imports():
    """Replace star imports in _mixin and _core files with explicit imports."""
    total = 0
    for dirpath, dirnames, filenames in os.walk(ROOT_STR):
        for filename in filenames:
            if filename.endswith(".py") and not filename.startswith("_exports"):
                filepath = os.path.join(dirpath, filename)
                # Skip __init__.py and _exports files
                if filename == "__init__.py":
                    continue

                fixed = replace_star_imports_in_file(filepath)
                if fixed > 0:
                    total += fixed

    print(f"  Replaced {total} star imports in mixin/core files")
    return total


def main():
    print("=" * 70)
    print("Phase 3 v4: AST-based Star Import Replacement")
    print("=" * 70)

    result = subprocess.run(["ruff", "check", ROOT_STR], capture_output=True, text=True)
    initial_count = 0
    for line in result.stdout.strip().split("\n"):
        match = re.search(r"Found (\d+) errors", line)
        if match:
            initial_count = int(match.group(1))

    print(f"\nInitial error count: {initial_count}")
    print("-" * 70)

    # Step 1: Fix _exports.py files (noqa approach)
    print("\n[1/4] Fixing _exports.py star imports...")
    fix_exports_files()

    # Step 2: Fix __init__.py with __all__ (noqa approach)
    print("\n[2/4] Fixing __init__.py star imports with __all__...")
    fix_init_star_imports()

    # Step 3: Fix _mixin/_core files (replace with explicit imports)
    print("\n[3/4] Replacing star imports in mixin/core files...")
    fix_mixin_star_imports()

    # Step 4: Run ruff --fix for remaining issues
    print("\n[4/4] Running ruff --fix for remaining auto-fixable issues...")
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
    main()
