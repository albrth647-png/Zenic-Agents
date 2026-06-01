"""
Generador de respuestas conversacionales humanizadas.

HUMANIZADO: Cada respuesta suena a persona real de negocio,
no a asistente de codigo. Usa contracciones, ritmo variable,
y vocabulario de facturacion, CRM, inventario y reportes.

Fase 5: Las respuestas se adaptan segun las capacidades del
Blueprint del tenant (facturacion, CRM, inventario, etc.)
y reemplazan {{empresa}} por el nombre real de la empresa.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..types.personality import PersonalityProfile
    from ..types.session import Session


class ResponseGenerator:
    """
    Genera respuestas conversacionales con voz humana.

    Cada metodo retorna texto que suena a persona real:
    con contracciones, ritmo variable, opinion y empatia.
    Soporta adaptacion por tenant via blueprint_capabilities.
    """

    # ─── Helpers ──────────────────────────────────────────────

    def _resolve_company_name(self, session: Session) -> str:
        """Resuelve el nombre de la empresa desde la config de sesion.
        Si no hay tenant configurado, retorna 'la empresa' generico."""
        company = session.config.company_name or ""
        lang = session.config.language
        if not company:
            return "la empresa" if lang == "es" else "the company"
        return company

    def _build_capabilities_text(self, session: Session) -> str:
        """Construye texto de capacidades desde los blueprints del tenant.
        Si no hay capacidades configuradas, usa las genericas."""
        capabilities = session.config.blueprint_capabilities
        if capabilities:
            from ..blueprint_adapter import BlueprintAdapter
            return BlueprintAdapter.format_capabilities_for_prompt(
                capabilities,
                language=session.config.language,
            )
        # Fallback generico
        lang = session.config.language
        if lang == "es":
            return (
                "📋 **Facturas** — Consultar, crear, enviar\n"
                "📦 **Pedidos** — Estado, historial, seguimiento\n"
                "👤 **CRM** — Clientes, contactos, oportunidades\n"
                "📊 **Reportes** — Ventas, inventario, rendimiento\n"
                "⚙️ **Tareas** — Agendar, recordatorios, workflows"
            )
        return (
            "📋 **Invoices** — Check, create, send\n"
            "📦 **Orders** — Status, history, tracking\n"
            "👤 **CRM** — Clients, contacts, opportunities\n"
            "📊 **Reports** — Sales, inventory, performance\n"
            "⚙️ **Tasks** — Schedule, reminders, workflows"
        )

    def _resolve_capabilities_list(self, session: Session) -> str:
        """Lista corta de capacidades para saludos y errores."""
        capabilities = session.config.blueprint_capabilities
        if capabilities:
            names = [c.get("name", "") for c in capabilities[:5]]
            return ", ".join(names)
        lang = session.config.language
        if lang == "es":
            return "facturas, pedidos, CRM, reportes, tareas y más"
        return "invoices, orders, CRM, reports, tasks and more"

    # ─── Chat general ─────────────────────────────────────────

    def generate_chat(self, text: str, profile: PersonalityProfile, session: Session) -> str:
        """Genera respuesta humanizada para chat general."""
        company = self._resolve_company_name(session)
        capabilities_text = self._build_capabilities_text(session)
        cap_list = self._resolve_capabilities_list(session)

        greetings = [
            "hola",
            "hey",
            "hi",
            "hello",
            "buenos",
            "buenas",
            "que tal",
            "how are you",
        ]
        if any(g in text for g in greetings):
            lang = session.config.language
            if lang == "es":
                return (
                    f"¡Hola! Soy el asistente de {company}. "
                    f"Puedo ayudarte con {cap_list}. "
                    "¿Qué necesitas?"
                )
            return (
                f"Hi! I'm the {company} assistant. "
                f"I can help with {cap_list}. "
                "What do you need?"
            )

        thanks = ["gracias", "thanks", "thank you", "ty"]
        if any(t in text for t in thanks):
            return "¡De nada! Para eso estamos. ¿Necesitas algo más o ahí la dejamos?"

        ok_words = ["ok", "bien", "perfecto", "genial", "great"]
        if any(o in text for o in ok_words):
            return "¡Perfecto! Ahí andamos para lo que se ofrezca."

        # Default conversacional humanizado — muestra capacidades
        lang = session.config.language
        if lang == "es":
            return (
                "No estoy seguro de cómo ayudarte con eso. "
                "Estas son las cosas que puedo hacer:\n\n"
                f"{capabilities_text}\n\n"
                "¿Qué se te ofrece?"
            )
        return (
            "I'm not sure how to help with that. "
            "Here's what I can do:\n\n"
            f"{capabilities_text}\n\n"
            "What do you need?"
        )

    # ─── Preguntas ────────────────────────────────────────────

    def generate_question(self, message: str, profile: PersonalityProfile) -> str:
        """Genera respuesta humanizada para preguntas."""
        lang = profile.language
        if lang and str(lang) != "es":
            return (
                f"Good question! Let me look into that for you.\n\n"
                f"You asked about: *{message}*\n\n"
                "Give me a sec to check the system and I'll get back to you with "
                "what I find. Sound good?"
            )
        return (
            "¡Buena pregunta! Déjame revisarlo en el sistema.\n\n"
            f"Me preguntaste sobre: *{message}*\n\n"
            "Dame un segundo para consultarlo y te digo qué encontré. ¿Va?"
        )

    # ─── Comandos ─────────────────────────────────────────────

    def handle_command(self, text: str, session: Session) -> str:
        """Maneja comandos directos con respuestas humanas."""
        if any(w in text for w in ["limpiar", "clear", "reset"]):
            session.messages = [m for m in session.messages if m.is_system]
            return "¡Listo! Historial limpiado. Empezamos de nuevo."

        if any(w in text for w in ["ayuda", "help", "comandos"]):
            return (
                "Aquí te van los comandos que puedes usar:\n\n"
                "- `limpiar` / `reset` — Borrar historial\n"
                "- `ayuda` / `help` — Mostrar esta ayuda\n"
                "- `cambiar idioma es|en` — Cambiar idioma\n"
                "- `cambiar tono casual|profesional|tecnico` — Cambiar tono\n"
                "- `personalidad business_default|retail|corporate|healthcare|logistics` — Cambiar personalidad\n"
                "- `estado` — Ver cómo vamos\n"
            )

        if "estado" in text:
            return (
                f"Aquí te va el estado de la sesión:\n"
                f"- Mensajes: {session.message_count}\n"
                f"- Estado: {session.state.value}\n"
                f"- Idioma: {session.config.language}\n"
                f"- Tono: {session.config.tone}\n"
            )

        return "Ese comando no lo conozco. Prueba con `ayuda` para ver los que tengo."

    # ─── Configuracion ────────────────────────────────────────

    def handle_config(self, text: str, session: Session) -> str:
        """Maneja cambios de configuracion con respuestas humanas."""
        if "idioma" in text or "language" in text:
            if "en" in text or "english" in text or "ingles" in text:
                session.config.language = "en"
                return "Changed to English. All set!"
            elif "es" in text or "spanish" in text or "espanol" in text:
                session.config.language = "es"
                return "Cambiado a español. ¡Listo!"

        if "tono" in text or "tone" in text:
            if "casual" in text:
                session.config.tone = "casual"
                return "Tono cambiado a casual. ¡A darle!"
            elif "tecnico" in text or "technical" in text:
                session.config.tone = "technical"
                return "Tono cambiado a técnico. Ahí está el detalle."
            elif "profesional" in text or "professional" in text:
                session.config.tone = "professional"
                return "Tono cambiado a profesional. ¡A darle!"

        if "personalidad" in text or "personality" in text:
            # Mapa de nombres cortos a presets empresariales (Fase 4)
            business_presets = {
                "business_default": "business_default",
                "default": "business_default",
                "retail": "retail",
                "corporate": "corporate",
                "healthcare": "healthcare",
                "logistics": "logistics",
            }
            for alias, preset in business_presets.items():
                if alias in text or preset in text:
                    session.config.personality_name = preset
                    return f"¡Listo! Personalidad cambiada a {preset}."

        return (
            "Esa configuración no la reconozco. Las opciones son:\n"
            "- `cambiar idioma es|en`\n"
            "- `cambiar tono casual|profesional|tecnico`\n"
            "- `personalidad business_default|retail|corporate|healthcare|logistics`"
        )

    # ─── Feedback ─────────────────────────────────────────────

    def handle_feedback(self, text: str, profile: PersonalityProfile) -> str:
        """Maneja feedback del usuario con empatía genuina."""
        positive = ["bien", "bueno", "correcto", "me gusta", "good", "great"]
        negative = ["mal", "incorrecto", "no me gusta", "wrong", "bad"]

        if any(p in text for p in positive):
            return "¡Qué bien! Me alegra que haya servido. ¿Necesitas algo más?"

        if any(n in text for n in negative):
            return (
                "Ay, qué mal que no fue lo que esperabas. "
                "Déjame intentarlo de nuevo con otro enfoque. "
                "¿Qué le cambiarías?"
            )

        return "¡Gracias por tu opinión! La neta eso ayuda caldísimo a mejorar."

    # ─── Resultados de negocio ────────────────────────────────

    @staticmethod
    def generate_business_result(
        operation: str,
        details: dict | None = None,
        language: str = "es",
    ) -> str:
        """Genera respuesta humanizada para resultados de operaciones de negocio.

        Args:
            operation: Tipo de operación (invoice, crm, report, error, etc.)
            details: Diccionario con detalles específicos de la operación
            language: Idioma de la respuesta

        Returns:
            Texto con voz humana según el tipo de operación.
        """
        details = details or {}

        if operation == "invoice":
            inv_id = details.get("id", "0000")
            amount = details.get("amount", "$0.00")
            client = details.get("client", "{{cliente}}")
            if language == "es":
                return (
                    f"He localizado la factura {inv_id} por {amount} a nombre de {client}. "
                    "¿Quieres descargarla, reenviarla o tienes alguna duda?"
                )
            return (
                f"I found invoice {inv_id} for {amount} under {client}. "
                "Do you want to download it, forward it, or do you have any questions?"
            )

        elif operation == "crm":
            client_name = details.get("name", "{{nombre}}")
            action = details.get("action", "actualizado")
            info = details.get("info", "")
            if language == "es":
                base = f"Cliente {client_name} {action} en el CRM."
                if info:
                    base += f" {info}"
                base += " ¿Necesitas algo más?"
                return base
            base = f"Client {client_name} {action} in the CRM."
            if info:
                base += f" {info}"
            base += " Need anything else?"
            return base

        elif operation == "report":
            report_name = details.get("name", "Reporte")
            transactions = details.get("transactions", "0")
            total = details.get("total", "$0.00")
            if language == "es":
                return (
                    f"{report_name} generado. {transactions} transacciones, {total} en ventas. "
                    "Puedes verlo en el dashboard."
                )
            return (
                f"{report_name} generated. {transactions} transactions, {total} in sales. "
                "You can view it on the dashboard."
            )

        elif operation == "error":
            if language == "es":
                return (
                    "Lo siento, no pude procesar esa solicitud. "
                    "¿Quieres que lo intente de nuevo o prefieres hablar con un agente humano?"
                )
            return (
                "Sorry, I couldn't process that request. "
                "Would you like me to try again or would you prefer to speak with a human agent?"
            )

        elif operation == "unknown":
            if language == "es":
                return (
                    "No estoy seguro de cómo ayudarte con eso. "
                    "Estas son las cosas que puedo hacer: facturas, pedidos, "
                    "CRM, reportes, tareas y más. ¿Qué te gustaría hacer?"
                )
            return (
                "I'm not sure how to help with that. "
                "Here's what I can do: invoices, orders, CRM, reports, "
                "tasks and more. What would you like to do?"
            )

        # Fallback genérico
        if language == "es":
            return "Listo, proceso completado. ¿Necesitas algo más?"
        return "Done, process completed. Need anything else?"
