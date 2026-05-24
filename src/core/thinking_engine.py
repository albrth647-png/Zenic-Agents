"""
ZENIC-AGENTS - ThinkingEngine (Qwen3-0.6B as Main Brain)

El CEREBRO del sistema. Qwen3-0.6B es el motor principal de razonamiento,
NO solo un copiloto. ThinkingEngine coordina:

  Qwen (PIENSA)  →  SemanticEngine (ENTIENDE)  →  SmartMemory (RECUERDA)
"""

from .thinking_parts import GenerationPlan, ThinkingEngine, ThinkingResult  # explicit

__all__ = ["GenerationPlan", "ThinkingEngine", "ThinkingResult"]
