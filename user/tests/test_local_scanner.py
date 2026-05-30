"""Tests reales del LocalDataScanner — SIN MOCKS.

Verifica que el scanner puede:
1. Conectarse a una BD SQLite real
2. Descubrir tablas y esquemas
3. Detectar productos con stock bajo
4. Detectar facturas vencidas
5. Detectar problemas de integridad
6. Escanear el filesystem
7. Generar un full_scan completo
"""

import os
import sqlite3
import sys
import tempfile
import unittest

# Añadir src al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.data.db_access import DBAccess
from src.data.fs_scanner import FileSystemScanner
from src.data.local_scanner import LocalDataScanner


class TestDBAccess(unittest.TestCase):
    """Tests de acceso a base de datos — BD REAL."""

    @classmethod
    def setUpClass(cls):
        """Crea una BD de prueba con datos reales."""
        cls.db_dir = tempfile.mkdtemp()
        cls.db_path = os.path.join(cls.db_dir, "test.db")
        conn = sqlite3.connect(cls.db_path)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")

        # Tabla productos (con stock bajo)
        conn.execute("""
            CREATE TABLE productos (
                id INTEGER PRIMARY KEY,
                nombre TEXT NOT NULL,
                codigo TEXT,
                stock INTEGER DEFAULT 0,
                precio REAL,
                ultima_venta DATE
            )
        """)
        # Insertar productos con stock bajo
        conn.execute(
            "INSERT INTO productos (nombre, codigo, stock, precio, ultima_venta) VALUES ('Lápiz', 'LAP001', 2, 1.50, date('now', '-120 days'))"
        )
        conn.execute(
            "INSERT INTO productos (nombre, codigo, stock, precio, ultima_venta) VALUES ('Cuaderno', 'CUA001', 0, 3.00, date('now', '-5 days'))"
        )
        conn.execute(
            "INSERT INTO productos (nombre, codigo, stock, precio, ultima_venta) VALUES ('Bolígrafo', 'BOL001', 50, 2.00, date('now', '-1 day'))"
        )
        conn.execute(
            "INSERT INTO productos (nombre, codigo, stock, precio, ultima_venta) VALUES ('Regla', 'REG001', 3, 1.75, date('now', '-200 days'))"
        )
        conn.execute(
            "INSERT INTO productos (nombre, codigo, stock, precio, ultima_venta) VALUES ('Mochila', 'MOC001', 10, 25.00, date('now', '-3 days'))"
        )

        # Tabla clientes
        conn.execute("""
            CREATE TABLE clientes (
                id INTEGER PRIMARY KEY,
                nombre TEXT NOT NULL,
                email TEXT,
                telefono TEXT,
                saldo_pendiente REAL DEFAULT 0
            )
        """)
        conn.execute(
            "INSERT INTO clientes (nombre, email, telefono, saldo_pendiente) VALUES ('Ana García', 'ana@test.com', '555-001', 150.00)"
        )
        conn.execute(
            "INSERT INTO clientes (nombre, email, telefono, saldo_pendiente) VALUES ('Bob López', 'bob@test.com', '555-002', 0)"
        )
        conn.execute(
            "INSERT INTO clientes (nombre, email, telefono, saldo_pendiente) VALUES ('Carlos Ruiz', 'carlos@test.com', '555-003', 500.50)"
        )

        # Tabla facturas (con vencidas)
        conn.execute("""
            CREATE TABLE facturas (
                id INTEGER PRIMARY KEY,
                cliente_id INTEGER,
                numero TEXT,
                monto REAL,
                fecha DATE,
                fecha_vencimiento DATE,
                estado TEXT DEFAULT 'pendiente',
                FOREIGN KEY (cliente_id) REFERENCES clientes(id)
            )
        """)
        conn.execute(
            "INSERT INTO facturas (cliente_id, numero, monto, fecha, fecha_vencimiento, estado) VALUES (1, 'F-001', 100.00, date('now', '-30 days'), date('now', '-5 days'), 'pendiente')"
        )
        conn.execute(
            "INSERT INTO facturas (cliente_id, numero, monto, fecha, fecha_vencimiento, estado) VALUES (2, 'F-002', 200.00, date('now', '-10 days'), date('now', '+10 days'), 'pendiente')"
        )
        conn.execute(
            "INSERT INTO facturas (cliente_id, numero, monto, fecha, fecha_vencimiento, estado) VALUES (3, 'F-003', 300.00, date('now', '-60 days'), date('now', '-30 days'), 'pendiente')"
        )
        conn.execute(
            "INSERT INTO facturas (cliente_id, numero, monto, fecha, fecha_vencimiento, estado) VALUES (1, 'F-004', 50.00, date('now', '-5 days'), date('now', '+25 days'), 'pagada')"
        )

        # Tabla citas
        conn.execute("""
            CREATE TABLE citas (
                id INTEGER PRIMARY KEY,
                cliente TEXT,
                fecha DATE,
                hora TEXT
            )
        """)
        conn.execute("INSERT INTO citas (cliente, fecha, hora) VALUES ('Ana García', date('now', '+1 day'), '10:00')")
        conn.execute("INSERT INTO citas (cliente, fecha, hora) VALUES ('Bob López', date('now', '+1 day'), '14:30')")
        conn.execute("INSERT INTO citas (cliente, fecha, hora) VALUES ('Carlos Ruiz', date('now', '+3 days'), '09:00')")

        # Tabla ventas
        conn.execute("""
            CREATE TABLE ventas (
                id INTEGER PRIMARY KEY,
                fecha DATE,
                monto REAL,
                producto_id INTEGER
            )
        """)
        # Ventas de los últimos 30 días
        for i in range(30):
            day = f"date('now', '-{i} days')"
            amount = 100 + (i % 7) * 20
            conn.execute(f"INSERT INTO ventas (fecha, monto, producto_id) VALUES ({day}, {amount}, {(i % 5) + 1})")  # noqa: S608

        # Registro huérfano (factura sin cliente válido)
        # Desactivar FK check para poder insertar un huérfano
        conn.commit()  # Commit antes de cambiar PRAGMA
        conn.execute("PRAGMA foreign_keys=OFF")
        conn.execute(
            "INSERT INTO facturas (cliente_id, numero, monto, fecha, fecha_vencimiento, estado) VALUES (999, 'F-ORPHAN', 50.00, date('now'), date('now', '+30 days'), 'pendiente')"
        )
        conn.commit()
        conn.execute("PRAGMA foreign_keys=ON")

        conn.commit()
        conn.close()

    def setUp(self):
        self.db = DBAccess(self.db_path)

    def tearDown(self):
        self.db.close()

    def test_list_tables(self):
        """Verifica que lista todas las tablas."""
        tables = self.db.list_tables()
        self.assertIn("productos", tables)
        self.assertIn("clientes", tables)
        self.assertIn("facturas", tables)
        self.assertIn("citas", tables)
        self.assertIn("ventas", tables)
        self.assertGreaterEqual(len(tables), 5)

    def test_get_table_schema(self):
        """Verifica que obtiene el esquema de una tabla."""
        schema = self.db.get_table_schema("productos")
        self.assertGreater(len(schema), 0)
        names = [c["name"] for c in schema]
        self.assertIn("id", names)
        self.assertIn("nombre", names)
        self.assertIn("stock", names)
        self.assertIn("precio", names)

    def test_get_table_count(self):
        """Verifica que cuenta registros correctamente."""
        count = self.db.get_table_count("productos")
        self.assertEqual(count, 5)

        count = self.db.get_table_count("clientes")
        self.assertEqual(count, 3)

    def test_check_integrity(self):
        """Verifica que check_integrity funciona."""
        result = self.db.check_integrity()
        self.assertIn("status", result)

    def test_low_stock_items(self):
        """Verifica detección de stock bajo — el SNA NO es adivino."""
        items = self.db.get_low_stock_items(threshold=5)
        self.assertGreater(len(items), 0)
        # Lápiz (stock=2) y Cuaderno (stock=0) y Regla (stock=3) deben aparecer
        names = [item.get("nombre", "") for item in items]
        self.assertIn("Lápiz", names)
        self.assertIn("Cuaderno", names)
        self.assertIn("Regla", names)
        # Bolígrafo (stock=50) y Mochila (stock=10) NO deben aparecer
        self.assertNotIn("Bolígrafo", names)
        self.assertNotIn("Mochila", names)

    def test_overdue_invoices(self):
        """Verifica detección de facturas vencidas — datos locales, no canales."""
        invoices = self.db.get_overdue_invoices()
        self.assertGreater(len(invoices), 0)
        # F-001 y F-003 están vencidas (fecha_vencimiento < today)
        numbers = [inv.get("numero", "") for inv in invoices]
        self.assertIn("F-001", numbers)
        self.assertIn("F-003", numbers)
        # F-002 no está vencida (+10 days)
        self.assertNotIn("F-002", numbers)

    def test_tomorrow_appointments(self):
        """Verifica detección de citas de mañana."""
        appointments = self.db.get_tomorrow_appointments()
        self.assertGreaterEqual(len(appointments), 2)  # Ana y Bob

    def test_unpaid_balances(self):
        """Verifica detección de saldos pendientes."""
        clients = self.db.get_unpaid_balances()
        self.assertGreater(len(clients), 0)
        # Ana (150) y Carlos (500.50) tienen saldo
        names = [c.get("nombre", "") for c in clients]
        self.assertIn("Ana García", names)
        self.assertIn("Carlos Ruiz", names)
        self.assertNotIn("Bob López", names)

    def test_stale_inventory(self):
        """Verifica detección de inventario estancado."""
        items = self.db.get_stale_inventory(days=90)
        self.assertGreater(len(items), 0)
        # Lápiz y Regla no se venden en 90+ días
        names = [item.get("nombre", "") for item in items]
        self.assertIn("Lápiz", names)
        self.assertIn("Regla", names)

    def test_sales_trend(self):
        """Verifica tendencia de ventas."""
        trend = self.db.get_sales_trend(days=30)
        self.assertGreater(len(trend), 0)

    def test_find_orphan_records(self):
        """Verifica detección de registros huérfanos."""
        orphans = self.db.find_orphan_records("facturas", "cliente_id", "clientes")
        self.assertGreater(len(orphans), 0)
        # F-ORPHAN tiene cliente_id=999 que no existe
        numbers = [o.get("numero", "") for o in orphans]
        self.assertIn("F-ORPHAN", numbers)

    def test_find_duplicates(self):
        """Verifica detección de duplicados."""
        # No hay emails duplicados en los datos de prueba
        dups = self.db.find_duplicates("clientes", ["email"])
        self.assertEqual(len(dups), 0)

    def test_execute_query_only_select(self):
        """Verifica que solo se permiten SELECT."""
        with self.assertRaises(ValueError):
            self.db.execute_query("DELETE FROM productos WHERE id = 1")

    def test_get_db_size(self):
        """Verifica tamaño de BD."""
        size = self.db.get_db_size_bytes()
        self.assertGreater(size, 0)


