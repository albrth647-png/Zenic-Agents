# PLAN VORTEX — Zenic-Agents: Los 3 Niveles
## Ejecución paso a paso completa

---

# ═══════════════════════════════════════════════
# NIVEL 1: ESTABILIZAR
# ═══════════════════════════════════════════════

## Objetivo: Sistema funcional y observable
## Duración estimada: 1-2 semanas
## Criterio VORTEX: Sin sistema observable, no hay Espejo Reflexivo

---

## PASO 1.1: Arreglar 4 Imports Rotos

### 1.1.A — Import roto: TECE Modules (agents/verdict/)

**Problema**: `user/src/core/agents/verdict/__init__.py` importa 4 módulos que NO EXISTEN:
- `interaction_matrix.py` → InteractionMatrix
- `ising_consensus_resolver.py` → IsingConsensusResolver
- `ising_hamiltonian.py` → IsingHamiltonian
- `tece_types.py` → SpinState, SpinValue, AnnealingConfig, etc.

**Impacto**: Todo el paquete `agents/verdict/` falla al importar. La arquitectura v18 (VerdictEngineV18) es INALCANZABLE.

**Razonamiento VORTEX**: El Manifold Semántico tiene una discontinuidad — existe una región del sistema que se referencia a sí misma pero no puede alcanzarse. Es como un mapa con una isla que no tiene coordenadas navegables. La Observación Interna no puede verificar esta región porque no puede cargarla.

**Acción**:
1. Verificar si estos módulos existen en OTRO lugar del repo (pueden haberse movido en un refactor)
2. Si NO existen: crear los 4 archivos con stubs mínimos — solo las clases y tipos referenciados, con raise NotImplementedError
3. Si SÍ existen en otro lugar: corregir los imports para apuntar al lugar correcto
4. Verificar que `from src.core.agents.verdict import VerdictEngineV18` funciona sin errores

**Verificación**: Ejecutar `python -c "from src.core.agents.verdict import VerdictEngineV18"` — debe pasar sin ModuleNotFoundError

---

### 1.1.B — Import roto: CompatibilityBridge (channel/)

**Problema**: 3 archivos importan `from src.core.channel._compat_bridge import CompatibilityBridge`:
- `user/src/core/channel/__init__.py` (línea 25)
- `user/src/core/channel/_proactive.py` (línea 30)
- `user/src/core/channel/_bootstrap.py` (línea 26)

El archivo `_compat_bridge.py` NO EXISTE.

**Impacto**: Todo el paquete `channel/` (deprecado) falla al importar. Tests que usan ProactiveChannelBridge también fallan.

**Razonamiento VORTEX**: La frontera entre el sistema viejo (channel/) y el nuevo (channels/) está rota. La Transformación Fronteriza requiere un puente funcional — sin él, la migración es imposible.

**Acción**:
1. Crear `user/src/core/channel/_compat_bridge.py` con una clase CompatibilityBridge mínima
2. Implementar solo los métodos que son llamados desde `_bootstrap.py` (línea 157) y `_proactive.py`
3. Los métodos deben delegar al nuevo sistema `channels/` o lanzar DeprecationWarning si la funcionalidad no existe
4. Agregar `warnings.warn("CompatibilityBridge is deprecated, use channels/", DeprecationWarning)` en `__init__`

**Verificación**: Ejecutar `python -c "from src.core.channel import CompatibilityBridge"` — debe pasar

---

### 1.1.C — Import roto: TelegramChannelProvider (channels/)

**Problema**: `user/src/core/channels/__init__.py` (línea 93) importa `from .providers.telegram import TelegramChannelProvider` y el directorio `providers/telegram/` NO EXISTE.

**Impacto**: Todo el paquete `channels/` falla al importar porque `__init__.py` importa eagermente de todos los providers.

**Razonamiento VORTEX**: La Membrana del Vacío está rota — el sistema referencia un proveedor de entrada que no existe, creando un agujero en la frontera. La importación eager es como una membrana que falla al primer input desconocido.

