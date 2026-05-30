"""ThresholdEngine — Motor de evaluación de umbrales configurables.

Cada monitor tiene umbrales configurables por el usuario.
Si no hay config, usa defaults.
Los umbrales se almacenan en la BD LOCAL del usuario (tabla sna_thresholds).
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class Threshold:
    """Un umbral configurable."""

    monitor_name: str
    key: str
    value: Any
    type: str  # "int", "float", "str", "bool"
    description: str

    def validate(self, input_value: Any) -> bool:
        """Valida si un valor cumple el umbral."""
        if self.type in ("int", "float"):
            return float(input_value) <= float(self.value)
        if self.type == "bool":
            return bool(input_value) == bool(self.value)
        return str(input_value) == str(self.value)


# Umbrales por defecto para cada monitor
DEFAULT_THRESHOLDS: dict[str, list[Threshold]] = {
    "low_stock": [
        Threshold("low_stock", "threshold", 5, "int", "Stock mínimo antes de alertar"),
    ],
    "disk_space": [
        Threshold("disk_space", "critical_percent", 95.0, "float", "Porcentaje de disco para alerta crítica"),
        Threshold("disk_space", "warning_percent", 85.0, "float", "Porcentaje de disco para alerta warning"),
    ],
    "sales_trend": [
        Threshold("sales_trend", "drop_threshold_percent", 30.0, "float", "Caída % para alertar"),
    ],
    "stale_inventory": [
        Threshold("stale_inventory", "stale_days", 90, "int", "Días sin venta para considerar estancado"),
    ],
    "backup_status": [
        Threshold("backup_status", "max_age_days", 7, "int", "Días máximos sin backup"),
    ],
    "overdue_invoice": [],
    "tomorrow_appointment": [],
    "unpaid_balance": [],
    "duplicate_records": [],
    "config_drift": [],
    "data_integrity": [],
    "api_health": [],
}


class ThresholdEngine:
    """Motor de evaluación de umbrales.

    Carga umbrales de la BD del usuario (si existen) o usa defaults.
    Permite al usuario customizar qué considera "problema".
    """

    def __init__(self, config_path: str | None = None):
        self._thresholds: dict[str, dict[str, Threshold]] = {}
        self._config_path = config_path
        self._load_defaults()
        if config_path:
            self._load_from_file(config_path)
        logger.info(f"ThresholdEngine inicializado con {len(self._thresholds)} monitores configurados")

    def _load_defaults(self):
        """Carga umbrales por defecto."""
        for monitor_name, threshold_list in DEFAULT_THRESHOLDS.items():
            self._thresholds[monitor_name] = {t.key: t for t in threshold_list}

    def _load_from_file(self, config_path: str):
        """Carga umbrales desde archivo de configuración JSON."""
        try:
            path = Path(config_path)
            if not path.exists():
                logger.debug(f"Archivo de umbrales no encontrado: {config_path}")
                return

            with open(path, encoding="utf-8") as f:
                custom = json.load(f)

            for monitor_name, thresholds in custom.items():
                if monitor_name not in self._thresholds:
                    self._thresholds[monitor_name] = {}
                for key, value in thresholds.items():
                    if isinstance(value, dict):
                        self._thresholds[monitor_name][key] = Threshold(
                            monitor_name=monitor_name,
                            key=key,
                            value=value.get("value"),
                            type=value.get("type", "str"),
                            description=value.get("description", ""),
                        )
                    else:
                        # Valor simple — inferir tipo
                        t = "int" if isinstance(value, int) else "float" if isinstance(value, float) else "str"
                        self._thresholds[monitor_name][key] = Threshold(
                            monitor_name=monitor_name, key=key, value=value, type=t, description=""
                        )

            logger.info(f"Umbrales custom cargados desde {config_path}")
        except Exception as e:
            logger.error(f"Error cargando umbrales desde {config_path}: {e}")

    def get(self, monitor_name: str, key: str, default: Any = None) -> Any:
        """Obtiene el valor de un umbral."""
        monitor_thresholds = self._thresholds.get(monitor_name, {})
        threshold = monitor_thresholds.get(key)
        if threshold:
            return threshold.value
        return default

    def set(self, monitor_name: str, key: str, value: Any, type_: str = "str", description: str = ""):
        """Establece un umbral (en memoria). Para persistir, usar save_to_file()."""
        if monitor_name not in self._thresholds:
            self._thresholds[monitor_name] = {}
        self._thresholds[monitor_name][key] = Threshold(
            monitor_name=monitor_name, key=key, value=value, type=type_, description=description
        )

    def get_all_for_monitor(self, monitor_name: str) -> dict[str, Any]:
        """Obtiene todos los umbrales de un monitor como dict de valores."""
        return {k: t.value for k, t in self._thresholds.get(monitor_name, {}).items()}

    def save_to_file(self, config_path: str):
        """Guarda umbrales actuales a archivo JSON."""
        data = {}
        for monitor_name, thresholds in self._thresholds.items():
            data[monitor_name] = {
                k: {"value": t.value, "type": t.type, "description": t.description} for k, t in thresholds.items()
            }
        path = Path(config_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.info(f"Umbrales guardados en {config_path}")
