"""SNA Monitors — 12 monitores que escanean datos LOCALES.

Cada monitor usa LocalDataScanner para ver directamente en la BD del usuario.
NO dependen de canales. Son los ojos del sistema.

Pesos:
    CRITICAL (3): Problemas que pueden causar pérdida de datos o dinero
    WARNING  (2): Problemas que afectan operaciones
    INFO     (1): Información útil para el usuario
"""

from src.core.sna.monitors.api_health import APIHealthMonitor
from src.core.sna.monitors.backup_status import BackupStatusMonitor
from src.core.sna.monitors.base import BaseMonitor, MonitorResult, MonitorWeight
from src.core.sna.monitors.config_drift import ConfigDriftMonitor
from src.core.sna.monitors.data_integrity import DataIntegrityMonitor
from src.core.sna.monitors.disk_space import DiskSpaceMonitor
from src.core.sna.monitors.duplicate_records import DuplicateRecordsMonitor
from src.core.sna.monitors.low_stock import LowStockMonitor
from src.core.sna.monitors.overdue_invoice import OverdueInvoiceMonitor
from src.core.sna.monitors.sales_trend import SalesTrendMonitor
from src.core.sna.monitors.stale_inventory import StaleInventoryMonitor
from src.core.sna.monitors.tomorrow_appointment import TomorrowAppointmentMonitor
from src.core.sna.monitors.unpaid_balance import UnpaidBalanceMonitor

__all__ = [
    "APIHealthMonitor",
    "BackupStatusMonitor",
    "BaseMonitor",
    "ConfigDriftMonitor",
    "DataIntegrityMonitor",
    "DiskSpaceMonitor",
    "DuplicateRecordsMonitor",
    "LowStockMonitor",
    "MonitorResult",
    "MonitorWeight",
    "OverdueInvoiceMonitor",
    "SalesTrendMonitor",
    "StaleInventoryMonitor",
    "TomorrowAppointmentMonitor",
    "UnpaidBalanceMonitor",
]
