"""
Generador de respuestas conversacionales humanizadas.

HUMANIZADO: Cada respuesta suena a persona real de negocio.
Usa VARIEDAD — múltiples variantes por intención, selección aleatoria.

Fase 5: Las respuestas se adaptan segun las capacidades del
Blueprint del tenant (facturacion, CRM, inventario, etc.)
"""

from __future__ import annotations

import random
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..types.personality import PersonalityProfile
    from ..types.session import Session


# ═══════════════════════════════════════════════════════════════
#  BANCOS DE RESPUESTAS HUMANIZADAS (múltiples variantes)
# ═══════════════════════════════════════════════════════════════

SALUDOS_ES = [
    "¡Hola! Soy el asistente de {empresa}. ¿En qué puedo ayudarte?",
    "¡Qué tal! Aquí el asistente de {empresa}. ¿Cómo va todo?",
    "¡Buenas! Soy el asistente virtual de {empresa}. ¿Qué necesitas?",
    "Hola, soy el asistente de {empresa}. Cuéntame, ¿en qué te ayudo?",
    "¡Hey! {empresa} al habla. ¿Qué se te ofrece?",
]

SALUDOS_EN = [
    "Hi! I'm the {company} assistant. How can I help you?",
    "Hey there! {company} assistant here. What can I do for you?",
    "Hello! I'm the virtual assistant for {company}. How's it going?",
    "Hi! How can I help you today with {company}?",
    "Hey! Welcome to {company}. What do you need help with?",
]

CAPABILITIES_ES = [
    "Puedo ayudarte con facturación, pedidos, clientes, reportes y más. ¿Qué necesitas?",
    "Tengo acceso a facturas, CRM, inventario, reportes y tareas. ¿Por dónde empezamos?",
    "Estas son las cosas que puedo hacer:\n{capacidades}\n\n¿Qué te gustaría?",
    "Mis herramientas: {lista_cap}. ¿Con cuál te ayudo?",
]

CAPABILITIES_EN = [
    "I can help with invoicing, orders, CRM, reports and more. What do you need?",
    "I have access to invoices, CRM, inventory, reports and tasks. Where should we start?",
    "Here's what I can do:\n{capacidades}\n\nWhat would you like?",
    "My tools: {lista_cap}. Which one can I help with?",
]

AGRADECIMIENTOS_ES = [
    "¡De nada! Para eso estamos. ¿Necesitas algo más?",
    "¡Con gusto! Cuando ocupes algo, aquí andamos.",
    "Un placer. Ahí estamos para lo que se ofrezca.",
    "¡A la orden! Cualquier cosa, aquí andamos.",
]

AGRADECIMIENTOS_EN = [
    "You're welcome! Anything else I can help with?",
    "My pleasure! Let me know if you need anything else.",
    "Happy to help! I'm here whenever you need me.",
    "Anytime! Is there anything else I can do for you?",
]

AFIRMACIONES_ES = [
    "¡Perfecto! Ahí andamos para lo que se ofrezca.",
    "¡Listo! Cuando gustes, aquí estamos.",
    "¡Excelente! Cualquier cosa, ya sabes dónde encontrarme.",
    "¡Bien! No dudes en pedir ayuda cuando la necesites.",
]

AFIRMACIONES_EN = [
    "Perfect! I'm here whenever you need me.",
    "Great! Let me know if you need anything else.",
    "Excellent! I'm always here to help.",
    "Awesome! Don't hesitate to ask if you need anything.",
]

NO_ENTIENDO_ES = [
    "No estoy seguro de cómo ayudarte con eso. {capacidades}",
    "Eso no lo tengo muy claro. Déjame decirte lo que sí puedo hacer:\n{capacidades}",
    "No entendí bien. {capacidades}",
]

NO_ENTIENDO_EN = [
    "I'm not sure how to help with that. {capacidades}",
    "I didn't quite get that. Here's what I can do:\n{capacidades}",
    "Not sure about that one. {capacidades}",
]

FEEDBACK_POSITIVO_ES = [
    "¡Qué bien! Me alegra que haya servido. ¿Necesitas algo más?",
    "¡Me da gusto! Para eso estamos. ¿Algo más?",
    "¡Qué chido! Siempre es un placer ayudar. ¿Necesitas algo más?",
]

