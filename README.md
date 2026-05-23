# Zenic-Agents v3.0.0

Sistema de IA determinista con sistema proactivo local para detección y notificación automática de problemas.

## Arquitectura

Zenic-Agents opera en 3 capas:

```
Capa 1: LocalDataScanner     — Ve los datos locales del usuario (SQLite + filesystem)
Capa 2: SNA + Autopilot      — Analiza datos, detecta problemas, genera planes de acción
Capa 3: Channels + Safety    — Entrega alertas al usuario por su canal, con seguridad inbypasseable
```

### Flujo Principal

```
LocalDataScanner → SNA Monitors → AlertManager → ProactiveChannelBridge → Canal del usuario
                                       ↓
                                 AutopilotEngine → SafetyGate (DENY es FINAL) → Ejecución
```

## Componentes

### LocalDataScanner (`src/data/`)
El ojo del sistema sobre los datos locales del usuario. Escanea directamente SQLite y filesystem sin depender de que el usuario reporte problemas.

- `db_access.py` — Acceso directo a bases de datos SQLite del usuario
- `fs_scanner.py` — Escaneo de filesystem (disco, configs, backups, logs)
- `local_scanner.py` — Fachada que unifica BD + filesystem

### SNA - Sistema de Navegación Autónoma (`src/core/sna/`)
12 monitores que detectan problemas en datos locales del usuario:

| Monitor | Peso | Qué detecta |
|---------|------|-------------|
| LowStockMonitor | CRITICAL | Productos con stock bajo |
| OverdueInvoiceMonitor | CRITICAL | Facturas vencidas sin pagar |
| TomorrowAppointmentMonitor | WARNING | Citas programadas para mañana |
| UnpaidBalanceMonitor | CRITICAL | Saldos pendientes de cobro |
| StaleInventoryMonitor | WARNING | Inventario sin movimiento |
| DuplicateRecordsMonitor | WARNING | Registros duplicados en la BD |
| DataIntegrityMonitor | CRITICAL | Registros huérfanos |
| DiskSpaceMonitor | WARNING | Espacio en disco bajo |
| BackupStatusMonitor | WARNING | Backups desactualizados |
| ConfigDriftMonitor | INFO | Cambios en configuración |
| SalesTrendMonitor | INFO | Tendencias de ventas |
| ApiHealthMonitor | INFO | Estado de APIs externas |

### Channels (`src/core/channel/`)
Sistema de canales para comunicación con el usuario:

- `a52_voice.py` — Canal de voz (A52)
- `a53_text.py` — Canal de texto (A53) — WhatsApp, Telegram, Web
- `message_bridge.py` — Puente entre canales
- `_proactive.py` — ProactiveChannelBridge — Conecta SNA/Autopilot → Canales
- `_bootstrap.py` — Inicialización del sistema de canales

### Autopilot (`src/core/autopilot/`)
Motor de automatización con objetivos y planes de acción:

- Genera planes basados en datos reales del usuario
- Ejecuta pasos automáticamente según nivel de autonomía
- Templates: retención de clientes, optimización de inventario, recuperación de ingresos, recordatorios de citas

### Safety (`src/core/safety/`)
Sistema de seguridad con DENY inbypasseable:

- `safety_gate.py` — SafetyGate — La IA solo dice YES/NO, nunca genera contenido
- `policy.py` — Motor de políticas determinísticas
- **DENY es FINAL** — No se puede cambiar esta regla

## Instalación

```bash
git clone https://github.com/ZenicAgents/Zenic-Agents.git
cd Zenic-Agents
pip install -r requirements.txt
```

## Configuración

Copia `.env.example` a `.env` y configura tus variables:

```bash
cp .env.example .env
```

Variables principales:

| Variable | Default | Descripción |
|----------|---------|-------------|
| `DATABASE_PATH` | `/home/z/my-project/db/custom.db` | Ruta a la BD SQLite |
| `PROACTIVE_CHANNEL` | `telegram` | Canal de notificaciones (telegram/whatsapp) |
| `PROACTIVE_RECIPIENT` | | Destinatario de notificaciones |
| `SNA_ENABLED` | `true` | Habilitar sistema proactivo |
| `SNA_SCAN_INTERVAL` | `300` | Intervalo de escaneo en segundos |
| `AUTOPILOT_ENABLED` | `true` | Habilitar Autopilot |
| `AUTOPILOT_AUTONOMY` | `semi_autonomous` | Nivel de autonomía |

## Testing

```bash
python -m pytest tests/ -v
```

56 tests — Sin mocks, SQLite real, datos reales.

## Estructura del Proyecto

```
Zenic-Agents/
├── src/
│   ├── config/          # Configuración centralizada
│   ├── core/
│   │   ├── autopilot/   # Motor de automatización
│   │   ├── channel/     # Canales de comunicación
│   │   ├── safety/      # SafetyGate + Policies
│   │   └── sna/         # Sistema de Navegación Autónoma
│   │       └── monitors/ # 12 monitores de datos locales
│   ├── data/            # LocalDataScanner (BD + filesystem)
│   └── entrypoints/     # Puntos de entrada
├── tests/               # 56 tests sin mocks
├── mcp-config/          # Configuración de servidores MCP
├── .env.example         # Template de variables de entorno
├── .gitignore
├── requirements.txt
└── README.md
```

## Licencia

MIT License — Ver [LICENSE](LICENSE)
