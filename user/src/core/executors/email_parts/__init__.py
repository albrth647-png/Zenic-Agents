"""
ZENIC-AGENTS — Email Parts (Phase 2)

Sub-modules for the enhanced EmailExecutor infrastructure:
  - templates: Email template engine (invoice, reminder, alert, welcome, low_stock)
  - rate_limiter: Per-recipient and global email rate limiting
  - oauth2: OAuth2 token manager for authorized services (Graph API, ServiceNow, etc.)
  - graph_api: Microsoft Graph API email provider
"""

from __future__ import annotations

from .graph_api import GraphAPIEmailProvider
from .oauth2 import OAuth2Config, OAuth2Token, OAuth2TokenManager
from .rate_limiter import EmailRateLimiter
from .templates import EmailTemplate, EmailTemplateEngine

__all__ = [
    "EmailRateLimiter",
    "EmailTemplate",
    "EmailTemplateEngine",
    "GraphAPIEmailProvider",
    "OAuth2Config",
    "OAuth2Token",
    "OAuth2TokenManager",
]
