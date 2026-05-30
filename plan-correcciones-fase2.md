# 🎯 Plan de Correcciones — Zenic-Agents v3.0.0

> **Basado en**: Diagnóstico Fase 1 (`diagnostico-fase1.md`)
> **Skills aplicables**: `debugging-and-error-recovery`, `incremental-implementation`, `doubt-driven-development`, `git-workflow-and-versioning`, `security-and-hardening`, `test-driven-development`
> **Principio rector**: Un fix = un commit = un PR. Batch fixes solo cuando sean del mismo tipo y archivo.

---

## 📐 Arquitectura del Plan

```
FASE 2A: Build Blockers (P0)
├── Bloque 1: Arreglar 570 errores TypeScript del Gateway
├── Bloque 2: Arreglar regex roto en tests (9 archivos)
└── Bloque 3: Reemplazar 912 blind-except en Python

FASE 2B: Seguridad y Calidad (P1)
├── Bloque 4: Fix 69 try-except-pass (S110)
├── Bloque 5: Eliminar 914 noqa innecesarias (RUF100)
├── Bloque 6: Migrar rate limiting a Redis (C2)
└── Bloque 7: Logger estructurado en gateway

FASE 2C: Mantenimiento (P2)
├── Bloque 8: Limpiar código muerto (Vulture)
├── Bloque 9: Eliminar unused imports en zenic-pybridge
├── Bloque 10: Instalar cargo-audit + escanear
└── Bloque 11: Resolver 50+ TODO/FIXME

FASE 3: Verificación (P3)
├── Bloque 12: pathlib migration
├── Bloque 13: Ruff auto-fix masivo (COM812, D212, etc.)
└── Bloque 14: Poblar base de datos SQLite
```

---

## ⚙️ Decisiones Arquitectónicas

| Decisión | Opción | Por qué |
|----------|--------|---------|
| Orden de fixes | **Build blockers primero → Seguridad → Mantenimiento** | No tiene sentido pulir código que no compila |
| Rust primero | **Solo si los errores TS dependen de Rust** | El gateway TS no depende del compilado Rust |
| Batch de `noqa` | **Ruff --fix en un solo commit** | Son 914 supresiones, pero son mecánicas y reversibles |
| Branch strategy | **Una rama por bloque** | Cada bloque es atómico y revisable |

---

## BLOQUE 1: 🔴 Arreglar 570 errores TypeScript (Gateway)

**Descripción**: El gateway Next.js tiene 570 errores de compilación TypeScript que impiden el build. La mayoría están en `src/lib/policy-engine/` (TS2304: Cannot find name), `src/lib/mcp/` y `src/app/api/` (missing exports, type mismatches).

**Dependencias**: Ninguna. Gateway es independiente de Python/Rust.

### Tarea 1.1: Policy Engine — Definir tipos faltantes

**Archivos**: `gateway/src/lib/policy-engine/`

**Problema**: 12 errores TS2304 — `PolicyEffectV2`, `ConflictSeverity`, `PolicyDocument` no existen.

**Acción**:
- Revisar `gateway/src/lib/policy-engine/` para entender qué tipos se esperan
- Definir los tipos faltantes en un archivo `types.ts` dentro del módulo
- Verificar que las importaciones sean correctas

**Criterios de aceptación**:
- [ ] `npx tsc --noEmit` reporta 0 errores en `src/lib/policy-engine/`
- [ ] Tipos definidos siguen el patrón de `src/lib/security/config/index.ts`

**Verificación**: `npx tsc --noEmit | grep "src/lib/policy-engine" | wc -l` = 0

---

### Tarea 1.2: MCP Gateway — Arreglar imports y exports

**Archivos**: `gateway/src/lib/mcp/`

**Problema**: Missing exports en `./types`, imports que no resuelven.

**Acción**:
- Leer `gateway/src/lib/mcp-gateway/` para entender la estructura
- Corregir exports faltantes o agregar re-exports con `type` keyword

**Criterios de aceptación**:
- [ ] `npx tsc --noEmit` reporta 0 errores en `src/lib/mcp/`
- [ ] Todos los tipos usan `type` keyword donde corresponde (TS1448)

**Verificación**: `npx tsc --noEmit | grep "src/lib/mcp" | wc -l` = 0

---

### Tarea 1.3: API Routes — Arreglar missing services

**Archivos**: `gateway/src/app/api/`

**Problema**: `getAuthService`, `getRateLimiter`, `getApprovalEngine` no existen como exports de sus módulos.

**Acción**:
- Identificar los archivos que exportan estos servicios
- Agregar exports faltantes o implementar stubs funcionales
- Usar `doubt-driven-development` para cada fix: "¿Estoy seguro de que este cambio no rompe otra cosa?"

