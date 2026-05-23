"""FileSystemScanner — Escaneo del filesystem local del usuario.

Detecta problemas en:
- Archivos de configuración (missing, stale, malformed)
- Backups (outdated, missing)
- Logs (size explosion, errors)
- Directorios de datos (permissions, disk usage)

El SNA usa esto para detectar problemas ANTES de que el usuario los reporte.
"""

from __future__ import annotations

import os
import json
import logging
import shutil
import hashlib
from pathlib import Path
from typing import Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class FileSystemScanner:
    """Escanea el filesystem del usuario buscando problemas proactivamente."""

    def __init__(self, base_path: str | None = None):
        self.base_path = Path(base_path or os.environ.get("ZENIC_DATA_PATH", "/home/z/my-project"))
        logger.info(f"FileSystemScanner inicializado → {self.base_path}")

    # ------------------------------------------------------------------ #
    #  Disco                                                             #
    # ------------------------------------------------------------------ #

    def get_disk_usage(self) -> dict[str, Any]:
        """Uso de disco del path base."""
        try:
            usage = shutil.disk_usage(str(self.base_path))
            total_gb = usage.total / (1024 ** 3)
            used_gb = usage.used / (1024 ** 3)
            free_gb = usage.free / (1024 ** 3)
            percent = (usage.used / usage.total) * 100 if usage.total > 0 else 0
            return {
                "total_gb": round(total_gb, 2),
                "used_gb": round(used_gb, 2),
                "free_gb": round(free_gb, 2),
                "percent_used": round(percent, 1),
                "status": "critical" if percent > 95 else ("warning" if percent > 85 else "ok"),
            }
        except Exception as e:
            logger.error(f"Error obteniendo uso de disco: {e}")
            return {"status": "error", "error": str(e)}

    # ------------------------------------------------------------------ #
    #  Configuraciones                                                   #
    # ------------------------------------------------------------------ #

    def scan_config_files(self, config_paths: list[str] | None = None) -> list[dict[str, Any]]:
        """Escanea archivos de configuración buscando problemas."""
        default_configs = [
            ".env",
            "config.json",
            "settings.json",
            "appsettings.json",
        ]
        paths_to_check = config_paths or default_configs
        results = []

        for config_name in paths_to_check:
            config_path = self.base_path / config_name
            result: dict[str, Any] = {
                "path": str(config_path),
                "exists": config_path.exists(),
            }

            if config_path.exists():
                try:
                    stat = config_path.stat()
                    result["size_bytes"] = stat.st_size
                    result["modified"] = datetime.fromtimestamp(stat.st_mtime).isoformat()
                    result["age_days"] = (datetime.now() - datetime.fromtimestamp(stat.st_mtime)).days

                    # Verificar si es JSON válido
                    if config_path.suffix == ".json":
                        try:
                            content = config_path.read_text(encoding="utf-8")
                            json.loads(content)
                            result["valid_json"] = True
                        except json.JSONDecodeError as e:
                            result["valid_json"] = False
                            result["json_error"] = str(e)

                    # Verificar permisos
                    result["readable"] = os.access(config_path, os.R_OK)
                    result["writable"] = os.access(config_path, os.W_OK)

                except Exception as e:
                    result["error"] = str(e)

            results.append(result)

        return results

    # ------------------------------------------------------------------ #
    #  Backups                                                           #
    # ------------------------------------------------------------------ #

    def scan_backups(self, backup_dir: str = "backups", max_age_days: int = 7) -> dict[str, Any]:
        """Verifica estado de los backups."""
        backup_path = self.base_path / backup_dir
        result: dict[str, Any] = {
            "backup_dir": str(backup_path),
            "exists": backup_path.exists(),
        }

        if not backup_path.exists():
            result["status"] = "missing"
            result["recommendation"] = f"Crear directorio de backups: {backup_path}"
            return result

        try:
            backup_files = list(backup_path.glob("*"))
            result["file_count"] = len(backup_files)

            if not backup_files:
                result["status"] = "empty"
                result["recommendation"] = "No hay archivos de backup"
                return result

            # Encontrar el backup más reciente
            latest = max(backup_files, key=lambda f: f.stat().st_mtime)
            latest_mtime = datetime.fromtimestamp(latest.stat().st_mtime)
            age_hours = (datetime.now() - latest_mtime).total_seconds() / 3600

            result["latest_backup"] = str(latest.name)
            result["latest_backup_age_hours"] = round(age_hours, 1)
            result["latest_backup_size_mb"] = round(latest.stat().st_size / (1024 * 1024), 2)

            if age_hours > max_age_days * 24:
                result["status"] = "outdated"
                result["recommendation"] = f"Último backup tiene {age_hours:.0f} horas. Recomendado: cada {max_age_days * 24}h"
            else:
                result["status"] = "ok"

            # Total de backups
            total_size = sum(f.stat().st_size for f in backup_files if f.is_file())
            result["total_size_mb"] = round(total_size / (1024 * 1024), 2)

        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)

        return result

    # ------------------------------------------------------------------ #
    #  Logs                                                              #
    # ------------------------------------------------------------------ #

    def scan_logs(self, log_dir: str = "logs", max_size_mb: float = 100) -> dict[str, Any]:
        """Escanea archivos de log buscando problemas."""
        log_path = self.base_path / log_dir
        result: dict[str, Any] = {
            "log_dir": str(log_path),
            "exists": log_path.exists(),
        }

        if not log_path.exists():
            result["status"] = "no_logs"
            return result

        try:
            log_files = list(log_path.glob("*.log"))
            result["file_count"] = len(log_files)

            oversized = []
            total_size = 0
            for lf in log_files:
                size_mb = lf.stat().st_size / (1024 * 1024)
                total_size += lf.stat().st_size
                if size_mb > max_size_mb:
                    oversized.append({"name": lf.name, "size_mb": round(size_mb, 2)})

            result["total_size_mb"] = round(total_size / (1024 * 1024), 2)
            result["oversized_files"] = oversized
            result["status"] = "warning" if oversized else "ok"

            if oversized:
                result["recommendation"] = f"{len(oversized)} archivo(s) de log exceden {max_size_mb}MB. Rotar logs."

        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)

        return result

    # ------------------------------------------------------------------ #
    #  Directorios de datos                                              #
    # ------------------------------------------------------------------ #

    def scan_data_directories(self, data_dirs: list[str] | None = None) -> list[dict[str, Any]]:
        """Escanea directorios de datos buscando problemas."""
        default_dirs = ["db", "data", "uploads", "exports", "temp"]
        dirs_to_scan = data_dirs or default_dirs
        results = []

        for dir_name in dirs_to_scan:
            dir_path = self.base_path / dir_name
            result: dict[str, Any] = {
                "path": str(dir_path),
                "exists": dir_path.exists(),
            }

            if dir_path.exists():
                try:
                    file_count = sum(1 for _ in dir_path.rglob("*") if _.is_file())
                    total_size = sum(f.stat().st_size for f in dir_path.rglob("*") if f.is_file())
                    result["file_count"] = file_count
                    result["total_size_mb"] = round(total_size / (1024 * 1024), 2)
                    result["writable"] = os.access(dir_path, os.W_OK)
                    result["readable"] = os.access(dir_path, os.R_OK)
                    result["status"] = "ok" if result["writable"] and result["readable"] else "permission_error"
                except Exception as e:
                    result["status"] = "error"
                    result["error"] = str(e)
            else:
                result["status"] = "missing"

            results.append(result)

        return results

    # ------------------------------------------------------------------ #
    #  Archivos huérfanos / temporales                                   #
    # ------------------------------------------------------------------ #

    def scan_temp_files(self, temp_dir: str = "temp", max_age_hours: int = 24) -> dict[str, Any]:
        """Busca archivos temporales que deberían haberse limpiado."""
        temp_path = self.base_path / temp_dir
        result: dict[str, Any] = {"temp_dir": str(temp_path), "exists": temp_path.exists()}

        if not temp_path.exists():
            result["status"] = "no_temp"
            return result

        try:
            stale_files = []
            now = datetime.now()
            for f in temp_path.rglob("*"):
                if f.is_file():
                    mtime = datetime.fromtimestamp(f.stat().st_mtime)
                    age_hours = (now - mtime).total_seconds() / 3600
                    if age_hours > max_age_hours:
                        stale_files.append({
                            "name": f.name,
                            "age_hours": round(age_hours, 1),
                            "size_kb": round(f.stat().st_size / 1024, 2),
                        })

            result["stale_file_count"] = len(stale_files)
            result["stale_files"] = stale_files[:20]  # Limitar a 20
            result["status"] = "warning" if stale_files else "ok"

            if stale_files:
                total_kb = sum(sf["size_kb"] for sf in stale_files)
                result["recommendation"] = f"{len(stale_files)} archivos temporales antiguos ({total_kb:.0f}KB). Limpiar."

        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)

        return result

    # ------------------------------------------------------------------ #
    #  Health check completo                                             #
    # ------------------------------------------------------------------ #

    def full_health_check(self) -> dict[str, Any]:
        """Ejecuta todos los escaneos del filesystem."""
        return {
            "disk": self.get_disk_usage(),
            "configs": self.scan_config_files(),
            "backups": self.scan_backups(),
            "logs": self.scan_logs(),
            "data_dirs": self.scan_data_directories(),
            "temp_files": self.scan_temp_files(),
            "timestamp": datetime.now().isoformat(),
        }
