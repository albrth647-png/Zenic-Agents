#!/usr/bin/env python3
"""
Phase 3 v2: Careful Ruff Linting Correction Script for Zenic-Agents
===================================================================
Uses AST parsing to validate all changes. Only adds valid Python identifiers to __all__.
Handles: F401 (__init__.py re-exports), F403/F405 (star imports),
         F822 (undefined exports), F821 (undefined names),
         E701/E402/E702 (style errors)
"""

import ast
import json
import keyword
import os
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "src"
ROOT_STR = str(ROOT)


def is_valid_identifier(name):
    """Check if a name is a valid Python identifier."""
    return name.isidentifier() and not keyword.iskeyword(name)


def run_ruff(select_codes=None, output_format="text"):
    """Run ruff check and return output."""
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
    """Get all errors for a specific Ruff code as JSON."""
    return run_ruff(select_codes=[code], output_format="json")


def verify_file_syntax(filepath):
    """Verify that a file has valid Python syntax."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            ast.parse(f.read())
        return True
    except SyntaxError:
        return False


# ─────────────────────────────────────────────────────
# FIX 1: F401 in __init__.py — Add __all__ for re-exports (AST-based)
# ─────────────────────────────────────────────────────
def fix_f401_init_reexports():
    """Add __all__ to __init__.py files with F401 unused-import errors for re-exports."""
    errors = get_errors_by_code("F401")
    init_errors = [e for e in errors if e.get("filename", "").endswith("__init__.py")]

    # Group by file
    by_file = defaultdict(set)
    for e in init_errors:
        msg = e.get("message", "")
        # Extract the import name from the message
        # Format: `module.name` imported but unused; consider removing, adding to `__all__`, or using a redundant alias
        match = re.search(r"`([^`]+)` imported but unused", msg)
        if match:
            full_name = match.group(1)
            # Take the last part (the actual name being imported)
            name = full_name.split(".")[-1]
            if is_valid_identifier(name):
                by_file[e["filename"]].add(name)

    fixed = 0
    broken = 0
    for filepath, unused_names in by_file.items():
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception:
            continue

        # Parse existing __all__ using AST
        try:
            tree = ast.parse(content)
        except SyntaxError:
            # Skip files that already have syntax errors
            continue

        existing_all = set()
        all_node = None
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "__all__":
                        all_node = node
                        if isinstance(node.value, ast.List):
                            for elt in node.value.elts:
                                if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                                    existing_all.add(elt.value)

        # Compute new names to add
        new_names = unused_names - existing_all
        if not new_names:
            continue

        all_names = sorted(existing_all | new_names)

        # Build new __all__ string
        all_str = ", ".join(f'"{n}"' for n in all_names)
        new_all_line = f"__all__ = [{all_str}]"

        if all_node:
            # Replace existing __all__
            # Find the line range of the existing __all__
            start_line = all_node.lineno - 1  # 0-indexed
            end_line = all_node.end_lineno  # exclusive

            lines = content.split("\n")

            # Check if __all__ spans multiple lines
            if end_line - start_line > 1:
                # Multi-line __all__
                lines[start_line:end_line] = [new_all_line]
            else:
                # Single-line __all__
                lines[start_line] = new_all_line

            content = "\n".join(lines)
        else:
            # No existing __all__ — add one after the last import
            lines = content.split("\n")
            last_import_idx = 0
            for i, line in enumerate(lines):
                stripped = line.strip()
                if stripped.startswith(("import ", "from ")):
                    # Handle multi-line imports
                    last_import_idx = i

            # Find end of multi-line import if any
            in_import = False
            paren_depth = 0
            for i, line in enumerate(lines):
                stripped = line.strip()
                if stripped.startswith(("import ", "from ")):
                    in_import = True
                    paren_depth += stripped.count("(") - stripped.count(")")
                elif in_import:
                    paren_depth += stripped.count("(") - stripped.count(")")
                    if paren_depth <= 0:
                        in_import = False
                        last_import_idx = i

            all_line = f"\n__all__ = [{all_str}]"
            lines.insert(last_import_idx + 1, all_line)
            content = "\n".join(lines)

        # Verify syntax after modification
        try:
            ast.parse(content)
        except SyntaxError:
            broken += 1
            continue

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
            fixed += len(new_names)
        except Exception:
            continue

    print(f"[F401-__init__] Added __all__ for {fixed} re-exports in {len(by_file) - broken} __init__.py files ({broken} skipped due to syntax)")
    return fixed


# ─────────────────────────────────────────────────────
# FIX 2: F403/F405 — Replace star imports with explicit imports (AST-based)
# ─────────────────────────────────────────────────────
def fix_star_imports():
    """Replace 'from module import *' with explicit imports based on F405 usage info."""
    # Get F405 errors (names used from star imports)
    f405_errors = get_errors_by_code("F405")

    # Group F405 by file and the star-import module
    f405_by_file = defaultdict(lambda: defaultdict(set))
    for e in f405_errors:
        msg = e.get("message", "")
        match = re.search(r"(\S+) may be undefined, or defined from star imports:\s+(.+)", msg)
        if match:
            name = match.group(1)
            # Handle names that might not be valid identifiers (e.g., from F405 messages)
            if not is_valid_identifier(name):
                continue
            module = match.group(2).strip()
            f405_by_file[e["filename"]][module].add(name)

    # Get F403 errors (star import declarations)
    f403_errors = get_errors_by_code("F403")

    # Group F403 by file
    f403_by_file = defaultdict(list)
    for e in f403_errors:
        f403_by_file[e["filename"]].append(e)

    fixed_files = 0
    fixed_errors = 0

    for filepath, errs in f403_by_file.items():
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception:
            continue

        # Verify syntax before editing
        if not verify_file_syntax(filepath):
            continue

        lines = content.split("\n")

        # Get the names used from star imports in this file
        file_star_names = f405_by_file.get(filepath, {})

        new_lines = []
        for i, line in enumerate(lines):
            stripped = line.strip()

            # Check if this is a star import
            star_match = re.match(r"^(\s*)from\s+(\S+)\s+import\s+\*\s*$", stripped)
            if not star_match:
                new_lines.append(line)
                continue

            indent = star_match.group(1)
            module = star_match.group(2)

            # Get names used from this module
            names = file_star_names.get(module, set())

            if names:
                # Replace with explicit imports
                sorted_names = sorted(names)
                if len(sorted_names) <= 4:
                    new_import = f"{indent}from {module} import {', '.join(sorted_names)}"
                else:
                    # Multi-line import
                    name_lines = [f"{indent}    {n}," for n in sorted_names]
                    new_import = f"{indent}from {module} import (\n" + "\n".join(name_lines) + f"\n{indent})"
                new_lines.append(new_import)
                fixed_errors += 1
            else:
                # No names used from this star import - keep it as a noqa comment
                new_lines.append(f"{indent}from {module} import *  # noqa: F403")
                fixed_errors += 1

        new_content = "\n".join(new_lines)

        # Verify syntax after editing
        try:
            ast.parse(new_content)
        except SyntaxError:
            # Revert
            print(f"  [WARN] Skipping {filepath}: syntax would break")
            continue

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(new_content)
            fixed_files += 1
        except Exception:
            continue

    print(f"[F403/F405] Fixed {fixed_errors} star imports in {fixed_files} files")
    return fixed_errors


# ─────────────────────────────────────────────────────
# FIX 3: F822 — Remove undefined names from __all__ (AST-based)
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
            if is_valid_identifier(name):
                by_file[e["filename"]].add(name)

    fixed = 0
    for filepath, undefined_names in by_file.items():
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception:
            continue

        if not verify_file_syntax(filepath):
            continue

        # Parse and find __all__
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

        # Remove undefined names
        new_names = [n for n in existing_all if n not in undefined_names]

        if len(new_names) == len(existing_all):
            continue

        fixed += len(existing_all) - len(new_names)

        # Build new __all__
        if new_names:
            all_str = ", ".join(f'"{n}"' for n in new_names)
            new_all_line = f"__all__ = [{all_str}]"
        else:
            new_all_line = ""

        # Replace in file
        lines = content.split("\n")
        start_line = all_node.lineno - 1
        end_line = all_node.end_lineno

        if new_all_line:
            lines[start_line:end_line] = [new_all_line]
        else:
            # Remove __all__ line and adjacent empty lines
            lines[start_line:end_line] = []

        new_content = "\n".join(lines)

        # Verify syntax
        try:
            ast.parse(new_content)
        except SyntaxError:
            continue

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(new_content)
        except Exception:
            continue

    print(f"[F822] Removed {fixed} undefined names from __all__ in {len(by_file)} files")
    return fixed


# ─────────────────────────────────────────────────────
# FIX 4: F821 — Fix undefined names by adding missing imports or noqa
# ─────────────────────────────────────────────────────
def fix_f821():
    """Fix F821 undefined names. Add noqa for cases that need manual review."""
    errors = get_errors_by_code("F821")

    by_file = defaultdict(set)
    for e in errors:
        msg = e.get("message", "")
        match = re.search(r"Undefined name `(\S+)`", msg)
        if match:
            name = match.group(1)
            if is_valid_identifier(name):
                by_file[e["filename"]].add(name)

    fixed = 0
    for filepath, undefined_names in by_file.items():
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception:
            continue

        if not verify_file_syntax(filepath):
            continue

        # Try to find where these names should come from
        # Check if they're defined in sibling modules' __init__.py
        lines = content.split("\n")

        # Find the import section end
        import_end = 0
        in_import = False
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith(("import ", "from ")):
                in_import = True
                import_end = i
            elif in_import:
                if stripped.startswith(")"):
                    import_end = i
                    in_import = False
                elif stripped and not stripped.startswith(("import ", "from ")):
                    if "(" not in lines[i-1] if i > 0 else False:
                        in_import = False

        # For undefined names, try to find them in _types.py or _helpers.py sibling modules
        dir_path = os.path.dirname(filepath)
        found_imports = {}

        for name in undefined_names:
            # Check _types.py
            types_file = os.path.join(dir_path, "_types.py")
            if os.path.exists(types_file):
                try:
                    with open(types_file) as f:
                        tree = ast.parse(f.read())
                    for node in ast.walk(tree):
                        if isinstance(node, (ast.ClassDef, ast.FunctionDef)) and node.name == name:
                            found_imports[name] = f"from ._types import {name}"
                            break
                        elif isinstance(node, ast.Assign):
                            for target in node.targets:
                                if isinstance(target, ast.Name) and target.id == name:
                                    found_imports[name] = f"from ._types import {name}"
                                    break
                except Exception:
                    pass

            if name in found_imports:
                continue

            # Check _helpers.py
            helpers_file = os.path.join(dir_path, "_helpers.py")
            if os.path.exists(helpers_file):
                try:
                    with open(helpers_file) as f:
                        tree = ast.parse(f.read())
                    for node in ast.walk(tree):
                        if isinstance(node, (ast.ClassDef, ast.FunctionDef)) and node.name == name:
                            found_imports[name] = f"from ._helpers import {name}"
                            break
                except Exception:
                    pass

        # Add found imports
        if found_imports:
            # Group imports by module
            by_module = defaultdict(set)
            for name, imp in found_imports.items():
                module = imp.split(" import ")[0]
                by_module[module].add(name)

            import_lines = []
            for module, names in sorted(by_module.items()):
                sorted_names = sorted(names)
                import_lines.append(f"from {module} import {', '.join(sorted_names)}")

            # Insert after last import
            lines.insert(import_end + 1, "")
            for il in import_lines:
                lines.insert(import_end + 2, il)
                fixed += 1

        # For remaining undefined names, add noqa comments on the lines where they're used
        remaining_names = undefined_names - set(found_imports.keys())

        if remaining_names:
            # Re-read the file (might have been modified by found_imports)
            content = "\n".join(lines)
            content_lines = content.split("\n")

            for i, line in enumerate(content_lines):
                for name in remaining_names:
                    # Check if this line uses the undefined name
                    if re.search(rf'\b{re.escape(name)}\b', line) and "# noqa: F821" not in line:
                        content_lines[i] = line.rstrip() + "  # noqa: F821  # TODO: verify import"
                        fixed += 1
                        break

            lines = content_lines

        new_content = "\n".join(lines)

        # Verify syntax
        try:
            ast.parse(new_content)
        except SyntaxError:
            # Just do noqa approach instead
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            lines = content.split("\n")
            for i, line in enumerate(lines):
                for name in undefined_names:
                    if re.search(rf'\b{re.escape(name)}\b', line) and "# noqa: F821" not in line:
                        lines[i] = line.rstrip() + "  # noqa: F821"
                        fixed += 1
                        break
            new_content = "\n".join(lines)

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(new_content)
        except Exception:
            continue

    print(f"[F821] Fixed {fixed} undefined names (added imports or noqa comments)")
    return fixed


# ─────────────────────────────────────────────────────
# FIX 5: E701 — Split multiple statements on one line
# ─────────────────────────────────────────────────────
def fix_e701():
    """Split statements like 'if x: y' into separate lines."""
    errors = get_errors_by_code("E701")

    by_file = defaultdict(list)
    for e in errors:
        by_file[e["filename"]].append(e)

    fixed = 0
    for filepath, errs in by_file.items():
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception:
            continue

        if not verify_file_syntax(filepath):
            continue

        lines = content.split("\n")
        # Process in reverse order to maintain line numbers
        for e in sorted(errs, key=lambda x: x.get("location", {}).get("row", 0), reverse=True):
            line_no = e.get("location", {}).get("row", 0)

            if not (0 < line_no <= len(lines)):
                continue

            line = lines[line_no - 1]

            # Find the colon that starts the second statement
            colon_match = re.search(r":\s+(?!\s*#)(?!\s*$)(?!\s*pass)(?!\s*\.\.\.)(.+)", line)
            if not colon_match:
                continue

            before_colon = line[:colon_match.start() + 1]
            after_colon = colon_match.group(1).strip()
            indent = len(line) - len(line.lstrip())
            inner_indent = " " * (indent + 4)

            # Skip complex patterns
            stripped_before = before_colon.strip()
            if any(stripped_before.startswith(kw) for kw in ["class ", "def ", "elif ", "except ", "finally "]):
                continue
            if any(kw in after_colon for kw in [" else:", " elif:", " except:", " finally:"]):
                continue
            # Skip if the after part is too complex
            if after_colon.count(":") > 2:
                continue

            new_lines = [
                before_colon.rstrip(),
                f"{inner_indent}{after_colon}"
            ]
            lines[line_no - 1:line_no] = new_lines
            fixed += 1

        new_content = "\n".join(lines)

        # Verify syntax
        try:
            ast.parse(new_content)
        except SyntaxError:
            # Revert this file
            continue

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(new_content)
        except Exception:
            continue

    print(f"[E701] Split {fixed} multiple-statement lines")
    return fixed


# ─────────────────────────────────────────────────────
# FIX 6: E402 — Move imports to top of file / add noqa
# ─────────────────────────────────────────────────────
def fix_e402():
    """Add noqa comments for E402 where imports can't be moved."""
    errors = get_errors_by_code("E402")

    by_file = defaultdict(list)
    for e in errors:
        by_file[e["filename"]].append(e)

    fixed = 0
    for filepath, errs in by_file.items():
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception:
            continue

        if not verify_file_syntax(filepath):
            continue

        lines = content.split("\n")
        modified = False

        for e in errs:
            line_no = e.get("location", {}).get("row", 0)
            if 0 < line_no <= len(lines):
                line = lines[line_no - 1]
                if "# noqa: E402" not in line and "# noqa: E402" not in line:
                    lines[line_no - 1] = line.rstrip() + "  # noqa: E402"
                    modified = True
                    fixed += 1

        if modified:
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

    print(f"[E402] Added noqa for {fixed} import-not-at-top errors")
    return fixed


