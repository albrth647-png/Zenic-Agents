"""
Motor de intencion multi-capa del Asistente.

Reemplaza el IntentClassifier de keyword matching simple
con un sistema de clasificacion en capas:

  Layer 1: Keyword scoring (rapido, determinista)
  Layer 2: Pattern matching (regex + estructura)
  Layer 3: Context-aware (historial + memoria)
  Layer 4: LLM refinement (opcional, solo si confianza baja)

Cada capa refina el resultado de la anterior.
Layer 4 usa Qwen para clasificar cuando los keywords no alcanzan
el umbral de confianza. VORTEX valida la respuesta del LLM.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from ..types.base import Ok, Result
from ..types.intent import AssistantIntent, ConversationMode, IntentCategory

if TYPE_CHECKING:
    from ..input.enricher import EnrichedInput
    from ..input.parser import ParsedInput
    from ..types.session import Session

# ─── Score por capa ──────────────────────────────────────────


@dataclass
class IntentScore:
    """Score de una categoria en una capa especifica."""

    category: IntentCategory = IntentCategory.UNKNOWN
    score: float = 0.0
    layer: int = 0  # 1=keyword, 2=pattern, 3=context
    evidence: list[str] = field(default_factory=list)


# ─── Layer 1: Keyword Scoring ────────────────────────────────

_KEYWORD_MAP: dict[IntentCategory, tuple[list[str], float]] = {
    IntentCategory.CHAT: (
        ["hola", "hey", "hi", "hello", "buenos", "buenas", "gracias", "thanks", "ok", "bien", "perfecto"],
        2.0,
    ),
    IntentCategory.QUESTION: (
        [
            "que es",
            "que significa",
            "como se",
            "por que",
            "what is",
            "how does",
            "why",
            "explain",
            "explica",
            "cual es la diferencia",
            "difference between",
            "definicion",
            "definition",
        ],
        2.5,
    ),
    IntentCategory.COMMAND: (
        [
            "limpiar",
            "reset",
            "borrar",
            "clear",
            "ayuda",
            "help",
            "comandos",
            "estado",
            "status",
            "salir",
            "exit",
            "stop",
        ],
        2.0,
    ),
    IntentCategory.CONFIG: (
        [
            "configura",
            "ajusta",
            "cambia la personalidad",
            "configure",
            "adjust",
            "change personality",
            "modo tecnico",
            "modo casual",
            "cambiar idioma",
            "cambiar tono",
        ],
        2.5,
    ),
    IntentCategory.FEEDBACK: (
        [
            "no me gusta",
            "mal",
            "incorrecto",
            "wrong",
            "me gusta",
            "bien",
            "correcto",
            "good",
            "intenta de nuevo",
            "try again",
        ],
        2.0,
    ),
    IntentCategory.INVOICE: (
        ["factura", "invoice", "pago", "pagar", "adeudo", "estado de cuenta", "recibo", "cobro", "payment", "debe"],
        3.0,
    ),
    IntentCategory.CRM: (
        ["cliente", "contacto", "crm", "direccion", "registrar", "actualizar datos", "customer", "contact"],
        3.0,
    ),
    IntentCategory.INVENTORY: (
        ["inventario", "stock", "producto", "existencia", "inventory", "disponible", "cuanto hay"],
        3.0,
    ),
    IntentCategory.REPORT: (
        ["reporte", "report", "dashboard", "metricas", "estadisticas", "ventas", "transacciones", "resumen", "kpi"],
        3.0,
    ),
    IntentCategory.SCHEDULING: (
        ["cita", "agendar", "agenda", "recordatorio", "schedule", "appointment", "programar", "calendario", "calendar", "cuando"],
        3.0,
    ),
    IntentCategory.AUTOMATION: (
        ["automatizar", "automate", "workflow", "trigger", "cron", "schedule", "programar tarea"],
        3.0,
    ),
    IntentCategory.BUSINESS: (
        ["negocio", "business", "operacion", "operation", "procesar", "proceso"],
        2.5,
    ),
}


def _layer1_keywords(normalized: str) -> list[IntentScore]:
    """Layer 1: Keyword scoring determinista."""
    scores: list[IntentScore] = []

    for category, (patterns, weight) in _KEYWORD_MAP.items():
        score = 0.0
        evidence: list[str] = []
        for pattern in patterns:
            if pattern in normalized:
                score += weight
                evidence.append(pattern)

        if score > 0:
            scores.append(
                IntentScore(
                    category=category,
                    score=score,
                    layer=1,
                    evidence=evidence,
                )
            )

    return scores


# ─── Layer 2: Pattern Matching ───────────────────────────────

_QUESTION_PATTERNS = [
    re.compile(r"^(que|como|por\s+que|cual|cuando|donde|quien)\b", re.I),
    re.compile(r"^(what|how|why|which|when|where|who)\b", re.I),
    re.compile(r"\?$"),
]

_BUSINESS_PATTERNS = [
    re.compile(r"\b(crear|generar|nueva?)\s+(factura|orden|pedido|folio)", re.I),
    re.compile(r"\b(create|generate|new)\s+(invoice|order|quote)", re.I),
    re.compile(r"\b(consultar|ver|mostrar)\s+(factura|cliente|producto|reporte)", re.I),
    re.compile(r"\b(programar|agendar|reservar)\s+(cita|cita|reunion)", re.I),
]

_COMMAND_PATTERNS = [
    re.compile(r"^/(help|reset|clear|status|config)", re.I),
    re.compile(r"^(limpiar|reset|borrar|ayuda|estado)\s*$", re.I),
]


def _layer2_patterns(text: str, parsed: ParsedInput) -> list[IntentScore]:
    """Layer 2: Pattern matching con regex."""
    scores: list[IntentScore] = []

    # Preguntas
    q_score = 0.0
    q_evidence: list[str] = []
    for pat in _QUESTION_PATTERNS:
        if pat.search(text):
            q_score += 3.0
            q_evidence.append(pat.pattern)
    if parsed.is_question:
        q_score += 2.0
        q_evidence.append("parsed:is_question")
    if q_score > 0:
        scores.append(
            IntentScore(
                category=IntentCategory.QUESTION,
                score=q_score,
                layer=2,
                evidence=q_evidence,
            )
        )

    # Negocio
    b_score = 0.0
    b_evidence: list[str] = []
    for pat in _BUSINESS_PATTERNS:
        if pat.search(text):
            b_score += 3.0
            b_evidence.append(pat.pattern)
    if b_score > 0:
        scores.append(
            IntentScore(
                category=IntentCategory.BUSINESS,
                score=b_score,
                layer=2,
                evidence=b_evidence,
            )
        )

    # Comandos
    if parsed.is_command:
        scores.append(
            IntentScore(
                category=IntentCategory.COMMAND,
                score=5.0,
                layer=2,
                evidence=["parsed:is_command"],
            )
        )

    return scores


# ─── Layer 3: Context-Aware ──────────────────────────────────


def _layer3_context(
    enriched: EnrichedInput,
    base_scores: dict[IntentCategory, float],
) -> list[IntentScore]:
    """Layer 3: Ajusta scores basado en contexto conversacional."""
    adjustments: list[IntentScore] = []

    # Si es continuacion de conversacion sobre negocio
    if enriched.is_continuation:
        recent = " ".join(enriched.recent_topics)
        business_words = [
            "factura",
            "invoice",
            "cliente",
            "customer",
            "inventario",
            "inventory",
            "reporte",
            "report",
            "cita",
            "appointment",
        ]
        if any(w in recent for w in business_words):
            for cat in (
                IntentCategory.INVOICE,
                IntentCategory.CRM,
                IntentCategory.INVENTORY,
                IntentCategory.REPORT,
                IntentCategory.SCHEDULING,
            ):
                if cat in base_scores:
                    adjustments.append(
                        IntentScore(
                            category=cat,
                            score=2.0,
                            layer=3,
                            evidence=["continuation:business_context"],
                        )
                    )

    # Si hay memoria relevante sobre negocio
    for entry in enriched.memory_context[:3]:
        source = entry.get("source", "")
        cat_str = entry.get("category", "")
        if source in ("invoice", "crm", "inventory", "report", "scheduling") or cat_str in ("business", "process"):
            adjustments.append(
                IntentScore(
                    category=IntentCategory.BUSINESS,
                    score=1.0,
                    layer=3,
                    evidence=["memory:business_relevant"],
                )
            )
            break

    return adjustments


# ─── Layer 4: LLM Refinement ─────────────────────────────────

_LLM_CONFIDENCE_THRESHOLD: float = 6.0  # Si max score < 6.0, LLM ayuda
_LLM_BOOST_SCORE: float = 8.0  # Peso de la sugerencia del LLM

# Mapa string → IntentCategory (para validación VORTEX de respuesta LLM)
_CATEGORY_FROM_STR: dict[str, IntentCategory] = {
    c.value.upper(): c for c in IntentCategory
}


def _layer4_llm(
    text: str,
    merged: dict[IntentCategory, float],
    llm_engine: Any | None,  # MiniAIEngine, pero evitamos import circular
) -> list[IntentScore]:
    """
    Layer 4: LLM refinement — solo cuando keywords no alcanzan.

    Si el score máximo con keywords es bajo (< threshold), pregunta
    a Qwen para clasificar. VORTEX valida la respuesta: solo acepta
    categorías reales. Si Qwen alucina o no responde, se ignora.

    Args:
        text: Texto original del mensaje.
        merged: Scores acumulados de L1-L3.
        llm_engine: Instancia de MiniAIEngine (o None si no disponible).

    Returns:
        Lista con 0 o 1 IntentScore (el sugerido por Qwen).
    """
    if llm_engine is None:
        return []

    # Solo activar si la confianza de keywords es baja
    max_score = max(merged.values()) if merged else 0.0
    if max_score >= _LLM_CONFIDENCE_THRESHOLD:
        return []  # Keywords ya tienen suficiente confianza

    # Preguntar a Qwen
    llm_category = llm_engine.classify_intent_llm(text)
    if llm_category is None:
        return []  # Qwen no respondió o respuesta inválida

    # VORTEX validation: solo categorías reales
    cat = _CATEGORY_FROM_STR.get(llm_category)
    if cat is None:
        return []  # Categoría no existe — Qwen alucinó, se ignora

    return [
        IntentScore(
            category=cat,
            score=_LLM_BOOST_SCORE,
            layer=4,
            evidence=[f"llm_classified:{llm_category}"],
        )
    ]


# ─── Intent Engine ────────────────────────────────────────────


class IntentEngine:
    """
    Motor de intencion multi-capa.

    Combina 3 (o 4) capas de clasificacion para producir
    una intencion con confianza calibrada.

    Layer 4 (LLM): Opcional. Se activa solo cuando keywords no
    alcanzan el umbral de confianza. VORTEX valida la respuesta.
    """

    def __init__(self, llm_engine: Any | None = None):
        """
        Args:
            llm_engine: Instancia de MiniAIEngine para Layer 4.
                        Si es None, Layer 4 se omite.
        """
        self._llm_engine = llm_engine

    def classify(
        self,
        enriched: EnrichedInput,
        session: Session | None = None,
    ) -> Result[AssistantIntent, Exception]:
        """
        Clasifica la intencion del mensaje enriquecido.

        Pipeline: L1 keywords → L2 patterns → L3 context → calibrate.
        """
        normalized = enriched.normalized
        text = enriched.text

        # Layer 1: Keywords
        l1_scores = _layer1_keywords(normalized)

        # Layer 2: Patterns
        l2_scores = _layer2_patterns(text, enriched.parsed)

        # Merge scores por categoria
        merged: dict[IntentCategory, float] = {}
        evidence_map: dict[IntentCategory, list[str]] = {}

        for s in l1_scores + l2_scores:
            merged[s.category] = merged.get(s.category, 0.0) + s.score
            if s.category not in evidence_map:
                evidence_map[s.category] = []
            evidence_map[s.category].extend(s.evidence)

        # Layer 3: Context adjustments
        l3_scores = _layer3_context(enriched, merged)
        for s in l3_scores:
            merged[s.category] = merged.get(s.category, 0.0) + s.score
            if s.category not in evidence_map:
                evidence_map[s.category] = []
            evidence_map[s.category].extend(s.evidence)

        # Layer 4: LLM refinement (solo si confianza baja)
        l4_scores = _layer4_llm(text, merged, self._llm_engine)
        for s in l4_scores:
            merged[s.category] = merged.get(s.category, 0.0) + s.score
            if s.category not in evidence_map:
                evidence_map[s.category] = []
            evidence_map[s.category].extend(s.evidence)

        # Determinar mejor categoria
        if not merged:
            category = IntentCategory.CHAT
            confidence = 0.3
        else:
            category = max(merged, key=merged.get)  # type: ignore
            max_score = merged[category]
            confidence = min(max_score / 10.0, 1.0)

        # Inferir modo
        mode = self._infer_mode(category, normalized)

        # Construir resultado
        intent = AssistantIntent(
            category=category,
            confidence=confidence,
            mode=mode,
            raw_text=text,
            language=enriched.sanitized.detected_language,
            source="multi_layer",
            entities={
                "evidence": evidence_map.get(category, []),
                "all_scores": {c.value: round(s, 2) for c, s in merged.items()},
                "conversation_turn": enriched.conversation_turn,
            },
        )

        return Ok(intent)

    @staticmethod
    def _infer_mode(category: IntentCategory, text: str) -> ConversationMode:
        """Infiere el modo de conversacion."""
        if category in (
            IntentCategory.INVOICE,
            IntentCategory.CRM,
            IntentCategory.INVENTORY,
            IntentCategory.REPORT,
            IntentCategory.SCHEDULING,
            IntentCategory.BUSINESS,
        ):
            return ConversationMode.BUSINESS

        if category == IntentCategory.QUESTION:
            step_words = ["paso a paso", "step by step", "explica", "explain"]
            if any(w in text for w in step_words):
                return ConversationMode.TEACHING
            return ConversationMode.REASONING

        if category == IntentCategory.AUTOMATION:
            return ConversationMode.AUTOMATION

        return ConversationMode.NORMAL