**Acción**:
1. OPCIÓN A (Recomendada): Cambiar la importación de Telegram de eager a lazy en `channels/__init__.py`:
   - Reemplazar `from .providers.telegram import TelegramChannelProvider` con un bloque try/except que silenciosamente omita providers no disponibles
   - Esto previene que un provider faltante rompa todo el paquete
2. OPCIÓN B: Crear `providers/telegram/` con un stub mínimo que implemente la interfaz de provider
3. Verificar que todos los demás providers (whatsapp, email, push, slack, teams, twilio_sms) siguen funcionando

**Verificación**: Ejecutar `python -c "from src.core.channels import ChannelManager"` (o la clase principal) — debe pasar

---

### 1.1.D — Import roto: degraded_mode/manager/types

**Problema**: `user/src/core/degraded_mode/manager/_mixin_core.py` (línea 12) importa:
```python
from .types import DegradationLevel, DegradationReason, DegradationState
```

Pero el archivo es `_types.py` (con underscore), y los símbolos realmente están en `degraded_mode/types.py` (padre).

**Impacto**: DegradedModeManager no puede instanciarse. Todo el sistema de degradación de modo está roto. phase6_init falla.

**Razonamiento VORTEX**: El sistema no puede observar su propio modo de operación — si no puede determinar si está degradado, no puede probar su determinismo en estados degradados. El Espejo Reflexivo es ciego a su propio estado.

**Acción**:
1. Cambiar el import en `_mixin_core.py` línea 12 de:
   ```python
   from .types import DegradationLevel, DegradationReason, DegradationState
   ```
   a:
   ```python
   from ..types import DegradationLevel, DegradationReason, DegradationState
   ```
   (doble punto para subir al paquete padre donde `types.py` realmente existe)

2. Verificar que `from src.core.degraded_mode import DegradedModeManager` funciona

**Verificación**: Ejecutar `python -c "from src.core.degraded_mode import DegradedModeManager"` — debe pasar

---

## PASO 1.2: Eliminar VerdictEngine Muerto

**Problema**: `user/src/core/verdict_parts/verdict_engine/_core_mixin.py` define una clase VerdictEngine que NUNCA es importada. Es dead code.

**Análisis detallado**:
- `_core_mixin.py` tiene MEJOR arquitectura (usa VerdictStatsMixin, evita duplicación)
- `__init__.py` tiene PEOR arquitectura (inlinea 5 métodos que deberían venir del mixin)
- Pero `__init__.py` es el archivo que Python carga cuando haces `from .verdict_engine import VerdictEngine`
- NINGÚN archivo en todo el repo importa de `_core_mixin.py`

**Razonamiento VORTEX**: La Verdad Binaria es un pilar absolutamente determinista. Un pilar no puede estar en dos lugares. Dos implementaciones de VerdictEngine son dos entidades reclamando ser la misma verdad. La clase muerta es una contradicción ontológica — existe pero no vive. Debe eliminarse o reactivarse, pero no puede quedar en limbo.

**Acción — DOS OPCIONES**:

OPCIÓN A (Conservadora — Recomendada): Eliminar el dead code
1. Borrar `user/src/core/verdict_parts/verdict_engine/_core_mixin.py`
2. No se necesita cambiar nada más — ningún archivo lo importa
3. Los 5 métodos inlineados en `__init__.py` (stats, health, update_engines, reset_circuit_breaker, get_audit_trail, get_failure_pattern) se quedan como están — funcionan correctamente

OPCIÓN B (Refactorización — Más trabajo, mejor resultado): Reactivar el mixin
1. Mover los 5 métodos inlineados de `__init__.py` a `VerdictStatsMixin`
2. Hacer que `__init__.py` herede de VerdictStatsMixin (como `_core_mixin.py` ya hacía)
3. Borrar los métodos duplicados de `__init__.py`
4. Esto elimina ~80 líneas de código duplicado
5. Verificar que todos los tests existentes pasan

**Verificación**: Ejecutar los tests del verdict engine — todos deben pasar. Verificar que `from src.core.verdict_parts.verdict_engine import VerdictEngine` funciona igual.

---

## PASO 1.3: Arreglar Mutation Bug en MemoryManager

**Problema**: En `user/src/core/conversational/memory/manager.py`, el método `retrieve()` (línea 282) muta los entries in-place:
```python
entry.relevance_score += level_boost.get(entry.memory_type, 0.0)
```

