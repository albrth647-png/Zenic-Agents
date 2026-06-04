"""
ZENIC-AGENTS — API Dependencies.

FastAPI dependency injection: provides singleton agent instances to route handlers.
All agents are lazily initialized and cached.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure _archived agents are importable
_ARCHIVED = Path(__file__).resolve().parent.parent / "_archived"
if str(_ARCHIVED) not in sys.path:
    sys.path.insert(0, str(_ARCHIVED))

from agents.shared.env import AgentsConfig, get_config
from agents.business.crm_pipeline import CRMPipeline
from agents.business.interactive_data_collector import InteractiveDataCollector
from agents.infrastructure.health_monitor_agent import HealthMonitorAgent
from agents.infrastructure.audit_logger_agent import AuditLoggerAgent


# ── Singleton caches ──────────────────────────────────────────

_crm: CRMPipeline | None = None
_collector: InteractiveDataCollector | None = None
_health_monitor_agent: HealthMonitorAgent | None = None
_audit_logger_agent: AuditLoggerAgent | None = None


def get_crm() -> CRMPipeline:
    """Return the singleton CRMPipeline instance (agent sets its own name)."""
    global _crm
    if _crm is None:
        _crm = CRMPipeline()
    return _crm


def get_collector() -> InteractiveDataCollector:
    """Return the singleton InteractiveDataCollector instance."""
    global _collector
    if _collector is None:
        _collector = InteractiveDataCollector()
    return _collector


def get_health_monitor() -> HealthMonitorAgent:
    """Return the singleton HealthMonitorAgent instance."""
    global _health_monitor_agent
    if _health_monitor_agent is None:
        _health_monitor_agent = HealthMonitorAgent()
    return _health_monitor_agent


def get_audit_logger() -> AuditLoggerAgent:
    """Return the singleton AuditLoggerAgent instance."""
    global _audit_logger_agent
    if _audit_logger_agent is None:
        _audit_logger_agent = AuditLoggerAgent()
    return _audit_logger_agent


def get_app_config() -> AgentsConfig:
    """Return the current agent configuration."""
    return get_config()


def get_plan_manager():
    """Return the singleton PlanManager instance."""
    from .plans import get_plan_manager as _get_pm
    return _get_pm()


def get_channel_manager():
    """Return the singleton ChannelManager instance."""
    from .channels import get_channel_manager as _get_cm
    return _get_cm()