class TestFileSystemScanner(unittest.TestCase):
    """Tests del escáner de filesystem — FS REAL."""

    @classmethod
    def setUpClass(cls):
        cls.test_dir = tempfile.mkdtemp()
        # Crear estructura de directorios
        os.makedirs(os.path.join(cls.test_dir, "db"), exist_ok=True)
        os.makedirs(os.path.join(cls.test_dir, "backups"), exist_ok=True)
        os.makedirs(os.path.join(cls.test_dir, "logs"), exist_ok=True)
        os.makedirs(os.path.join(cls.test_dir, "temp"), exist_ok=True)
        os.makedirs(os.path.join(cls.test_dir, "data"), exist_ok=True)

        # Crear archivos
        with open(os.path.join(cls.test_dir, ".env"), "w") as f:
            f.write("DATABASE_URL=file:test.db\nTEST=true\n")

        with open(os.path.join(cls.test_dir, "config.json"), "w") as f:
            f.write('{"key": "value"}\n')

        # Backup reciente
        with open(os.path.join(cls.test_dir, "backups", "backup_001.db"), "w") as f:
            f.write("x" * 1000)

        # Log pequeño
        with open(os.path.join(cls.test_dir, "logs", "app.log"), "w") as f:
            f.write("log entry\n")

        # Archivo temporal viejo
        old_file = os.path.join(cls.test_dir, "temp", "old_cache.tmp")
        with open(old_file, "w") as f:
            f.write("temp data")
        # Hacerlo viejo (modificar mtime)
        import time

        old_time = time.time() - 48 * 3600  # 48 horas atrás
        os.utime(old_file, (old_time, old_time))

    def setUp(self):
        self.scanner = FileSystemScanner(base_path=self.test_dir)

    def test_disk_usage(self):
        """Verifica escaneo de disco."""
        usage = self.scanner.get_disk_usage()
        self.assertIn("percent_used", usage)
        self.assertIn("status", usage)
        self.assertNotEqual(usage["status"], "error")

    def test_scan_config_files(self):
        """Verifica escaneo de configuraciones."""
        configs = self.scanner.scan_config_files()
        self.assertGreater(len(configs), 0)

        # .env debe existir
        env_config = next((c for c in configs if ".env" in c.get("path", "")), None)
        self.assertIsNotNone(env_config)
        self.assertTrue(env_config["exists"])

        # config.json debe ser JSON válido
        json_config = next((c for c in configs if "config.json" in c.get("path", "")), None)
        self.assertIsNotNone(json_config)
        self.assertTrue(json_config.get("valid_json", False))

    def test_scan_backups(self):
        """Verifica escaneo de backups."""
        backup = self.scanner.scan_backups()
        self.assertEqual(backup["status"], "ok")
        self.assertGreater(backup.get("file_count", 0), 0)

    def test_scan_logs(self):
        """Verifica escaneo de logs."""
        logs = self.scanner.scan_logs()
        self.assertIn("status", logs)

    def test_scan_temp_files(self):
        """Verifica detección de archivos temporales viejos."""
        temp = self.scanner.scan_temp_files(max_age_hours=24)
        # old_cache.tmp tiene 48 horas → debe ser detectado como stale
        self.assertGreater(temp.get("stale_file_count", 0), 0)

    def test_full_health_check(self):
        """Verifica health check completo."""
        health = self.scanner.full_health_check()
        self.assertIn("disk", health)
        self.assertIn("configs", health)
        self.assertIn("backups", health)
        self.assertIn("timestamp", health)


