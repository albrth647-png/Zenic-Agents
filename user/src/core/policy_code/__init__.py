from __future__ import annotations

try:
    from .types import (
        PolicyCondition,
        PolicyDocument,
        PolicyEffect,
        PolicyOperator,
        PolicyStatement,
    )
except ImportError:
    PolicyEffect = None  # type: ignore[assignment,misc]
    PolicyOperator = None  # type: ignore[assignment,misc]
    PolicyCondition = None  # type: ignore[assignment,misc]
    PolicyStatement = None  # type: ignore[assignment,misc]
    PolicyDocument = None  # type: ignore[assignment,misc]

try:
    from .engine import (
        PolicyCodeEngine,
        PolicyEvaluationResult,
        get_policy_code_engine,
        reset_policy_code_engine,
    )
except ImportError:
    PolicyEvaluationResult = None  # type: ignore[assignment,misc]
    PolicyCodeEngine = None  # type: ignore[assignment,misc]
    get_policy_code_engine = None  # type: ignore[assignment,misc]
    reset_policy_code_engine = None  # type: ignore[assignment,misc]

try:
    from .builtins import get_builtin_policies, install_builtin_policies
except ImportError:
    get_builtin_policies = None  # type: ignore[assignment,misc]
    install_builtin_policies = None  # type: ignore[assignment,misc]

__all__ = [
    "PolicyCodeEngine",
    "PolicyCondition",
    "PolicyDocument",
    "PolicyEffect",
    "PolicyEvaluationResult",
    "PolicyOperator",
    "PolicyStatement",
    "get_builtin_policies",
    "get_policy_code_engine",
    "install_builtin_policies",
    "reset_policy_code_engine",
]