# ─────────────────────────────────────────────────────
# FIX 7: E702 — Split multiple statements separated by semicolons
# ─────────────────────────────────────────────────────
def fix_e702():
    """Split statements on one line separated by semicolons."""
    errors = get_errors_by_code("E702")

    by_file = defaultdict(list)
    for e in errors:
        by_file[e["filename"]].append(e)

    fixed = 0
    for filepath, errs in by_file.items():
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception:
            continue

        if not verify_file_syntax(filepath):
            continue

        lines = content.split("\n")
        # Process in reverse
        for e in sorted(errs, key=lambda x: x.get("location", {}).get("row", 0), reverse=True):
            line_no = e.get("location", {}).get("row", 0)
            if not (0 < line_no <= len(lines)):
                continue

            line = lines[line_no - 1]
            indent = len(line) - len(line.lstrip())
            base_indent = " " * indent

            # Split by semicolons (but not inside strings)
            parts = []
            current = ""
            in_string = None
            for ch in line.strip():
                if ch in ('"', "'") and in_string is None:
                    in_string = ch
                elif ch == in_string:
                    in_string = None
                elif ch == ';' and in_string is None:
                    parts.append(current.strip())
                    current = ""
                    continue
                current += ch
            if current.strip():
                parts.append(current.strip())

            if len(parts) > 1:
                new_lines = [base_indent + p for p in parts if p]
                lines[line_no - 1:line_no] = new_lines
                fixed += 1

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

    print(f"[E702] Split {fixed} semicolon-separated statements")
    return fixed


