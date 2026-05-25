"""Safety System — SafetyGate inbypassable.

La IA solo dice YES/NO. NUNCA genera contenido.
DENY no puede ser sobrepasado.
Determinístico por diseño: funciona 100% sin IA.
"""

from src.core.safety.safety_gate import SafetyGate, SafetyResult
from src.core.safety.policy import PolicyEngine

__all__ = ["SafetyGate", "SafetyResult", "PolicyEngine"]
