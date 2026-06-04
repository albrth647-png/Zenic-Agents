"""
TemperatureController — Temperatura dinámica para la Free Energy.

T(t+1) = T_base · (2.0 - accuracy_historical)

Si accuracy_historical = 1.0 (siempre acierta) → T = T_base (confianza normal)
Si accuracy_historical = 0.5 (falla la mitad)  → T = T_base · 1.5 (precaución)
Si accuracy_historical = 0.0 (siempre falla)   → T = T_base · 2.0 (máxima precaución)
"""

from __future__ import annotations

import logging
import os
import sqlite3
import time
from typing import Any

from .tece_types import TemperatureHistory

logger = logging.getLogger("zenic_agents.verdict.temperature")


class TemperatureController:
    """
    Controla la temperatura del sistema TECE.

    La temperatura es un "termómetro de confianza":
    - Sube cuando el sistema ha estado fallando → más conservador
    - Baja cuando el sistema ha estado acertando → más seguro
    """

    def __init__(
        self,
        base_temperature: float = 1.0,
        db_path: str | None = None,
        window_size: int = 100,
    ):
        self._history = TemperatureHistory(
            base_temperature=base_temperature,
            temperature=base_temperature,
            window_size=window_size,
        )

        # Persistencia opcional en SQLite
        self._db_path = db_path or os.environ.get(
            "TECE_HISTORY_DB",
            os.path.join(os.environ.get("HOME", "/var/tmp"), ".tece_history.db"),  # noqa: S108
        )
        self._db: sqlite3.Connection | None = None
        self._init_db()

    def _init_db(self) -> None:
        """Inicializar base de datos SQLite para persistencia."""
        try:
            self._db = sqlite3.connect(self._db_path)
            self._db.execute("""
                CREATE TABLE IF NOT EXISTS verdict_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL NOT NULL,
                    evidence_hash TEXT,
                    verdict TEXT NOT NULL,
                    was_correct INTEGER NOT NULL,
                    temperature REAL NOT NULL,
                    energy REAL
                )
            """)
            self._db.execute("""
                CREATE INDEX IF NOT EXISTS idx_timestamp
                ON verdict_history(timestamp)
            """)
            self._db.commit()
        except Exception as e:
            logger.warning("TemperatureController: DB init failed: %s", e)
            self._db = None

    def record_outcome(
        self,
        was_correct: bool,
        verdict: str = "",
        energy: float = 0.0,
        evidence_hash: str = "",
    ) -> None:
        """
        Registrar el resultado de una decisión.

        Args:
            was_correct: True si la decisión fue correcta
            verdict: Verdict emitido
            energy: Energía del sistema en el momento de la decisión
            evidence_hash: Hash de las evidencias
        """
        # Actualizar estadísticas en memoria
        self._history.total_decisions += 1
        if was_correct:
            self._history.correct_decisions += 1

        # Actualizar ventana de accuracy reciente
        self._history.recent_accuracy.append(1.0 if was_correct else 0.0)
        if len(self._history.recent_accuracy) > self._history.window_size:
            self._history.recent_accuracy.pop(0)

        # Recalcular temperatura
        self._recalculate_temperature()

        # Persistir en DB
        if self._db is not None:
            try:
                self._db.execute(
                    """
                    INSERT INTO verdict_history
                        (timestamp, evidence_hash, verdict, was_correct, temperature, energy)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (time.time(), evidence_hash, verdict, int(was_correct),
                     self._history.temperature, energy),
                )
                self._db.commit()
            except Exception as e:
                logger.debug("Failed to persist outcome: %s", e)

    def _recalculate_temperature(self) -> None:
        """Recalcular la temperatura basada en accuracy histórica."""
        if not self._history.recent_accuracy:
            self._history.temperature = self._history.base_temperature
            return

        # Accuracy de la ventana reciente
        recent_accuracy = sum(self._history.recent_accuracy) / len(
            self._history.recent_accuracy
        )

        # T = T_base · (2.0 - accuracy)
        # accuracy=1.0 → T = T_base · 1.0 (confianza normal)
        # accuracy=0.5 → T = T_base · 1.5 (precaución)
        # accuracy=0.0 → T = T_base · 2.0 (máxima precaución)
        self._history.temperature = (
            self._history.base_temperature * (2.0 - recent_accuracy)
        )

    def get_temperature(self) -> float:
        """Obtener la temperatura actual."""
        return self._history.temperature

    def get_stats(self) -> dict[str, Any]:
        """Obtener estadísticas del controlador."""
        return {
            "temperature": round(self._history.temperature, 3),
            "base_temperature": self._history.base_temperature,
            "total_decisions": self._history.total_decisions,
            "correct_decisions": self._history.correct_decisions,
            "accuracy": (
                round(
                    self._history.correct_decisions / self._history.total_decisions, 4
                )
                if self._history.total_decisions > 0
                else 1.0
            ),
            "window_accuracy": (
                round(
                    sum(self._history.recent_accuracy)
                    / len(self._history.recent_accuracy),
                    4,
                )
                if self._history.recent_accuracy
                else 1.0
            ),
            "window_size": self._history.window_size,
        }

    def reset(self) -> None:
        """Reiniciar el controlador a valores iniciales."""
        self._history = TemperatureHistory(
            base_temperature=self._history.base_temperature,
            temperature=self._history.base_temperature,
            window_size=self._history.window_size,
        )