class TestLocalDataScanner(unittest.TestCase):
    """Tests del LocalDataScanner (fachada) — BD REAL + FS REAL."""

    @classmethod
    def setUpClass(cls):
        # Reutilizar la BD del TestDBAccess
        cls.db_dir = tempfile.mkdtemp()
        cls.db_path = os.path.join(cls.db_dir, "test.db")
        conn = sqlite3.connect(cls.db_path)
        conn.execute("""
            CREATE TABLE productos (
                id INTEGER PRIMARY KEY, nombre TEXT, stock INTEGER DEFAULT 0,
                precio REAL, ultima_venta DATE
            )
        """)
        conn.execute(
            "INSERT INTO productos (nombre, stock, precio, ultima_venta) VALUES ('Item1', 1, 10.0, date('now', '-100 days'))"
        )
        conn.execute(
            "INSERT INTO productos (nombre, stock, precio, ultima_venta) VALUES ('Item2', 20, 5.0, date('now', '-1 day'))"
        )
        conn.commit()
        conn.close()

        cls.base_dir = tempfile.mkdtemp()
        os.makedirs(os.path.join(cls.base_dir, "db"), exist_ok=True)

    def test_scan_low_stock(self):
        """Verifica que LocalDataScanner detecta stock bajo en BD REAL."""
        scanner = LocalDataScanner(db_path=self.db_path, base_path=self.base_dir)
        items = scanner.scan_low_stock(threshold=5)
        self.assertGreater(len(items), 0)
        scanner.close()

    def test_scan_database_schema(self):
        """Verifica escaneo de esquema de BD REAL."""
        scanner = LocalDataScanner(db_path=self.db_path, base_path=self.base_dir)
        schema = scanner.scan_database_schema()
        self.assertEqual(schema["status"], "ok")
        self.assertGreater(schema["table_count"], 0)
        scanner.close()

    def test_full_scan(self):
        """Verifica full_scan completo (BD + FS)."""
        scanner = LocalDataScanner(db_path=self.db_path, base_path=self.base_dir)
        result = scanner.full_scan()
        self.assertIn("database", result)
        self.assertIn("disk", result)
        self.assertIn("business_data", result)
        self.assertIn("timestamp", result)
        scanner.close()


if __name__ == "__main__":
    unittest.main()
