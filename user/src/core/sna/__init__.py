"""SNA — Sistema Nervioso Autónomo.

El SNA NO es adivino: escanea los datos LOCALES del usuario.
Cada monitor consulta directamente la base de datos SQLite y el filesystem.
No necesita que el usuario reporte problemas por canales.

Arquitectura:
    LocalDataScanner → Monitor → AlertManager → ProactiveChannelBridge → Canal
"""

from src.core.sna.alert_manager import AlertManager
from src.core.sna.scheduler import SNAScheduler
from src.core.sna.sna_engine import SNAEngine

__all__ = ["AlertManager", "SNAEngine", "SNAScheduler"]
