"""
Tipos de intencion del asistente.

Extiende los tipos de Zenic-Agents con categorias de intencion
orientadas a conversacion: chat, preguntas, comandos, tareas,
configuracion y feedback.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class IntentCategory(str, Enum):
    """
    Categorias de intencion del asistente.

    Clasifica la intencion del usuario en categorias de negocio
    y conversacionales. Sin categorias de codigo — el sistema
    esta enfocado en automatizacion empresarial.
    """

    # Conversacionales
    CHAT = "chat"  # Conversacion general
    QUESTION = "question"  # Pregunta factual o explicativa
    COMMAND = "command"  # Comando directo (ej: "limpiar", "reset")
    FEEDBACK = "feedback"  # Feedback del usuario sobre respuesta
    CONFIG = "config"  # Cambio de configuracion

    # Operaciones de negocio (locales, no requieren ZenicOrchestrator)
    INVOICE = "invoice"  # Facturacion, pagos, estados de cuenta
    CRM = "crm"  # Clientes, contactos, relaciones
    INVENTORY = "inventory"  # Inventario, productos, stock
    REPORT = "report"  # Reportes, metricas, dashboards
    SCHEDULING = "scheduling"  # Citas, agendas, recordatorios
    BUSINESS = "business"  # Otras operaciones de negocio no categorizadas

    # Automatizaciones avanzadas (requieren ZenicOrchestrator)
    AUTOMATION = "automation"  # Automatizaciones, workflows avanzados
    CODE = "code"  # Generacion de codigo, scripts, automatizaciones tecnicas

    # Especiales
    UNKNOWN = "unknown"  # No se pudo clasificar
    MULTI = "multi"  # Multiples intenciones en un mensaje


class ConversationMode(str, Enum):
    """Modo de conversacion del asistente."""

    NORMAL = "normal"  # Conversacion estandar
    BUSINESS = "business"  # Modo enfocado en operaciones de negocio
    REASONING = "reasoning"  # Modo de razonamiento paso a paso
    TEACHING = "teaching"  # Modo de ensenanza/explicacion
    AUTOMATION = "automation"  # Configuracion de automatizaciones


@dataclass
class AssistantIntent:
    """
    Intencion detectada del usuario en contexto de asistente.

    Combina la clasificacion original de Zenic-Agents con
    las nuevas categorias conversacionales.
    """

    category: IntentCategory = IntentCategory.UNKNOWN
    operation: str = ""  # Operacion original de Zenic-Agents (CREATE, etc.)
    goal: str = ""  # Goal original (FEATURE_ADD, etc.)
    confidence: float = 0.0
    mode: ConversationMode = ConversationMode.NORMAL
    entities: dict[str, Any] = field(default_factory=dict)
    raw_text: str = ""
    language: str = "es"
    source: str = "deterministic"

    @property
    def is_conversational(self) -> bool:
        """True si la intencion es puramente conversacional."""
        return self.category in (
            IntentCategory.CHAT,
            IntentCategory.QUESTION,
            IntentCategory.FEEDBACK,
            IntentCategory.CONFIG,
        )

    @property
    def is_business_operation(self) -> bool:
        """True si la intencion involucra una operacion de negocio LOCAL.

        Estas operaciones se manejan directamente por ConversationEngine
        con ToolManager, NO requieren ZenicOrchestrator.
        """
        return self.category in (
            IntentCategory.INVOICE,
            IntentCategory.CRM,
            IntentCategory.INVENTORY,
            IntentCategory.REPORT,
            IntentCategory.SCHEDULING,
            IntentCategory.BUSINESS,
        )

    @property
    def is_advanced_operation(self) -> bool:
        """True si la intencion necesita el motor avanzado (ZenicOrchestrator).

        Automatizaciones complejas y generacion de codigo requieren
        el pipeline completo de ZenicOrchestrator via ZenicBridge.
        """
        return self.category in (
            IntentCategory.AUTOMATION,
            IntentCategory.CODE,
        )

    @property
    def needs_engine(self) -> bool:
        """True si necesita pasar por un motor externo.

        - Business operations → NO, se manejan localmente
        - Advanced operations (CODE, AUTOMATION) → SÍ, via ZenicBridge
        """
        return self.is_advanced_operation

    def to_business_action(self) -> str:
        """Mapea la categoria a una accion de negocio."""
        mapping = {
            IntentCategory.INVOICE: "GENERATE_INVOICE",
            IntentCategory.CRM: "MANAGE_CRM",
            IntentCategory.INVENTORY: "CHECK_INVENTORY",
            IntentCategory.REPORT: "GENERATE_REPORT",
            IntentCategory.SCHEDULING: "MANAGE_SCHEDULE",
            IntentCategory.BUSINESS: "PROCESS_BUSINESS",
            IntentCategory.AUTOMATION: "RUN_AUTOMATION",
        }
        return mapping.get(self.category, "SEARCH")


@dataclass
class IntentResult:
    """Resultado del proceso de deteccion de intencion."""

    intent: AssistantIntent = field(default_factory=AssistantIntent)
    alternative_intents: list[AssistantIntent] = field(default_factory=list)
    context_keywords: list[str] = field(default_factory=list)
    source: str = "deterministic"
    processing_time_ms: float = 0.0


# ─── Busqueda de intenciones de negocio ───────────────────────

BUSINESS_INTENTS: set[IntentCategory] = {
    IntentCategory.INVOICE,
    IntentCategory.CRM,
    IntentCategory.INVENTORY,
    IntentCategory.REPORT,
    IntentCategory.SCHEDULING,
}

BUSINESS_INTENT_NAMES: dict[IntentCategory, str] = {
    IntentCategory.INVOICE: "facturación",
    IntentCategory.CRM: "clientes",
    IntentCategory.INVENTORY: "inventario",
    IntentCategory.REPORT: "reportes",
    IntentCategory.SCHEDULING: "agendamiento",
}