Esto significa que cada llamada a `retrieve()` incrementa permanentemente el `relevance_score` de los entries almacenados. Después de 10 llamadas, un entry WORKING tiene +1.0 de boost artificial.

**Razonamiento VORTEX**: La Memoria Cristalizada es INMUTABLE por naturaleza. Un cristal que se modifica cada vez que lo miras no es un cristal — es un líquido. El boost de relevancia no es una propiedad del cristal — es una propiedad de la RELACIÓN entre el cristal y el observador. Aplicar el boost al cristal confunde la observación con la naturaleza.

**Acción**:
1. En `manager.py`, método `retrieve()`, línea ~274-282:
   - ANTES de modificar entries, crear COPIAS de los objetos
   - Aplicar el boost a las COPIAS, no a los originales
   - Devolver las copias con boost

   Cambiar de:
   ```python
   entries = list(all_entries.values())
   for entry in entries:
       level_boost = {...}
       entry.relevance_score += level_boost.get(entry.memory_type, 0.0)
   ```
   
   A:
   ```python
   import copy
   entries = [copy.copy(e) for e in all_entries.values()]
   for entry in entries:
       level_boost = {...}
       entry.relevance_score += level_boost.get(entry.memory_type, 0.0)
   ```

2. Verificar que múltiples llamadas a `retrieve()` con los mismos entries producen el mismo resultado (no boost acumulativo)

**Verificación**:
```python
manager.store("test", "test content", ...)
result1 = manager.retrieve("test", ...)
score1 = result1.entries[0].relevance_score
result2 = manager.retrieve("test", ...)
score2 = result2.entries[0].relevance_score
assert score1 == score2, f"Mutation bug: {score1} != {score2}"
```

---

## PASO 1.4: Unificar Circuit Breakers

**Problema**: Hay 5 implementaciones de circuit breaker con defaults inconsistentes y enums de estado incompatibles:

| Implementación | failure_threshold | recovery_timeout | Estados |
|---|---|---|---|
| AgentCircuitBreaker | 3 | 60.0 | UPPERCASE |
| VerdictCircuitBreaker | 3 | 60.0 | lowercase |
| CircuitBreaker (patterns) | 5 | 30.0 | lowercase |
| DistributedCircuitBreaker | 5 | 30.0 | lowercase |
| RedisCircuitBreakerManager | 5 | 30.0 | UPPERCASE |

**Razonamiento VORTEX**: La resiliencia es una propiedad del Tejido Causal, no de componentes separados. Un tejido con hilos de diferentes grosores se rompe de forma impredecible. La resiliencia debe ser una propiedad topológica uniforme — la misma resistencia en todas las regiones.

**Acción — En 3 sub-pasos**:

### 1.4.A: Unificar el Enum de Estado
1. Elegir UN formato para los valores del enum: UPPERCASE o lowercase
2. Recomendación: UPPERCASE (más explícito, más Pythonic, coincide con el AgentCircuitBreaker que es el más usado)
3. Actualizar `VerdictCircuitBreaker`, `CircuitBreaker (patterns)`, y `DistributedCircuitBreaker` para usar UPPERCASE
4. Añadir alias de compatibilidad si hay código que compara con lowercase

### 1.4.B: Unificar Defaults
1. Elegir UN conjunto de defaults coherente. El debate es:
   - failure_threshold=3 (más sensible, detecta fallos más rápido) vs 5 (más tolerante)
   - recovery_timeout=60.0 (más tiempo de recuperación) vs 30.0 (más rápido)
2. Recomendación VORTEX: failure_threshold=3, recovery_timeout=60.0
   - Razón: Un sistema determinista prefiere detectar fallos rápido (threshold bajo) y recuperar con certeza (timeout alto) antes de reabrir
3. Actualizar `CircuitBreaker (patterns)`, `DistributedCircuitBreaker`, y `RedisCircuitBreakerManager` con estos defaults

