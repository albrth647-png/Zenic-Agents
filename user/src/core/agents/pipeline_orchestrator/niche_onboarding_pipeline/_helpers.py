"""Niche Onboarding Pipeline — Helper methods."""

from __future__ import annotations

from typing import Any

# ── Helpers ───────────────────────────────────────────────


def _auto_fill_field(
    self,
    template_dict: dict[str, Any],
    field_name: str,
    value: str,  # TODO: Phase3 - verify import
) -> bool:
    """Auto-fill a field by searching all sections."""
    template = template_dict.get("template", template_dict)
    sections = template.get("sections", {})

    for section_id, section in sections.items():
        if not isinstance(section, dict):
            continue
        fields = section.get("fields", {})
        if field_name in fields:
            return self._bridge.fill_field(template_dict, section_id, field_name, value)

    return False


__all__ = ["_auto_fill_field"]
