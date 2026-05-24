"""
ProjectRunner — Types and Constants

RunResult dataclass and timeout constants.
"""

from dataclasses import dataclass, field

# Default timeout for operations
INSTALL_TIMEOUT = 120  # seconds
START_TIMEOUT = 15  # seconds
HEALTH_TIMEOUT = 5  # seconds


@dataclass
class RunResult:
    """Result of a project run attempt."""

    success: bool = False
    project_name: str = ""
    project_dir: str = ""
    venv_dir: str = ""
    port: int = 0
    pid: int | None = None
    health_ok: bool = False
    installed_deps: list[str] = field(default_factory=list)
    failed_deps: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    startup_time_s: float = 0.0


__all__ = ["HEALTH_TIMEOUT", "INSTALL_TIMEOUT", "START_TIMEOUT", "RunResult"]
