"""
BaseOrchestrator — facade re-exporting all sub-modules.

Backward-compatible: ``from src.core.orchestrator_base import BaseOrchestrator``
still works exactly as before.
"""

from ._api_mixin import APIMixin
from ._compat_mixin import CompatMixin
from ._imports import (
    AbortiveProtocol,
    AgentCache,
    # ChainValidator, ChainExecutor, execute_chain_safe, validate_chain, RecoveryAction removed — module deleted
    AgentRunner,
    # PartialReasoningManager removed — depends on deleted partial_reason_parts
    # CodeGenerator removed — module deleted
    # CodeTransformer removed — module deleted
    AnalysisUtils,
    Any,
    APAPlanner,
    ASTSurgeon,
    AuthService,
    # CodeAgent removed — module deleted
    AutomationAgent,
    # AppGenerator removed — module deleted
    AutomationEngine,
    BusinessLogicAgent,
    Dict,
    # SchemaDesigner removed — module deleted
    ExecutorRegistry,
    GenerationPlan,
    GitHubScrapAgent,
    GraphASTEngine,
    List,
    LogicBuilder,
    MacroRouter,
    MerkleLedger,
    Optional,
    Path,
    ReasoningAgent,
    ReasoningEngine,
    ReasoningMode,
    ReasoningResult,
    ReflexionSandbox,
    SandboxWorkspace,
    SemanticParser,
    SubtaskDescriptor,
    SurgicalAgent,
    TheoremCache,
    ThinkingEngine,
    ValidationAgent,
    get_default_registry,
    get_isolation_manager,
    get_projects_dir,
    initialize_databases,
    load_settings,
    logger,
    shutdown_isolation,
)
from ._init_mixin import InitMixin
from ._phase7_mixin import Phase7Mixin
from ._phase8_mixin import Phase8Mixin
from ._phases import (  # H-83: Extracted init phases
    PHASE_ORDER,
    AgentFrameworkPhase,
    AIArchitecturePhase,
    CommonStatePhase,
    DecomposedModulesPhase,
    ExtendedArchitecturePhase,
    GodLevelImprovementsPhase,
    OrchestratorPhase,
    Phase7EnginesPhase,
    Phase8IntelligencePhase,
    PipelinePhase,
)


class BaseOrchestrator(InitMixin, APIMixin, Phase7Mixin, Phase8Mixin, CompatMixin):
    """
    Shared base for ZenicOrchestrator and DAGOrchestrator.

    Contains all initialization, public API, backward-compat delegation,
    and shared properties that were previously duplicated between the two
    orchestrator implementations.
    """


__all__ = [
    "PHASE_ORDER",
    "AIArchitecturePhase",
    "APAPlanner",
    "ASTSurgeon",
    "AbortiveProtocol",
    "AgentCache",
    "AgentFrameworkPhase",
    # "ChainValidator", "ChainExecutor", "execute_chain_safe", "validate_chain", "RecoveryAction" removed — module deleted
    "AgentRunner",
    # "PartialReasoningManager" removed — depends on deleted partial_reason_parts
    # "CodeGenerator" removed — module deleted
    # "CodeTransformer" removed — module deleted
    "AnalysisUtils",
    "Any",
    "AuthService",
    # "CodeAgent" removed — module deleted
    "AutomationAgent",
    # "AppGenerator" removed — module deleted
    "AutomationEngine",
    "BaseOrchestrator",
    "BusinessLogicAgent",
    "CommonStatePhase",
    "DecomposedModulesPhase",
    "Dict",
    # "SchemaDesigner" removed — module deleted
    "ExecutorRegistry",
    "ExtendedArchitecturePhase",
    "GenerationPlan",
    "GitHubScrapAgent",
    "GodLevelImprovementsPhase",
    "GraphASTEngine",
    "List",
    "LogicBuilder",
    "MacroRouter",
    "MerkleLedger",
    "Optional",
    # H-83: OrchestratorPhase classes for testable init pipeline
    "OrchestratorPhase",
    "Path",
    "Phase7EnginesPhase",
    "Phase8IntelligencePhase",
    "PipelinePhase",
    "ReasoningAgent",
    "ReasoningEngine",
    "ReasoningMode",
    "ReasoningResult",
    "ReflexionSandbox",
    "SandboxWorkspace",
    "SemanticParser",
    "SubtaskDescriptor",
    "SurgicalAgent",
    "TheoremCache",
    "ThinkingEngine",
    "ValidationAgent",
    "get_default_registry",
    "get_isolation_manager",
    "get_projects_dir",
    "initialize_databases",
    "load_settings",
    # Re-export all imports for backward compatibility
    "logger",
    "shutdown_isolation",
]