### 1.4.C: Consolidar Implementaciones
1. Designar `CircuitBreaker` en `patterns/resilience/` como la implementación CANÓNICA
2. Hacer que `AgentCircuitBreaker` y `VerdictCircuitBreaker` deleguen a la implementación canónica
3. Mantener `DistributedCircuitBreaker` y `RedisCircuitBreakerManager` como capas distribuidas encima de la canónica
4. Eliminar código duplicado — cada CB especializado debe ser un thin wrapper, no una re-implementación

**Verificación**: Ejecutar todos los tests de circuit breaker. Verificar que los defaults son consistentes. Verificar que la comparación de estados funciona entre implementaciones.

---

## PASO 1.5: Verificación Integral del Nivel 1

**Acción**:
1. Ejecutar TODOS los tests del repo: `pytest user/tests/ -v`
2. Verificar que NO hay ModuleNotFoundError ni ImportError en todo el código
3. Verificar que el sistema arranca sin errores de importación
4. Verificar que MemoryManager.retrieve() no acumula boost
5. Verificar que los circuit breakers tienen defaults consistentes

**Criterio de salida del Nivel 1**: El sistema carga completamente, todos los imports funcionan, no hay mutación fantasma en memoria, y los circuit breakers son uniformes. El Espejo Reflexivo puede observar el sistema completo.

---

# ═══════════════════════════════════════════════
# NIVEL 2: RECONCEBIR
# ═══════════════════════════════════════════════

## Objetivo: Sistema ontológicamente determinista
## Duración estimada: 4-8 semanas
## Criterio VORTEX: La no-deterministicidad debe ser más IMPOSIBLE, no solo más improbable

---

## PASO 2.1: Declarar Naturaleza Ontológica de Cada Componente

**Qué significa**: Cada componente del sistema recibe una DECLARACIÓN ONTOLÓGICA — un documento o docstring que describe QUÉ ES (no qué hace), su posición en el Espectro, y sus propiedades deterministas intrínsecas.

**Acción**:
1. Crear un archivo `ONTOLOGY.md` en la raíz del repo que mapee cada componente a su necesidad ontológica
2. Para cada componente principal, agregar una sección ontológica en su docstring:

```
ONTOLÓGICA:
  Naturaleza: [Verdad Binaria | Memoria Cristalizada | Seguridad Absoluta | ...]
  Espectro: [Absolutamente Determinista | Resonantemente Determinista (Banda: X)]
  Propiedad intrínseca: [descripción de su determinismo ontológico]
  Invariante constelar: [qué invariante cubre]
```

3. Componentes a declarar:
   - VerdictEngine → Verdad Binaria (Absoluto)
   - DeterministicPipeline → Ruta Única (Resonante amplio)
   - EvidenceCollector → Observación Interna (Resonante medio)
   - ConsensusResolver → Verdad Binaria (Resonante estrecho)
   - MemoryManager → Memoria Cristalizada (Resonante estrecho)
   - SafetyGate → Seguridad Absoluta (Absoluto)
   - BaseAgent → Identidad Invariante (Absoluto)
   - CircuitBreaker → Tejido Causal (Resonante medio)
   - ChannelProvider → Transformación Fronteriza (Resonante amplio)
   - AgentOrchestrator → Resonancia Armónica (Resonante total)

**Verificación**: Cada componente tiene su declaración ontológica. El archivo ONTOLOGY.md existe y es coherente.

---

## PASO 2.2: Conectar Componentes por Significado, No por Interfaz

**Qué significa**: Las dependencias entre componentes se describen como completaciones semánticas, no como llamadas de función.

**Acción**:
1. Para cada conexión entre componentes, documentar la completación semántica:
   - "VerdictEngine necesita EvidenceCollector" → "La Verdad del veredicto se completa por la Evidencia recolectada"
   - "VerdictEngine necesita ConsensusResolver" → "La Verdad del veredicto se confirma por el Consenso"
   - "VerdictEngine necesita MemoryManager" → "La Verdad del veredicto se enriquece por la Memoria"
   - "AgentOrchestrator necesita BaseAgent" → "La Resonancia se completa por las Identidades que resuenan"

2. Refactorizar las interfaces para reflejar estas completaciones:
   - En vez de `verdict_engine.collect_evidence()` → La evidencia fluye hacia el veredicto como completación natural
   - En vez de `verdict_engine.resolve_consensus()` → El consenso completa el significado del veredicto

