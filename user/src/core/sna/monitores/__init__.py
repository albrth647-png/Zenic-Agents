"""
Zenic-Agents Asistente - SNA Monitores Package

Exports all monitor classes and the monitor registry utilities.
Importing this package registers all built-in monitors.
"""

from .base import (
    MonitorBase,
    create_monitor,
    get_all_monitor_ids,
    get_monitor_class,
    register_monitor,
)
from .heavy import (
    CapacityPlanningMonitor,
    DemandProjectionMonitor,
    MultiSourceAnalysisMonitor,
)

# Import monitor modules to trigger @register_monitor decorators
from .lightweight import (
    DiskSpaceMonitor,
    LowStockMonitor,
    OverdueInvoiceMonitor,
    SystemHealthMonitor,
    TomorrowAppointmentMonitor,
)
from .medium import (
    CRMConversionMonitor,
    ErrorRateMonitor,
    ResponseTimeMonitor,
    SalesTrendMonitor,
)

__all__ = [
    "CRMConversionMonitor",
    "CapacityPlanningMonitor",
    # Heavy
    "DemandProjectionMonitor",
    "DiskSpaceMonitor",
    "ErrorRateMonitor",
    # Lightweight
    "LowStockMonitor",
    # Base
    "MonitorBase",
    "MultiSourceAnalysisMonitor",
    "OverdueInvoiceMonitor",
    "ResponseTimeMonitor",
    # Medium
    "SalesTrendMonitor",
    "SystemHealthMonitor",
    "TomorrowAppointmentMonitor",
    "create_monitor",
    "get_all_monitor_ids",
    "get_monitor_class",
    "register_monitor",
]
