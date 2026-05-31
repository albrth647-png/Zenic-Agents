"""
Native extension loader — DELEGATES to canonical _bindings module.

H-84 FIX: This file was a duplicate of ``_bindings.py``. Both tried
to import ``_zenic_native`` independently, which could cause:
  1. Double import attempt of the Rust extension
  2. Inconsistent HAS_NATIVE flags if one succeeds and the other fails
  3. Maintenance burden (any new Rust function must be added in two places)

Now this module simply re-exports everything from the canonical
``src.core.native._bindings``, ensuring a single source of truth.
"""