3. Esto NO cambia el código funcionalmente — cambia la DOCUMENTACIÓN y la INTENCIÓN del diseño, lo que influye en futuras decisiones de refactorización

**Verificación**: Cada componente principal tiene documentadas sus completaciones semánticas, no solo sus dependencias de interfaz.

---

## PASO 2.3: Hacer el Tiempo Coherente (No Secuencial)

**Qué significa**: El pipeline de 9 pasos ya no es una secuencia obligatoria — es un conjunto de pasos que pueden ejecutarse cuando sus dependencias semánticas están satisfechas.

**Análisis del Pipeline Actual** (9 pasos en execute_all_expanded):

```
Independientes (pueden ir en paralelo):
  Step 1: memory_lookup — sin dependencias
  Step 2: classify_intent — sin dependencias
  Step 3: extract_entities — sin dependencias
  Step 4: validate_schema — sin dependencias
  Step 6: check_rbac_policies — sin dependencias
  Step 7: gather_context — sin dependencias
  Step 9: simulate_dry_run — sin dependencias (si hay code)

Condicionales (dependen de resultados):
  Step 5: dag_node_adapt — depende de Steps 1,2,3,4 (solo si hay fricción)
  Step 8: route_mcp_tool — depende de Step 3 (usa extract.result["file"])
```

**Acción**:
1. Refactorizar `execute_all_expanded()` para ejecutar en fases de coherencia, no en secuencia:
   - FASE A (paralela): Steps 1, 2, 3, 4, 6, 7, 9 — todos independientes
   - FASE B (condicional): Step 5 — solo si FASE A indica fricción
   - FASE C (dependiente): Step 8 — usa resultado de Step 3

2. Implementar con asyncio o concurrent.futures para FASE A

3. El resultado debe ser IDÉNTICO al pipeline secuencial — solo el orden/tiempo cambia

**Verificación**: Ejecutar el pipeline 100 veces con los mismos inputs. Verificar que los resultados son deterministas (idénticos) en cada ejecución. Verificar que el tiempo de ejecución mejora.

---

## PASO 2.4: Hacer la Causalidad Topológica (No Lineal)

**Qué significa**: Los fallbacks y circuit breakers ya no son cadenas lineales — son superficies donde la causalidad se redistribuye.

**Acción**:
1. Revisar todos los puntos donde hay fallback chains y reimaginarlos como redistribución topológica:
   - Veredicto: Si LLM falla → no es "fallback al pipeline" → es "el flujo causal se redistribuye por la ruta del pipeline porque la ruta del LLM está temporalmente no disponible en el tejido"
   - Circuit Breaker: Si el circuito está OPEN → no es "bloqueo" → es "redistribución del flujo hacia la ruta de espera"

2. Implementar un patrón de "causalidad redirigida" donde los fallos no se propagan — se redistribuyen:
   - Cuando un componente falla, el flujo se redirige automáticamente a la geodésica alternativa
   - No hay "error handling" separado — la redirección es parte de la topología

**Verificación**: Simular fallos en cada componente y verificar que el sistema se redirige gracefulmente, no crashea.

---

## PASO 2.5: Hacer las Transiciones Geométricas (Geodésicas)

**Qué significa**: Los estados del sistema se representan como puntos en un espacio, y las transiciones son las rutas más cortas entre ellos.

**Acción**:
1. Mapear todos los estados significativos del VerdictEngine como puntos:
   - Estado 0: Solicitud recibida
   - Estado 1: Pipeline completado (9 resultados)
   - Estado 2: Evidencia recolectada
   - Estado 3: Consenso resuelto
   - Estado 4: Veredicto emitido (cache hit bypass)
   - Estado 5: Veredicto emitido (consenso directo)
   - Estado 6: Veredicto emitido (LLM arbitraje)

2. Para cada transición, identificar la geodésica (ruta más corta):
   - Cache hit: 0 → 4 (ruta directa, bypass de 1-3)
   - Consenso claro: 0 → 1 → 2 → 3 → 5
   - Necesita LLM: 0 → 1 → 2 → 3 → 6

