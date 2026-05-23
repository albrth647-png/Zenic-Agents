"""Tests del SafetyGate — Verifica que DENY es inbypassable."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.safety.safety_gate import SafetyGate, SafetyVerdict
from src.core.safety.policy import PolicyEngine, PolicyAction


class TestSafetyGate(unittest.TestCase):
    """Test: SafetyGate bloquea acciones peligrosas."""

    def setUp(self):
        self.gate = SafetyGate(policy_engine=PolicyEngine())

    def test_approves_scan_action(self):
        """Scan es de bajo riesgo → auto-aprobado."""
        result = self.gate.evaluate("scan", {})
        self.assertTrue(result.approved)

    def test_approves_notify_action(self):
        """Notify es de bajo riesgo → auto-aprobado."""
        result = self.gate.evaluate("notify", {})
        self.assertTrue(result.approved)

    def test_blocks_delete_action(self):
        """Delete es bloqueado por policy (DENY)."""
        result = self.gate.evaluate("delete", {})
        self.assertFalse(result.approved)
        self.assertEqual(result.verdict, SafetyVerdict.DENY)

    def test_blocks_dangerous_patterns(self):
        """Patrones peligrosos son bloqueados por regla determinística."""
        result = self.gate.evaluate("execute", {"description": "rm -rf /"})
        self.assertFalse(result.approved)

    def test_update_requires_review(self):
        """Update requiere revisión humana (RESTRICT)."""
        result = self.gate.evaluate("update", {})
        self.assertFalse(result.approved)
        self.assertTrue(result.requires_human)

    def test_deny_is_final(self):
        """DENY no puede ser sobrepasado."""
        result = self.gate.evaluate("delete", {})
        self.assertEqual(result.verdict, SafetyVerdict.DENY)
        self.assertFalse(result.approved)
        # El veredicto DENY es inmutable en su significado
        self.assertEqual(result.verdict, SafetyVerdict.DENY)

    def test_blocks_sql_injection(self):
        """Bloquea intentos de SQL injection."""
        result = self.gate.evaluate("action", {"description": "DROP TABLE users"})
        self.assertFalse(result.approved)

    def test_stats(self):
        """Verifica estadísticas del gate."""
        self.gate.evaluate("scan", {})  # approve
        self.gate.evaluate("delete", {})  # deny
        self.gate.evaluate("update", {})  # review

        stats = self.gate.get_stats()
        self.assertGreater(stats["approved"], 0)
        self.assertGreater(stats["denied"], 0)
        self.assertGreater(stats["review"], 0)


class TestPolicyEngine(unittest.TestCase):
    """Test: PolicyEngine evalúa políticas correctamente."""

    def setUp(self):
        self.engine = PolicyEngine()

    def test_scan_allowed(self):
        result = self.engine.evaluate("scan")
        self.assertEqual(result, PolicyAction.ALLOW)

    def test_delete_denied(self):
        result = self.engine.evaluate("delete")
        self.assertEqual(result, PolicyAction.DENY)

    def test_update_restricted(self):
        result = self.engine.evaluate("update")
        self.assertEqual(result, PolicyAction.RESTRICT)

    def test_unknown_restricted(self):
        """Acciones sin política son restringidas por defecto."""
        result = self.engine.evaluate("unknown_action")
        self.assertEqual(result, PolicyAction.RESTRICT)


if __name__ == "__main__":
    unittest.main()
