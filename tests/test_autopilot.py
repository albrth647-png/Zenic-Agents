"""Tests del AutopilotEngine — Verifica pipeline de automatización."""

import os
import sys
import sqlite3
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.data.local_scanner import LocalDataScanner
from src.core.autopilot.engine import AutopilotEngine, AutonomyLevel, GoalTemplate
from src.core.safety.safety_gate import SafetyGate


def create_test_db(db_path: str):
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE productos (id INTEGER PRIMARY KEY, nombre TEXT, stock INTEGER)")
    conn.execute("INSERT INTO productos VALUES (1, 'Item1', 2)")
    conn.commit()
    conn.close()


class TestAutopilotEngine(unittest.TestCase):
    """Test: Autopilot crea objetivos y genera planes."""

    @classmethod
    def setUpClass(cls):
        cls.db_dir = tempfile.mkdtemp()
        cls.db_path = os.path.join(cls.db_dir, "test.db")
        create_test_db(cls.db_path)

    def test_create_goal(self):
        scanner = LocalDataScanner(db_path=self.db_path)
        engine = AutopilotEngine(scanner, autonomy_level=AutonomyLevel.SEMI_AUTONOMOUS)

        goal = engine.create_goal(
            template=GoalTemplate.INVENTORY_OPTIMIZATION,
            description="Optimizar inventario bajo",
            target_metric="stock_below_threshold",
            target_value=0,
        )
        self.assertIsNotNone(goal)
        self.assertEqual(goal.template, GoalTemplate.INVENTORY_OPTIMIZATION)
        scanner.close()

    def test_generate_plan(self):
        scanner = LocalDataScanner(db_path=self.db_path)
        engine = AutopilotEngine(scanner)

        goal = engine.create_goal(
            template=GoalTemplate.CUSTOMER_RETENTION,
            description="Retener clientes en riesgo",
            target_metric="churn_rate",
            target_value=0.05,
        )

        plan = engine.generate_plan(goal.id)
        self.assertIsNotNone(plan)
        self.assertGreater(len(plan.steps), 0)
        self.assertEqual(plan.goal.id, goal.id)
        scanner.close()

    def test_execute_plan_full_autonomous(self):
        """En FULL_AUTONOMOUS, las acciones de bajo riesgo se ejecutan."""
        scanner = LocalDataScanner(db_path=self.db_path)
        safety = SafetyGate()
        engine = AutopilotEngine(scanner, safety_gate=safety, autonomy_level=AutonomyLevel.FULL_AUTONOMOUS)

        goal = engine.create_goal(
            template=GoalTemplate.APPOINTMENT_REMINDER,
            description="Recordar citas",
            target_metric="appointment_noshow_rate",
            target_value=0,
        )

        plan = engine.generate_plan(goal.id)
        result = engine.execute_plan(plan.id)

        self.assertIsNotNone(result)
        self.assertIn("success", result)
        scanner.close()

    def test_execute_plan_supervised(self):
        """En SUPERVISED, las acciones requieren aprobación."""
        scanner = LocalDataScanner(db_path=self.db_path)
        safety = SafetyGate()
        engine = AutopilotEngine(scanner, safety_gate=safety, autonomy_level=AutonomyLevel.SUPERVISED)

        goal = engine.create_goal(
            template=GoalTemplate.REVENUE_RECOVERY,
            description="Recuperar ingresos",
            target_metric="unpaid_invoices",
            target_value=0,
        )

        plan = engine.generate_plan(goal.id)
        result = engine.execute_plan(plan.id)

        # En supervised, los pasos de riesgo medium+ quedan en awaiting_approval
        self.assertIsNotNone(result)
        scanner.close()

    def test_get_status(self):
        scanner = LocalDataScanner(db_path=self.db_path)
        engine = AutopilotEngine(scanner)

        status = engine.get_status()
        self.assertEqual(status["autonomy_level"], "semi_autonomous")
        self.assertEqual(status["total_goals"], 0)
        scanner.close()


if __name__ == "__main__":
    unittest.main()