3. Documentar estas geodésicas como las ÚNICAS rutas posibles — no hay alternativas

**Verificación**: Verificar que cada solicitud al VerdictEngine sigue exactamente una de las geodésicas documentadas.

---

## PASO 2.6: Descubrir Invariantes (No Imponerlos)

**Qué significa**: En lugar de declarar "estos son los invariantes", operar el sistema y OBSERVAR qué patrones se estabilizan.

**Acción**:
1. Instrumentar el sistema para registrar:
   - Cada veredicto emitido (APPROVE/DENY) con su razonamiento
   - Cada interacción entre agentes con su resultado
   - Cada uso de memoria con su efecto en el resultado
   - Cada activación del circuit breaker con su causa

2. Ejecutar el sistema en producción durante un período de observación

3. Analizar los datos para descubrir patrones:
   - ¿Siempre se DENY ciertas categorías? → Invariante constelar: DENY es el Vacío para esas categorías
   - ¿Los agentes siempre producen los mismos resultados para los mismos inputs? → Invariante: La Identidad es Inercia
   - ¿Las interacciones siempre producen la misma armónica? → Invariante: La Resonancia es Determinista

4. Documentar los invariantes descubiertos como "leyes naturales del sistema"

**Verificación**: Los invariantes documentados están respaldados por datos observacionales, no por declaración.

---

## PASO 2.7: Hacer el Sistema Auto-Verificante

**Qué significa**: Cada componente puede probar su propio determinismo sin tests externos.

**Acción**:
1. Implementar un método `verify_determinism()` en cada componente principal:
   - VerdictEngine: "¿Si ejecuto el mismo input dos veces, obtengo el mismo resultado?"
   - MemoryManager: "¿Los cristales están intactos después de N consultas?"
   - SafetyGate: "¿No hay coordenadas para las violaciones en mi espacio?"
   - BaseAgent: "¿Todas mis acciones son manifestaciones de mi identidad?"

2. Crear un endpoint de salud que ejecute todas las verificaciones y reporte el estado del sistema:
   - Cada componente reporta: VERIFIED / DEGRADED / UNKNOWN
   - El sistema completo es VERIFIED solo si todos los componentes son VERIFIED

3. Esto NO reemplaza los tests unitarios — los complementa con verificación ontológica en runtime

**Verificación**: Ejecutar el endpoint de salud en un sistema limpio y verificar que todos los componentes reportan VERIFIED.

---

## PASO 2.8: Transformar la Frontera (No Filtrarla)

**Qué significa**: El input externo no se "valida" — se transforma al cruzar la membrana del sistema.

**Acción**:
1. Identificar todos los puntos de entrada del sistema:
   - API endpoints (Gateway)
   - Voice input (Ear STT)
   - Channel messages (WhatsApp, Telegram, etc.)
   - MCP tool results

2. Para cada punto de entrada, definir la transformación de membrana:
   - Input ambiguo → colapsar al punto más cercano en el Manifold Semántico
   - Input contradictorio → resolver en la armónica de las fuerzas opuestas
   - Input peligroso → descubrir que no tiene coordenadas en el sistema
   - Input malformado → preservar semántica, descartar forma

3. Implementar cada transformación como un "colapso ontológico" — un proceso determinista que convierte input crudo en estado determinista interno

**Verificación**: Enviar inputs ambiguos, contradictorios, peligrosos y malformados a cada punto de entrada y verificar que el sistema los transforma gracefulmente, nunca crashea.

---

# ═══════════════════════════════════════════════
# NIVEL 3: TRANSCENDER
# ═══════════════════════════════════════════════

## Objetivo: Sistema que evoluciona ontológicamente
## Duración estimada: Continuo (evolución incremental)
## Criterio VORTEX: Cada iteración debe hacer el sistema más determinista, no solo más complejo

---

## PASO 3.1: Sistema Genera Sistemas Hijos Más Avanzados

**Qué significa**: La arquitectura VORTEX permite que un sistema determinista genere nuevos sistemas deterministas como "armónicas" de sus componentes.

