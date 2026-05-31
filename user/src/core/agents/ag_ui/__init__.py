"""
AG-UI Protocol — Agent-Generated UI

Enables Zenic agents to dynamically generate UI components
on the frontend. Supports forms, dashboards, charts, tables,
and HITL approval cards.
"""

from ._emitter import AGUIEmitter
from ._types import (
    AGUIComponentSpec,
    AGUIComponentType,
    AGUIEventPayload,
    AGUIFormField,
    AGUIChartData,
    AGUITableColumn,
    AGUIMetricCard,
    AGUIApprovalProps,
)

__all__ = [
    "AGUIEmitter",
    "AGUIComponentSpec",
    "AGUIComponentType",
    "AGUIEventPayload",
    "AGUIFormField",
    "AGUIChartData",
    "AGUITableColumn",
    "AGUIMetricCard",
    "AGUIApprovalProps",
]
