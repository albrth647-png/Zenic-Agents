"""
Pipeline de entrada del Asistente.

Procesa el mensaje crudo del usuario en tres fases:
  1. Sanitize: Limpieza y validacion
  2. Parse: Extraccion de estructura y entidades
  3. Enrich: Enriquecimiento con contexto y memoria
"""

from .enricher import InputEnricher
from .parser import InputParser
from .sanitizer import InputSanitizer

__all__ = [
    "InputEnricher",
    "InputParser",
    "InputSanitizer",
]
