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

import logging
import threading
from typing import Any, Dict, Optional

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
        from src.core.executors.safety_gate import SafetyCheckResult, SafetyVerdict, ActionCategory
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
                    try:
                        setattr(self, attr_name, getattr(original_gate, attr_name))
                    except (AttributeError, TypeError):
                        pass

        def check(
            self,
            action_type: str,
            config: Dict[str, Any],
            context: Optional[Dict[str, Any]] = None,
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


def initialize_phase6(start_defense_monitoring: bool = True) -> Dict[str, Any]:
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

    results: Dict[str, Any] = {}

    # ── 1. Degraded Mode Manager ──────────────────────────
    try:
        from src.core.degraded_mode.manager import get_degraded_mode_manager
        dm = get_degraded_mode_manager()
        results["degraded_mode"] = {"status": "ok", "mode": dm.get_current_mode().value}
        logger.info("Phase6: DegradedModeManager initialized (mode=%s)", dm.get_current_mode().value)
    except Exception as exc:
        results["degraded_mode"] = {"status": "error", "error": str(exc)}
        logger.error("Phase6: DegradedModeManager init failed: %s", exc)

    # ── 2. License Manager ────────────────────────────────
    try:
        from src.core.license.manager import get_license_manager
        lm = get_license_manager()
        results["license"] = {"status": "ok", "data": lm.get_status()}

        # Wire license events to degraded mode
        try:
            from src.core.degraded_mode.manager import get_degraded_mode_manager

            dm = get_degraded_mode_manager()

            def _on_license_event(event_type: str, data: Dict[str, Any]) -> None:
                """React to license events by adjusting operating mode."""
                if event_type == "kill_switch_activated":
                    dm.enter_paralysis(level=3, reason=f"Kill switch: {data.get('reason', '')}")
                elif event_type == "kill_switch_deactivated":
                    # Only return to normal if license is valid
                    result = lm.verify()
                    if result.valid:
                        dm.return_to_normal(reason="Kill switch deactivated, license valid")

            lm.on_license_event(_on_license_event)
            logger.info("Phase6: License → DegradedMode wired")
        except Exception as exc:
            logger.warning("Phase6: License-DegradedMode wiring failed: %s", exc)

    except Exception as exc:
        results["license"] = {"status": "error", "error": str(exc)}
        logger.error("Phase6: LicenseManager init failed: %s", exc)

    # ── 3. Defense Manager ────────────────────────────────
    try:
        from src.core.defense import get_defense_manager
        defense = get_defense_manager()
        defense.initialize_all(start_monitoring=start_defense_monitoring)
        results["defense"] = {"status": "ok", "active_layers": defense.get_status().active_layers}
        logger.info("Phase6: DefenseManager initialized (%d active layers)", defense.get_status().active_layers)
    except Exception as exc:
        results["defense"] = {"status": "error", "error": str(exc)}
        logger.error("Phase6: DefenseManager init failed: %s", exc)

    # ── 4. Approval Chain ─────────────────────────────────
    try:
        from src.core.approval.chain import get_approval_chain
        from src.core.approval.workflows import get_workflow_engine

        chain = get_approval_chain()
        engine = get_workflow_engine()
        results["approval"] = {
            "status": "ok",
            "workflows": len(engine.list_workflows()),
        }
        logger.info("Phase6: ApprovalChain + WorkflowEngine initialized")
    except Exception as exc:
        results["approval"] = {"status": "error", "error": str(exc)}
        logger.error("Phase6: ApprovalChain init failed: %s", exc)

    # ── 5. Wire SafetyGate → ApprovalChain (Composition) ──
    try:
        from src.core.executors.safety_gate import (
            get_default_safety_gate,
            set_default_safety_gate,
        )
        from src.core.approval.chain import get_approval_chain

        safety_gate = get_default_safety_gate()
        chain = get_approval_chain()

        # FASE 4 FIX: Use composition instead of monkey-patching.
        # Create an EnhancedSafetyGate that wraps the original and
        # integrates with the ApprovalChain, without mutating the
        # original instance's check method.
        enhanced_gate = _create_enhanced_safety_gate(safety_gate, chain)

        # Replace the global singleton with the enhanced version
        # using the official API. This is thread-safe and preserves
        # denied actions from the original instance.
        set_default_safety_gate(enhanced_gate)

        results["safety_gate_wiring"] = {"status": "ok", "pattern": "composition"}
        logger.info("Phase6: SafetyGate → ApprovalChain wired (composition pattern)")
    except Exception as exc:
        results["safety_gate_wiring"] = {"status": "error", "error": str(exc)}
        logger.warning("Phase6: SafetyGate wiring failed: %s", exc)

    # ── 6. Auto-create default license if none exists ──────
    try:
        from src.core.license.types import LicenseTier
        from src.core.license.manager import get_license_manager
        lm = get_license_manager()
        if not lm.get_current_license():
            # Create a starter-tier license by default
            lm.create_license(
                tier=LicenseTier.STARTER,
                issued_to="Zenic-Agents Default",
                features=["basic_pipeline", "chat_completions"],
                max_users=1,
                expires_days=0,  # Perpetual starter license
            )
            logger.info("Phase6: Default starter license created")
    except Exception as exc:
        logger.warning("Phase6: Default license creation failed: %s", exc)

    # ── Mark as initialized (idempotency guard) ───────────
    with _phase6_lock:
        _phase6_initialized = True

    # ── Summary ────────────────────────────────────────────
    ok_count = sum(1 for v in results.values() if v.get("status") == "ok")
    total = len(results)
    logger.info("Phase6: Initialization complete (%d/%d components OK)", ok_count, total)
    return results


def get_phase6_status() -> Dict[str, Any]:
    """Get comprehensive Phase 6 status across all components."""
    status: Dict[str, Any] = {}

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


__all__ = ["initialize_phase6", "get_phase6_status", "reset_phase6"]
