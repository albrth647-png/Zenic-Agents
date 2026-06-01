"""
AG-UI Protocol — Agent-Generated UI

Enables Zenic agents to dynamically generate UI components
on the frontend. Supports forms, dashboards, charts, tables,
and HITL approval cards.
"""

from ._emitter import AGUIEmitter
from ._types import (
    AGUIApprovalProps,
    AGUIChartData,
    AGUIComponentSpec,
    AGUIComponentType,
    AGUIEventPayload,
    AGUIFormField,
    AGUIMetricCard,
    AGUITableColumn,
)

__all__ = [
    "AGUIApprovalProps",
    "AGUIChartData",
    "AGUIComponentSpec",
    "AGUIComponentType",
    "AGUIEmitter",
    "AGUIEventPayload",
    "AGUIFormField",
    "AGUIMetricCard",
    "AGUITableColumn",
]
