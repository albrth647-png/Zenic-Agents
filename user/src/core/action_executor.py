"""
ZENIC-AGENTS - ActionExecutor System (Phase 3)

Facade module that re-exports all public symbols from the executors sub-package.
All implementation has been modularized into src/core/executors/.
Phase 3 adds: Safety Gate, Audit Logger, Blueprint Schema, DiscordExecutor,
and DAG integration via ActionDispatcher.
"""

# Notification Parts — imported from channels package
from .channels import ChannelPriority, ChannelRouter
from .executors import (
    _HAS_AIOHTTP,
    _HAS_AIOSMTPLIB,
    _HAS_APSCHEDULER,
    ActionCategory,
    # Dispatch Action
    ActionDispatcher,
    ActionExecutor,
    ActionRateLimiter,
    # Base
    ActionResult,
    ActionTemplate,
    AuditEntry,
    AuditMerkleChain,
    AuditPersistence,
    AuditQuery,
    # Blueprint Schema
    Blueprint,
    BlueprintLoader,
    BlueprintMetadata,
    BlueprintValidator,
    BusinessRule,
    CRUDValidator,
    DatabaseExecutor,
    DispatchRequest,
    DispatchResult,
    # Executors
    EmailExecutor,
    EmailRateLimiter,
    EmailTemplate,
    # Email Parts
    EmailTemplateEngine,
    # Audit Logger
    ExecutorAuditLogger,
    ExecutorRegistry,
    ExecutorSchema,
    FileExecutor,
    SafetyCheckResult,
    # Safety Gate
    SafetyGate,
    SafetyRule,
    SafetyVerdict,
    ScheduleExecutor,
    # Database Parts
    SQLCipherAdapter,
    Transaction,
    TransactionManager,
    TransformExecutor,
    _safe_path,
    _validate_email,
    _validate_sql,
    _validate_url,
    exec_dispatch_action,
    get_default_audit_logger,
    get_default_blueprint,
    get_default_dispatcher,
    get_default_registry,
    get_default_safety_gate,
    reset_audit_logger,
    reset_default_registry,
    reset_dispatcher,
    reset_safety_gate,
)

__all__ = [
    "_HAS_AIOHTTP",
    "_HAS_AIOSMTPLIB",
    "_HAS_APSCHEDULER",
    "ActionCategory",
    # Dispatch Action
    "ActionDispatcher",
    "ActionExecutor",
    "ActionRateLimiter",
    # Base
    "ActionResult",
    "ActionTemplate",
    "AuditEntry",
    "AuditMerkleChain",
    "AuditPersistence",
    "AuditQuery",
    # Blueprint Schema
    "Blueprint",
    "BlueprintLoader",
    "BlueprintMetadata",
    "BlueprintValidator",
    "BusinessRule",
    "CRUDValidator",
    "ChannelPriority",
    # Notification Parts (from channels)
    "ChannelRouter",
    "DatabaseExecutor",
    "DispatchRequest",
    "DispatchResult",
    # Executors
    "EmailExecutor",
    "EmailRateLimiter",
    "EmailTemplate",
    # Email Parts
    "EmailTemplateEngine",
    # Audit Logger
    "ExecutorAuditLogger",
    "ExecutorRegistry",
    "ExecutorSchema",
    "FileExecutor",
    # Database Parts
    "SQLCipherAdapter",
    "SafetyCheckResult",
    # Safety Gate
    "SafetyGate",
    "SafetyRule",
    "SafetyVerdict",
    "ScheduleExecutor",
    "Transaction",
    "TransactionManager",
    "TransformExecutor",
    "_safe_path",
    "_validate_email",
    "_validate_sql",
    "_validate_url",
    "exec_dispatch_action",
    "get_default_audit_logger",
    "get_default_blueprint",
    "get_default_dispatcher",
    "get_default_registry",
    "get_default_safety_gate",
    "reset_audit_logger",
    "reset_default_registry",
    "reset_dispatcher",
    "reset_safety_gate",
]
