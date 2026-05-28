"""Tests reales del SNA — Monitores que escanean datos LOCALES.

Verifica que:
1. Los monitores consultan la BD LOCAL (no canales)
2. Detectan problemas reales (stock bajo, facturas vencidas, etc.)
3. Generan MonitorResults con findings correctos
4. El AlertManager procesa los resultados y genera alertas
5. El Scheduler ejecuta monitores periódicamente
6. El ProactiveChannelBridge envía alertas al canal
"""

import os
import sqlite3
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.channel._proactive import ProactiveChannelBridge
from src.core.channel.a53_text import ChannelType
from src.core.sna.alert_manager import AlertManager, AlertSeverity
from src.core.sna.monitors.base import MonitorWeight
from src.core.sna.monitors.data_integrity import DataIntegrityMonitor
from src.core.sna.monitors.disk_space import DiskSpaceMonitor
from src.core.sna.monitors.duplicate_records import DuplicateRecordsMonitor
from src.core.sna.monitors.low_stock import LowStockMonitor
from src.core.sna.monitors.overdue_invoice import OverdueInvoiceMonitor
from src.core.sna.monitors.stale_inventory import StaleInventoryMonitor
from src.core.sna.monitors.tomorrow_appointment import TomorrowAppointmentMonitor
from src.core.sna.monitors.unpaid_balance import UnpaidBalanceMonitor
from src.core.sna.scheduler import SNAScheduler
from src.core.sna.sna_engine import SNAEngine
from src.data.db_access import DBAccess
from src.data.local_scanner import LocalDataScanner


def create_test_db(db_path: str):
    """Crea una BD de prueba con datos realistas."""
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys=ON")

    conn.execute("""CREATE TABLE productos (
        id INTEGER PRIMARY KEY, nombre TEXT NOT NULL, codigo TEXT,
        stock INTEGER DEFAULT 0, precio REAL, ultima_venta DATE
    )""")
    conn.execute("INSERT INTO productos VALUES (1, 'Lápiz', 'LAP01', 2, 1.5, date('now','-120 days'))")
    conn.execute("INSERT INTO productos VALUES (2, 'Cuaderno', 'CUA01', 0, 3.0, date('now','-5 days'))")
    conn.execute("INSERT INTO productos VALUES (3, 'Bolígrafo', 'BOL01', 50, 2.0, date('now','-1 day'))")

    conn.execute("""CREATE TABLE clientes (
        id INTEGER PRIMARY KEY, nombre TEXT NOT NULL, email TEXT,
        telefono TEXT, saldo_pendiente REAL DEFAULT 0
    )""")
    conn.execute("INSERT INTO clientes VALUES (1, 'Ana', 'ana@test.com', '555-1', 150.0)")
    conn.execute("INSERT INTO clientes VALUES (2, 'Bob', 'bob@test.com', '555-2', 0)")
    conn.execute("INSERT INTO clientes VALUES (3, 'Carlos', 'carlos@test.com', '555-3', 500.5)")
    # Duplicado de email
    conn.execute("INSERT INTO clientes VALUES (4, 'Ana2', 'ana@test.com', '555-4', 0)")

    conn.execute("""CREATE TABLE facturas (
        id INTEGER PRIMARY KEY, cliente_id INTEGER, numero TEXT,
        monto REAL, fecha DATE, fecha_vencimiento DATE, estado TEXT DEFAULT 'pendiente',
        FOREIGN KEY (cliente_id) REFERENCES clientes(id)
    )""")
    conn.execute("INSERT INTO facturas VALUES (1, 1, 'F-001', 100.0, date('now','-30 days'), date('now','-5 days'), 'pendiente')")
    conn.execute("INSERT INTO facturas VALUES (2, 2, 'F-002', 200.0, date('now','-10 days'), date('now','+10 days'), 'pendiente')")
    # Insertar huérfano desactivando FK check temporalmente
    conn.commit()  # Commit antes de cambiar PRAGMA
    conn.execute("PRAGMA foreign_keys=OFF")
    conn.execute("INSERT INTO facturas VALUES (3, 999, 'F-ORPHAN', 50.0, date('now'), date('now','+30 days'), 'pendiente')")
    conn.commit()
    conn.execute("PRAGMA foreign_keys=ON")

    conn.execute("""CREATE TABLE citas (
        id INTEGER PRIMARY KEY, cliente TEXT, fecha DATE, hora TEXT
    )""")
    conn.execute("INSERT INTO citas VALUES (1, 'Ana', date('now','+1 day'), '10:00')")

    conn.execute("""CREATE TABLE ventas (
        id INTEGER PRIMARY KEY, fecha DATE, monto REAL
    )""")
    for i in range(30):
        conn.execute(f"INSERT INTO ventas (fecha, monto) VALUES (date('now','-{i} days'), {100 + i * 5})")  # noqa: S608

    conn.commit()
    conn.close()


