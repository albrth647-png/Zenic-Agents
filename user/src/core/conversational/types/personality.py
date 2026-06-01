"""
Tipos de personalidad y tono del asistente.

Modela el perfil de personalidad configurable que define
como responde el asistente: tono, idioma, nivel tecnico.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ToneLevel(str, Enum):
    """Niveles de tono del asistente."""

    CASUAL = "casual"  # Informal, amigable — max humanizacion
    PROFESSIONAL = "professional"  # Profesional, directo — humanizacion moderada
    TECHNICAL = "technical"  # Tecnico, detallado — precision con voz humana
    FRIENDLY = "friendly"  # Calido, cercano — alta humanizacion
    FORMAL = "formal"  # Formal, respetuoso — humanizacion sutil


class LanguagePreference(str, Enum):
    """Preferencia de idioma del usuario."""

    SPANISH = "es"
    ENGLISH = "en"
    BILINGUAL = "bi"  # Responde en el idioma de la pregunta


# ─── Personalidades predefinidas ─────────────────────────────

PERSONALITY_PRESETS: dict[str, dict[str, Any]] = {
    "business_default": {
        "name": "Asistente Empresarial",
        "description": "Perfil profesional-cálido — ideal para cualquier empresa. Tono 'usted' con cercanía.",
        "default_tone": "professional",
        "greeting_es": "Buen día, soy el asistente de {{empresa}}. Puedo ayudarle con facturación, clientes, inventario, reportes y más. ¿En qué puedo servirle?",
        "greeting_en": "Good day, I'm the {{company}} assistant. I can help with invoicing, CRM, inventory, reports and more. How may I assist you?",
        "traits": ["professional", "warm", "bilingual", "reliable"],
    },
    "retail": {
        "name": "Asistente Comercial",
        "description": "Perfil cercano y rápido — ideal para tiendas y e-commerce. Tono 'tú' directo.",
        "default_tone": "friendly",
        "greeting_es": "¡Qué onda! Soy el asistente de {{empresa}}. ¿Vas a hacer un pedido, checar tu factura o necesitas ayuda con algo?",
        "greeting_en": "Hey there! I'm the {{company}} assistant. Placing an order, checking an invoice, or need help with something?",
        "traits": ["friendly", "fast", "direct", "bilingual"],
    },
    "corporate": {
        "name": "Asistente Corporativo",
        "description": "Perfil formal y preciso — ideal para empresas grandes y fintech. Tono 'usted' formal.",
        "default_tone": "formal",
        "greeting_es": "Bienvenido al sistema corporativo de {{empresa}}. Estoy a su disposición para procesar facturación, reportes ejecutivos, gestión de cuentas y más.",
        "greeting_en": "Welcome to {{company}} corporate system. I am at your service for invoice processing, executive reports, account management and more.",
        "traits": ["formal", "precise", "professional", "bilingual"],
    },
    "healthcare": {
        "name": "Asistente de Salud",
        "description": "Perfil empático y pausado — ideal para clínicas y salud. Tono 'usted' cuidadoso.",
        "default_tone": "professional",
        "greeting_es": "Hola, soy el asistente de {{empresa}}. Estoy aquí para ayudarle con agendar citas, recordatorios, consultar resultados y todo lo que necesite con la calidez que merece.",
        "greeting_en": "Hello, I'm the {{company}} assistant. I'm here to help with appointments, reminders, test results and anything you need with the care you deserve.",
        "traits": ["empathetic", "patient", "caring", "bilingual"],
    },
    "logistics": {
        "name": "Asistente Logístico",
        "description": "Perfil directo y técnico-preciso — ideal para logística y transporte. Tono 'usted' sin rodeos.",
        "default_tone": "technical",
        "greeting_es": "Sistema de logística de {{empresa}} activo. Puedo consultar envíos, estatus de rutas, inventario de almacén y reportes operativos. ¿Qué necesita?",
        "greeting_en": "{{company}} logistics system active. I can check shipments, route status, warehouse inventory and operational reports. What do you need?",
        "traits": ["direct", "precise", "efficient", "bilingual"],
    },
}


@dataclass
class PersonalityProfile:
    """
    Perfil de personalidad del asistente.

    Define como el asistente se comunica: tono, idioma,
    nivel de detalle, saludo y rasgos de personalidad.
    """

    name: str = "business_default"
    tone: ToneLevel = ToneLevel.PROFESSIONAL
    language: LanguagePreference = LanguagePreference.BILINGUAL
    detail_level: int = 2  # 1=conciso, 2=normal, 3=detallado
    use_emoji: bool = False  # Usar emojis en respuestas
    code_comments: bool = True  # Incluir comentarios en codigo
    greeting: str = ""
    traits: list[str] = field(default_factory=lambda: ["helpful", "precise", "bilingual"])
    custom_instructions: str = ""  # Instrucciones adicionales del usuario
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Carga preset si el nombre coincide con uno predefinido."""
        if self.name in PERSONALITY_PRESETS and not self.greeting:
            preset = PERSONALITY_PRESETS[self.name]
            lang_key = "greeting_es" if self.language != LanguagePreference.ENGLISH else "greeting_en"
            self.greeting = preset.get(lang_key, "")
            self.traits = preset.get("traits", self.traits)
            if "default_tone" in preset:
                self.tone = ToneLevel(preset["default_tone"])

    @property
    def is_bilingual(self) -> bool:
        return self.language == LanguagePreference.BILINGUAL

    @property
    def is_technical(self) -> bool:
        return self.tone == ToneLevel.TECHNICAL

    @property
    def is_concise(self) -> bool:
        return self.detail_level == 1

    def get_system_prompt_suffix(self) -> str:
        """
        Genera un sufijo para el system prompt basado en la personalidad.

        HUMANIZADO: Cada tono incluye instrucciones de escritura humana
        ademas de las reglas de comportamiento. El objetivo es que el
        sistema suene a persona real, no a asistente virtual.
        """
        parts: list[str] = []

        # Tono + humanizacion
        tone_humanization = {
            ToneLevel.CASUAL: (
                "ESCRIBE COMO HUMANO (tono CASUAL):\n"
                "- Usa contracciones SIEMPRE: 'no voy', 'está bien', 'dame un segundo'\n"
                "- Máximo coloquialismo: 'dale', 'qué onda', 'la neta', 'simón'\n"
                "- Frases cortas e incompletas: 'Listo. Ahí está. Next.'\n"
                "- Emojis SIEMPRE que tenga sentido\n"
                "- Opiniones fuertes: 'La neta esta opción es la mejor'\n"
                "- NUNCA uses: 'es importante destacar', 'cabe mencionar', 'por otro lado'"
            ),
            ToneLevel.FRIENDLY: (
                "ESCRIBE COMO HUMANO (tono FRIENDLY):\n"
                "- Usa contracciones NATURALES: 'no voy', 'está bien', 'dame un segundo'\n"
                "- Coloquialismo moderado: 'vale', 'qué bien', 'claro que sí'\n"
                "- Mezcla frases cortas con medias\n"
                "- Emojis SÍ, con moderación\n"
                "- Opiniones suaves: 'La verdad, creo que esta opción es la mejor'\n"
                "- NUNCA uses: frases hechas de asistente virtual"
            ),
            ToneLevel.PROFESSIONAL: (
                "ESCRIBE COMO HUMANO (tono PROFESSIONAL):\n"
                "- Usa contracciones MODERADAS: 'no pude', 'está listo', 'le explico'\n"
                "- Coloquialismo MÍNIMO: 'perfecto', 'excelente', 'por supuesto'\n"
                "- Longitud balanceada: mezcla cortas con largas\n"
                "- Emojis NO (excepto canales informales como WhatsApp)\n"
                "- Opiniones calificadas: 'En mi experiencia, esta suele ser la mejor opción'\n"
                "- Suena a consultor experto, no a manual técnico"
            ),
            ToneLevel.TECHNICAL: (
                "ESCRIBE COMO HUMANO (tono TECHNICAL):\n"
                "- Usa contracciones SÍ: 'no va a funcionar', 'está usando'\n"
                "- Vocabulario técnico pero natural\n"
                "- Precisión ante todo, pero con ritmo variable\n"
                "- Emojis NO\n"
                "- Opiniones técnicas: 'No recomendaría esa config porque... mejor haz esto'\n"
                "- Suena a ingeniero explicando, no a documentación"
            ),
            ToneLevel.FORMAL: (
                "ESCRIBE COMO HUMANO (tono FORMAL):\n"
                "- Contracciones MÍNIMAS pero no cero: 'no fue posible', 'estaremos'\n"
                "- Sin coloquialismos\n"
                "- Estructura cuidada pero con ritmo natural\n"
                "- Emojis NO\n"
                "- Sin opiniones explícitas\n"
                "- Suena a ejecutivo profesional, no a automated message"
            ),
        }
        parts.append(tone_humanization.get(self.tone, tone_humanization[ToneLevel.PROFESSIONAL]))

        # Idioma
        if self.language == LanguagePreference.SPANISH:
            parts.append("Responde SIEMPRE en español.")
        elif self.language == LanguagePreference.ENGLISH:
            parts.append("Always respond in English.")
        else:
            parts.append("Responde en el mismo idioma en que te hablen (español o inglés).")

        # Nivel de detalle
        detail_map = {
            1: "Sé conciso. Respuestas cortas y al punto, como un mensaje de WhatsApp.",
            2: "Extensión normal. Da contexto sin enrollarte, como un colega explicando algo.",
            3: "Sé detallado. Explica bien, con ejemplos, como un experto asesorando.",
        }
        parts.append(detail_map.get(self.detail_level, detail_map[2]))

        # Emojis
        if self.use_emoji:
            parts.append("Puedes usar emojis para darle más expresión a las respuestas, pero sin exagerar.")

        # Custom instructions
        if self.custom_instructions:
            parts.append(f"Instrucciones del usuario: {self.custom_instructions}")

        return "\n\n".join(parts)

    @classmethod
    def from_preset(cls, name: str) -> PersonalityProfile:
        """Crea un perfil desde un preset predefinido."""
        preset = PERSONALITY_PRESETS.get(name, PERSONALITY_PRESETS["business_default"])
        return cls(
            name=name,
            tone=ToneLevel(preset.get("default_tone", "professional")),
            traits=preset.get("traits", ["professional", "warm", "bilingual", "reliable"]),
        )
