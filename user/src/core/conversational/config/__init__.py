"""
Configuracion del Asistente.

Carga desde .env + defaults + YAML, con validacion
y valores por defecto seguros para produccion.
"""

from .constants import (
    APP_NAME,
    APP_VERSION,
    DEFAULT_HOST,
    DEFAULT_PORT,
    HEALTH_CHECK_INTERVAL_SECONDS,
    MAX_CONTEXT_TOKENS,
    MAX_MESSAGES_PER_SESSION,
    MAX_SESSIONS,
    PERSONALITY_DEFAULT,
    RATE_LIMIT_RPM,
    SESSION_TIMEOUT_SECONDS,
    STREAMING_CHUNK_SIZE,
)
from .env import AgentsConfig, get_config, load_agents_config

__all__ = [
    "APP_NAME",
    "APP_VERSION",
    "DEFAULT_HOST",
    "DEFAULT_PORT",
    "HEALTH_CHECK_INTERVAL_SECONDS",
    "MAX_CONTEXT_TOKENS",
    "MAX_MESSAGES_PER_SESSION",
    "MAX_SESSIONS",
    "PERSONALITY_DEFAULT",
    "RATE_LIMIT_RPM",
    "SESSION_TIMEOUT_SECONDS",
    "STREAMING_CHUNK_SIZE",
    "AgentsConfig",
    "get_config",
    "load_agents_config",
]
