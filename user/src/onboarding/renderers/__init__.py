"""
Zenic-Agents — Onboarding Renderers Package (Phase 10)

Rich-based rendering components for the onboarding TUI:
welcome screens, status displays, and progress indicators.

Design Patterns:
  - Strategy: different renderers for different contexts
  - Facade: simplified rendering API
"""

from .welcome import WelcomeRenderer, render_welcome
from .status_display import StatusRenderer, render_status_panel
from .progress import ProgressRenderer, StepIndicator, render_progress

__all__ = [
    "WelcomeRenderer",
    "render_welcome",
    "StatusRenderer",
    "render_status_panel",
    "ProgressRenderer",
    "StepIndicator",
    "render_progress",
]
