"""
Zenic-Agents Asistente - Phase 6 Integration Wiring

Connects all Phase 6 components into the existing system:
- SafetyGate → ApprovalChain → WorkflowEngine
- LicenseManager → DegradedModeManager
- DefenseManager → DegradedModeManager
- DegradedModeManager → SafetyGate (enforcement)
- AuthService RBAC → ApprovalChain (role-based approval)

This module provides the `initialize_phase6()` function that
should be called during application startup to wire everything.

Fase 4 Fix: Replaced monkey-patching of SafetyGate.check with composition
pattern (EnhancedSafetyGate) and added idempotency guard to prevent
double-initialization issues.
"""

from __future__ import annotations

import contextlib
import logging
import threading
from typing import Any

from src.core.degraded_mode.manager import get_degraded_mode_manager
from src.core.license.manager import get_license_manager

logger = logging.getLogger(__name__)

# ── Idempotency Guard ──────────────────────────────────────────────
_phase6_initialized = False
_phase6_lock = threading.Lock()


def _create_enhanced_safety_gate(
    safety_gate: Any,
    approval_chain: Any,
) -> Any:
    """Create an EnhancedSafetyGate that wraps the original with ApprovalChain integration.

    Instead of monkey-patching safety_gate.check, we create a new class
    that extends SafetyGate and overrides check() with the enhanced behavior.
    This is safer, testable, and avoids double-patch issues.

    Args:
        safety_gate: The original SafetyGate instance.
        approval_chain: The ApprovalChain instance to integrate.

    Returns:
        A new EnhancedSafetyGate instance that wraps the original.
    """
    try:
        from src.core.executors.safety_gate import ActionCategory, SafetyCheckResult, SafetyVerdict
    except ImportError:
        logger.warning("Phase6: Cannot import SafetyGate types — skipping enhancement")
        return safety_gate

    class EnhancedSafetyGate:
        """Compositional wrapper around SafetyGate that integrates with ApprovalChain.

        Instead of replacing safety_gate.check via monkey-patching, this wrapper
        delegates to the original check method and adds:
        1. Degraded mode enforcement (blocks actions when system is degraded)
        2. Auto-creation of approval requests for APPROVE verdicts

        The original safety_gate instance is preserved and can be accessed
        via the `.original` attribute if needed.
        """

        def __init__(self, original_gate: Any, chain: Any) -> None:
            self.original = original_gate
            self._chain = chain
            # Copy all public attributes from the original to support
            # attribute access patterns like gate.some_property
            for attr_name in dir(original_gate):
                if not attr_name.startswith("_") and not hasattr(type(self), attr_name):
                    with contextlib.suppress(AttributeError, TypeError):
                        setattr(self, attr_name, getattr(original_gate, attr_name))

        def check(
            self,
            action_type: str,
            config: dict[str, Any],
            context: dict[str, Any] | None = None,
        ) -> Any:
            """Enhanced SafetyGate check that integrates with ApprovalChain.

            When SafetyGate returns APPROVE, automatically creates an
            approval request in the chain.
            """
            result = self.original.check(action_type, config, context)

            # Check degraded mode before proceeding
            try:
                from src.core.degraded_mode.manager import get_degraded_mode_manager

                dm = get_degraded_mode_manager()
                action_check = dm.check_action(action_type)
                if not action_check["allowed"]:
                    return SafetyCheckResult(
                        verdict=SafetyVerdict.DENY,
                        category=ActionCategory.SYSTEM,
                        reason=action_check["reason"],
                        rule_name="degraded_mode_block",
                    )
            except ImportError:
                pass

            # If APPROVE, create approval request
            if result.verdict == SafetyVerdict.APPROVE:
                try:
                    requested_by = 0
                    if context and "user_id" in context:
                        requested_by = context["user_id"]

                    self._chain.create_request(
                        action_type=action_type,
                        action_config=config,
                        requested_by=requested_by,
                        required_role="gerente",
                    )
                except Exception as exc:
                    logger.warning("Phase6: Auto-approval request creation failed: %s", exc)

            return result

        def __repr__(self) -> str:
            return f"EnhancedSafetyGate(wrapping={self.original!r})"

    return EnhancedSafetyGate(safety_gate, approval_chain)


def _init_component(
    results: dict[str, Any],
    name: str,
    import_fn: Any,
    success_fn: Any | None = None,
) -> Any | None:
    """Initialize a Phase 6 component with standard try/except/log.

    Args:
        results: Results dict to populate (mutated in place).
        name: Component name for result keys and log messages.
        import_fn: Callable that returns the initialized component.
        success_fn: Optional post-init callback receiving the component.

    Returns:
        The initialized component, or None on failure.
    """
    try:
        component = import_fn()
        results[name] = {"status": "ok"}
        if success_fn:
            extra = success_fn(component)
            if isinstance(extra, dict):
                results[name].update(extra)
        logger.info("Phase6: %s initialized", name)
        return component
    except Exception as exc:
        results[name] = {"status": "error", "error": str(exc)}
        logger.error("Phase6: %s init failed: %s", name, exc)
        return None


