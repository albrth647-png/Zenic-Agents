"""
Shared imports, types, and constants for dna_loader_parts.
"""

import logging
import os
from dataclasses import dataclass, field

try:
    import yaml  # noqa: F401

    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

logger = logging.getLogger(__name__)

DNA_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "templates", "dna")


@dataclass
class LogicModule:
    """Módulo de función atómica reutilizable."""

    id: str
    domain: str
    description: str
    code_block: str
    dependencies: list[str] = field(default_factory=list)
    verification_rule: str = ""
    inputs: list[str] = field(default_factory=list)
    outputs: list[str] = field(default_factory=list)


@dataclass
class DomainRule:
    """Regla de negocio obligatoria por industria."""

    name: str
    display_name: str
    description: str
    mandatory_logic: list[str] = field(default_factory=list)
    ux_patterns: list[str] = field(default_factory=list)
    compliance_requirements: list[str] = field(default_factory=list)
    business_invariants: list[str] = field(default_factory=list)
    edge_cases: list[str] = field(default_factory=list)
    suggested_entities: list[str] = field(default_factory=list)
    notification_triggers: list[str] = field(default_factory=list)


@dataclass
class ValidationGate:
    """Regla de validación de calidad."""

    id: str
    category: str
    rule: str
    action: str
    severity: str = "warning"
    auto_fix: bool = False
    fix_strategy: str = ""
    pattern: str = ""
    applies_to: list[str] = field(default_factory=list)


@dataclass
class GlossaryEntry:
    """Transformación de jerga técnica a lenguaje corporativo."""

    from_term: str
    to_term: str
    context: str = ""
