"""
ProjectGenMixin — Stub for removed project generation feature.

Project generation was removed in v3.0.0 (code generation is not part
of the assistant-agent concept). This mixin preserves the class hierarchy
without providing any project generation functionality.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class ProjectGenMixin:
    """Stub mixin: project generation was removed in v3.0.0.

    All methods return empty/None results, preserving the AutomationEngine
    class hierarchy without breaking imports.
    """

    def generate_project(self, description: str, **kwargs) -> dict[str, Any] | None:
        """Removed: project generation is not part of assistant-agent."""
        logger.warning("ProjectGenMixin.generate_project: feature removed in v3.0.0")
        return None

    def list_project_templates(self) -> list[dict[str, Any]]:
        """Removed: project generation is not part of assistant-agent."""
        logger.warning("ProjectGenMixin.list_project_templates: feature removed in v3.0.0")
        return []

    def validate_project_spec(self, spec: dict[str, Any]) -> dict[str, Any]:
        """Removed: project generation is not part of assistant-agent."""
        logger.warning("ProjectGenMixin.validate_project_spec: feature removed in v3.0.0")
        return {"valid": False, "errors": ["Project generation removed in v3.0.0"]}
