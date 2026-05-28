"""
ZENIC-AGENTS - ActionExecutor System (Phase 3)

Sistema de ejecutores de acciones reales para el AutomationEngine.
Fase 3: Integracion Safety Gate + Audit + Blueprint + remaining executors.

Executors (remaining):
  1. DatabaseExecutor   - Operaciones SQLite/SQLCipher (enhanced: CRUD validation + transactions)
  2. FileExecutor       - Operaciones de archivos con proteccion path-traversal
  3. TransformExecutor  - Transformacion y mapeo de datos
  4. ScheduleExecutor   - Programacion de jobs (APScheduler/fallback)

Removed executors (external API connections deleted):
  - EmailExecutor      - Was SMTP via aiosmtplib
  - HttpExecutor       - Was outbound HTTP via aiohttp/urllib
  - NotificationExecutor - Was multi-channel notification dispatch
  - WebhookExecutor    - Was outbound webhook + HMAC verification
  - DiscordExecutor    - Was Discord webhook messages

Infraestructura (remaining):
  - SafetyGate          - Pre-execution validation (destructive/financial/system)
  - ExecutorAuditLogger - Audit logging with Merkle chain integrity
  - BlueprintSchema     - Blueprint parameterization for executors
  - ActionDispatcher    - DAG -> Executor pipeline integration
  - SQLCipherAdapter    - Encrypted database connections (AES-256)
  - CRUDValidator       - CRUD operation validation with Blueprint schema
  - TransactionManager  - Transaction management with rollback support

Removed infrastructure (external connections deleted):
  - ChannelRouter       - Was multi-channel notification routing
  - EmailTemplateEngine - Was email template rendering

Todos los ejecutores:
  - Manejan errores gracefulmente (nunca raise, siempre devuelven ActionResult)
  - Tienen modo dry-run/fallback cuando faltan dependencias
  - Son testeable sin servicios externos
  - Usan logging extensivo
  - Pasan por Safety Gate antes de ejecutar (si esta habilitado)
  - Son auditados despues de ejecutar (si esta habilitado)
"""

# ── Base ──
# ── Audit Logger ──
from .audit_logger import (
    AuditEntry,
    AuditMerkleChain,
    AuditPersistence,
    AuditQuery,
    ExecutorAuditLogger,
    get_default_audit_logger,
    reset_audit_logger,
)
from .base import (
    _HAS_AIOHTTP,
    _HAS_AIOSMTPLIB,
    _HAS_APSCHEDULER,
    ActionExecutor,
    ActionResult,
    ExecutorRegistry,
    _safe_path,
    _validate_email,
    _validate_sql,
    _validate_url,
    get_default_registry,
    reset_default_registry,
)

# ── Blueprint Schema ──
from .blueprint_schema import (
    ActionTemplate,
    Blueprint,
    BlueprintLoader,
    BlueprintMetadata,
    BlueprintValidator,
    BusinessRule,
    ExecutorSchema,
    get_default_blueprint,
)
from .coordinated_rollback import (
    ActionStatus as CoordinatedActionStatus,
)
from .coordinated_rollback import (
    CoordinatedAction,
    CoordinatedRollbackManager,
    CoordinatedRollbackResult,
    ResourceRecord,
    ResourceType,
    get_coordinated_rollback_manager,
    reset_coordinated_rollback_manager,
)

# ── Executors (remaining) ──
from .database_executor import DatabaseExecutor

# Phase A: DB Journal + Coordinated Rollback
from .db_journal import (
    DBTransactionJournal,
    JournalEntry,
    get_db_journal,
    reset_db_journal,
)
from .db_journal import (
    RollbackResult as JournalRollbackResult,
)

# ── Database Parts ──
from .db_parts import CRUDValidator, SQLCipherAdapter, Transaction, TransactionManager
from .diff_preview import (
    DiffEntry,
    DiffPreviewEngine,
    DiffResult,
    get_diff_preview_engine,
    reset_diff_preview_engine,
)

# ── Dispatch Action (DAG Integration) ──
from .dispatch_action import (
    ActionDispatcher,
    DispatchRequest,
    DispatchResult,
    exec_dispatch_action,
    get_default_dispatcher,
    reset_dispatcher,
)

# Phase C1: Dry-Run / Simulation Engine
from .dry_run_executor import (
    DryRunExecutor,
    DryRunOperation,
    DryRunResult,
    dry_run_dispatch,
    get_dry_run_executor,
    reset_dry_run_executor,
)

# ── Executors (Phase 2 — channel integration) ──
from .email_executor import EmailExecutor

