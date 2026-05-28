"""
ZENIC-AGENTS — B2 Auto-chained Workflows Package.

Provides dynamic chain composition, template management, inter-workflow
handoff, and conditional branching for building production-grade
automated workflow pipelines.

Modules:
  chain_composer   — DynamicChainComposer: composes & executes workflow chains
  chain_templates  — ChainTemplateLibrary: reusable workflow templates
  inter_workflow   — InterWorkflowHandoff: passes output between chains
  conditional_branch — ConditionalBranching: if/then/else logic in chains
"""

from .chain_composer import (
    ChainExecutionResult,
    ChainStatus,
    ChainStep,
    ChainStepResult,
    ChainStepType,
    ChainValidationResult,
    ComposedChain,
    DynamicChainComposer,
    get_chain_composer,
)
from .chain_templates import (
    ChainTemplate,
    ChainTemplateLibrary,
    TemplateCategory,
    TemplateStep,
    TemplateVariable,
    get_template_library,
)
from .conditional_branch import (
    BranchCondition,
    BranchRule,
    ConditionalBranching,
    get_conditional_branching,
)
from .inter_workflow import (
    FieldMapping,
    HandoffResult,
    HandoffRule,
    InterWorkflowHandoff,
    get_inter_workflow_handoff,
)

__all__ = [
    "BranchCondition",
    # conditional_branch
    "BranchRule",
    "ChainExecutionResult",
    "ChainStatus",
    # chain_composer
    "ChainStep",
    "ChainStepResult",
    "ChainStepType",
    # chain_templates
    "ChainTemplate",
    "ChainTemplateLibrary",
    "ChainValidationResult",
    "ComposedChain",
    "ConditionalBranching",
    "DynamicChainComposer",
    "FieldMapping",
    "HandoffResult",
    # inter_workflow
    "HandoffRule",
    "InterWorkflowHandoff",
    "TemplateCategory",
    "TemplateStep",
    "TemplateVariable",
    "get_chain_composer",
    "get_conditional_branching",
    "get_inter_workflow_handoff",
    "get_template_library",
]
