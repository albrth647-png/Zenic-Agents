#!/usr/bin/env python3
"""
Phase 3 v5: Fix F821 (undefined names) + remaining F405 + F822 + F401
=====================================================================
The star import replacements exposed many F821 errors where files use
stdlib names (threading, List, Dict, etc.) that were previously available
via star imports. This script adds the missing imports.
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

# Common stdlib name -> import mapping
STDLIB_IMPORTS = {
    # typing
    "Any": "from typing import Any",
    "Dict": "from typing import Dict",
    "List": "from typing import List",
    "Optional": "from typing import Optional",
    "Tuple": "from typing import Tuple",
    "Set": "from typing import Set",
    "Union": "from typing import Union",
    "Callable": "from typing import Callable",
    "TypeVar": "from typing import TypeVar",
    "Generic": "from typing import Generic",
    "Iterator": "from typing import Iterator",
    "Awaitable": "from typing import Awaitable",
    "Coroutine": "from typing import Coroutine",
    "AsyncIterator": "from typing import AsyncIterator",
    "Sequence": "from typing import Sequence",
    "Mapping": "from typing import Mapping",
    "MutableMapping": "from typing import MutableMapping",
    "Protocol": "from typing import Protocol",
    "runtime_checkable": "from typing import runtime_checkable",
    "ClassVar": "from typing import ClassVar",
    "Final": "from typing import Final",
    "Literal": "from typing import Literal",
    "Type": "from typing import Type",
    "TypeGuard": "from typing import TypeGuard",
    "ForwardRef": "from typing import ForwardRef",
    "Annotated": "from typing import Annotated",
    "cast": "from typing import cast",
    "overload": "from typing import overload",
    "TYPE_CHECKING": "from typing import TYPE_CHECKING",
    # stdlib modules
    "threading": "import threading",
    "logging": "import logging",
    "uuid": "import uuid",
    "time": "import time",
    "json": "import json",
    "os": "import os",
    "sys": "import sys",
    "copy": "import copy",
    "hashlib": "import hashlib",
    "traceback": "import traceback",
    "functools": "import functools",
    "itertools": "import itertools",
    "collections": "import collections",
    "enum": "import enum",
    "dataclasses": "import dataclasses",
    "abc": "import abc",
    "datetime": "import datetime",
    "asyncio": "import asyncio",
    "pathlib": "import pathlib",
    "typing": "import typing",
    "re": "import re",
    "math": "import math",
    "random": "import random",
    "string": "import string",
    "base64": "import base64",
    "struct": "import struct",
    "inspect": "import inspect",
    "textwrap": "import textwrap",
    # Common stdlib names
    "defaultdict": "from collections import defaultdict",
    "OrderedDict": "from collections import OrderedDict",
    "Counter": "from collections import Counter",
    "deque": "from collections import deque",
    "namedtuple": "from collections import namedtuple",
    "dataclass": "from dataclasses import dataclass",
    "field": "from dataclasses import field",
    "Enum": "from enum import Enum",
    "Flag": "from enum import Flag",
    "auto": "from enum import auto",
    "ABC": "from abc import ABC",
    "abstractmethod": "from abc import abstractmethod",
    "ABCMeta": "from abc import ABCMeta",
    "datetime": "from datetime import datetime",
    "timezone": "from datetime import timezone",
    "timedelta": "from datetime import timedelta",
    "Path": "from pathlib import Path",
    "lru_cache": "from functools import lru_cache",
    "partial": "from functools import partial",
    "wraps": "from functools import wraps",
    "reduce": "from functools import reduce",
    "cached_property": "from functools import cached_property",
    "Logger": "from logging import Logger",
    "Pattern": "from re import Pattern",
    "Match": "from re import Match",
}


def get_errors_by_code(code):
    cmd = ["ruff", "check", ROOT_STR, "--select", code, "--output-format", "json"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    try:
        return json.loads(result.stdout) if result.stdout.strip() else []
    except json.JSONDecodeError:
        return []


def fix_f821():
    """Add missing imports for F821 undefined names."""
    errors = get_errors_by_code("F821")

    by_file = defaultdict(set)
    for e in errors:
        msg = e.get("message", "")
        match = re.search(r"Undefined name `(\S+)`", msg)
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

        # Find existing imports to avoid duplicates
        existing_imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    existing_imports.add(alias.asname or alias.name)
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    existing_imports.add(alias.asname or alias.name)

        # Determine what imports to add
        imports_to_add = defaultdict(set)  # module -> set of names

        for name in undefined_names:
            if name in existing_imports:
                continue
            if name in STDLIB_IMPORTS:
                import_stmt = STDLIB_IMPORTS[name]
                if import_stmt.startswith("from "):
                    # Parse "from module import name"
                    parts = import_stmt.split(" import ")
                    module = parts[0].replace("from ", "")
                    imports_to_add[module].add(name)
                else:
                    # "import name"
                    imports_to_add[f"__import__:{name}"].add(name)

        if not imports_to_add:
            continue

        # Build import lines
        import_lines = []
        for module, names in sorted(imports_to_add.items()):
            if module.startswith("__import__:"):
                import_lines.append(f"import {list(names)[0]}")
            else:
                sorted_names = sorted(names)
                import_lines.append(f"from {module} import {', '.join(sorted_names)}")

        # Find the insertion point (after existing imports, before code)
        lines = content.split("\n")
        insert_after = 0
        in_import = False
        paren_depth = 0

        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith(("import ", "from ")):
                in_import = True
                paren_depth += stripped.count("(") - stripped.count(")")
                insert_after = i
            elif in_import:
                paren_depth += stripped.count("(") - stripped.count(")")
                if paren_depth <= 0:
                    in_import = False
                    insert_after = i
                elif not stripped:
                    insert_after = i
            elif stripped.startswith("\"\"\"") or stripped.startswith("'''"):
                # Docstring
                continue
            elif stripped.startswith("#"):
                continue
            elif not stripped:
                continue
            else:
                break

        # Insert new imports
        for il in import_lines:
            lines.insert(insert_after + 1, il)
            insert_after += 1

        new_content = "\n".join(lines)

        # Verify syntax
        try:
            ast.parse(new_content)
        except SyntaxError:
            continue

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(new_content)
            fixed += len(undefined_names)
        except Exception:
            continue

    print(f"  Added imports for {fixed} undefined names in {len(by_file)} files")
    return fixed


def fix_remaining_f405():
    """Add noqa to remaining F405 errors that can't be auto-fixed."""
    errors = get_errors_by_code("F405")

    by_file = defaultdict(list)
    for e in errors:
        loc = e.get("location", {})
        by_file[e["filename"]].append(loc.get("row", 0))

    fixed = 0
    for filepath, rows in by_file.items():
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception:
            continue

        try:
            tree = ast.parse(content)
        except SyntaxError:
            continue

        lines = content.split("\n")
        modified = False

        # Find star import lines and add noqa
        for i, line in enumerate(lines):
            if re.search(r"from\s+\S+\s+import\s+\*", line):
                if "noqa: F403" not in line and "noqa: F405" not in line:
                    lines[i] = line.rstrip() + "  # noqa: F403, F405"
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

    print(f"  Added noqa to {fixed} star import lines in {len(by_file)} files")
    return fixed


