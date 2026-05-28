"""
Zenic-Agents Asistente - Approval Package (Phase 6.1 + C3 + Phase 5)

Chain-of-approval system + configurable workflows for critical actions.

Components:
- ApprovalChain: Request/approve/reject approval requests with role-based authority
- WorkflowEngine: Multi-step approval workflows with configurable triggers
- AdaptiveApprovalEngine: Learns from past approvals to auto-approve safe actions
- RiskBasedApprovalRouter: Routes approval based on contextual risk score
- DelegationManager: Handles approver substitution when primary is unavailable
- BatchApprovalEngine: Approve/reject multiple similar actions at once
- EvidenceManager: Attach immutable evidence to approval requests (Phase 5)
- JustificationManager: Mandatory justification for approve/reject (Phase 5)
- ExpiryManager: Expiration with auto-revert (Phase 5)
- RollbackManager: SAGA-inspired compensation/rollback (Phase 5)
- NotificationDispatcher: Multi-channel approval notifications (Phase 5)
- EscalationManager: SLA-based escalation (Phase 5)
- ApprovalAuditMerkle: Merkle-chain audit trail (Phase 5)
"""

from .adaptive import (
    AdaptiveApprovalEngine,
    AdaptiveApprovalRecord,
    get_adaptive_approval,
    reset_adaptive_approval,
)
from .audit_merkle import (
    GENESIS_HASH,
    ApprovalAuditMerkle,
    AuditEventType,
    AuditRecord,
    MerkleProof,
    get_approval_audit_merkle,
    reset_approval_audit_merkle,
)
from .batch import (
    BatchApprovalEngine,
    BatchRequest,
    BatchResult,
    get_batch_approval,
    reset_batch_approval,
)
from .chain import (
    ApprovalChain,
    ApprovalPriority,
    ApprovalRequest,
    ApprovalResult,
    ApprovalStatus,
    MemoryApprovalPayload,
    get_approval_chain,
    reset_approval_chain,
)
from .delegation import (
    DelegationManager,
    DelegationRecord,
    DelegationRule,
    get_delegation_manager,
    reset_delegation_manager,
)
from .escalation import (
    EscalationLevel,
    EscalationManager,
    EscalationSLA,
    SLAPolicy,
    get_escalation_manager,
    reset_escalation_manager,
)
from .evidence import (
    ApprovalEvidence,
    EvidenceManager,
    EvidenceType,
    get_evidence_manager,
    reset_evidence_manager,
)
from .expiry import (
    ExpiryConfig,
    ExpiryManager,
    ExpiryRecord,
    get_expiry_manager,
    reset_expiry_manager,
)
from .justification import (
    ApprovalJustification,
    JustificationManager,
    JustificationRequirement,
    get_justification_manager,
    reset_justification_manager,
)
from .notification import (
    ChannelConfig,
    NotificationChannel,
    NotificationDispatcher,
    NotificationEvent,
    NotificationMessage,
    NotificationPriority,
    get_notification_dispatcher,
    reset_notification_dispatcher,
)
from .risk_routing import (
    RiskAssessment,
    RiskBasedApprovalRouter,
    RiskLevel,
    get_risk_router,
    reset_risk_router,
)
from .rollback import (
    CompensationAction,
    RollbackManager,
    RollbackRecord,
    RollbackStatus,
    RollbackTrigger,
    get_rollback_manager,
    reset_rollback_manager,
)
from .workflows import (
    WorkflowDefinition,
    WorkflowEngine,
    WorkflowExecution,
    WorkflowStep,
    WorkflowStepType,
    get_workflow_engine,
    reset_workflow_engine,
)

__all__ = [
    "GENESIS_HASH",
    "AdaptiveApprovalEngine",
    # Adaptive (C3)
    "AdaptiveApprovalRecord",
    "ApprovalAuditMerkle",
    # Chain
    "ApprovalChain",
    "ApprovalEvidence",
    "ApprovalJustification",
    "ApprovalPriority",
    "ApprovalRequest",
    "ApprovalResult",
    "ApprovalStatus",
    # Audit Merkle (Phase 5)
    "AuditEventType",
    "AuditRecord",
    "BatchApprovalEngine",
    # Batch (C3)
    "BatchRequest",
    "BatchResult",
    "ChannelConfig",
    "CompensationAction",
    "DelegationManager",
    "DelegationRecord",
    # Delegation (C3)
    "DelegationRule",
    # Escalation (Phase 5)
    "EscalationLevel",
    "EscalationManager",
    "EscalationSLA",
    "EvidenceManager",
    # Evidence (Phase 5)
    "EvidenceType",
    # Expiry (Phase 5)
    "ExpiryConfig",
    "ExpiryManager",
    "ExpiryRecord",
    "JustificationManager",
    # Justification (Phase 5)
    "JustificationRequirement",
    "MemoryApprovalPayload",
    "MerkleProof",
    # Notification (Phase 5)
    "NotificationChannel",
    "NotificationDispatcher",
    "NotificationEvent",
    "NotificationMessage",
    "NotificationPriority",
    "RiskAssessment",
    "RiskBasedApprovalRouter",
    # Risk Routing (C3)
    "RiskLevel",
    "RollbackManager",
    "RollbackRecord",
    # Rollback (Phase 5)
    "RollbackStatus",
    "RollbackTrigger",
    "SLAPolicy",
    "WorkflowDefinition",
    # Workflows
    "WorkflowEngine",
    "WorkflowExecution",
    "WorkflowStep",
    "WorkflowStepType",
    "get_adaptive_approval",
    "get_approval_audit_merkle",
    "get_approval_chain",
    "get_batch_approval",
    "get_delegation_manager",
    "get_escalation_manager",
    "get_evidence_manager",
    "get_expiry_manager",
    "get_justification_manager",
    "get_notification_dispatcher",
    "get_risk_router",
    "get_rollback_manager",
    "get_workflow_engine",
    "reset_adaptive_approval",
    "reset_approval_audit_merkle",
    "reset_approval_chain",
    "reset_batch_approval",
    "reset_delegation_manager",
    "reset_escalation_manager",
    "reset_evidence_manager",
    "reset_expiry_manager",
    "reset_justification_manager",
    "reset_notification_dispatcher",
    "reset_risk_router",
    "reset_rollback_manager",
    "reset_workflow_engine",
]
