"""
ZENIC-AGENTS — Policy Engine Helpers

Utility functions for policy engine operations: factory constructors
for conditions and rules, decision builders, validation, and audit
serialization.

These helpers reduce boilerplate when programmatically constructing
policy objects and converting between string-based configs and enums.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from ._types import ConditionOperator, PolicyAction, PolicyDecision, PolicyRule

# ── Enum Conversion ─────────────────────────────────────────

_ACTION_MAP: dict[str, PolicyAction] = {a.value: a for a in PolicyAction}
_OPERATOR_MAP: dict[str, ConditionOperator] = {o.value: o for o in ConditionOperator}


def policy_action_from_string(action_str: str) -> PolicyAction:
    """Safely convert a string to a PolicyAction enum value.

    Args:
        action_str: String representation (case-insensitive), e.g. "ALLOW" or "deny".

    Returns:
        The corresponding PolicyAction enum member.

    Raises:
        ValueError: If the string does not match any PolicyAction.
    """
    key = action_str.strip().upper()
    if key in _ACTION_MAP:
        return _ACTION_MAP[key]
    valid = ", ".join(a.value for a in PolicyAction)
    raise ValueError(f"Invalid PolicyAction '{action_str}'. Valid values: {valid}")


def condition_operator_from_string(op_str: str) -> ConditionOperator:
    """Safely convert a string to a ConditionOperator enum value.

    Args:
        op_str: String representation (case-sensitive), e.g. "eq", "regex".

    Returns:
        The corresponding ConditionOperator enum member.

    Raises:
        ValueError: If the string does not match any ConditionOperator.
    """
    key = op_str.strip().lower()
    if key in _OPERATOR_MAP:
        return _OPERATOR_MAP[key]
    valid = ", ".join(o.value for o in ConditionOperator)
    raise ValueError(f"Invalid ConditionOperator '{op_str}'. Valid values: {valid}")


# ── Factory Constructors ────────────────────────────────────


def make_condition(
    field: str,
    operator: str,
    value: Any = None,
) -> Any:
    """Create a PolicyCondition from string operator name.

    Convenience factory that converts the string operator to
    ConditionOperator enum and constructs a PolicyCondition.

    Args:
        field: Dot-notation field path, e.g. "config.tier".
        operator: Operator string, e.g. "eq", "in", "regex".
        value: Expected value for comparison.

    Returns:
        A new PolicyCondition instance.

    Raises:
        ValueError: If the operator string is invalid.
    """
    from ._evaluator import PolicyCondition  # Avoid circular import at module level

    op_enum = condition_operator_from_string(operator)
    return PolicyCondition(field=field, operator=op_enum, value=value)


def make_rule(
    name: str,
    action: str,
    field: str = "",
    operator: str = "eq",
    value: Any = None,
    priority: int = 0,
    description: str = "",
    escalation_role: str = "",
    category_filter: str = "",
) -> PolicyRule:
    """Create a PolicyRule from string arguments.

    Convenience factory that converts string action/operator to enums
    and constructs a complete PolicyRule with an optional condition.

    Args:
        name: Human-readable rule name.
        action: Action string, e.g. "ALLOW", "DENY".
        field: Condition field path (empty = no condition = always matches).
        operator: Condition operator string.
        value: Condition expected value.
        priority: Rule priority (higher = evaluated first).
        description: Rule description.
        escalation_role: Role for ESCALATE actions.
        category_filter: Category filter string.

    Returns:
        A new PolicyRule instance.
    """
    action_enum = policy_action_from_string(action)
    condition = make_condition(field, operator, value) if field else None
    return PolicyRule(
        name=name,
        description=description,
        condition=condition,
        action=action_enum,
        priority=priority,
        escalation_role=escalation_role,
        category_filter=category_filter,
    )


# ── Decision Builders ───────────────────────────────────────


def make_deny_decision(
    action_type: str,
    reason: str,
    matched_rules: list[str] | None = None,
) -> PolicyDecision:
    """Create a DENY PolicyDecision with standard fields.

    Args:
        action_type: The action type that was denied.
        reason: Human-readable denial reason.
        matched_rules: Optional list of rule names that triggered the denial.

    Returns:
        A PolicyDecision with action=DENY.
    """
    return PolicyDecision(
        action=PolicyAction.DENY,
        action_type=action_type,
        matched_rules=matched_rules or [],
        denial_reason=reason,
    )


def make_allow_decision(
    action_type: str,
    evaluation_count: int = 0,
) -> PolicyDecision:
    """Create an ALLOW PolicyDecision.

    Args:
        action_type: The action type that was allowed.
        evaluation_count: Number of rules evaluated.

    Returns:
        A PolicyDecision with action=ALLOW.
    """
    return PolicyDecision(
        action=PolicyAction.ALLOW,
        action_type=action_type,
        evaluation_count=evaluation_count,
    )


# ── Sorting ─────────────────────────────────────────────────


def sort_rules_by_priority(rules: list[PolicyRule]) -> list[PolicyRule]:
    """Sort policy rules by priority descending (highest first).

    Rules with the same priority maintain their original relative order
    (stable sort).

    Args:
        rules: List of PolicyRule objects.

    Returns:
        New list sorted by priority descending.
    """
    return sorted(rules, key=lambda r: r.priority, reverse=True)


# ── Validation ──────────────────────────────────────────────


def validate_policy_dict(data: dict[str, Any]) -> list[str]:
    """Validate a policy dict structure and return list of validation errors.

    Checks that required fields are present and have valid types/values.

    Args:
        data: Dictionary representing a policy rule.

    Returns:
        Empty list if valid, list of error message strings otherwise.
    """
    errors: list[str] = []

    if not data.get("name"):
        errors.append("Missing required field: 'name'")

    action_str = data.get("action", "")
    if action_str:
        try:
            policy_action_from_string(action_str)
        except ValueError as exc:
            errors.append(str(exc))
    else:
        errors.append("Missing required field: 'action'")

    condition = data.get("condition")
    if condition and isinstance(condition, dict):
        op_str = condition.get("operator", "")
        if op_str:
            try:
                condition_operator_from_string(op_str)
            except ValueError as exc:
                errors.append(str(exc))

    priority = data.get("priority")
    if priority is not None and not isinstance(priority, int):
        errors.append("'priority' must be an integer")

    return errors


# ── Audit Serialization ─────────────────────────────────────


def decision_to_audit_dict(decision: PolicyDecision) -> dict[str, Any]:
    """Convert a PolicyDecision to an audit-friendly dict with ISO timestamp.

    Adds a ``audited_at`` field with the current UTC time for traceability.

    Args:
        decision: The PolicyDecision to serialize.

    Returns:
        Dictionary suitable for audit log storage.
    """
    base = decision.to_dict()
    base["audited_at"] = datetime.now(timezone.utc).isoformat()
    return base


# ── Public Exports ──────────────────────────────────────────

__all__ = [
    "condition_operator_from_string",
    "decision_to_audit_dict",
    "make_allow_decision",
    "make_condition",
    "make_deny_decision",
    "make_rule",
    "policy_action_from_string",
    "sort_rules_by_priority",
    "validate_policy_dict",
]
