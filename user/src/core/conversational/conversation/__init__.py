"""
Modulo de gestion de conversacion del Asistente.

Gestiona conversaciones multi-turno con:
  - ConversationManager: Orquesta sesiones de conversacion
  - TurnTracker: Trackea turnos y detecta topic shifts
  - ContextSummarizer: Resume contexto para ventanas largas
  - ConversationState: Estado inmutable de la conversacion
"""

from .manager import ConversationManager
from .state import ConversationPhase, ConversationState
from .summarizer import ContextSummarizer
from .turn_tracker import TurnTracker

__all__ = [
    "ContextSummarizer",
    "ConversationManager",
    "ConversationPhase",
    "ConversationState",
    "TurnTracker",
]
