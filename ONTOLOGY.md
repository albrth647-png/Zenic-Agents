# ONTOLOGÍA DE ZENIC-AGENTS v3

> *"La IA no genera, solo arbitra"*

Este documento declara la **naturaleza ontológica** de cada componente del sistema y las **completaciones semánticas** que existen entre ellos. No describe implementación — describe **esencia**.

---

## 1. Ontología de Componentes

### 1.1 VerdictEngine

**LO QUE ES:** El árbitro final del sistema. Un motor que recibe una pregunta binaria y evidencia estructurada, y emite un veredicto SÍ/NO. Solo interviene cuando el consenso determinístico no es suficiente.

**LO QUE NO ES:** No es un generador de contenido. No es un clasificador. No es un chatbot. No toma decisiones sin evidencia.

**INVARIANTE EXISTENCIAL:** Toda decisión debe tener un rastro de evidencia. Nunca emite un veredicto sin al menos un intento de consenso determinístico previo.

**FRONTERA:** No ejecuta código. No clasifica intenciones. No extrae entidades. No genera texto. Solo arbitra entre opciones binarias.

---

### 1.2 DeterministicPipeline

**LO QUE ES:** El sistema que HACE todo el trabajo productivo. Ejecuta 9 tareas determinísticas sin IA: lookup de memoria, clasificación, extracción, validación, adaptación, permisos, contexto, ruteo y simulación.

**LO QUE NO ES:** No es un LLM. No toma decisiones. No evalúa calidad. No tiene opiniones.

**INVARIANTE EXISTENCIAL:** Dado el mismo input + estado, produce exactamente el mismo output. Cero no-determinismo.

**FRONTERA:** No decide si algo es seguro o no. No emite veredictos. Solamente produce resultados estructurados para que otros componentes evalúen.

---

### 1.3 EvidenceCollector

**LO QUE ES:** Un sistema de recolección de señales. Examina texto, código y contexto usando análisis estático, regex, reglas y patrones para producir objetos `Evidence` que representan hechos objetivos.

**LO QUE NO ES:** No es un motor de inferencia. No evalúa la evidencia que recolecta. No tiene opiniones sobre lo que significa la evidencia.

**INVARIANTE EXISTENCIAL:** La evidencia producida debe ser reproducible. Otro EvidenceCollector con los mismos inputs debe producir la misma evidencia.

**FRONTERA:** No resuelve consenso. No decide qué evidencia es más importante. Solo recolecta hechos observables.

---

### 1.4 ConsensusResolver

**LO QUE ES:** El sistema que RESUELVE el significado de la evidencia. Aplica pesos por tipo de señal, calcula score normalizado, verifica vetos automáticos y determina si hay consenso o se necesita arbitraje humano/de IA.

**LO QUE NO ES:** No recolecta evidencia. No emite veredictos finales (solo recomendaciones). No puede anular un veto de seguridad.

**INVARIANTE EXISTENCIAL:** En caso de duda absoluta (score=0), el resultado siempre es NO. Principio de precaución innegociable.

**FRONTERA:** No decide si el sistema debe ejecutar una acción. Solo determina si la evidencia disponible es suficiente para decidir.

---

### 1.5 MemoryManager

**LO QUE ES:** El sistema de memoria unificado. Orquesta tres niveles (working, short-term, long-term) con retrieval, promoción automática y decay. Proporciona contexto relevante al pipeline sin intervención de IA.

**LO QUE NO ES:** No es una base de datos SQL. No es un vector store. No es un sistema de archivos. No almacena datos brutos sin procesar.

**INVARIANTE EXISTENCIAL:** El retrieval nunca falla — siempre devuelve un resultado válido (posiblemente vacío). No puede bloquear el pipeline.

**FRONTERA:** No evalúa la relevancia semántica del contenido (eso es responsabilidad del Scorer). No persiste datos críticos del sistema.

---

### 1.6 SafetyGate

**LO QUE ES:** La barrera inbypassable del sistema. Evalúa cada acción contra 3 capas: reglas determinísticas (DENY es final), policy engine, y evaluación de IA (solo SÍ/NO). Ninguna acción puede eludir esta evaluación.

**LO QUE NO ES:** No es un log de auditoría. No es configurable por el usuario. No tiene modo degradado — DENY es DENY siempre.

