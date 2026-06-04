"""
ZENIC-AGENTS — Plan Manager.

Defines subscription plans (FREE/PRO/ENTERPRISE) and enforces limits.
Tracks daily usage per tenant and rejects operations that exceed plan limits.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from . import models

# ── Plan definitions ───────────────────────────────────────────


@dataclass
class PlanDef:
    slug: str
    name: str
    max_clients: int
    max_messages_per_day: int
    max_collector_sessions: int
    features: list[str]


PLANS: dict[str, PlanDef] = {
    "free": PlanDef(
        slug="free",
        name="Free",
        max_clients=1,
        max_messages_per_day=50,
        max_collector_sessions=1,
        features=["Chat básico", "1 cliente", "Soporte email"],
    ),
    "pro": PlanDef(
        slug="pro",
        name="Pro",
        max_clients=50,
        max_messages_per_day=500,
        max_collector_sessions=10,
        features=[
            "Chat personalizado por nicho",
            "50 clientes",
            "Soporte prioritario",
            "Dashboard analytics",
            "Exportación CSV",
        ],
    ),
    "enterprise": PlanDef(
        slug="enterprise",
        name="Enterprise",
        max_clients=9999,
        max_messages_per_day=99999,
        max_collector_sessions=9999,
        features=[
            "Clientes ilimitados",
            "White-label",
            "API key dedicada",
            "Soporte 24/7",
            "Custom integrations",
            "SLA garantizado",
        ],
    ),
}


def get_plan(plan_slug: str) -> PlanDef:
    """Get a plan definition. Falls back to FREE if unknown."""
    return PLANS.get(plan_slug, PLANS["free"])


def list_plans() -> list[dict]:
    """List all available plans."""
    return [
        {
            "slug": p.slug,
            "name": p.name,
            "max_clients": p.max_clients,
            "max_messages_per_day": p.max_messages_per_day,
            "max_collector_sessions": p.max_collector_sessions,
            "features": p.features,
        }
        for p in PLANS.values()
    ]


# ── Plan Manager ────────────────────────────────────────────────


class PlanManager:
    """
    Centralized plan enforcement.

    Usage:
        pm = PlanManager()
        if not pm.can_create_client(tenant_id):
            raise HTTPException(402, "Plan limit reached")
        pm.record_client_created(tenant_id)
    """

    def can_create_client(self, tenant_id: str) -> bool:
        """Check if tenant can create another client under their plan."""
        tenant = models.get_tenant(tenant_id)
        if tenant is None:
            return False

        plan = get_plan(tenant.get("plan", "free"))
        current_total = self._get_client_count_for_tenant(tenant_id)
        return current_total < plan.max_clients

    def record_client_created(self, tenant_id: str) -> None:
        """Record that a client was created for usage tracking."""
        models.increment_usage(tenant_id, "clients_created")

    def can_send_message(self, tenant_id: str) -> bool:
        """Check if tenant can send another message today."""
        tenant = models.get_tenant(tenant_id)
        if tenant is None:
            return False

        plan = get_plan(tenant.get("plan", "free"))
        used = models.get_usage_today(tenant_id).get("messages_sent", 0)
        return used < plan.max_messages_per_day

    def record_message_sent(self, tenant_id: str) -> None:
        """Record a message sent for usage tracking."""
        models.increment_usage(tenant_id, "messages_sent")

    def can_start_collector_session(self, tenant_id: str) -> bool:
        """Check if tenant can start another collector session today."""
        tenant = models.get_tenant(tenant_id)
        if tenant is None:
            return False

        plan = get_plan(tenant.get("plan", "free"))
        used = models.get_usage_today(tenant_id).get("collector_sessions", 0)
        return used < plan.max_collector_sessions

    def record_collector_session(self, tenant_id: str) -> None:
        """Record a collector session started for usage tracking."""
        models.increment_usage(tenant_id, "collector_sessions")

    def get_usage(self, tenant_id: str) -> dict:
        """Get current usage stats for a tenant."""
        tenant = models.get_tenant(tenant_id)
        plan_slug = tenant.get("plan", "free") if tenant else "free"
        plan = get_plan(plan_slug)

        daily = models.get_usage_today(tenant_id)

        return {
            "plan": plan_slug,
            "plan_name": plan.name,
            "daily": {
                "messages_sent": daily.get("messages_sent", 0),
                "messages_limit": plan.max_messages_per_day,
                "clients_created": daily.get("clients_created", 0),
                "collector_sessions": daily.get("collector_sessions", 0),
                "collector_limit": plan.max_collector_sessions,
            },
            "total_clients": self._get_client_count_for_tenant(tenant_id),
            "total_clients_limit": plan.max_clients,
            "features": plan.features,
        }

    def upgrade_tenant(self, tenant_id: str, new_plan: str) -> dict | None:
        """Upgrade (or downgrade) a tenant's plan. Returns updated tenant or None."""
        if new_plan not in PLANS:
            return None

        plan = get_plan(new_plan)
        return models.update_tenant(
            tenant_id,
            {
                "plan": new_plan,
                "max_clients": plan.max_clients,
                "max_messages": plan.max_messages_per_day,
            },
        )

    def _get_client_count_for_tenant(self, tenant_id: str) -> int:
        """Get total number of clients for a tenant from CRM."""
        from .deps import get_crm

        crm = get_crm()
        return len(crm.list_clients(tenant_id=tenant_id))


# ── Singleton ────────────────────────────────────────────────────

_plan_manager: PlanManager | None = None


def get_plan_manager() -> PlanManager:
    """Return the singleton PlanManager instance."""
    global _plan_manager
    if _plan_manager is None:
        _plan_manager = PlanManager()
    return _plan_manager
