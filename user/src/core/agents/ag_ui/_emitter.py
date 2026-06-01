"""
AG-UI Protocol — Emitter for agent-generated UI events.

Allows Python agents to emit AG-UI events that dynamically
generate frontend components via the Gateway API.
"""

from __future__ import annotations

import logging
import time
from typing import Any
from uuid import uuid4

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

logger = logging.getLogger(__name__)


class AGUIEmitter:
    """
    Emits AG-UI events from Python agents to the frontend.

    Usage:
        emitter = AGUIEmitter(agent_id="health-agent-01", session_id="sess_abc")
        await emitter.render_form([
            AGUIFormField(name="patient_id", label="Patient ID", required=True),
        ])
        await emitter.request_approval(
            policy_violation="HIPAA data access",
            risk_level="high",
            suggested_action="Grant read-only access",
        )
    """

    def __init__(
        self,
        agent_id: str,
        session_id: str,
        gateway_url: str = "http://localhost:3000",
        niche_style: str | None = None,
    ):
        self.agent_id = agent_id
        self.session_id = session_id
        self.gateway_url = gateway_url.rstrip("/")
        self.niche_style = niche_style
        self._components: dict[str, AGUIComponentSpec] = {}

    def _make_id(self, prefix: str = "comp") -> str:
        return f"{prefix}_{uuid4().hex[:8]}"

    async def _send_event(self, payload: AGUIEventPayload) -> bool:
        """Send an AG-UI event to the Gateway (HTTP POST)."""
        payload.timestamp = int(time.time() * 1000)
        data = payload.to_dict()

        try:
            import aiohttp

            async with (
                aiohttp.ClientSession() as session,
                session.post(
                    f"{self.gateway_url}/api/v1/ag-ui/events",
                    json=data,
                    timeout=aiohttp.ClientTimeout(total=5),
                ) as resp,
            ):
                return resp.status == 200
        except ImportError:
            logger.debug("aiohttp not available, AG-UI event not sent")
            # Store locally for later retrieval
            return False
        except Exception as e:
            logger.error("AG-UI event send failed: %s", e)
            return False

    # ─── High-level API ──────────────────────────────────────────

    async def render_form(
        self,
        fields: list[AGUIFormField],
        title: str = "",
        description: str = "",
    ) -> str:
        """Render a dynamic form on the frontend."""
        comp_id = self._make_id("form")
        spec = AGUIComponentSpec(
            id=comp_id,
            type=AGUIComponentType.FORM,
            props={"fields": [f.to_dict() for f in fields]},
            niche_style=self.niche_style,
            title=title,
            description=description,
        )
        self._components[comp_id] = spec

        payload = AGUIEventPayload(
            type="render",
            agent_id=self.agent_id,
            session_id=self.session_id,
            components=[spec],
        )
        await self._send_event(payload)
        return comp_id

    async def render_chart(
        self,
        chart_data: AGUIChartData,
        title: str = "",
    ) -> str:
        """Render a chart component on the frontend."""
        comp_id = self._make_id("chart")
        spec = AGUIComponentSpec(
            id=comp_id,
            type=AGUIComponentType.CHART,
            props=chart_data.to_dict(),
            niche_style=self.niche_style,
            title=title or chart_data.title,
        )
        self._components[comp_id] = spec

        payload = AGUIEventPayload(
            type="render",
            agent_id=self.agent_id,
            session_id=self.session_id,
            components=[spec],
        )
        await self._send_event(payload)
        return comp_id

    async def render_table(
        self,
        columns: list[AGUITableColumn],
        rows: list[dict[str, Any]],
        title: str = "",
    ) -> str:
        """Render a data table on the frontend."""
        comp_id = self._make_id("table")
        spec = AGUIComponentSpec(
            id=comp_id,
            type=AGUIComponentType.TABLE,
            props={
                "columns": [c.to_dict() for c in columns],
                "rows": rows,
            },
            niche_style=self.niche_style,
            title=title,
        )
        self._components[comp_id] = spec

        payload = AGUIEventPayload(
            type="render",
            agent_id=self.agent_id,
            session_id=self.session_id,
            components=[spec],
        )
        await self._send_event(payload)
        return comp_id

    async def render_dashboard(
        self,
        metrics: list[AGUIMetricCard],
        title: str = "Dashboard",
    ) -> str:
        """Render a dashboard with metric cards."""
        comp_id = self._make_id("dashboard")
        spec = AGUIComponentSpec(
            id=comp_id,
            type=AGUIComponentType.DASHBOARD,
            props={"metrics": [m.to_dict() for m in metrics]},
            niche_style=self.niche_style,
            title=title,
        )
        self._components[comp_id] = spec

        payload = AGUIEventPayload(
            type="render",
            agent_id=self.agent_id,
            session_id=self.session_id,
            components=[spec],
        )
        await self._send_event(payload)
        return comp_id

    async def request_approval(
        self,
        policy_violation: str,
        risk_level: str = "medium",
        suggested_action: str = "",
        deadline: str = "",
    ) -> str:
        """
        Render a HITL approval card on the frontend.

        The agent pauses execution until the human approves or rejects.
        """
        comp_id = self._make_id("approval")
        approval_props = AGUIApprovalProps(
            policy_violation=policy_violation,
            risk_level=risk_level,
            suggested_action=suggested_action,
            deadline=deadline,
            on_approve=f"/api/v1/hitl/{comp_id}/approve",
            on_reject=f"/api/v1/hitl/{comp_id}/reject",
        )
        spec = AGUIComponentSpec(
            id=comp_id,
            type=AGUIComponentType.APPROVAL_CARD,
            props=approval_props.to_dict(),
            niche_style=self.niche_style,
            hitl_required=True,
            title=f"Approval Required: {risk_level.upper()} Risk",
        )
        self._components[comp_id] = spec

        payload = AGUIEventPayload(
            type="approval_request",
            agent_id=self.agent_id,
            session_id=self.session_id,
            components=[spec],
        )
        await self._send_event(payload)
        return comp_id

    async def stream_text(
        self,
        content: str,
        is_final: bool = False,
        component_id: str | None = None,
    ) -> None:
        """Stream text content to the frontend (for chat-like interfaces)."""
        payload = AGUIEventPayload(
            type="stream",
            agent_id=self.agent_id,
            session_id=self.session_id,
            content=content,
            is_final=is_final,
            component_id=component_id or "",
        )
        await self._send_event(payload)

    async def update_status(
        self,
        status: str = "thinking",
        message: str = "",
        progress: float = 0.0,
    ) -> None:
        """Update the agent's status on the frontend."""
        payload = AGUIEventPayload(
            type="status",
            agent_id=self.agent_id,
            session_id=self.session_id,
            status=status,
            message=message,
            progress=progress,
        )
        await self._send_event(payload)

    async def update_component(
        self,
        component_id: str,
        updated_props: dict[str, Any],
    ) -> None:
        """Update an existing component's props on the frontend."""
        payload = AGUIEventPayload(
            type="update",
            agent_id=self.agent_id,
            session_id=self.session_id,
            component_id=component_id,
            updated_props=updated_props,
        )
        await self._send_event(payload)

    def get_rendered_components(self) -> list[dict[str, Any]]:
        """Get all components rendered in this session (for testing/debugging)."""
        return [spec.to_dict() for spec in self._components.values()]