FEEDBACK_NEGATIVO_ES = [
    "Ay, qué mal que no fue lo que esperabas. Déjame intentarlo de nuevo. ¿Qué le cambiarías?",
    "Oops, no dio en el clavo. Dame más contexto y lo ajusto. ¿Qué esperabas?",
    "Bueno, no siempre sale bien al primer intento. Cuéntame más para afinarlo.",
]


class ResponseGenerator:
    """
    Genera respuestas conversacionales con voz humana y VARIEDAD.

    NOTA SOBRE RENDIMIENTO: Qwen-0.6B corre a ~25-30 tok/s en ARM.
    No se usa el LLM para respuestas simples — solo templates variados.
    """

    # ─── Helpers ──────────────────────────────────────────────

    def _resolve_company_name(self, session: Session) -> str:
        company = session.config.company_name or ""
        if not company:
            return "la empresa" if session.config.language == "es" else "the company"
        return company

    def _build_capabilities_text(self, session: Session) -> str:
        capabilities = session.config.blueprint_capabilities
        if capabilities:
            from ..blueprint_adapter import BlueprintAdapter
            return BlueprintAdapter.format_capabilities_for_prompt(
                capabilities, language=session.config.language,
            )
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
        """Genera respuesta humanizada con VARIEDAD para chat general."""
        company = self._resolve_company_name(session)
        cap_list = self._resolve_capabilities_list(session)

        text_lower = text.lower().strip()

        # ── Saludos con variedad ──
        greetings = ["hola", "hey", "hi", "hello", "buenos", "buenas", "que tal",
                     "how are you", "buen día", "buenas tardes", "qué tal"]
        if any(g in text_lower for g in greetings):
            if session.config.language == "es":
                template = random.choice(SALUDOS_ES)
            else:
                template = random.choice(SALUDOS_EN)
            response = template.format(empresa=company, company=company)
            # Agregar capacidades 50% de las veces (no siempre)
            if random.random() < 0.5:
                cap_texts = CAPABILITIES_ES if session.config.language == "es" else CAPABILITIES_EN
                response += " " + random.choice(cap_texts).format(
                    capacidades=self._build_capabilities_text(session),
                    lista_cap=cap_list,
                )
            return response

        # ── Agradecimientos con variedad ──
        thanks = ["gracias", "thanks", "thank you", "ty", "muchas gracias"]
        if any(t in text_lower for t in thanks):
            pool = AGRADECIMIENTOS_ES if session.config.language == "es" else AGRADECIMIENTOS_EN
            return random.choice(pool)

        # ── Afirmaciones con variedad ──
        affirm = ["ok", "bien", "perfecto", "genial", "great", "okey", "vale", "de acuerdo", "okey dokey"]
        if any(o in text_lower for o in affirm):
            pool = AFIRMACIONES_ES if session.config.language == "es" else AFIRMACIONES_EN
            return random.choice(pool)

        # ── Preguntas sobre el asistente ──
        if any(q in text_lower for q in ["quién eres", "who are you", "qué eres", "what are you",
                                          "cómo te llamas", "what's your name"]):
            if session.config.language == "es":
                return f"Soy el asistente virtual de {company}. Estoy aquí para ayudarte con facturación, clientes, reportes y más. ¿Qué necesitas?"
            return f"I'm the virtual assistant for {company}. I'm here to help with invoicing, clients, reports and more. What do you need?"

        # ── Preguntas sobre capacidades ──
        if any(q in text_lower for q in ["qué puedes hacer", "what can you do", "cómo funcionas",
                                          "how do you work", "tus funciones", "your functions"]):
            if session.config.language == "es":
                return (
                    f"Puedo ayudarte con varias cosas:\n\n"
                    f"{self._build_capabilities_text(session)}\n\n"
                    "¿Con qué te ayudo?"
                )
            return (
                f"I can help you with several things:\n\n"
                f"{self._build_capabilities_text(session)}\n\n"
                "What can I help you with?"
            )

        # ── Despedidas ──
        byes = ["adiós", "bye", "chao", "nos vemos", "hasta luego", "see you", "goodbye"]
        if any(b in text_lower for b in byes):
            if session.config.language == "es":
                return random.choice([
                    "¡Hasta luego! Cuando ocupes algo, aquí andamos.",
                    "¡Chao! Ahí estamos para lo que necesites.",
                    "Nos vemos. Cuídate y cuando quieras, aquí estoy.",
                ])
            return random.choice([
                "See you later! I'm here whenever you need me.",
                "Bye! Take care and don't hesitate to reach out.",
                "Goodbye! I'll be here when you need me.",
            ])

        # ── Insultos o groserías (respuesta humana con límite) ──
        groserias = ["pendejo", "idiota", "estúpido", "tonto", "puto", "mierda",
                     "fuck", "shit", "dumb", "stupid", "asshole"]
        if any(g in text_lower for g in groserias):
            if session.config.language == "es":
                return random.choice([
                    "Con todo respeto, mejor mantengamos la conversación en buen tono. ¿En qué puedo ayudarte?",
                    "Entiendo que puedas estar frustrado. ¿Por qué mejor no me cuentas qué necesitas y vemos cómo resolverlo?",
                ])
            return random.choice([
                "Let's keep it respectful. How can I help you?",
                "I understand you might be frustrated. Why not tell me what you need and let's solve it?",
            ])

        # ── Default conversacional con variedad ──
        if session.config.language == "es":
            template = random.choice(NO_ENTIENDO_ES)
            cap_key = "capacidades" if "{capacidades}" in template else "lista_cap"
            return template.format(
                capacidades=self._build_capabilities_text(session),
                lista_cap=cap_list,
            )
        template = random.choice(NO_ENTIENDO_EN)
        cap_key = "capacidades" if "{capacidades}" in template else "lista_cap"
        return template.format(
            capacidades=self._build_capabilities_text(session),
            lista_cap=cap_list,
        )

    # ─── Preguntas ────────────────────────────────────────────

    def generate_question(self, message: str, profile: PersonalityProfile) -> str:
        """Genera respuesta humanizada para preguntas (con variedad)."""
        lang = profile.language
        if lang and str(lang) != "es":
            return random.choice([
                f"Good question! Let me look into that for you.\n\nYou asked about: *{message}*\n\nGive me a sec to check the system.",
                f"Great question! I'll check on that.\n\nAbout: *{message}*\n\nLet me look it up.",
            ])
        return random.choice([
            f"¡Buena pregunta! Déjame revisarlo en el sistema.\n\nMe preguntaste sobre: *{message}*\n\nDame un segundo para consultarlo.",
            f"¡Déjame ver! Voy a consultarlo.\n\nSobre: *{message}*\n\nYa te digo qué encontré.",
        ])

    # ─── Comandos ─────────────────────────────────────────────

    def handle_command(self, text: str, session: Session) -> str:
        """Maneja comandos directos con respuestas humanas."""
        text_lower = text.lower().strip()

        if any(w in text_lower for w in ["limpiar", "clear", "reset"]):
            session.messages = [m for m in session.messages if m.is_system]
            return random.choice([
                "¡Listo! Historial limpiado. Empezamos de nuevo.",
                "Hecho. Borré el historial. ¿En qué más te ayudo?",
                "Memoria fresca. Historial eliminado.",
            ])

        if any(w in text_lower for w in ["ayuda", "help", "comandos"]):
            return (
                "Comandos disponibles:\n\n"
                "- `limpiar` / `reset` — Borrar historial\n"
                "- `ayuda` / `help` — Mostrar esta ayuda\n"
                "- `cambiar idioma es|en` — Cambiar idioma\n"
                "- `cambiar tono casual|profesional|tecnico` — Cambiar tono\n"
                "- `personalidad business_default|retail|corporate|healthcare|logistics` — Cambiar personalidad\n"
                "- `estado` — Ver la sesión actual\n"
            )

        if "estado" in text_lower:
            return (
                f"Estado de la sesión:\n"
                f"- Mensajes: {session.message_count}\n"
                f"- Estado: {session.state.value}\n"
                f"- Idioma: {session.config.language}\n"
                f"- Tono: {session.config.tone}\n"
            )

        return "Ese comando no lo conozco. Prueba con `ayuda` para ver los disponibles."

    # ─── Configuracion ────────────────────────────────────────

    def handle_config(self, text: str, session: Session) -> str:
        """Maneja cambios de configuracion con respuestas humanas."""
        text_lower = text.lower().strip()

        if "idioma" in text_lower or "language" in text_lower:
            if any(w in text_lower for w in ["en", "english", "ingles", "inglés"]):
                session.config.language = "en"
                return "Changed to English. All set!"
            elif any(w in text_lower for w in ["es", "spanish", "español", "espanol"]):
                session.config.language = "es"
                return "Cambiado a español. ¡Listo!"

        if "tono" in text_lower or "tone" in text_lower:
            if "casual" in text_lower:
                session.config.tone = "casual"
                return "Tono cambiado a casual. ¡A darle!"
            elif any(w in text_lower for w in ["tecnico", "técnico", "technical"]):
                session.config.tone = "technical"
                return "Tono cambiado a técnico. Ahí está el detalle."
            elif "profesional" in text_lower or "professional" in text_lower:
                session.config.tone = "professional"
                return "Tono cambiado a profesional. ¡A darle!"

        if "personalidad" in text_lower or "personality" in text_lower:
            business_presets = {
                "business_default": "business_default", "default": "business_default",
                "retail": "retail", "corporate": "corporate",
                "healthcare": "healthcare", "logistics": "logistics",
            }
            for alias, preset in business_presets.items():
                if alias in text_lower:
                    session.config.personality_name = preset
                    return f"¡Listo! Personalidad cambiada a {preset}."

        return (
            "Esa configuración no la reconozco. Opciones:\n"
            "- `cambiar idioma es|en`\n"
            "- `cambiar tono casual|profesional|tecnico`\n"
            "- `personalidad business_default|retail|corporate|healthcare|logistics`"
        )

    # ─── Feedback ─────────────────────────────────────────────

    def handle_feedback(self, text: str, profile: PersonalityProfile) -> str:
        """Maneja feedback del usuario con empatía genuina y variedad."""
        text_lower = text.lower().strip()
        positive = ["bien", "bueno", "correcto", "me gusta", "good", "great", "excelente", "perfecto"]
        negative = ["mal", "incorrecto", "no me gusta", "wrong", "bad", "pesimo", "pesimo"]

        if any(p in text_lower for p in positive):
            return random.choice(FEEDBACK_POSITIVO_ES)

        if any(n in text_lower for n in negative):
            return random.choice(FEEDBACK_NEGATIVO_ES)

        return "¡Gracias por tu opinión! Eso ayuda caldísimo a mejorar."

    # ─── Resultados de negocio ────────────────────────────────

    @staticmethod
    def generate_business_result(
        operation: str,
        details: dict | None = None,
        language: str = "es",
    ) -> str:
        """Genera respuesta humanizada para resultados de operaciones de negocio."""
        details = details or {}

        if operation == "invoice":
            inv_id = details.get("id", "0000")
            amount = details.get("amount", "$0.00")
            client = details.get("client", "cliente")
            if language == "es":
                return (
                    f"Encontré la factura {inv_id} por {amount} de {client}. "
                    "¿Quieres descargarla, reenviarla o tienes alguna duda?"
                )
            return (
                f"I found invoice {inv_id} for {amount} for {client}. "
                "Do you want to download it, forward it, or ask anything?"
            )

        elif operation == "crm":
            client_name = details.get("name", "cliente")
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
                    f"{report_name} listo. {transactions} transacciones, {total} en ventas. "
                    "Puedes verlo en el dashboard."
                )
            return (
                f"{report_name} generated. {transactions} transactions, {total} in sales. "
                "You can view it on the dashboard."
            )

        elif operation == "error":
            if language == "es":
                return (
                    "No pude procesar esa solicitud. "
                    "¿Quieres que lo intente de nuevo o prefieres hablar con un agente humano?"
                )
            return (
                "Sorry, I couldn't process that request. "
                "Would you like me to try again or speak with a human agent?"
            )

        elif operation == "unknown":
            if language == "es":
                return (
                    "No estoy seguro de cómo ayudarte con eso. "
                    "Puedo ayudarte con facturas, pedidos, CRM, reportes, tareas y más. "
                    "¿Qué te gustaría hacer?"
                )
            return (
                "I'm not sure how to help with that. "
                "I can help with invoices, orders, CRM, reports, tasks and more. "
                "What would you like to do?"
            )

        if language == "es":
            return random.choice([
                "Listo, proceso completado. ¿Necesitas algo más?",
                "Hecho. ¿Algo más en lo que pueda ayudarte?",
                "Proceso terminado. ¿Qué sigue?",
            ])
        return random.choice([
            "Done, process completed. Need anything else?",
            "All set. Is there anything else I can help with?",
            "Process complete. What's next?",
        ])
