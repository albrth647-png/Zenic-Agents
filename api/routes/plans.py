"""
ZENIC-AGENTS — Plans Routes.

GET  /plans       — List all available plans (public)
GET  /plans/usage — Get current tenant's usage (authenticated)
POST /plans/upgrade — Upgrade tenant's plan (admin only)
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from ..middleware import get_current_tenant, require_admin
from ..plans import get_plan_manager, list_plans
from ..schemas import PlanResponse, UpgradeRequest, UsageResponse

router = APIRouter(prefix="/plans", tags=["plans"])


@router.get("", response_model=list[PlanResponse])
def available_plans() -> list[PlanResponse]:
    """List all available subscription plans."""
    return [PlanResponse(**p) for p in list_plans()]


@router.get("/usage", response_model=UsageResponse)
def my_usage(
    tenant: dict = Depends(get_current_tenant),
    pm=Depends(get_plan_manager),
) -> UsageResponse:
    """Get current usage stats for the authenticated tenant."""
    usage = pm.get_usage(tenant["id"])
    return UsageResponse(**usage)


@router.post("/upgrade", response_model=UsageResponse)
def upgrade_plan(
    payload: UpgradeRequest,
    admin: dict = Depends(require_admin),
    pm=Depends(get_plan_manager),
) -> UsageResponse:
    """Upgrade (or downgrade) a tenant's plan (admin only)."""
    if payload.plan not in ("free", "pro", "enterprise"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown plan: {payload.plan}. Use: free, pro, enterprise.",
        )

    updated = pm.upgrade_tenant(payload.tenant_id, payload.plan)
    if updated is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant {payload.tenant_id} not found",
        )

    usage = pm.get_usage(payload.tenant_id)
    return UsageResponse(**usage)
