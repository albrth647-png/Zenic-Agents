"""
ZENIC-AGENTS - Logic Blocks Sub-Package

Composable business logic engine that replaces the _process() placeholder
with real, executable business logic blocks.

Architecture:
  1. LogicBlock: Abstract base class for logic blocks
  2. LogicChain: Composable pipeline of sequential blocks with branching
  3. LogicBuilder: Main builder that composes chains from descriptions or templates
  4. 30+ pre-built blocks in 6 categories:
     - Flow: conditional, loop, parallel, switch, try_catch
     - Validation: required, types, ranges, unique, sanitize
     - Business Logic: invoice, inventory, crm, task, report, notification, analyzer
     - Data: crud_create, crud_read, crud_update, crud_delete, transform
     - Integration: email, http, webhook, file
     - Auth: login, register, verify, rbac
  5. generate_inline_block_code(): Generates real _process() source code per block

Modules:
  - chain: LogicBlock ABC, LogicChain, _validate_identifier
  - flow: ConditionalBlock, LoopBlock, ParallelBlock, SwitchBlock, TryCatchBlock
  - validation: ValidateRequiredBlock, ValidateTypesBlock, ValidateRangesBlock,
                ValidateUniqueBlock, SanitizeBlock
  - business_logic: InvoiceCalculatorBlock, InventoryTrackerBlock, CRMPipelineBlock,
                    TaskSchedulerBlock
  - business_analytics: ReportGeneratorBlock, NotificationDispatchBlock, DataAnalyzerBlock
  - data: CRUDCreateBlock, CRUDReadBlock, CRUDUpdateBlock, CRUDDeleteBlock
  - data_transform: DataTransformBlock
  - integration: EmailSendBlock, HTTPRequestBlock, WebhookCallBlock, FileOperationBlock
  - auth: AuthLoginBlock, AuthRegisterBlock, AuthVerifyBlock, AuthRBACBlock
  - builder: LogicBuilder
  - builder_registry: build_keyword_map, map_template_block, get_block_template_code,
                      generate_inline_block_code, safe_var_name
"""

from .auth import (
    AuthLoginBlock,
    AuthRBACBlock,
    AuthRegisterBlock,
    AuthVerifyBlock,
)
from .builder import LogicBuilder
from .builder_registry import (
    build_keyword_map,
    generate_inline_block_code,
    get_block_template_code,
    map_template_block,
    safe_var_name,
)
from .business_analytics import (
    DataAnalyzerBlock,
    NotificationDispatchBlock,
    ReportGeneratorBlock,
)
from .business_logic import (
    CRMPipelineBlock,
    InventoryTrackerBlock,
    InvoiceCalculatorBlock,
    TaskSchedulerBlock,
)
from .chain import (
    LogicBlock,
    LogicChain,
    _validate_identifier,
)
from .data import (
    CRUDCreateBlock,
    CRUDDeleteBlock,
    CRUDReadBlock,
    CRUDUpdateBlock,
)
from .data_transform import (
    DataTransformBlock,
)
from .flow import (
    ConditionalBlock,
    LoopBlock,
    ParallelBlock,
    SwitchBlock,
    TryCatchBlock,
)
from .integration import (
    EmailSendBlock,
    FileOperationBlock,
    HTTPRequestBlock,
    WebhookCallBlock,
)
from .validation import (
    SanitizeBlock,
    ValidateRangesBlock,
    ValidateRequiredBlock,
    ValidateTypesBlock,
    ValidateUniqueBlock,
)

__all__ = [
    # Auth blocks
    'AuthLoginBlock',
    'AuthRBACBlock',
    'AuthRegisterBlock',
    'AuthVerifyBlock',
    'CRMPipelineBlock',
    # Data blocks
    'CRUDCreateBlock',
    'CRUDDeleteBlock',
    'CRUDReadBlock',
    'CRUDUpdateBlock',
    # Flow blocks
    'ConditionalBlock',
    'DataAnalyzerBlock',
    'DataTransformBlock',
    # Integration blocks
    'EmailSendBlock',
    'FileOperationBlock',
    'HTTPRequestBlock',
    'InventoryTrackerBlock',
    # Business logic blocks
    'InvoiceCalculatorBlock',
    # Chain module
    'LogicBlock',
    # Builder
    'LogicBuilder',
    'LogicChain',
    'LoopBlock',
    'NotificationDispatchBlock',
    'ParallelBlock',
    'ReportGeneratorBlock',
    'SanitizeBlock',
    'SwitchBlock',
    'TaskSchedulerBlock',
    'TryCatchBlock',
    'ValidateRangesBlock',
    # Validation blocks
    'ValidateRequiredBlock',
    'ValidateTypesBlock',
    'ValidateUniqueBlock',
    'WebhookCallBlock',
    '_validate_identifier',
    # Builder registry helpers
    'build_keyword_map',
    'generate_inline_block_code',
    'get_block_template_code',
    'map_template_block',
    'safe_var_name',
]
