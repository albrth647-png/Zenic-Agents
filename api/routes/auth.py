"""
ZENIC-AGENTS — Auth Routes.

POST /register  — Register a new user
POST /login     — Login and get JWT token
GET  /me        — Get current user info
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from ..auth import create_access_token, verify_password
from ..middleware import get_current_user, require_admin
from ..models import create_user, get_tenant, get_user_by_email, list_tenants
from ..schemas import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=201)
def register(payload: RegisterRequest) -> UserResponse:
    """Register a new user. Creates a tenant if none exists."""
    # If no tenants exist, create a default one
    tenants = list_tenants()
    if not tenants:
        from ..models import create_tenant
        tenant = create_tenant(name="Default", slug="default", plan="free")
        tenant_id = tenant["id"]
    else:
        tenant_id = payload.tenant_id or tenants[0]["id"]

    # Validate tenant exists
    tenant = get_tenant(tenant_id)
    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid tenant_id. Provide a valid tenant_id or leave empty to auto-create one.",
        )

    # Check email uniqueness
    existing = get_user_by_email(payload.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    user = create_user(
        email=payload.email,
        password=payload.password,
        tenant_id=tenant_id,
        role=payload.role,
        name=payload.name,
    )

    return UserResponse(**user)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest) -> TokenResponse:
    """Login with email and password. Returns JWT access token."""
    user = get_user_by_email(payload.email)
    if user is None or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    token = create_access_token({
        "sub": user["id"],
        "tenant_id": user["tenant_id"],
        "email": user["email"],
        "role": user["role"],
    })

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse(
            id=user["id"],
            tenant_id=user["tenant_id"],
            email=user["email"],
            role=user["role"],
            name=user.get("name", ""),
            created_at=user.get("created_at", ""),
        ),
    )


@router.get("/me", response_model=UserResponse)
def me(user: dict = Depends(get_current_user)) -> UserResponse:
    """Get the currently authenticated user's info."""
    return UserResponse(**user)


# ── Admin-only routes ──────────────────────────────────────────


@router.get("/tenants")
def admin_list_tenants(
    admin: dict = Depends(require_admin),
) -> list[dict]:
    """List all tenants (admin only)."""
    return list_tenants()