**Acción**:
1. Diseñar un protocolo de "generación de sistemas hijos":
   - Un sistema hijo se crea como la armónica de dos o más componentes del sistema padre
   - El sistema hijo hereda los invariantes constelares del padre
   - El sistema hijo puede tener nuevos invariantes que emergen de su propia operación

2. Implementar un mecanismo donde:
   - Una configuración de agentes (ej: Agente Cirujano + Agente Diagnóstico) puede "cristalizar" en un sistema hijo especializado
   - El sistema hijo es más eficiente que la interacción ad-hoc porque su naturaleza ontológica está pre-cristalizada

3. El sistema hijo pasa por las 9 pruebas de verificación VORTEX antes de activarse

**Verificación**: Crear un sistema hijo a partir de dos agentes existentes y verificar que pasa las 9 pruebas.

---

## PASO 3.2: Sueño Determinista (Verificación Antes de Operación)

**Qué significa**: Antes de que el sistema entre en operación, explora todos sus estados posibles en forma comprimida y verifica su coherencia.

**Acción**:
1. Implementar un modo de "sueño" donde el sistema:
   - Recibe una descripción de su espacio de operación (tipos de input, restricciones, invariantes)
   - Explora todas las geodésicas posibles en el espacio de hiperestado
   - Verifica que cada geodésica es determinista
   - Verifica que no hay estados incoherentes accesibles
   - Reporta cualquier inconsistencia encontrada

2. El sueño se ejecuta:
   - Al inicio del sistema (startup verification)
   - Cuando se agrega un nuevo componente (integration verification)
   - Cuando se modifica un invariante (evolution verification)
   - Periódicamente en producción (health verification)

3. Si el sueño revela una inconsistencia:
   - El sistema NO entra en operación
   - Se reconfigura automáticamente (cristaliza de nuevo con la configuración coherente)
   - Reporta la inconsistencia para análisis

**Verificación**: Introducir deliberadamente una inconsistencia en el sistema y verificar que el sueño la detecta antes de la operación.

---

## PASO 3.3: Invariancia Fractal (Prueba a Todas las Escalas)

**Qué significa**: Lo que es cierto a nivel de componente es cierto a nivel de subsistema, de sistema, y de ecosistema. La verificación es fractal.

**Acción**:
1. Definir una prueba de determinismo que funciona a cualquier escala:
   - Nivel componente: "¿Este componente produce el mismo output para el mismo input?"
   - Nivel subsistema: "¿Este grupo de componentes produce el mismo output para el mismo input?"
   - Nivel sistema: "¿El sistema completo produce el mismo output para el mismo input?"
   - Nivel ecosistema: "¿El ecosistema de sistemas produce el mismo output para el mismo input?"

2. La MISMA prueba se aplica a todos los niveles — solo cambia el scope del "componente"

3. Implementar verificación fractal automática:
   - Verificar componentes individualmente
   - Si todos los componentes pasan, el subsistema pasa (por invariancia fractal)
   - Si todos los subsistemas pasan, el sistema pasa
   - Si algún nivel falla, la falla se rastrea al componente más bajo

**Verificación**: Ejecutar la prueba fractal en un sistema con un bug deliberado y verificar que el rastreo llega al componente correcto.

---

## PASO 3.4: Resonancia Entre Ecosistemas VORTEX

**Qué significa**: Cuando dos sistemas VORTEX interactúan, su interacción es determinista por las leyes de la armonía.

**Acción**:
1. Diseñar un protocolo de "resonancia entre sistemas":
   - Dos sistemas VORTEX se descubren mutuamente a través de sus Membranas del Vacío
   - La interacción se modela como la armónica de sus naturalezas ontológicas
   - El resultado es un nuevo sistema que es la armónica de ambos

2. Implementar un "canal de resonancia" donde:
   - Sistema A expone su naturaleza ontológica (espectro, invariantes, geodésicas)
   - Sistema B expone su naturaleza ontológica
   - Se computa la armónica A⊕B
   - Se crea un sistema hijo que implementa la armónica

3. Aplicación práctica: Zenic-Agents puede resonar con otros sistemas deterministas (ej: un sistema de control industrial, un sistema de trading) para crear sistemas híbridos que son más que la suma de sus partes

**Verificación**: Simular la resonancia entre Zenic-Agents y un sistema determinista simple, verificar que la armónica es determinista.