# ── Email Parts (Phase 2) ──
from .email_parts import (
    EmailRateLimiter,
    EmailTemplate,
    EmailTemplateEngine,
    GraphAPIEmailProvider,
    OAuth2Config,
    OAuth2Token,
    OAuth2TokenManager,
)
from .file_executor import FileExecutor

# Phase A: Impact Preview + Policy Engine
from .impact_preview import (
    DBImpactPreview,
    EmailImpactPreview,
    FileImpactPreview,
    ImpactField,
    ImpactPreview,
    ImpactPreviewEngine,
    ImpactRiskLevel,
    get_impact_preview_engine,
    reset_impact_preview_engine,
)
from .jira_executor import JiraExecutor
from .policy_engine import (
    ConditionOperator,
    PolicyAction,
    PolicyCondition,
    PolicyDecision,
    PolicyEngine,
    PolicyRule,
    get_policy_engine,
    reset_policy_engine,
)

# ── Safety Gate ──
from .safety_gate import (
    ActionCategory,
    ActionRateLimiter,
    SafetyCheckResult,
    SafetyGate,
    SafetyRule,
    SafetyVerdict,
    get_default_safety_gate,
    reset_safety_gate,
)
from .schedule_executor import ScheduleExecutor
from .servicenow_executor import ServiceNowExecutor
from .simulation_engine import (
    ScenarioComparison,
    SimulationEngine,
    SimulationResult,
    get_simulation_engine,
    reset_simulation_engine,
)
from .transform_executor import TransformExecutor

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
    "ConditionOperator",
    "CoordinatedAction",
    "CoordinatedActionStatus",
    # Phase A: Coordinated Rollback
    "CoordinatedRollbackManager",
    "CoordinatedRollbackResult",
    "DBImpactPreview",
    # Phase A: DB Journal
    "DBTransactionJournal",
    # Executors (7)
    "DatabaseExecutor",
    "DiffEntry",
    "DiffPreviewEngine",
    "DiffResult",
    "DispatchRequest",
    "DispatchResult",
    "DryRunExecutor",
    # Phase C1: Dry-Run / Simulation Engine
    "DryRunOperation",
    "DryRunResult",
    # Executors (Phase 2)
    "EmailExecutor",
    "EmailImpactPreview",
    "EmailRateLimiter",
    "EmailTemplate",
    # Email Parts (Phase 2)
    "EmailTemplateEngine",
    # Audit Logger
    "ExecutorAuditLogger",
    "ExecutorRegistry",
    "ExecutorSchema",
    "FileExecutor",
    "FileImpactPreview",
    "GraphAPIEmailProvider",
    "ImpactField",
    "ImpactPreview",
    # Phase A: Impact Preview
    "ImpactPreviewEngine",
    "ImpactRiskLevel",
    "JiraExecutor",
    "JournalEntry",
    "JournalRollbackResult",
    "OAuth2Config",
    "OAuth2Token",
    "OAuth2TokenManager",
    "PolicyAction",
    "PolicyCondition",
    "PolicyDecision",
    # Phase A: Policy Engine
    "PolicyEngine",
    "PolicyRule",
    "ResourceRecord",
    "ResourceType",
    # Database Parts
    "SQLCipherAdapter",
    "SafetyCheckResult",
    # Safety Gate
    "SafetyGate",
    "SafetyRule",
    "SafetyVerdict",
    "ScenarioComparison",
    "ScheduleExecutor",
    "ServiceNowExecutor",
    "SimulationEngine",
    "SimulationResult",
    "Transaction",
    "TransactionManager",
    "TransformExecutor",
    "_safe_path",
    "_validate_email",
    "_validate_sql",
    "_validate_url",
    "dry_run_dispatch",
    "exec_dispatch_action",
    "get_coordinated_rollback_manager",
    "get_db_journal",
    "get_default_audit_logger",
    "get_default_blueprint",
    "get_default_dispatcher",
    "get_default_registry",
    "get_default_safety_gate",
    "get_diff_preview_engine",
    "get_dry_run_executor",
    "get_impact_preview_engine",
    "get_policy_engine",
    "get_simulation_engine",
    "reset_audit_logger",
    "reset_coordinated_rollback_manager",
    "reset_db_journal",
    "reset_default_registry",
    "reset_diff_preview_engine",
    "reset_dispatcher",
    "reset_dry_run_executor",
    "reset_impact_preview_engine",
    "reset_policy_engine",
    "reset_safety_gate",
    "reset_simulation_engine",
]
