"""
Gestor de personalidad del asistente.

Maneja perfiles de personalidad empresariales, permite cambiar entre
presets de negocio y crear perfiles personalizados.

Fase 4 + Fase 5: Los presets son perfiles empresariales:
  - business_default: Profesional-cálido, "usted"
  - retail: Cercano, rápido, "tú"
  - corporate: Formal, preciso
  - healthcare: Empático, pausado
  - logistics: Directo, técnico-preciso

Fase 5: El BlueprintAdapter puede configurar automaticamente
la personalidad segun el dominio del tenant.
"""

from __future__ import annotations

import logging

from .types.personality import (
    PERSONALITY_PRESETS,
    LanguagePreference,
    PersonalityProfile,
    ToneLevel,
)

logger = logging.getLogger("zenic_agents.conversational.personality")


class PersonalityManager:
    """
    Gestiona los perfiles de personalidad empresariales.

    Permite:
      - Obtener perfiles predefinidos (business_default, retail, corporate, etc.)
      - Crear perfiles personalizados
      - Cambiar tono e idioma en runtime
      - Generar system prompts basados en personalidad
      - Ser configurado por BlueprintAdapter segun el dominio del tenant
    """

    def __init__(self) -> None:
        self._profiles: dict[str, PersonalityProfile] = {}
        self._default_name: str = "business_default"
        self._load_presets()

    def _load_presets(self) -> None:
        """Carga los presets empresariales predefinidos."""
        for name in PERSONALITY_PRESETS:
            self._profiles[name] = PersonalityProfile.from_preset(name)
        logger.info(f"Perfiles de personalidad cargados: {list(self._profiles.keys())}")

    # ─── Lectura ──────────────────────────────────────────────

    def get(self, name: str) -> PersonalityProfile | None:
        """Obtiene un perfil por nombre."""
        return self._profiles.get(name)

    def get_default(self) -> PersonalityProfile:
        """Obtiene el perfil por defecto."""
        return self._profiles.get(
            self._default_name,
            PersonalityProfile(),
        )

    def list_profiles(self) -> list[str]:
        """Lista los nombres de perfiles disponibles."""
        return list(self._profiles.keys())

    def get_profile_info(self, name: str) -> dict:
        """Obtiene informacion resumida de un perfil."""
        profile = self._profiles.get(name)
        if profile is None:
            return {"error": f"Perfil '{name}' no encontrado"}
        return {
            "name": profile.name,
            "tone": profile.tone.value,
            "language": profile.language.value,
            "detail_level": profile.detail_level,
            "traits": profile.traits,
            "greeting": profile.greeting,
        }

    # ─── Modificacion ─────────────────────────────────────────

    def set_default(self, name: str) -> bool:
        """Cambia el perfil por defecto. Retorna True si existe."""
        if name in self._profiles:
            self._default_name = name
            logger.info(f"Personalidad por defecto cambiada a: {name}")
            return True
        return False

    def create_profile(self, profile: PersonalityProfile) -> None:
        """Crea o reemplaza un perfil personalizado."""
        self._profiles[profile.name] = profile
        logger.info(f"Perfil creado/actualizado: {profile.name}")

    def update_tone(self, name: str, tone: ToneLevel) -> bool:
        """Actualiza el tono de un perfil existente."""
        profile = self._profiles.get(name)
        if profile is None:
            return False
        profile.tone = tone
        return True

    def update_language(self, name: str, lang: LanguagePreference) -> bool:
        """Actualiza el idioma de un perfil existente."""
        profile = self._profiles.get(name)
        if profile is None:
            return False
        profile.language = lang
        return True

    def set_custom_instructions(self, name: str, instructions: str) -> bool:
        """Establece instrucciones personalizadas para un perfil."""
        profile = self._profiles.get(name)
        if profile is None:
            return False
        profile.custom_instructions = instructions
        return True

    # ─── System prompt ────────────────────────────────────────

    def build_system_prompt(
        self,
        personality_name: str | None = None,
        session_context: str = "",
    ) -> str:
        """
        Construye el system prompt completo para una sesion.

        Combina:
          1. System prompt base del asistente
          2. Sufijo de personalidad
          3. Contexto de sesion (si hay)
        """
        profile = self._profiles.get(
            personality_name or self._default_name,
            PersonalityProfile(),
        )            # Base prompt — identidad empresarial (Fase 1)
        # {{empresa}} es un placeholder para reemplazo externo por el nombre real
        base = (
            "Eres Zenic, el sistema operativo de automatización empresarial. "
            "Tu propósito es automatizar procesos de negocio: facturación, CRM, "
            "inventario, reportes, tareas y más. Estás integrado en {{empresa}} "
            "para ayudar a sus clientes y equipos. Eres profesional, amable y "
            "resolutivo.\n\n"
            "ESCRIBE COMO HUMANO, NO COMO ASISTENTE VIRTUAL:\n"
            "- Usa contracciones SIEMPRE: 'no voy', 'está bien', 'dame un segundo'\n"
            "- Varía la longitud de tus oraciones: mezcla cortas, medias y largas\n"
            "- Empieza con naturalidad: 'Bueno...', 'A ver...', 'Mira...'\n"
            "- Sé empático cuando la situación lo requiera\n"
            "- Usa el tono que corresponda según el perfil (casual, profesional, etc.)\n"
            "- NUNCA uses frases hechas de IA como 'Es importante destacar', "
            "'Cabe mencionar', 'En el mundo actual'\n"
            "- Suena a persona real, no a chatbot\n\n"
        )

        # Personality suffix
        suffix = profile.get_system_prompt_suffix()

        # Session context
        context_part = ""
        if session_context:
            context_part = f"\n\nContexto de la sesion:\n{session_context}"

        return base + suffix + context_part