**Criterios de aceptación**:
- [ ] `npx tsc --noEmit` reporta 0 errores en `src/app/api/`
- [ ] Todos los servicios importados existen como exports

**Verificación**: `npx tsc --noEmit | grep "src/app/api" | wc -l` = 0

---

### Tarea 1.4: Fix restante de errores dispersos

**Problema**: Errores varios en `src/lib/` (type mismatches, PrismaClient, js-yaml, WASM paths).

**Acción**:
- Fix TS1448 (type-only re-export con `type`)
- Fix TS2339/TS2551 (property not on type)
- Fix TS2352 (conversion overlap)
- Fix TS2571 (object is 'unknown')
- Fix TS2739 (missing property)
- Fix TS2367 (comparison type mismatch)
- Fix TS7022 (implicit 'any')
- Fix TS2307 (WASM engine paths)

**Criterios de aceptación**:
- [ ] `npx tsc --noEmit` = 0 errores totales
- [ ] `npm run build` en gateway pasa sin errores

**Verificación**: `npx tsc --noEmit 2>&1 | grep "error TS" | wc -l` = 0

---

### Checkpoint: Gateway compila
- [ ] `npx tsc --noEmit` = 0 errores
- [ ] `npm run build` exitoso
- [ ] Commit con mensaje: `fix: resolve 570 TypeScript compilation errors in gateway`

---

## BLOQUE 2: 🔴 Arreglar regex roto en tests (9 archivos)

**Descripción**: 9 archivos de test fallan al recolectar por un `re.PatternError: missing ), unterminated subpattern`.

**Dependencias**: Ninguna.

**Acción**:
1. Identificar qué patrón regex está roto en los archivos afectados
2. Corregir el patrón regex mal formado
3. Verificar que `python3 -m pytest tests/ --collect-only -q` pase sin errores

**Archivos afectados**:
- `tests/test_a52_voice_channel.py`
- `tests/test_a53_text_channel.py`
- `tests/test_channel_system.py`
- `tests/test_ear_service.py`
- `tests/test_format_adapter.py`
- `tests/test_sna_monitors.py`
- `tests/test_transport_types.py`
- `tests/test_voice_pipeline.py`
- `tests/test_voice_pipeline_types.py`

**Criterios de aceptación**:
- [ ] `python3 -m pytest tests/ --collect-only -q` muestra 0 errores
- [ ] Los 318 tests se recolectan correctamente
- [ ] Commit atómico con `fix: correct malformed regex in test files`

**Verificación**: `python3 -m pytest tests/ --collect-only -q 2>&1 | grep "error"` = vacío

---

## BLOQUE 3: 🔴 Reemplazar 912 blind-except en Python

**Descripción**: 912 `except:` sin especificar tipo de excepción. Esto traga errores como KeyboardInterrupt y SystemExit.

**Dependencias**: Ninguna.

**Acción**:
1. `ruff check --select BLE001 --fix src/` para auto-fix donde Ruff pueda determinar el tipo
2. Para los casos donde Ruff no pueda auto-fix, revisar manualmente y cambiar a excepciones específicas
3. Usar `doubt-driven-development`: "Cambiar un except ciego puede cambiar el comportamiento del programa"

**Skill**: `doubt-driven-development` — cada fix manual requiere revisión adversarial

**Criterios de aceptación**:
- [ ] `ruff check --select BLE001 src/` = 0 errores
- [ ] Los tests existentes siguen pasando (después de fixear BLOQUE 2)
- [ ] Commits atómicos: `fix: replace blind except with specific exceptions in <module>`

**Verificación**: `ruff check --select BLE001 --statistics src/` = 0

---

## BLOQUE 4: 🟠 Fix 69 try-except-pass (S110)

**Descripción**: 69 bloques `try-except-pass` que tragan excepciones silenciosamente. Riesgo de seguridad porque ocultan errores.

**Dependencias**: Ninguna (independiente de otros bloques).

**Skill**: `security-and-hardening`

**Acción**:
1. `ruff check --select S110 src/` para listar todas las ocurrencias
2. Evaluar cada caso:
   - Si realmente debe tragar la excepción → agregar comentario explicando por qué
   - Si no → agregar logging o re-raises
3. Batch de fixes por módulo, un commit por módulo

**Criterios de aceptación**:
- [ ] `ruff check --select S110 src/` = 0 o casos documentados
- [ ] Todos los `pass` tienen justificación explícita

**Verificación**: `ruff check --select S110 --statistics src/` < umbral aceptable

---

## BLOQUE 5: 🟠 Eliminar 914 noqa innecesarias (RUF100)

**Descripción**: 914 supresiones `# noqa` que ya no son necesarias. Código muerto de lint.