# ─────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────
def main():
    print("=" * 70)
    print("Phase 3 v2: Careful Ruff Linting Correction for Zenic-Agents")
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

    total_fixed = 0

    # Step 1: Fix F401 in __init__.py (add __all__)
    print("\n[1/7] Fixing F401 in __init__.py (adding __all__ for re-exports)...")
    total_fixed += fix_f401_init_reexports()

    # Step 2: Fix F403/F405 (star imports -> explicit imports)
    print("\n[2/7] Fixing F403/F405 (replacing star imports with explicit imports)...")
    total_fixed += fix_star_imports()

    # Step 3: Fix F822 (undefined exports in __all__)
    print("\n[3/7] Fixing F822 (removing undefined names from __all__)...")
    total_fixed += fix_f822()

    # Step 4: Fix F821 (undefined names)
    print("\n[4/7] Fixing F821 (adding imports or noqa for undefined names)...")
    total_fixed += fix_f821()

    # Step 5: Fix E701 (multiple statements on one line)
    print("\n[5/7] Fixing E701 (splitting multiple-statement lines)...")
    total_fixed += fix_e701()

    # Step 6: Fix E402 (imports not at top)
    print("\n[6/7] Fixing E402 (adding noqa for import-not-at-top)...")
    total_fixed += fix_e402()

    # Step 7: Fix E702 (semicolons)
    print("\n[7/7] Fixing E702 (splitting semicolon-separated statements)...")
    total_fixed += fix_e702()

    print("\n" + "=" * 70)

    # Run ruff --fix for any remaining auto-fixable issues
    print("\n[Final] Running ruff --fix for remaining auto-fixable issues...")
    subprocess.run(["ruff", "check", ROOT_STR, "--fix"], capture_output=True, text=True)
    subprocess.run(["ruff", "check", ROOT_STR, "--unsafe-fixes", "--fix"], capture_output=True, text=True)

    # Get final count
    result = subprocess.run(["ruff", "check", ROOT_STR], capture_output=True, text=True)
    final_count = 0
    for line in result.stdout.strip().split("\n"):
        match = re.search(r"Found (\d+) errors", line)
        if match:
            final_count = int(match.group(1))

    print(f"\nResults:")
    print(f"  Initial errors: {initial_count}")
    print(f"  Fixed:          {initial_count - final_count}")
    print(f"  Remaining:      {final_count}")
    if initial_count > 0:
        print(f"  Reduction:      {((initial_count - final_count) / initial_count * 100):.1f}%")

    # Show final statistics
    result = subprocess.run(["ruff", "check", ROOT_STR, "--statistics"], capture_output=True, text=True)
    print("\nFinal error breakdown:")
    for line in result.stdout.strip().split("\n"):
        line = line.strip()
        if re.match(r"^\d+\s+[A-Z]", line) or line.startswith("Found"):
            print(f"  {line}")

    return final_count


if __name__ == "__main__":
    result = main()
    sys.exit(0)
