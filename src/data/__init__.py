"""Capa de acceso a datos locales — el corazón del sistema proactivo.

El LocalDataScanner NO depende de canales. Escanea directamente:
- SQLite: tablas, registros, integridad, tendencias
- Filesystem: configs, logs, backups
- Métricas del sistema: disco, memoria, procesos

Sin esto, el sistema proactivo es "adivino" porque solo ve lo que llega por canales.
Con esto, el sistema VE los datos del usuario y detecta problemas ANTES de que se manifiesten.
"""

from src.data.local_scanner import LocalDataScanner
from src.data.db_access import DBAccess
from src.data.fs_scanner import FileSystemScanner

__all__ = ["LocalDataScanner", "DBAccess", "FileSystemScanner"]