**Dependencias**: Ninguna.

**Acción**: `ruff check --select RUF100 --fix src/`

**Skill**: `debugging-and-error-recovery` si algún fix rompe algo

**Criterios de aceptación**:
- [ ] `ruff check --select RUF100 --statistics src/` = 0
- [ ] Tests siguen pasando
- [ ] Commit: `chore: remove 914 unnecessary noqa suppressions (RUF100)`

**Verificación**: `ruff check --select RUF100 --statistics src/` = 0

---

## BLOQUE 6: 🟠 Migrar rate limiting a Redis (C2)

**Descripción**: El rate limiting actual usa un `Map<string, RateLimitEntry>` en memoria que es volátil entre reinicios e instancias. Pendiente desde la auditoría de seguridad.

**Dependencias**: BLOQUE 1 (Gateway debe compilar para verificar).

**Skill**: `source-driven-development` (verificar API de Redis antes de implementar)

**Acción**:
1. Revisar la implementación actual en `gateway/src/middleware.ts`
2. Verificar que `REDIS_URL` ya está configurado en `.env.example`
3. Migrar el store de rate limiting a Redis usando la conexión existente
4. Mantener el Map en memoria como fallback para casos sin Redis

**Criterios de aceptación**:
- [ ] Rate limiting funciona con Redis cuando `REDIS_URL` está configurado
- [ ] Rate limiting funciona con Map en memoria como fallback
- [ ] `npx tsc --noEmit` = 0 errores después del cambio
- [ ] Commit: `fix: migrate rate limiting from in-memory Map to Redis`

**Verificación**: Prueba de rate limiting con Redis y sin Redis

---

## BLOQUE 7: 🟠 Logger estructurado en gateway

**Descripción**: 20+ instancias de `console.error` y `console.log` en API routes sin un logger estructurado.

**Dependencias**: BLOQUE 1 (Gateway debe compilar).

**Acción**:
1. Revisar `gateway/src/lib/security/log-redact` (ya existe un logger redactado)
2. Reemplazar `console.*` calls en `src/app/api/` con el logger estructurado
3. Agregar contexto (ruta, método, request ID) a cada log

**Criterios de aceptación**:
- [ ] 0 `console.log` en `src/app/api/` (excepto en error boundaries)
- [ ] Todos los logs usan el logger redactado
- [ ] `npx tsc --noEmit` = 0 errores

---

## BLOQUE 8: 🟡 Limpiar código muerto (Vulture)

**Descripción**: Vulture reportó múltiples métodos sin usar en business agents: `crm_pipeline.py`, `inventory_manager.py`, `invoice_processor.py`, y variables `runner` en compat layer.

**Dependencias**: BLOQUE 3 (blind-except) para evitar conflictos.

**Skill**: `doubt-driven-development` — código "muerto" puede ser usado en runtime vía import dinámico

**Acción**:
1. Revisar cada hallazgo de Vulture manualmente
2. Verificar que el código no sea usado en runtime (imports, reflexión, etc.)
3. Eliminar o comentar el código muerto
4. Un archivo por commit

**Criterios de aceptación**:
- [ ] Vulture reporta significativamente menos código muerto
- [ ] Tests siguen pasando

---

## BLOQUE 9: 🟡 Eliminar unused imports en zenic-pybridge (Rust)

**Descripción**: Warnings de unused imports en `zenic-pybridge/src/catalog/mod.rs`, `completer/mod.rs`, `extractor/mod.rs`, `forensic/types.rs`, `ingest/mod.rs`.

**Dependencias**: Ninguna.

**Acción**:
1. Eliminar los imports no usados
2. Un archivo por commit (o batch pequeño)

**Criterios de aceptación**:
- [ ] `cargo check` en zenic-pybridge = 0 warnings
- [ ] Tests Rust pasan (si existen)

**Verificación**: `cd user/zenic-v2 && cargo check 2>&1 | grep "warning: unused import" | wc -l` = 0

---

## BLOQUE 10: 🟡 Instalar cargo-audit + escanear

**Descripción**: No se pudo escanear dependencias Rust por falta de `cargo-audit`.

**Dependencias**: Ninguna.

**Acción**:
1. `cargo install cargo-audit`
2. `cargo audit` en `zenic-v2/`
3. Documentar hallazgos

**Criterios de aceptación**:
- [ ] `cargo audit` ejecuta sin errores
- [ ] Si hay vulnerabilidades, crear issues para cada una

---

## BLOQUE 11: 🟡 Resolver 50+ TODO/FIXME

**Descripción**: 50+ marcadores TODO/FIXME/HACK/XXX en la base de código.

**Dependencias**: Bloques 1-10 (para evitar conflictos).

