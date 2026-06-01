"""
Conocimiento base del motor de conversacion.

HUMANIZADO: Contenido de negocio con tono humano.
Define lo que el sistema sabe sobre la empresa, sus
procesos y capacidades.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .knowledge import KnowledgeBase

logger = logging.getLogger("zenic_agents.conversational.engine_knowledge")


def load_builtin_knowledge(kb: KnowledgeBase) -> None:
    """Carga conocimiento base del sistema en la KnowledgeBase."""
    concepts: list[tuple[str, str, str, list[str]]] = [
        (
            "Sistema de Facturacion",
            "El sistema puede crear, consultar y enviar facturas a clientes. "
            "Soporta facturas electronicas, multiples monedas y descuentos. "
            "Las facturas se pueden descargar en PDF, enviar por correo o "
            "compartir por WhatsApp.",
            "business",
            ["factura", "facturacion", "invoice", "billing", "pago"],
        ),
        (
            "Gestion de Clientes (CRM)",
            "El CRM guarda historial de clientes, contactos, oportunidades "
            "y telefonos. Se pueden agregar notas, registrar interacciones "
            "y ver el historial completo de cada cliente. Tambien se pueden "
            "exportar listas de clientes.",
            "business",
            ["crm", "clientes", "contactos", "client", "customer", "lead"],
        ),
        (
            "Inventario y Productos",
            "Gestiona el inventario de productos: entradas, salidas, "
            "ajustes y transferencias. Consulta stock en tiempo real, "
            "recibe alertas de stock minimo y genera reportes de inventario.",
            "business",
            ["inventario", "stock", "productos", "almacen", "warehouse"],
        ),
        (
            "Pedidos y Ventas",
            "Crea y consulta pedidos de clientes. Cada pedido tiene "
            "estado (pendiente, confirmado, enviado, entregado), total "
            "y metodo de pago. Se pueden reenviar facturas de pedidos "
            "y consultar el historial de ventas.",
            "business",
            ["pedido", "venta", "order", "sale", "compra", "purchase"],
        ),
        (
            "Reportes y Dashboard",
            "Genera reportes de ventas, inventario, clientes y "
            "rendimiento. Los reportes se pueden ver en el dashboard "
            "o descargar en PDF/Excel. Incluye graficos comparativos "
            "y tendencias.",
            "business",
            ["reporte", "dashboard", "report", "estadistica", "grafico"],
        ),
        (
            "Notificaciones y Alertas",
            "El sistema envia notificaciones por WhatsApp, Telegram "
            "y correo electronico. Alertas de stock bajo, facturas "
            "vencidas, pedidos pendientes y recordatorios de tareas.",
            "business",
            ["notificacion", "alerta", "notification", "alert", "recordatorio"],
        ),
    ]

    for title, content, category, keywords in concepts:
        kb.store_concept(
            title=title,
            content=content,
            category=category,
            tags=keywords,
            keywords=keywords,
        )

    logger.info(f"Conocimiento base cargado: {len(concepts)} entradas")