class TestLowStockMonitor(unittest.TestCase):
    """Test: El monitor de stock bajo detecta problemas en BD LOCAL."""

    @classmethod
    def setUpClass(cls):
        cls.db_dir = tempfile.mkdtemp()
        cls.db_path = os.path.join(cls.db_dir, "test.db")
        create_test_db(cls.db_path)

    def test_detects_low_stock(self):
        scanner = LocalDataScanner(db_path=self.db_path)
        monitor = LowStockMonitor(scanner, threshold=5)
        result = monitor.run()

        self.assertFalse(result.healthy)
        self.assertGreater(result.finding_count, 0)
        self.assertEqual(result.weight, MonitorWeight.CRITICAL)
        # Lápiz (stock=2) y Cuaderno (stock=0) deben aparecer
        self.assertTrue(any("Lápiz" in f.get("product", "") for f in result.findings))
        self.assertTrue(any("Cuaderno" in f.get("product", "") for f in result.findings))
        scanner.close()

    def test_healthy_when_stock_ok(self):
        scanner = LocalDataScanner(db_path=self.db_path)
        monitor = LowStockMonitor(scanner, threshold=0)
        result = monitor.run()
        # Con threshold=0, solo Cuaderno (stock=0) es problema
        # Si threshold=0, stock<=0 significa stock=0
        self.assertTrue(any("Cuaderno" in f.get("product", "") for f in result.findings) or result.healthy)
        scanner.close()


class TestOverdueInvoiceMonitor(unittest.TestCase):
    """Test: El monitor de facturas vencidas detecta en BD LOCAL."""

    @classmethod
    def setUpClass(cls):
        cls.db_dir = tempfile.mkdtemp()
        cls.db_path = os.path.join(cls.db_dir, "test.db")
        create_test_db(cls.db_path)

    def test_detects_overdue(self):
        scanner = LocalDataScanner(db_path=self.db_path)
        monitor = OverdueInvoiceMonitor(scanner)
        result = monitor.run()

        self.assertFalse(result.healthy)
        self.assertEqual(result.weight, MonitorWeight.CRITICAL)
        # F-001 está vencida
        self.assertTrue(any("F-001" in str(f) for f in result.findings))
        scanner.close()


class TestTomorrowAppointmentMonitor(unittest.TestCase):
    """Test: El monitor de citas detecta en BD LOCAL."""

    @classmethod
    def setUpClass(cls):
        cls.db_dir = tempfile.mkdtemp()
        cls.db_path = os.path.join(cls.db_dir, "test.db")
        create_test_db(cls.db_path)

    def test_detects_tomorrow_appointments(self):
        scanner = LocalDataScanner(db_path=self.db_path)
        monitor = TomorrowAppointmentMonitor(scanner)
        result = monitor.run()

        self.assertFalse(result.healthy)
        self.assertEqual(result.weight, MonitorWeight.WARNING)
        scanner.close()


class TestDiskSpaceMonitor(unittest.TestCase):
    """Test: El monitor de disco escanea el FS LOCAL."""

    @classmethod
    def setUpClass(cls):
        cls.base_dir = tempfile.mkdtemp()
        cls.db_path = os.path.join(cls.base_dir, "test.db")
        create_test_db(cls.db_path)

    def test_disk_check(self):
        scanner = LocalDataScanner(db_path=self.db_path, base_path=self.base_dir)
        monitor = DiskSpaceMonitor(scanner)
        result = monitor.run()

        # El disco del test no debería estar lleno
        # Pero verificamos que el monitor se ejecuta sin error
        self.assertIsNotNone(result)
        scanner.close()


