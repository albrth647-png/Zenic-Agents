# 🔬 FASE 1: DIAGNÓSTICO — Zenic-Agents v3.0.0

> **Fecha**: 30 de Mayo 2026
> **Alcance**: Proyecto completo (Python + Rust + TypeScript Gateway + Mobile)
> **Scanners**: Ruff 0.15.14, Vulture, TSC, Cargo, SQLite3

---

## 📊 RESUMEN EJECUTIVO

| Métrica | Valor |
|---------|-------|
| **Python (src/)** | 1,162 archivos · ~204,455 LOC |
| **TypeScript (gateway/)** | 621 archivos · ~12,675 LOC |
| **Rust (zenic-v2/)** | 310 archivos · ~58,980 LOC |
| **Tests Python** | 318 tests encontrados · **9 errores de colección** |
| **Total estimado** | ~276,000 LOC |

### Estado por componente

| Componente | Estado | 🔴 Críticos | 🟠 Errores | 🟡 Warnings |
|------------|--------|:-----------:|:----------:|:-----------:|
| **Python src/** | ⚠️ Deficiencias | 1,000+ blind-except | 3,500+ lint issues | 882 noqa innecesarias |
| **Gateway (Next.js)** | ❌ No compila | 570 errors TS | — | — |
| **Rust (zenic-v2)** | ✅ Compila limpio | 0 | 0 | ~30 unused imports |
| **Tests** | ⚠️ 9 fallan | 1 regex roto | 9 collection errors | 1,081 lint issues |
| **Base de datos** | ⚠️ Vacía | 0 | 1 (empty db) | — |
| **Seguridad** | ⚠️ Auditoría previa OK | 0 nuevos (4 corregidos) | — | 88 S-findings |

---

## 1️⃣ Python — `user/src/` (204,455 LOC)

### Ruff Lint — Top violaciones

| Regla | Descripción | Conteo | Severidad |
|-------|-------------|:------:|:---------:|
| **BLE001** | Blind `except:` (except genérico) | **900** | 🔴 Crítico |
| D212 | Multi-line docstring first line | 1,642 | 🟢 Estilo |
| EXE002 | Missing shebang on executable | 1,133 | 🟢 Estilo |
| COM812 | Missing trailing comma | 976 | 🟢 Estilo |
| D413 | Missing blank line after last section | 946 | 🟢 Estilo |
| TID252 | Relative imports | 854 | 🟡 Convención |
| PLC0415 | Import outside top-level | 559 | 🟡 Convención |
| **RUF100** | Unnecessary `# noqa` | **882** | 🟡 Mantenibilidad |
| PTH118 | `os.path.join` (prefer pathlib) | 87 | 🟢 Estilo |
| PTH123 | `open()` builtin (prefer pathlib) | 65 | 🟢 Estilo |

### Seguridad (Ruff S-select)

| Regla | Conteo | Descripción |
|-------|:------:|-------------|
| S110 | **65** | `try-except-pass` (tragar excepciones) |
| S101 | **20** | `assert` en código no-test |
| S608 | **2** | SQL expression hardcodeada |
| S307 | **1** | `eval()` sospechoso |

### Código Muerto (Vulture)

- Múltiples métodos y funciones sin usar en:
  - `core/agents/business/` — `crm_pipeline.py`, `inventory_manager.py`, `invoice_processor.py`
  - `core/agents/compat/` — varias variables `runner` (100% confianza)
  - Atributos no usados como `_serializer`, `_code_generator`
  - Constantes globales como `VALID_ACTIONS`, `SUPPORTED_METRICS`, `MAX_ROUNDS`

### Syntax Errors
- ✅ **0 errores de sintaxis** — todos los archivos .py compilan AST correctamente

### Imports Problemáticos
- Uso extensivo de `aiohttp` en canales (email, push, Slack, Teams, Twilio, WhatsApp)
- `subprocess` en `defense/binary_hardening.py` y `defense/encryption.py`
- `shutil` en `executors/coordinated_rollback/_compensation.py`
- Múltiples patrones de lazy imports para evitar dependencias circulares

---

## 2️⃣ TypeScript Gateway — `user/gateway/` (12,675 LOC)

### Compilación ❌ — **570 errores TS**

| Error | Conteo | Descripción |
|-------|:------:|-------------|
| TS2304 | 12 | Cannot find name (`PolicyEffectV2`, `ConflictSeverity`, etc.) |
| TS1448 | 3 | Type-only re-export sin `type` keyword |
| TS2307 | 2 | Cannot find module (WASM engine paths) |
| TS2551 | 2 | Property does not exist (PrismaClient, js-yaml) |
| TS2724 | 2 | Exported member not found |
| TS2339 | 1 | Property not on type |
| TS2352 | 1 | Conversion overlap |
| TS2571 | 1 | Object is of type 'unknown' |
| TS2739 | 1 | Missing property in type |
| TS2305 | 1 | Module has no exported member |
| TS2440 | 1 | Import conflict |
| TS2367 | 1 | Unintentional comparison |
| TS7022 | 1 | Implicit 'any' type |

### Dependencias
- **73 dependencias** en `package.json`
- `npm audit` no pudo ejecutarse (timeout)
- Prisma schema presente con estructura de schema parts

### Consola en producción
- Múltiples `console.error` en API routes y error boundaries
- Sin logger estructurado consistente

---

## 3️⃣ Rust — `user/zenic-v2/` (58,980 LOC)

### Compilación ✅ — **0 errores**

- `cargo check` pasa sin errores fatales
- Warnings de **unused imports** en `zenic-pybridge`:
  - `src/catalog/mod.rs`: `ALL_NICHES`
  - `src/completer/mod.rs`: Múltiples imports de sesión
  - `src/extractor/mod.rs`: Múltiples imports de extracción
  - `src/forensic/types.rs`: `PyDict`, `PyList`
  - `src/ingest/mod.rs`: `extract_csv`, `extract_json`, `truncate_text`
- `cargo audit` no instalado — no se pudo escanear vulnerabilidades

---

## 4️⃣ Tests — `user/tests/` (18 archivos)

### Estado
- **318 tests detectados**, pero **9 errores de colección**
- ❌ **Patrón regex roto**: `re.PatternError: missing ), unterminated subpattern`
- 9 archivos fallan al recolectar:
  - `test_a52_voice_channel.py`, `test_a53_text_channel.py`
  - `test_channel_system.py`, `test_ear_service.py`
  - `test_format_adapter.py`, `test_sna_monitors.py`
  - `test_transport_types.py`, `test_voice_pipeline.py`
  - `test_voice_pipeline_types.py`

### Ruff Lint (tests/)
| Regla | Conteo |
|-------|:------:|
| PT009 (pytest-unittest-assertion) | 226 |
| D102 (undocumented public method) | 208 |
| SLF001 (private member access) | 123 |
| PLR2004 (magic value comparison) | 101 |
| PLC0415 (import outside top-level) | 96 |

---

## 5️⃣ Base de Datos

| DB | Estado |
|----|--------|
| `mydatabase.db` | ⚠️ **0 bytes — vacía** (sin tablas) |
| SQLite3 | ✅ Disponible (v3.46.1) |

---

## 6️⃣ Seguridad

### Auditoría Previa (`SECURITY_AUDIT.md`)
Ya existe una auditoría de seguridad con **16 hallazgos**:

| Severidad | Cantidad | Estado |
|-----------|:--------:|--------|
| 🔴 **Crítico** | 4 | ✅ 4 corregidos |
| 🟡 **Alto** | 4 | ✅ 4 corregidos |
| 🟢 **Medio** | 5 | ✅ 5 corregidos |
| 🔵 **Bajo** | 3 | ✅ 3 corregidos |

### Pendiente de la auditoría previa
- **C2**: Rate limiting en memoria (volátil) — pendiente migrar a Redis

### Hallazgos de seguridad nuevos (Ruff S-select)
- 65 `try-except-pass` que tragan excepciones
- 20 `assert` en código no-test
- 2 SQL expressions hardcodeadas
- 1 `eval()` sospechoso

---

## 7️⃣ Calidad de Código

| Métrica | Valor |
|---------|:-----:|
| Supresiones `# noqa` / `type: ignore` | **1,894** |
| `# noqa` innecesarias (RUF100) | **882** |
| TODO/FIXME/HACK/XXX | **50+** en todo el codebase |
| Circular import workarounds | Varios (lazy imports) |
| `console.log/error` en producción | **20+** instancias |

---

## 🎯 RECOMENDACIONES PRIORIZADAS

### Prioridad 0 — Inmediato
1. **🔴 Arreglar TypeErrorScript** — 570 errores impiden el build del gateway
2. **🔴 Arreglar regex roto en tests** — 9 archivos no pueden recolectarse
3. **🔴 Reemplazar 900 `except:` con excepciones específicas** — riesgo de tragar errores

### Prioridad 1 — Alto
4. **🟠 Migrar rate limiting a Redis** (C2 pendiente de SECURITY_AUDIT.md)
5. **🟠 Revisar 65 `try-except-pass`** — riesgo de seguridad
6. **🟠 Eliminar 882 `# noqa` innecesarias**
7. **🟠 Implementar logger estructurado en gateway** (reemplazar console.error)

### Prioridad 2 — Medio
8. **🟡 Limpiar código muerto** (Vulture findings en business agents)
9. **🟡 Eliminar unused imports en zenic-pybridge** (Rust)
10. **🟡 Instalar `cargo audit`** y escanear dependencias Rust
11. **🟡 Resolver 50+ TODO/FIXME** en el código

### Prioridad 3 — Bajo
12. **🔵 Migrar `os.path.*` a `pathlib`** (200+ instancias)
13. **🔵 Mejorar docstrings** (1,642 D212, 946 D413)
14. **🔵 Población de base de datos SQLite**

---

> *Reporte generado con Ruff 0.15.14, Vulture, TSC 5.x, Cargo 1.95.0*
> *Próximo paso: **FASE 2 — ESTABILIZACIÓN***
