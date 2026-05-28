"""Safety System — SafetyGate inbypassable.

La IA solo dice YES/NO. NUNCA genera contenido.
DENY no puede ser sobrepasado.
Determinístico por diseño: funciona 100% sin IA.
"""

from src.core.safety.policy import PolicyEngine
from src.core.safety.safety_gate import SafetyGate, SafetyResult

__all__ = ["PolicyEngine", "SafetyGate", "SafetyResult"]