**INVARIANTE EXISTENCIAL:** Es imposible saltarse una regla DENY. El código nunca contiene caminos que puedan evitar la evaluación del SafetyGate.

**FRONTERA:** No ejecuta acciones. No decide qué acciones son válidas desde el punto de vista funcional. Solo evalúa seguridad.

---

### 1.7 BaseAgent

**LO QUE ES:** La plantilla ontológica para todos los agentes del sistema. Cada agente tiene EXACTAMENTE UNA responsabilidad, implementada en `execute()`. Todos los agentes son determinísticos por defecto. El patrón de resiliencia (circuit breaker, bulkhead, retry, auditoría) se aplica automáticamente.

**LO QUE NO ES:** No es un framework de agentes genérico. No permite que los agentes llamen al LLM directamente. No soporta herencia múltiple de responsabilidades.

**INVARIANTE EXISTENCIAL:** El sistema funciona 100% sin IA. Cada agente tiene un `fallback()` determinístico que nunca falla.

**FRONTERA:** Un agente no puede llamar a otro agente. Solo el orquestador coordina agentes.

---

### 1.8 CircuitBreaker

**LO QUE ES:** Una máquina de estados CLOSED → OPEN → HALF_OPEN que protege al sistema de fallos en cascada. Thread-safe, stdlib-only, diseñado para entornos con recursos limitados (Android/Termux, 500MB RAM).

**LO QUE NO ES:** No es un timeout. No es un rate limiter. No es un retry mechanism. No es un health check.

**INVARIANTE EXISTENCIAL:** Una vez OPEN, todas las llamadas fallan inmediatamente sin ejecutar la operación subyacente. Solo el tiempo de recovery puede transicionar a HALF_OPEN.

**FRONTERA:** No decide si una operación es correcta o no. Solo decide si permitir que se ejecute basado en el historial de fallos recientes.

---

### 1.9 ChannelProvider

**LO QUE ES:** Un protocolo estructural que define el contrato para todos los canales de comunicación. Los providers implementan `send()`, `send_confirmation()`, y opcionalmente `set_message_handler()` para canales bidireccionales. No hay herencia — solo implementación de protocolo.

**LO QUE NO ES:** No es un adaptador de API específica. No es un router de mensajes. No es un sistema de colas.

**INVARIANTE EXISTENCIAL:** `send()` nunca lanza excepción. Siempre devuelve un `ChannelResponse` con estado éxito/fallo. `start()` y `stop()` son idempotentes.

**FRONTERA:** No procesa el contenido del mensaje. No decide a dónde enrutar un mensaje. Solo entrega.

---

### 1.10 ZenicOrchestrator

**LO QUE ES:** El orquestador central que coordina el pipeline completo de 8 niveles. Inicializa todos los subsistemas en 9 fases, ejecuta el flujo de decisión completo: clasificación → routing → planning → ejecución → veredicto → sandbox → commit/rollback.

**LO QUE NO ES:** No es un agente. No es un framework. No toma decisiones autónomas — solo coordina el flujo entre componentes.

**INVARIANTE EXISTENCIAL:** Toda ejecución sigue el mismo flujo. No hay atajos que salten el SafetyGate o el VerdictEngine.

**FRONTERA:** No ejecuta código de usuario. No almacena estado persistente. La IA solo puede decir SÍ o NO a través del VerdictEngine.

---

## 2. Completaciones Semánticas

Cada componente de Zenic tiene un **vacío ontológico** — algo que no puede hacer por sí mismo — que otro componente completa. Estas no son dependencias funcionales (llamadas de método), sino **completaciones semánticas**: el significado de un componente se completa con el significado de otro.

### 2.1 DeterministicPipeline → EvidenceCollector

**Vacío del Pipeline:** Produce resultados estructurados (`DeterministicResult`) con campos como `confidence`, `result`, `source`. Pero estos resultados no tienen *significado evaluativo* — un confidence de 0.8 no es evidencia a favor o en contra de algo.

**Completación de EvidenceCollector:** Toma los outputs del pipeline y los envuelve en objetos `Evidence` que tienen dirección semántica (`favors=Verdict.YES/NO`), peso (`weight`), y tipo (`evidence_type`). El pipeline produce hechos; EvidenceCollector produce *señales evaluativas*.

