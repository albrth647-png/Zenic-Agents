"""Settings — Configuración centralizada de Zenic-Agents.

Lee de:
1. Variables de entorno (prioridad alta)
2. Archivo .env
3. Defaults

No usa IA. Todo es configuración determinística.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any
from pathlib import Path


@dataclass
class DatabaseConfig:
    """Configuración de base de datos."""
    url: str = ""
    path: str = ""

    def __post_init__(self):
        if not self.path and self.url.startswith("file:"):
            self.path = self.url[5:]
        if not self.path:
            self.path = "/home/z/my-project/db/custom.db"


@dataclass
class ChannelConfig:
    """Configuración de canales."""
    proactive_default_channel: str = "telegram"
    proactive_default_recipient: str = ""
    whatsapp_api_url: str = ""
    telegram_api_url: str = ""
    telegram_bot_token: str = ""


@dataclass
class SNAConfig:
    """Configuración del SNA."""
    enabled: bool = True
    scan_interval_seconds: int = 300
    alert_cooldown_seconds: int = 1800
    rate_limit_per_minute: int = 5
    threshold_config_path: str = ""


@dataclass
class AutopilotConfig:
    """Configuración del Autopilot."""
    enabled: bool = True
    autonomy_level: str = "semi_autonomous"  # "supervised", "semi_autonomous", "full_autonomous"


@dataclass
class SafetyConfig:
    """Configuración del SafetyGate."""
    enabled: bool = True
    deny_is_final: bool = True  # Siempre True — no se puede cambiar


@dataclass
class ZenicConfig:
    """Configuración centralizada de Zenic-Agents."""
    app_name: str = "Zenic-Agents"
    version: str = "3.0.0"
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    channels: ChannelConfig = field(default_factory=ChannelConfig)
    sna: SNAConfig = field(default_factory=SNAConfig)
    autopilot: AutopilotConfig = field(default_factory=AutopilotConfig)
    safety: SafetyConfig = field(default_factory=SafetyConfig)
    data_base_path: str = "/home/z/my-project"

    @classmethod
    def from_env(cls) -> "ZenicConfig":
        """Carga configuración desde variables de entorno."""
        db_url = os.environ.get("DATABASE_URL", "")
        db_path = os.environ.get("DATABASE_PATH", "")

        config = cls(
            database=DatabaseConfig(url=db_url, path=db_path),
            channels=ChannelConfig(
                proactive_default_channel=os.environ.get("PROACTIVE_CHANNEL", "telegram"),
                proactive_default_recipient=os.environ.get("PROACTIVE_RECIPIENT", ""),
                whatsapp_api_url=os.environ.get("WHATSAPP_API_URL", ""),
                telegram_api_url=os.environ.get("TELEGRAM_API_URL", ""),
                telegram_bot_token=os.environ.get("TELEGRAM_BOT_TOKEN", ""),
            ),
            sna=SNAConfig(
                enabled=os.environ.get("SNA_ENABLED", "true").lower() == "true",
                scan_interval_seconds=int(os.environ.get("SNA_SCAN_INTERVAL", "300")),
                alert_cooldown_seconds=int(os.environ.get("SNA_ALERT_COOLDOWN", "1800")),
                rate_limit_per_minute=int(os.environ.get("SNA_RATE_LIMIT", "5")),
                threshold_config_path=os.environ.get("SNA_THRESHOLD_CONFIG", ""),
            ),
            autopilot=AutopilotConfig(
                enabled=os.environ.get("AUTOPILOT_ENABLED", "true").lower() == "true",
                autonomy_level=os.environ.get("AUTOPILOT_AUTONOMY", "semi_autonomous"),
            ),
            data_base_path=os.environ.get("ZENIC_DATA_PATH", "/home/z/my-project"),
        )

        return config
