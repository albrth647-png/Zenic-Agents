"""
Shared imports, constants, and dataclasses for thinking_parts sub-modules.
"""

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# === Thinking Configuration ===
MAX_THINKING_TOKENS = 500
MAX_PLAN_TOKENS = 600
MAX_DECOMPOSE_TOKENS = 400
MAX_EVALUATE_TOKENS = 300
THINKING_TIMEOUT_S = 15.0
CHAIN_MAX_STEPS = 3

# Template types
APP_TEMPLATES = [
    "web_api",
    "crud_dashboard",
    "inventory",
    "invoice_billing",
    "crm",
    "task_manager",
    "email_automation",
    "data_pipeline",
    "report_generator",
    "auth_system",
    "notification_service",
    "file_manager",
    "scheduler",
    "chatbot_service",
]

AUTOMATION_TEMPLATES = [
    "email_sender",
    "data_sync",
    "file_watcher",
    "webhook_handler",
    "scheduled_report",
    "database_backup",
    "api_monitor",
    "social_media_poster",
    "invoice_generator",
    "notification_dispatcher",
]


@dataclass
class GenerationPlan:
    """Plan de generación producido por ThinkingEngine."""

    template_type: str = ""
    modules: list[str] = field(default_factory=list)
    entities: list[dict[str, Any]] = field(default_factory=list)
    endpoints: list[dict[str, str]] = field(default_factory=list)
    automations: list[dict[str, Any]] = field(default_factory=list)
    config_vars: dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    source: str = "fallback"


@dataclass
class ThinkingResult:
    """Resultado de una operación de pensamiento."""

    answer: str = ""
    confidence: float = 0.0
    source: str = "fallback"
    context_used: bool = False
    memory_hits: int = 0
    thinking_time_s: float = 0.0