def initialize_phase6(start_defense_monitoring: bool = True) -> dict[str, Any]:
    """Initialize all Phase 6 components and wire them together.

    Call this during application startup, after AuthService is initialized.

    This function is idempotent — calling it multiple times will return
    the cached result from the first call without re-initializing.

    Args:
        start_defense_monitoring: Whether to start background defense monitoring.

    Returns:
        Dict with initialization status for each component.
    """
    global _phase6_initialized

    # Idempotency guard: prevent double-initialization
    with _phase6_lock:
        if _phase6_initialized:
            logger.info("Phase6: Already initialized — skipping (idempotent)")
            return get_phase6_status()

    results: dict[str, Any] = {}

    # ── 1. Degraded Mode Manager ──────────────────────────
    dm = _init_component(results, "degraded_mode", lambda: get_degraded_mode_manager())

    # ── 2. License Manager ────────────────────────────────
    lm = _init_component(results, "license", lambda: get_license_manager())
    if lm is not None:
        # Wire license events to degraded mode
        _init_component(
            results, "license_degraded_wiring",
            lambda: _wire_license_events(lm, dm),
        )

        # Auto-create default license if none exists
        try:
            if not lm.get_current_license():
                from src.core.license.types import LicenseTier
                lm.create_license(
                    tier=LicenseTier.STARTER,
                    issued_to="Zenic-Agents Default",
                    features=["basic_pipeline", "chat_completions"],
                    max_users=1,
                    expires_days=0,
                )
                logger.info("Phase6: Default starter license created")
        except Exception as exc:
            logger.warning("Phase6: Default license creation failed: %s", exc)

    # ── 3. Defense Manager ────────────────────────────────
    _init_component(
        results, "defense",
        lambda: _init_defense(start_defense_monitoring),
    )

    # ── 4. Approval Chain ─────────────────────────────────
    chain = _init_component(results, "approval", lambda: _init_approval())

    # ── 5. Wire SafetyGate → ApprovalChain (Composition) ──
    if chain is not None:
        _init_component(
            results, "safety_gate_wiring",
            lambda: _wire_safety_gate(chain),
        )

    # ── Mark as initialized (idempotency guard) ───────────
    with _phase6_lock:
        _phase6_initialized = True

    # ── Summary ────────────────────────────────────────────
    ok_count = sum(1 for v in results.values() if v.get("status") == "ok")
    total = len(results)
    logger.info("Phase6: Initialization complete (%d/%d components OK)", ok_count, total)
    return results


def _init_defense(start_monitoring: bool) -> Any:
    """Initialize DefenseManager."""
    from src.core.defense import get_defense_manager
    defense = get_defense_manager()
    defense.initialize_all(start_monitoring=start_monitoring)
    return defense


def _init_approval() -> Any:
    """Initialize ApprovalChain and WorkflowEngine."""
    from src.core.approval.chain import get_approval_chain
    return get_approval_chain()


def _wire_license_events(lm: Any, dm: Any) -> None:
    """Wire license events to degraded mode manager."""
    def _on_license_event(event_type: str, data: dict[str, Any]) -> None:
        """React to license events by adjusting operating mode."""
        if event_type == "kill_switch_activated":
            dm.enter_paralysis(level=3, reason=f"Kill switch: {data.get('reason', '')}")
        elif event_type == "kill_switch_deactivated":
            result = lm.verify()
            if result.valid:
                dm.return_to_normal(reason="Kill switch deactivated, license valid")

    lm.on_license_event(_on_license_event)
    logger.info("Phase6: License → DegradedMode wired")


def _wire_safety_gate(chain: Any) -> None:
    """Wire SafetyGate to ApprovalChain via composition."""
    from src.core.executors.safety_gate import (
        get_default_safety_gate,
        set_default_safety_gate,
    )
    safety_gate = get_default_safety_gate()
    enhanced_gate = _create_enhanced_safety_gate(safety_gate, chain)
    set_default_safety_gate(enhanced_gate)
    logger.info("Phase6: SafetyGate → ApprovalChain wired (composition pattern)")


def get_phase6_status() -> dict[str, Any]:
    """Get comprehensive Phase 6 status across all components."""
    status: dict[str, Any] = {}

    try:
        from src.core.degraded_mode.manager import get_degraded_mode_manager

        status["degraded_mode"] = get_degraded_mode_manager().get_status()
    except Exception:
        status["degraded_mode"] = {"error": "unavailable"}

    try:
        from src.core.license.manager import get_license_manager

        status["license"] = get_license_manager().get_status()
    except Exception:
        status["license"] = {"error": "unavailable"}

    try:
        from src.core.defense import get_defense_manager

        ds = get_defense_manager().get_status()
        status["defense"] = {
            "score": ds.overall_score,
            "active_layers": ds.active_layers,
            "recommendations": ds.recommendations,
        }
    except Exception:
        status["defense"] = {"error": "unavailable"}

    try:
        from src.core.approval.chain import get_approval_chain

        status["approval"] = get_approval_chain().get_stats()
    except Exception:
        status["approval"] = {"error": "unavailable"}

    status["initialized"] = _phase6_initialized

    return status


def reset_phase6() -> None:
    """Reset Phase 6 initialization state (for testing).

    This allows initialize_phase6() to be called again after a reset.
    Should only be used in test environments.
    """
    global _phase6_initialized
    with _phase6_lock:
        _phase6_initialized = False
    logger.info("Phase6: Initialization state reset")


__all__ = ["get_phase6_status", "initialize_phase6", "reset_phase6"]