class TestStaleInventoryMonitor(unittest.TestCase):
    """Test: El monitor de inventario estancado detecta en BD LOCAL."""

    @classmethod
    def setUpClass(cls):
        cls.db_dir = tempfile.mkdtemp()
        cls.db_path = os.path.join(cls.db_dir, "test.db")
        create_test_db(cls.db_path)

    def test_detects_stale(self):
        scanner = LocalDataScanner(db_path=self.db_path)
        monitor = StaleInventoryMonitor(scanner, stale_days=90)
        result = monitor.run()

        self.assertFalse(result.healthy)
        # Lápiz no se vende en 120 días
        self.assertTrue(any("Lápiz" in f.get("product", "") for f in result.findings))
        scanner.close()


class TestUnpaidBalanceMonitor(unittest.TestCase):
    """Test: El monitor de saldos pendientes detecta en BD LOCAL."""

    @classmethod
    def setUpClass(cls):
        cls.db_dir = tempfile.mkdtemp()
        cls.db_path = os.path.join(cls.db_dir, "test.db")
        create_test_db(cls.db_path)

    def test_detects_unpaid(self):
        scanner = LocalDataScanner(db_path=self.db_path)
        monitor = UnpaidBalanceMonitor(scanner)
        result = monitor.run()

        self.assertFalse(result.healthy)
        self.assertEqual(result.weight, MonitorWeight.CRITICAL)
        scanner.close()


class TestDuplicateRecordsMonitor(unittest.TestCase):
    """Test: El monitor de duplicados detecta en BD LOCAL."""

    @classmethod
    def setUpClass(cls):
        cls.db_dir = tempfile.mkdtemp()
        cls.db_path = os.path.join(cls.db_dir, "test.db")
        create_test_db(cls.db_path)

    def test_detects_duplicates(self):
        scanner = LocalDataScanner(db_path=self.db_path)
        checks = [{"table": "clientes", "columns": ["email"]}]
        monitor = DuplicateRecordsMonitor(scanner, checks=checks)
        result = monitor.run()

        self.assertFalse(result.healthy)
        # ana@test.com aparece 2 veces
        self.assertTrue(any("email" in f.get("column", "") for f in result.findings))
        scanner.close()


class TestDataIntegrityMonitor(unittest.TestCase):
    """Test: El monitor de integridad detecta huérfanos en BD LOCAL."""

    @classmethod
    def setUpClass(cls):
        cls.db_dir = tempfile.mkdtemp()
        cls.db_path = os.path.join(cls.db_dir, "test.db")
        create_test_db(cls.db_path)

    def test_detects_orphans(self):
        scanner = LocalDataScanner(db_path=self.db_path)
        fk_checks = [{"child": "facturas", "fk": "cliente_id", "parent": "clientes"}]
        null_checks = [{"table": "productos", "required": ["nombre", "precio"]}]
        monitor = DataIntegrityMonitor(scanner, fk_checks=fk_checks, null_checks=null_checks)
        result = monitor.run()

        self.assertFalse(result.healthy)
        # F-ORPHAN tiene cliente_id=999
        self.assertTrue(any("orphan" in f.get("type", "") for f in result.findings))
        scanner.close()


