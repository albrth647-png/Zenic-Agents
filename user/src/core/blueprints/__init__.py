"""
Zenic-Agents Asistente - Blueprints Certificados (Phase 5)

From YAML templates to certified, composable Blueprints.

Architecture:
  BlueprintRegistry (facade + singleton)
  ├── BlueprintLoaderV2 (load from YAML/JSON/dict)
  ├── NicheConverter (Niche YAML → CertifiedBlueprint)
  ├── BlueprintComposer (compose multiple Blueprints)
  ├── BlueprintValidatorV2 (schema + compatibility validation)
  ├── BlueprintCertifier (ECDSA signing + verification)
  ├── OnboardingEngine (guided setup flow)
  └── BlueprintSDK (partner API + revenue share)

Usage:
    from src.core.blueprints import get_blueprint_registry

    registry = get_blueprint_registry()
    registry.load_from_niches()

    # Get a Blueprint
    bp = registry.get("inventory_retail")

    # Compose for a tenant
    result = registry.compose_for_tenant(
        tenant_id="acme",
        blueprint_names=["inventory_retail", "accounting"],
    )
    if result.success:
        active_bp = result.blueprint
"""

# ── Types ─────────────────────────────────────────────────────
# ── Certifier ─────────────────────────────────────────────────
from .certifier import (
    BlueprintCertifier,
    CertifierKeyPair,
    certify_blueprint,
    get_default_certifier,
    verify_blueprint,
)

# ── Composer ──────────────────────────────────────────────────
from .composer import BlueprintComposer, CompositionResult

# ── Converter ─────────────────────────────────────────────────
from .converter import NicheConverter

# ── Loader ────────────────────────────────────────────────────
from .loader import BlueprintLoaderV2

# ── Onboarding ────────────────────────────────────────────────
from .onboarding import OnboardingEngine

# ── Partner Registry ──────────────────────────────────────────
from .partner_registry import PartnerRegistry

# ── Registry ──────────────────────────────────────────────────
from .registry import (
    BlueprintRegistry,
    get_blueprint_registry,
    reset_blueprint_registry,
)

# ── Schema ────────────────────────────────────────────────────
from .schema import CertifiedBlueprint

# ── SDK ───────────────────────────────────────────────────────
from .sdk import BlueprintBuilder, BlueprintSDK
from .types import (
    ActionTemplateDef,
    BlueprintCompatibility,
    BlueprintMetadataV2,
    BlueprintSignature,
    BlueprintStats,
    # Enums
    BlueprintStatus,
    BlueprintTier,
    BusinessRuleDef,
    ConflictStrategy,
    DBEntitySchema,
    # Dataclasses
    DBFieldSchema,
    DBSchema,
    FieldType,
    MonitorHook,
    OnboardingSession,
    OnboardingStep,
    OnboardingStepType,
    PartnerInfo,
)

# ── Validator ─────────────────────────────────────────────────
from .validator import BlueprintValidatorV2, ValidationResult

__all__ = [
    "ActionTemplateDef",
    "BlueprintBuilder",
    "BlueprintCertifier",
    "BlueprintCompatibility",
    # Composer
    "BlueprintComposer",
    # Loader
    "BlueprintLoaderV2",
    "BlueprintMetadataV2",
    # Registry
    "BlueprintRegistry",
    # SDK
    "BlueprintSDK",
    "BlueprintSignature",
    "BlueprintStats",
    # Types
    "BlueprintStatus",
    "BlueprintTier",
    # Validator
    "BlueprintValidatorV2",
    "BusinessRuleDef",
    # Schema
    "CertifiedBlueprint",
    # Certifier
    "CertifierKeyPair",
    "CompositionResult",
    "ConflictStrategy",
    "DBEntitySchema",
    "DBFieldSchema",
    "DBSchema",
    "FieldType",
    "MonitorHook",
    # Converter
    "NicheConverter",
    # Onboarding
    "OnboardingEngine",
    "OnboardingSession",
    "OnboardingStep",
    "OnboardingStepType",
    "PartnerInfo",
    "PartnerRegistry",
    "ValidationResult",
    "certify_blueprint",
    "get_blueprint_registry",
    "get_default_certifier",
    "reset_blueprint_registry",
    "verify_blueprint",
]