**Acción**:
1. Clasificar los TODOs:
   - Fáciles (imports por verificar) → resolver inmediato
   - Planificados (Phase3) → mover a backlog del proyecto
   - Complejos → crear issue en GitHub
2. Un commit por tipo

**Criterios de aceptación**:
- [ ] Todos los TODOs están resueltos o trackeados como issues
- [ ] `grep -rn 'TODO\\|FIXME' src/` = 0 sin resolver

---

## FASE 3: VERIFICACIÓN

### BLOQUE 12: 🔵 pathlib migration (PTH118, PTH123)

**Acción**: `ruff check --select PTH --fix src/`

> ⚠️ **PRECAUCIÓN**: Ruff auto-fix a pathlib puede cambiar semántica si hay casos con `os.path.join` que dependen de comportamiento específico. Usar `doubt-driven-development` para revisar los diffs.

### BLOQUE 13: 🔵 Ruff auto-fix masivo

**Acción**: Ejecutar `ruff check --fix src/` para reglas de estilo automáticas (COM812, D212, etc.)

### BLOQUE 14: 🔵 Poblar base de datos SQLite

**Acción**: Crear schema y seed data para `mydatabase.db`

---

## 📋 CHECKPOINTS DE VERIFICACIÓN

### Checkpoint 1: Build Blocker (después de Bloques 1-3)
- [ ] `npx tsc --noEmit` = 0 errores en gateway
- [ ] `npm run build` en gateway exitoso
- [ ] `python3 -m pytest tests/ --collect-only -q` = 0 errores
- [ ] `ruff check --select BLE001 --statistics src/` = 0

### Checkpoint 2: Seguridad (después de Bloques 4-7)
- [ ] `ruff check --select S110 --statistics src/` < umbral
- [ ] `ruff check --select RUF100 --statistics src/` = 0
- [ ] Rate limiting con Redis funcional
- [ ] Logger estructurado implementado

### Checkpoint 3: Mantenimiento (después de Bloques 8-11)
- [ ] Vulture reporta < 50% de código muerto original
- [ ] `cargo check` en zenic-v2 = 0 warnings
- [ ] `cargo audit` sin vulnerabilidades críticas
- [ ] 0 TODO/FIXME sin resolver

### Checkpoint 4: Polish (después de Bloques 12-14)
- [ ] `ruff check --select PTH --statistics src/` = 0
- [ ] `ruff check src/` = 0 errores de estilo
- [ ] Base de datos SQLite poblada con schema

---

## 🚨 RIESGOS Y MITIGACIONES

| Riesgo | Impacto | Mitigación |
|--------|---------|------------|
| Fix TS rompe runtime de API | Alto | Tests + `doubt-driven-development` en cada fix |
| Blind-except fix cambia comportamiento | Alto | Revisión adversarial (doubt-driven) antes de commit |
| `ruff --fix` en RUF100 elimina noqa necesarias | Medio | Hacer diff review antes de commit |
| Redis no disponible en entorno actual | Medio | Mantener fallback Map en memoria |
| Código "muerto" es usado vía import dinámico | Alto | Revisión manual de cada hallazgo de Vulture |

---

## 📊 ESTIMACIÓN DE ESFUERZO

| Bloque | Archivos | Esfuerzo | Tipo |
|--------|:--------:|:--------:|------|
| 1. TS errors | 50+ | 🔴 Alto | Manual + tooling |
| 2. Regex tests | 9 | 🟢 Bajo | Manual |
| 3. Blind-except | 300+ | 🟡 Medio | Auto-fix + manual |
| 4. try-except-pass | 69 | 🟢 Bajo | Manual + revisión |
| 5. noqa innecesarias | 500+ | 🟢 Bajo | Auto-fix |
| 6. Redis rate limit | 3-5 | 🟡 Medio | Manual |
| 7. Logger | 20+ | 🟢 Bajo | Manual |
| 8. Dead code | 20-50 | 🟡 Medio | Manual |
| 9. Rust imports | 5 | 🟢 Bajo | Manual |
| 10. cargo-audit | 1 | 🟢 Bajo | Tooling |
| 11. TODO/FIXME | 50+ | 🟡 Medio | Manual |
| 12-14. Polish | 100+ | 🟡 Medio | Auto-fix |

---

## 🔄 LOOP DIARIO (de la Fase 2 en adelante)

```bash
# 1. Estado actual
ruff check --select BLE001,S110,RUF100 --statistics src/
npx tsc --noEmit        # en gateway/

# 2. Avanzar un bloque
# 3. Testear
# 4. Commit atómico
# 5. Repetir
```

---

> **Siguiente**: Confirmar orden de ejecución con el usuario y empezar BLOQUE 1