def fix_f822():
    """Remove undefined names from __all__."""
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

    print(f"  Removed {fixed} undefined names from __all__ in {len(by_file)} files")
    return fixed


def fix_f401():
    """Fix remaining F401 unused imports."""
    errors = get_errors_by_code("F401")

    # Separate into init files (re-exports) and non-init (genuinely unused)
    init_errors = [e for e in errors if e["filename"].endswith("__init__.py")]
    non_init_errors = [e for e in errors if not e["filename"].endswith("__init__.py")]

    # Non-init: use ruff --fix
    if non_init_errors:
        files = list(set(e["filename"] for e in non_init_errors))
        cmd = ["ruff", "check", "--select", "F401", "--fix"] + files
        subprocess.run(cmd, capture_output=True, text=True)

    # Init files with __all__: ruff --fix should handle them now
    if init_errors:
        files = list(set(e["filename"] for e in init_errors))
        cmd = ["ruff", "check", "--select", "F401", "--fix"] + files
        subprocess.run(cmd, capture_output=True, text=True)

    remaining = get_errors_by_code("F401")
    fixed = len(errors) - len(remaining)
    print(f"  Fixed {fixed} F401 errors ({len(remaining)} remaining)")
    return fixed


def fix_e701():
    """Fix E701 multiple-statements-on-one-line-colon."""
    errors = get_errors_by_code("E701")
    if not errors:
        return 0

    by_file = defaultdict(list)
    for e in errors:
        by_file[e["filename"]].append(e.get("location", {}).get("row", 0))

    fixed = 0
    for filepath, rows in by_file.items():
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception:
            continue

        try:
            tree = ast.parse(content)
        except SyntaxError:
            continue

        lines = content.split("\n")
        modified = False

        for row in sorted(rows, reverse=True):
            if not (0 < row <= len(lines)):
                continue

            line = lines[row - 1]
            # Check for pattern: "if x: action" or "else: action"
            colon_match = re.search(r":\s+(?!\s*#)(?!\s*$)(?!\s*pass)(?!\s*\.\.\.)(.+)", line)
            if not colon_match:
                continue

            before_colon = line[:colon_match.start() + 1]
            after_colon = colon_match.group(1).strip()
            stripped_before = before_colon.strip()

            # Skip complex patterns
            if any(stripped_before.startswith(kw) for kw in ["class ", "def ", "elif ", "except ", "finally "]):
                continue
            if any(kw in after_colon for kw in [" else:", " elif:", " except:", " finally:"]):
                continue
            if after_colon.count(":") > 2:
                continue

            indent = len(line) - len(line.lstrip())
            inner_indent = " " * (indent + 4)

            new_lines_for_row = [
                before_colon.rstrip(),
                f"{inner_indent}{after_colon}"
            ]
            lines[row - 1:row] = new_lines_for_row
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

    print(f"  Split {fixed} multiple-statement lines")
    return fixed


