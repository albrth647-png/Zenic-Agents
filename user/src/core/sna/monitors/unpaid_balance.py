"""UnpaidBalanceMonitor — Detecta saldos pendientes de clientes.

Peso: CRITICAL (3) — Dinero no cobrado.

Escanea la tabla 'clientes' en la BD LOCAL buscando saldos > 0.
NO espera a que el cliente pague espontáneamente.
"""

from __future__ import annotations

import contextlib
import logging

from src.core.sna.monitors.base import BaseMonitor, MonitorResult, MonitorWeight

logger = logging.getLogger(__name__)


class UnpaidBalanceMonitor(BaseMonitor):
    """Monitor de saldos pendientes — escanea la BD del usuario."""

    name = "unpaid_balance"
    weight = MonitorWeight.CRITICAL
    description = "Detecta clientes con saldo pendiente en la BD local"
    interval_seconds = 1800  # Cada 30 minutos

    def check(self) -> MonitorResult:
        """Busca saldos pendientes en la BD del usuario."""
        clients = self.scanner.scan_unpaid_balances()

        if not clients:
            return MonitorResult(
                monitor_name=self.name,
                weight=self.weight,
                healthy=True,
                details={"message": "No hay saldos pendientes"},
            )

        findings = []
        total_pending = 0.0
        for client in clients:
            name_val = client.get("nombre", client.get("name", client.get("cliente", str(client.get("id", "?")))))
            balance = client.get("saldo_pendiente", client.get("balance", 0))
            with contextlib.suppress(ValueError, TypeError):
                total_pending += float(balance)
            findings.append(
                {
                    "type": "unpaid_balance",
                    "client": name_val,
                    "balance": balance,
                    "message": f"Saldo pendiente: {name_val} debe {balance}",
                }
            )

        return MonitorResult(
            monitor_name=self.name,
            weight=self.weight,
            findings=findings,
            healthy=False,
            details={
                "total_clients": len(clients),
                "total_pending": round(total_pending, 2),
                "source": "local_database",
            },
        )
