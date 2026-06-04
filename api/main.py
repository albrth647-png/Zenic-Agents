"""
ZENIC-AGENTS — API Main Entry Point.

FastAPI application that exposes Zenic Agents as REST endpoints.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure _archived agents are importable
_ARCHIVED = Path(__file__).resolve().parent.parent / "_archived"
if str(_ARCHIVED) not in sys.path:
    sys.path.insert(0, str(_ARCHIVED))

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .deps import get_app_config
from .routes import admin, auth, channels, clients, collector, plans, stream


# ── Lifespan (startup/shutdown) ────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: pre-load config. Shutdown: clean up if needed."""
    config = get_app_config()
    print(f"🚀 Zenic-Agents API starting on {config.host}:{config.port}")
    yield
    print("🛑 Zenic-Agents API shutting down")


# ── App Creation ───────────────────────────────────────────────

app = FastAPI(
    title="Zenic-Agents API",
    description="REST API for Zenic-Agents — multi-agent pipeline for business automation",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# ── CORS ───────────────────────────────────────────────────────

config = get_app_config()
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Mount Routers ──────────────────────────────────────────────

app.include_router(auth.router, prefix="/api/v1")
app.include_router(plans.router, prefix="/api/v1")
app.include_router(channels.router, prefix="/api/v1")
app.include_router(clients.router, prefix="/api/v1")
app.include_router(collector.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")
app.include_router(stream.router, prefix="/api/v1")


# ── Root ───────────────────────────────────────────────────────

@app.get("/")
def root():
    """API root — returns basic info."""
    return {
        "name": "Zenic-Agents API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/v1/admin/health",
    }


@app.get("/api/v1/ping")
def ping():
    """Health check ping."""
    return {"ping": "pong", "ok": True}