### 2.2 EvidenceCollector → ConsensusResolver

**Vacío de EvidenceCollector:** Produce muchas señales de diferentes tipos, pero no tiene capacidad de sopesarlas. Un SECURITY_CHECK con weight=0.9 y un KEYWORD_CLASSIFY con weight=0.5 coexisten sin jerarquía.

**Completación de ConsensusResolver:** Aplica pesos ontológicos por tipo de evidencia (security=1.5x, keyword=0.5x), verifica vetos automáticos, normaliza el score y decide qué tan lejos está la evidencia del consenso. El collector produce *señales*; el resolver produce *juicio evaluativo*.

### 2.3 ConsensusResolver → VerdictEngine

**Vacío de ConsensusResolver:** Puede determinar que no hay consenso suficiente (needs_llm=True), pero no puede arbitrar el empate. Su output es un "no sé" estructural.

**Completación de VerdictEngine:** Toma el empate y aplica el arbitraje binario de la IA. Pero siguiendo la regla de oro, solo puede emitir SÍ o NO. El resolver produce *indeterminación*; el engine produce *resolución final*.

### 2.4 MemoryManager → DeterministicPipeline

**Vacío de MemoryManager:** Almacena y recupera memorias, pero no sabe cómo usar esas memorias para tomar decisiones o clasificar input. Sus entradas son datos sin contexto de pipeline.

**Completación del Pipeline:** Los pasos 1 (memory_lookup) y 5 (dag_node_adapt) del pipeline consumen las salidas de MemoryManager y las integran en el flujo de decisión. La memoria produce *contexto histórico*; el pipeline produce *acción contextualizada*.

### 2.5 SafetyGate → ZenicOrchestrator

**Vacío de SafetyGate:** Evalúa seguridad pero no sabe qué acciones son válidas funcionalmente ni cómo encajan en el flujo del sistema. Su output es un veredicto de seguridad sin contexto de orquestación.

**Completación del Orchestrator:** Toma el veredicto de seguridad y lo integra en la decisión final de commit/rollback. El gate produce *permiso/denegación*; el orchestrator produce *ejecución coordinada*.

### 2.6 CircuitBreaker → BaseAgent

**Vacío de CircuitBreaker:** Decide si permitir llamadas, pero no sabe qué operación ejecutar ni cómo recuperarse de un fallo. Su output es una puerta abierta/cerrada.

**Completación de BaseAgent:** El `run()` de BaseAgent consulta el CircuitBreaker, y si está abierto, ejecuta `fallback()` en lugar de `execute()`. El breaker produce *protección*; el agent produce *recuperación*.

### 2.7 VerdictEngine → ZenicOrchestrator

**Vacío de VerdictEngine:** Produce un veredicto SÍ/NO con confianza, pero no sabe qué hacer con él — no puede hacer commit, rollback, ni cachear resultados.

**Completación del Orchestrator:** Toma el veredicto y lo usa como señal principal para decidir entre SUCCESS (YES + sandbox PASS), REJECTED (NO), o NO_OP. El engine produce *veredicto*; el orchestrator produce *acción*.

### 2.8 ChannelProvider → DeterministicPipeline

**Vacío de ChannelProvider:** Puede enviar mensajes, pero no sabe qué contenido enviar ni a quién. No entiende el contexto del veredicto.

**Completación del Pipeline:** Los pasos 7 (gather_context) y 8 (route_mcp_tool) del pipeline determinan qué información es relevante y a dónde debe enviarse. El provider produce *transporte*; el pipeline produce *contenido direccionado*.

---

## 3. Invariantes Transversales

1. **La IA nunca genera contenido.** En ninguna parte del sistema la IA produce texto, código, o decisiones no-binarias.
2. **DENY es inapelable.** Ningún componente puede revertir un DENY del SafetyGate.
3. **Determinismo por defecto.** El sistema funciona al 100% sin IA. La IA es un árbitro de respaldo.
4. **Trazabilidad total.** Toda decisión tiene un rastro de evidencia auditable.
5. **Principio de precaución.** En caso de duda, la respuesta es NO.

---

## 4. Geodésicas del VerdictEngine (VORTEX 2.5)

