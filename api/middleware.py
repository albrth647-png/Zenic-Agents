"""
ZENIC-AGENTS — Auth Middleware (Dependencies).

FastAPI dependencies for JWT authentication and tenant scoping.
"""

from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .auth import decode_access_token
from .models import get_tenant, get_user_by_id

# ── Bearer token scheme ────────────────────────────────────────

security = HTTPBearer(auto_error=False)


# ── Current User ───────────────────────────────────────────────


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> dict:
    """
    Extract and validate JWT from Authorization header.
    Returns user dict: {id, tenant_id, email, role, name, created_at}.

    Raises 401 if token is missing, expired, or invalid.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    try:
        payload = decode_access_token(token)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    user = get_user_by_id(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return user


# ── Current Tenant ─────────────────────────────────────────────


def get_current_tenant(
    user: dict = Depends(get_current_user),
) -> dict:
    """
    Extract tenant from current user's tenant_id.
    Raises 404 if tenant not found.
    """
    tenant = get_tenant(user["tenant_id"])
    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found",
        )
    return tenant


# ── Optional User (public routes that benefit from auth) ───────


def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> dict | None:
    """
    Extract user from JWT if present. Returns None if no token.
    Does NOT raise 401 — for routes that work both ways.
    """
    if credentials is None:
        return None
    try:
        payload = decode_access_token(credentials.credentials)
        return get_user_by_id(payload.get("sub", ""))
    except Exception:
        return None


# ── Require Admin ──────────────────────────────────────────────


def require_admin(
    user: dict = Depends(get_current_user),
) -> dict:
    """Require admin role. Raises 403 if not admin."""
    if user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return user


# ── Plan Limits ────────────────────────────────────────────────


def check_client_limit(
    tenant: dict = Depends(get_current_tenant),
) -> dict:
    """
    Check if the current tenant can create another client.
    Raises 402 Payment Required if limit reached.
    """
    from .plans import get_plan_manager

    pm = get_plan_manager()
    if not pm.can_create_client(tenant["id"]):
        usage = pm.get_usage(tenant["id"])
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=(
                f"Plan limit reached: {usage['total_clients']}/{usage['total_clients_limit']} clients. "
                f"Upgrade to {_next_plan(usage['plan'])} for more capacity."
            ),
        )
    return tenant


def check_message_limit(
    tenant: dict = Depends(get_current_tenant),
) -> dict:
    """
    Check if the current tenant can send another message today.
    Raises 402 Payment Required if daily limit reached.
    """
    from .plans import get_plan_manager

    pm = get_plan_manager()
    if not pm.can_send_message(tenant["id"]):
        usage = pm.get_usage(tenant["id"])
        daily = usage.get("daily", {})
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=(
                f"Daily message limit reached: {daily.get('messages_sent', 0)}/"
                f"{daily.get('messages_limit', 0)}. "
                f"Limits reset at midnight UTC. Upgrade to {_next_plan(usage['plan'])} for more."
            ),
        )
    return tenant


def check_collector_limit(
    tenant: dict = Depends(get_current_tenant),
) -> dict:
    """
    Check if the current tenant can start another collector session today.
    Raises 402 Payment Required if daily limit reached.
    """
    from .plans import get_plan_manager

    pm = get_plan_manager()
    if not pm.can_start_collector_session(tenant["id"]):
        usage = pm.get_usage(tenant["id"])
        daily = usage.get("daily", {})
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=(
                f"Daily collector session limit reached: {daily.get('collector_sessions', 0)}/"
                f"{daily.get('collector_limit', 0)}. "
                f"Limits reset at midnight UTC. Upgrade to {_next_plan(usage['plan'])} for more."
            ),
        )
    return tenant


def _next_plan(current: str) -> str:
    """Return the next plan up from current."""
    order = ["free", "pro", "enterprise"]
    try:
        idx = order.index(current)
        return order[min(idx + 1, len(order) - 1)]
    except ValueError:
        return "pro"
