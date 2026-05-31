"""
AG-UI Protocol — Type definitions for Agent-Generated UI.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class AGUIComponentType(Enum):
    """Types of UI components that agents can generate."""
    FORM = "form"
    DASHBOARD = "dashboard"
    CHART = "chart"
    TABLE = "table"
    APPROVAL_CARD = "approval-card"
    CODE_BLOCK = "code-block"
    STATUS_INDICATOR = "status-indicator"
    DATA_GRID = "data-grid"
    METRIC_CARD = "metric-card"


@dataclass
class AGUIFormField:
    """Definition of a form field for agent-generated forms."""
    name: str
    label: str
    type: str = "text"  # text, email, number, select, textarea, checkbox, date, password
    required: bool = False
    placeholder: str = ""
    default_value: Any = None
    options: list[dict[str, str]] = field(default_factory=list)
    validation: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        result = {
            "name": self.name,
            "label": self.label,
            "type": self.type,
            "required": self.required,
            "placeholder": self.placeholder,
        }
        if self.default_value is not None:
            result["defaultValue"] = self.default_value
        if self.options:
            result["options"] = self.options
        if self.validation:
            result["validation"] = self.validation
        return result


@dataclass
class AGUIChartData:
    """Chart data specification for agent-generated charts."""
    type: str = "bar"  # line, bar, pie, area
    title: str = ""
    labels: list[str] = field(default_factory=list)
    datasets: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "title": self.title,
            "labels": self.labels,
            "datasets": self.datasets,
        }


@dataclass
class AGUITableColumn:
    """Table column definition for agent-generated tables."""
    key: str
    label: str
    sortable: bool = False
    width: str = ""
    align: str = "left"

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "label": self.label,
            "sortable": self.sortable,
            "width": self.width,
            "align": self.align,
        }


@dataclass
class AGUIMetricCard:
    """Metric card for agent-generated dashboards."""
    title: str
    value: str | int | float
    change: float | None = None
    change_label: str = ""
    icon: str = ""
    color: str = ""

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {"title": self.title, "value": self.value}
        if self.change is not None:
            result["change"] = self.change
        if self.change_label:
            result["changeLabel"] = self.change_label
        if self.icon:
            result["icon"] = self.icon
        if self.color:
            result["color"] = self.color
        return result


@dataclass
class AGUIApprovalProps:
    """HITL Approval card properties."""
    policy_violation: str = ""
    risk_level: str = "medium"  # low, medium, high, critical
    suggested_action: str = ""
    deadline: str = ""
    on_approve: str = ""
    on_reject: str = ""
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "policyViolation": self.policy_violation,
            "riskLevel": self.risk_level,
            "suggestedAction": self.suggested_action,
            "deadline": self.deadline,
            "onApprove": self.on_approve,
            "onReject": self.on_reject,
            "details": self.details,
        }


@dataclass
class AGUIComponentSpec:
    """Specification for an agent-generated UI component."""
    id: str
    type: AGUIComponentType
    props: dict[str, Any] = field(default_factory=dict)
    niche_style: str | None = None
    hitl_required: bool = False
    title: str = ""
    description: str = ""
    priority: int = 0

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "id": self.id,
            "type": self.type.value,
            "props": self.props,
        }
        if self.niche_style:
            result["nicheStyle"] = self.niche_style
        if self.hitl_required:
            result["hitlRequired"] = True
        if self.title:
            result["title"] = self.title
        if self.description:
            result["description"] = self.description
        if self.priority:
            result["priority"] = self.priority
        return result


@dataclass
class AGUIEventPayload:
    """Payload for an AG-UI event sent to the Gateway."""
    type: str  # render, update, action, stream, approval_request, status
    agent_id: str
    session_id: str
    components: list[AGUIComponentSpec] = field(default_factory=list)
    component_id: str = ""
    updated_props: dict[str, Any] = field(default_factory=dict)
    content: str = ""
    is_final: bool = False
    status: str = "thinking"
    message: str = ""
    progress: float = 0.0
    timestamp: int = 0

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "type": self.type,
            "agentId": self.agent_id,
            "sessionId": self.session_id,
            "timestamp": self.timestamp,
        }
        if self.components:
            result["components"] = [c.to_dict() for c in self.components]
        if self.component_id:
            result["componentId"] = self.component_id
        if self.updated_props:
            result["updatedProps"] = self.updated_props
        if self.content:
            result["content"] = self.content
        if self.type == "stream":
            result["isFinal"] = self.is_final
        if self.type == "status":
            result["status"] = self.status
            result["message"] = self.message
            result["progress"] = self.progress
        return result
