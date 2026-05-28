"""
Zenic-Agents — Onboarding Renderers Package (Phase 10)

Rich-based rendering components for the onboarding TUI:
welcome screens, status displays, and progress indicators.

Design Patterns:
  - Strategy: different renderers for different contexts
  - Facade: simplified rendering API
"""

from .progress import ProgressRenderer, StepIndicator, render_progress
from .status_display import StatusRenderer, render_status_panel
from .welcome import WelcomeRenderer, render_welcome

__all__ = [
    "ProgressRenderer",
    "StatusRenderer",
    "StepIndicator",
    "WelcomeRenderer",
    "render_progress",
    "render_status_panel",
    "render_welcome",
]