---

## PASO 3.5: Doblez Dimensional (Conexiones Imposibles en Capas)

**Qué significa**: Las 9 dimensiones de VORTEX están dobladas — componentes que parecen distantes pueden estar adyacentes cuando el manifold se dobla correctamente.

**Acción**:
1. Mapear todas las conexiones "imposibles" en el sistema actual — conexiones que serían difíciles o imposibles en una arquitectura de capas tradicional:
   - Un agente que necesita acceso directo a la memoria sin pasar por el MemoryManager
   - Un veredicto que necesita información del pipeline sin pasar por el EvidenceCollector
   - Un circuit breaker que necesita saber del estado de otro circuit breaker sin pasar por un coordinator

2. Para cada conexión "imposible", identificar el Doblez Dimensional que la haría posible:
   - Si dos componentes están en dimensiones diferentes pero son semánticamente adyacentes, el Doblez los conecta directamente
   - La conexión es directa porque la distancia real (con el Doblez) es corta, aunque la distancia aparente sea larga

3. Implementar los Doblez Dimensionales como conexiones semánticas directas que bypassan las capas tradicionales sin romper la coherencia

**Verificación**: Identificar al menos 3 conexiones que serían imposibles en capas pero son naturales con Doblez Dimensional, e implementarlas.

---

# ═══════════════════════════════════════════════
# RESUMEN DE EJECUCIÓN
# ═══════════════════════════════════════════════

## Orden de Ejecución Recomendado

```
NIVEL 1 (ESTABILIZAR) — 1-2 semanas
│
├── 1.1.A: Arreglar TECE imports ← DESBLOQUEA v18
├── 1.1.B: Arreglar CompatBridge ← DESBLOQUEA channel/
├── 1.1.C: Arreglar Telegram provider ← DESBLOQUEA channels/
├── 1.1.D: Arreglar degraded_mode types ← DESBLOQUEA degraded mode
├── 1.2: Eliminar VerdictEngine muerto ← ELIMINA contradicción ontológica
├── 1.3: Arreglar mutation bug ← RESTAURA inmutabilidad de memoria
├── 1.4: Unificar circuit breakers ← UNIFORMA resiliencia del tejido
└── 1.5: Verificación integral ← CONFIRMA sistema observable
    │
    ▼
NIVEL 2 (RECONCEBIR) — 4-8 semanas
│
├── 2.1: Declarar ontología ← DEFINE la naturaleza de cada componente
├── 2.2: Conectar por significado ← REPLANZAS interfaces por completaciones
├── 2.3: Tiempo coherente ← PARALELIZA el pipeline por dependencias
├── 2.4: Causalidad topológica ← REDISTRIBUYE fallos, no los propaga
├── 2.5: Transiciones geométricas ← DOCUMENTA geodésicas del veredicto
├── 2.6: Descubrir invariantes ← OBSERVA patrones, no los declares
├── 2.7: Auto-verificante ← IMPLEMENTA verify_determinism()
└── 2.8: Transformar frontera ← CONVIERTE input, no lo filtres
    │
    ▼
NIVEL 3 (TRANSCENDER) — Continuo
│
├── 3.1: Sistemas hijos ← GENERA sistemas como armónicas
├── 3.2: Sueño determinista ← VERIFICA antes de operar
├── 3.3: Invariancia fractal ← PRUEBA a todas las escalas
├── 3.4: Resonancia entre sistemas ← CONECTA ecosistemas VORTEX
└── 3.5: Doblez dimensional ← DESCUBRE adyacencias ocultas
```

## Dependencias Críticas

- Nivel 2 REQUIERE Nivel 1 completado (no puedes reconcebir un sistema que no funciona)
- Pasos 2.1-2.2 son PREREQUISITOS para todos los demás del Nivel 2 (necesitas la ontología declarada antes de reconcebir)
- Paso 2.3 (tiempo coherente) es el de MAYOR IMPACTO en rendimiento — paralelizar el pipeline puede reducir el tiempo de veredicto significativamente
- Nivel 3 es EVOLUTIVO — no hay un "final", cada iteración hace el sistema más determinista