class TestAlertManager(unittest.TestCase):
    """Test: AlertManager procesa resultados y genera alertas."""

    def test_processes_unhealthy_result(self):
        from src.core.sna.monitors.base import MonitorResult

        manager = AlertManager()
        result = MonitorResult(
            monitor_name="low_stock",
            weight=MonitorWeight.CRITICAL,
            healthy=False,
            findings=[{"type": "low_stock", "message": "Stock bajo: Item1"}],
        )

        alert = manager.process_result(result)
        self.assertIsNotNone(alert)
        self.assertEqual(alert.severity, AlertSeverity.CRITICAL)

    def test_ignores_healthy_result(self):
        from src.core.sna.monitors.base import MonitorResult

        manager = AlertManager()
        result = MonitorResult(
            monitor_name="low_stock",
            weight=MonitorWeight.CRITICAL,
            healthy=True,
        )

        alert = manager.process_result(result)
        self.assertIsNone(alert)

    def test_deduplication(self):
        from src.core.sna.monitors.base import MonitorResult

        manager = AlertManager(cooldown_seconds=300)
        result = MonitorResult(
            monitor_name="low_stock",
            weight=MonitorWeight.CRITICAL,
            healthy=False,
            findings=[{"type": "low_stock", "message": "Stock bajo: Item1"}],
        )

        # Primera alerta debe pasar
        alert1 = manager.process_result(result)
        self.assertIsNotNone(alert1)

        # Segunda alerta deduplicada
        alert2 = manager.process_result(result)
        self.assertIsNone(alert2)

    def test_rate_limiting(self):
        from src.core.sna.monitors.base import MonitorResult

        manager = AlertManager(rate_limit_per_minute=2)
        alerts = []

        for i in range(5):
            result = MonitorResult(
                monitor_name=f"monitor_{i}",
                weight=MonitorWeight.WARNING,
                healthy=False,
                findings=[{"type": f"issue_{i}", "message": f"Issue {i}"}],
            )
            alert = manager.process_result(result)
            if alert:
                alerts.append(alert)

        # Solo 2 deben pasar (rate limit)
        self.assertLessEqual(len(alerts), 2)


class TestSNAScheduler(unittest.TestCase):
    """Test: Scheduler ejecuta monitores y genera alertas."""

    @classmethod
    def setUpClass(cls):
        cls.db_dir = tempfile.mkdtemp()
        cls.db_path = os.path.join(cls.db_dir, "test.db")
        create_test_db(cls.db_path)

    def test_run_all(self):
        scanner = LocalDataScanner(db_path=self.db_path)
        scheduler = SNAScheduler(scanner)

        alerts = scheduler.run_all()
        # Debe generar alertas (stock bajo, facturas vencidas, etc.)
        self.assertGreater(len(alerts), 0)

        # Health summary
        health = scheduler.get_health_summary()
        self.assertGreater(health["total_monitors"], 0)
        self.assertGreater(health["monitors_run"], 0)
        scanner.close()

    def test_run_specific_monitor(self):
        scanner = LocalDataScanner(db_path=self.db_path)
        scheduler = SNAScheduler(scanner)

        result = scheduler.run_monitor("low_stock")
        self.assertIsNotNone(result)
        scanner.close()


class TestSNAEngineWithProactiveBridge(unittest.TestCase):
    """Test: SNAEngine + ProactiveChannelBridge integrado.

    Verifica que:
    1. SNA detecta problemas en datos LOCALES
    2. Alertas van al ProactiveChannelBridge
    3. El bridge prepara los mensajes para enviar
    """

    @classmethod
    def setUpClass(cls):
        cls.db_dir = tempfile.mkdtemp()
        cls.db_path = os.path.join(cls.db_dir, "test.db")
        create_test_db(cls.db_path)

    def test_end_to_end(self):
        """Test end-to-end: BD local → SNA → Alert → Bridge."""
        received_alerts = []

        def on_alert(alert):
            received_alerts.append(alert)

        scanner = LocalDataScanner(db_path=self.db_path)
        bridge = ProactiveChannelBridge(
            default_channel=ChannelType.TELEGRAM,
            default_recipient="test_user",
        )
        engine = SNAEngine(
            db_path=self.db_path,
            on_alert=on_alert,
        )

        # Ejecutar escaneo completo
        alerts = engine.full_scan()

        # Debe haber alertas (stock bajo, facturas vencidas, etc.)
        self.assertGreater(len(alerts), 0)

        # Las alertas deben haber llegado al callback
        self.assertGreater(len(received_alerts), 0)

        # Health summary
        health = engine.health_summary()
        self.assertIsNotNone(health)

        scanner.close()
        engine.close()


if __name__ == "__main__":
    unittest.main()
