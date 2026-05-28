"""
Routing del Asistente.

Selecciona el pipeline de procesamiento adecuado
basado en la intencion detectada, capacidades del
sistema y contexto de la sesion.
"""

from .fallback_chain import FallbackChain
from .pipeline_selector import PipelineSelector
from .router import AssistantRouter

__all__ = [
    "AssistantRouter",
    "FallbackChain",
    "PipelineSelector",
]
