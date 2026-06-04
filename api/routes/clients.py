"""
ZENIC-AGENTS — Client Routes (CRMPipeline).

REST endpoints for CRM client management.
All endpoints require authentication and are tenant-scoped.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from ..deps import get_crm
from ..middleware import check_client_limit, get_current_tenant, get_current_user
from ..schemas import (
    ClientCreate,
    ClientListResponse,
    ClientResponse,
    ClientUpdate,
    PipelineResponse,
    StatsResponse,
)

router = APIRouter(prefix="/clients", tags=["clients"])


@router.get("", response_model=ClientListResponse)
def list_clients(
    search: str = Query(default="", description="Search by name, email, or company"),
    tenant: dict = Depends(get_current_tenant),
    crm=Depends(get_crm),
) -> ClientListResponse:
    """List all clients for the current tenant, optionally filtered by search term."""
    clients = crm.list_clients(search=search, tenant_id=tenant["id"])
    return ClientListResponse(
        clients=[ClientResponse(**c) for c in clients],
        total=len(clients),
    )


@router.get("/stats", response_model=StatsResponse)
def get_stats(
    tenant: dict = Depends(get_current_tenant),
    crm=Depends(get_crm),
) -> StatsResponse:
    """Get CRM pipeline statistics for the current tenant."""
    stats = crm.get_stats(tenant_id=tenant["id"])
    return StatsResponse(**stats)


@router.get("/pipeline", response_model=PipelineResponse)
def get_pipeline(
    tenant: dict = Depends(get_current_tenant),
    crm=Depends(get_crm),
) -> PipelineResponse:
    """Get clients grouped by pipeline stage for the current tenant."""
    pipeline = crm.get_pipeline_view(tenant_id=tenant["id"])
    return PipelineResponse(
        stages={
            stage: [ClientResponse(**c) for c in clients]
            for stage, clients in pipeline.items()
        }
    )


@router.get("/{client_id}", response_model=ClientResponse)
def get_client(
    client_id: str,
    tenant: dict = Depends(get_current_tenant),
    crm=Depends(get_crm),
) -> ClientResponse:
    """Get a single client by ID (tenant-scoped)."""
    client = crm.get_client(client_id, tenant_id=tenant["id"])
    if client is None:
        raise HTTPException(status_code=404, detail=f"Client {client_id} not found")
    return ClientResponse(**client)


@router.post("", response_model=ClientResponse, status_code=201)
def create_client(
    payload: ClientCreate,
    tenant: dict = Depends(check_client_limit),
    crm=Depends(get_crm),
) -> ClientResponse:
    """Create a new client for the current tenant (plan limit enforced)."""
    from datetime import datetime

    from ..plans import get_plan_manager

    data = payload.model_dump()
    data["tenant_id"] = tenant["id"]
    data.setdefault("created_at", datetime.utcnow().isoformat())
    client = crm.add_client(data, tenant_id=tenant["id"])

    # Record usage
    get_plan_manager().record_client_created(tenant["id"])

    return ClientResponse(**client)


@router.put("/{client_id}", response_model=ClientResponse)
def update_client(
    client_id: str,
    payload: ClientUpdate,
    tenant: dict = Depends(get_current_tenant),
    crm=Depends(get_crm),
) -> ClientResponse:
    """Update an existing client (tenant-scoped)."""
    updates = payload.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    client = crm.update_client(client_id, updates, tenant_id=tenant["id"])
    if client is None:
        raise HTTPException(status_code=404, detail=f"Client {client_id} not found")
    return ClientResponse(**client)


@router.delete("/{client_id}")
def delete_client(
    client_id: str,
    tenant: dict = Depends(get_current_tenant),
    crm=Depends(get_crm),
) -> dict[str, str]:
    """Delete a client by ID (tenant-scoped)."""
    deleted = crm.delete_client(client_id, tenant_id=tenant["id"])
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Client {client_id} not found")
    return {"ok": True, "deleted": client_id}