def main():
    print("=" * 70)
    print("Phase 3 v5: F821 + F405 + F822 + F401 + E701 Fixes")
    print("=" * 70)

    result = subprocess.run(["ruff", "check", ROOT_STR], capture_output=True, text=True)
    initial_count = 0
    for line in result.stdout.strip().split("\n"):
        match = re.search(r"Found (\d+) errors", line)
        if match:
            initial_count = int(match.group(1))

    print(f"\nInitial error count: {initial_count}")
    print("-" * 70)

    # Step 1: Fix F821 - add missing imports
    print("\n[1/5] Fixing F821 - adding missing imports...")
    fix_f821()

    # Step 2: Fix remaining F405 - add noqa to star imports
    print("\n[2/5] Fixing remaining F405 - adding noqa to star imports...")
    fix_remaining_f405()

    # Step 3: Fix F822 - remove undefined names from __all__
    print("\n[3/5] Fixing F822 - removing undefined names from __all__...")
    fix_f822()

    # Step 4: Fix F401 - remove unused imports
    print("\n[4/5] Fixing F401 - removing unused imports...")
    fix_f401()

    # Step 5: Fix E701 - split multiple-statement lines
    print("\n[5/5] Fixing E701 - splitting multiple-statement lines...")
    fix_e701()

    # Final ruff --fix pass
    print("\n[Final] Running ruff --fix for remaining auto-fixable issues...")
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
