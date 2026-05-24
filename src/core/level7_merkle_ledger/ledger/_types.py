"""
ZENIC-AGENTS - Merkle Ledger v17 (Tenant-Aware + Sandbox Isolated)

Ledger con arbol Merkle real para integridad criptografica.
Soporta snapshots, commits con verificacion, y rollbacks atomicos.

v17 - TENANT-AWARE:
- Todas las operaciones filtran por tenant_id para aislar datos entre tenants
- Columna tenant_id con default '__anonymous__' para compatibilidad retroactiva
- purge_tenant_ledger() para GDPR / deprovisioning
- set_tenant_id() para cambio dinamico de contexto de tenant
- Thread-local TenantContext para obtener tenant_id automaticamente

v16 - AISLAMIENTO:
- Los commits se escriben en el workspace AISLADO del sandbox
- NUNCA escribe directamente en el filesystem del proyecto real
- Los snapshots y rollbacks operan dentro del workspace aislado
- Las DBs del ledger son INDEPENDIENTES cuando opera en sandbox

FIX (Phase 2): Added retry with exponential backoff for DB operations.
SQLite can fail transiently (database locked, busy timeout) especially
under concurrent write access.

Sin dependencias externas. Compatible con Android.
"""

import logging


logger = logging.getLogger(__name__)

# Number of hex characters to use for hashed backup filenames
_BACKUP_HASH_LENGTH = 16
__all__ = ["_BACKUP_HASH_LENGTH", "logger"]