Cada solicitud al VerdictEngine sigue EXACTAMENTE una de estas geodésicas:

| Geodésica | Ruta | Latencia | Descripción |
|-----------|------|----------|-------------|
| **CACHE** | 0 → 4 | <5ms | Cache hit del Chip de Memoria, bypass del pipeline completo |
| **CONSENSUS** | 0 → 1 → 2 → 3 → 5 | ~50ms | Consenso determinístico claro, sin IA |
| **LLM** | 0 → 1 → 2 → 3 → 6 | ~500ms | Empate determinístico → arbitraje de IA |
| **FALLBACK** | 0 → 1 → 2 → 3 → 7 | ~50ms | LLM no disponible → fallback NO |
| **VETO** | 0 → 1 → 2 → 8 | ~30ms | Veto de seguridad → NO inmediato |
| **ERROR** | 0 → 7 | ~5ms | Error en cualquier punto → fallback NO |

**Estados:**
- 0: Solicitud recibida
- 1: Pipeline completado (9 resultados determinísticos)
- 2: Evidencia recolectada
- 3: Consenso resuelto
- 4: Veredicto emitido (cache hit bypass)
- 5: Veredicto emitido (consenso directo)
- 6: Veredicto emitido (LLM arbitraje)
- 7: Veredicto emitido (fallback)
- 8: Veredicto emitido (veto de seguridad)

## 5. Causalidad Topológica (VORTEX 2.4)

Los fallos NO se propagan — se REDISTRIBUYEN. Cada punto de fallo tiene
una geodésica alternativa:

| Componente | Ruta Nominal | Redistribución | Fallback |
|------------|-------------|----------------|----------|
| VerdictEngine | LLM arbitraje | Consensus directo | Fallback NO |
| BaseAgent | execute() | fallback() | Error graceful |
| CircuitBreaker | CLOSED | HALF_OPEN | OPEN |
| MemoryManager | Cache hit | Retrieval | Resultado vacío |

## 6. Invariantes del Sistema (VORTEX 2.6)

Declarados para observación — serán confirmados por operación continuada:

1. **Determinismo de veredicto**: Mismo input → mismo output en VerdictEngine
2. **Inmutabilidad de memoria**: retrieve() no muta entries originales
3. **Determinismo de pipeline**: DeterministicPipeline produce mismo output para mismo input
4. **Inbypassabilidad de seguridad**: SafetyGate.DENY nunca se puede sobrepasar
5. **Recuperación de circuito**: CircuitBreaker transiciona a HALF_OPEN tras recovery_timeout
6. **Validez geodésica**: Toda ejecución sigue una geodésica documentada
7. **Absolutismo de veto**: Un veto de seguridad es siempre DENY
8. **Disponibilidad de fallback**: Todo componente tiene un fallback disponible

## 7. Transformación de Membrana (VORTEX 2.8)

Los puntos de entrada del sistema transforman el input externo mediante colapsos ontológicos:

| Punto de Entrada | Colapso | Descripción |
|------------------|---------|-------------|
| chat_message | Ambiguo→Cercano + Peligroso→Vacío | Input de usuario colapsa a nearest point |
| voice_input | Malformado + Ambiguo | Audio transcrito se limpia |
| channel_message | Malformado + Peligroso | Mensajes de canales externos |
| mcp_tool_result | Malformado | Resultados de herramientas externas |
| api_request | Malformado + Peligroso | Requests HTTP externos |

## 8. Glosario Ontológico

| Término | Significado |
|---------|-------------|
| **Arbitrar** | Emitir un veredicto SÍ/NO basado en evidencia existente |
| **Colapso ontológico** | Transformación de input externo a estado interno determinista |
| **Completar** | Llenar el vacío semántico de otro componente |
| **Consenso** | Acuerdo entre múltiples señales de evidencia independientes |
| **Determinístico** | Mismo input + estado → mismo output, siempre |
| **Geodésica** | Ruta única documentada entre estados del sistema |
| **Inbypassable** | No existe camino de código que pueda evitar este componente |
| **Redistribución topológica** | Cuando un componente falla, el flujo se redirige a la geodésica alternativa |
| **Veto** | Señal de evidencia que anula cualquier decisión en contrario |
| **Veredicto** | Decisión binaria con rastro de evidencia |
