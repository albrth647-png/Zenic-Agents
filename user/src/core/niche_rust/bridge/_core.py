"""
Niche Rust Bridge — NicheBridge facade and factory.

Unified facade combining NicheCatalog and NicheTemplate.
"""

from __future__ import annotations

import logging
from typing import Any

from ._catalog import NicheCatalog
from ._native import NATIVE_AVAILABLE
from ._template import NicheTemplate

logger = logging.getLogger(__name__)


class NicheBridge:
    """Unified facade for the Rust niche system.

    Combines NicheCatalog and NicheTemplate into a single
    interface for convenience.

    Usage::

        bridge = NicheBridge()

        # List all niches
        niches = bridge.list_niches()

        # Generate a template
        template = bridge.create_template("telemedicine")

        # Fill fields
        bridge.fill_field(template, "business_identity", "business_name", "My Clinic")

        # Check status
        status = bridge.template_status(template)

        # Get next question for user
        next_question = bridge.next_missing_field(template)
    """

    def __init__(self) -> None:
        self._catalog = NicheCatalog()
        self._template = NicheTemplate()

    # ── Catalog Operations ────────────────────────────────

    def list_niches(self) -> list[Any]:
        """List all available niches from the catalog."""
        return self._catalog.get_all()

    def list_niche_ids(self) -> list[str]:
        """List all niche_id strings."""
        return self._catalog.ids()

    def list_categories(self) -> list[str]:
        """List all niche categories."""
        return self._catalog.categories()

    def get_niche(self, niche_id: str) -> Any | None:
        """Get a specific niche by ID."""
        return self._catalog.get_by_id(niche_id)

    def search_niches(self, query: str) -> list[Any]:
        """Search niches by text."""
        return self._catalog.search(query)

    def niches_by_category(self, category: str) -> list[Any]:
        """Get niches filtered by category."""
        return self._catalog.get_by_category(category)

    def niche_count(self) -> int:
        """Get total niche count."""
        return self._catalog.count()

    # ── Template Operations ───────────────────────────────

    def create_template(self, niche_id: str) -> dict[str, Any] | None:
        """Generate a YAML template from a niche_id."""
        return self._template.generate(niche_id)

    def validate_template(self, template_dict: dict[str, Any]) -> dict[str, Any]:
        """Validate a template for completeness."""
        return self._template.validate(template_dict)

    def fill_field(
        self,
        template_dict: dict[str, Any],
        section_id: str,
        field_name: str,
        value: Any,
    ) -> bool:
        """Fill a field in the template."""
        return self._template.set_field(
            template_dict, section_id, field_name, value
        )

    def template_status(self, template_dict: dict[str, Any]) -> dict[str, Any]:
        """Get validation status of a template."""
        return self._template.validate(template_dict)

    def next_missing_field(self, template_dict: dict[str, Any]) -> dict[str, Any] | None:
        """Get the next missing required field for the interactive agent."""
        missing = self._template.missing_fields(template_dict)
        if not missing:
            return None
        return missing[0]

    def all_missing_fields(self, template_dict: dict[str, Any]) -> list[dict[str, Any]]:
        """Get all missing required fields."""
        return self._template.missing_fields(template_dict)

    def template_to_yaml(self, template_dict: dict[str, Any]) -> str | None:
        """Export template to YAML string."""
        return self._template.to_yaml(template_dict)


# ──────────────────────────────────────────────────────────────
#  Factory Function
# ──────────────────────────────────────────────────────────────

_bridge_instance: NicheBridge | None = None


def get_bridge() -> NicheBridge | None:
    """Get or create the singleton NicheBridge instance.

    Returns None if the Rust extension is not available.

    Usage::

        from src.core.niche_rust.bridge import get_bridge
        bridge = get_bridge()
        if bridge is not None:
            niches = bridge.list_niches()
    """
    global _bridge_instance
    if not NATIVE_AVAILABLE:
        return None
    if _bridge_instance is None:
        _bridge_instance = NicheBridge()
    return _bridge_instance
