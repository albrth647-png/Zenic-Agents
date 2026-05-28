"""OverdueInvoiceMonitor — Detecta facturas vencidas sin pagar.

Peso: CRITICAL (3) — Puede causar pérdida de dinero.

Escanea la tabla 'facturas' en la BD LOCAL del usuario.
NO espera a que el cliente reclame.
"""

from __future__ import annotations

import contextlib
import logging

from src.core.sna.monitors.base import BaseMonitor, MonitorResult, MonitorWeight

logger = logging.getLogger(__name__)


class OverdueInvoiceMonitor(BaseMonitor):
    """Monitor de facturas vencidas — escanea la BD del usuario directamente."""

    name = "overdue_invoice"
    weight = MonitorWeight.CRITICAL
    description = "Detecta facturas vencidas sin pagar en la BD local"
    interval_seconds = 600  # Cada 10 minutos

    def check(self) -> MonitorResult:
        """Busca facturas vencidas en la BD del usuario."""
        invoices = self.scanner.scan_overdue_invoices()

        if not invoices:
            return MonitorResult(
                monitor_name=self.name,
                weight=self.weight,
                healthy=True,
                details={"message": "No hay facturas vencidas"},
            )

        findings = []
        total_amount = 0.0
        for inv in invoices:
            amount = inv.get("monto", inv.get("total", inv.get("importe", 0)))
            client = inv.get("cliente", inv.get("cliente_id", str(inv.get("id", "?"))))
            due = inv.get("fecha_vencimiento", inv.get("due_date", "?"))
            numero = inv.get("numero", inv.get("invoice_number", ""))
            with contextlib.suppress(ValueError, TypeError):
                total_amount += float(amount)
            label = f"{numero} " if numero else ""
            findings.append(
                {
                    "type": "overdue_invoice",
                    "invoice_number": numero,
                    "client": client,
                    "amount": amount,
                    "due_date": due,
                    "message": f"Factura vencida {label}cliente {client} — {amount} (venció: {due})",
                }
            )

        return MonitorResult(
            monitor_name=self.name,
            weight=self.weight,
            findings=findings,
            healthy=False,
            details={
                "total_overdue": len(invoices),
                "total_amount": total_amount,
                "source": "local_database",
            },
        )
