# Contratos, estados persistentes y recuperación

Versión conceptual 0.1 · estado de implementación actualizado 2026-10-05 · contratos de la arquitectura ampliada, clasificados **I**. Las firmas numeradas son el diseño objetivo; los contratos y diferencias del subconjunto implementado se documentan en [MVP v0.1](mvp-v0.1.md), [v0.2](mvp-v0.2.md), [v0.3](mvp-v0.3.md), [ADR-0002](decisions/0002-delayed-cue-slice.md), [ADR-0003](decisions/0003-persistent-association-learning.md) y [ADR-0004](decisions/0004-capability-predictor.md).

## Contrato ejecutable de capacidades v0.3

La política optativa `capability` conserva `{'records': [...], 'capability': model}`. El modelo contiene `backend`, `probabilities`, `updates` y `last_update`; esta última guarda tick, episodio y hash del feedback, sin pista en caché. Self representa probabilidades como `{fast: qf, safe: qs}` y generic como `[qf, qs]`. `model_estimates` devuelve una lista copiada; `update_model` devuelve otro modelo validado, actualiza solo la herramienta observada y rechaza feedback anterior o reutilizado. Los reintentos públicos pertenecen a `Runtime.step(expected_tick)`.

| Interfaz v0.3 | Contrato efectivo |
|---|---|
| Config pública | Modo/backend, permisos de escritura/lectura, tasa 0.2, exploración 0.1 y costes 0.05/0.20 por defecto; sin calendario ni eficacia verdadera |
| TaskConfig privada | Tarea `capability-v1`, episodio de degradación y eficacias generadoras; acceso exclusivo al mundo/evaluador |
| Observación | Exactamente `episode`, `phase`, `value`; choice tiene value null |
| Acción | `wait` o combinación `left:fast`, `left:safe`, `right:fast`, `right:safe` |
| Outcome | `terminal`, `success`, `reward`, `episode`, `decision_correct`, `execution_success`, `tool`, `cost`; éxito requiere decisión y ejecución correctas |
| Vista de capacidad | `[q_fast, q_safe]`, o `[0.5, 0.5]` al cortar lectura; el selector de herramienta no recibe modelo privado ni etiqueta de condición |
| Predicción registrada | Lado, herramienta, distribuciones de selección, ejecución y éxito global previstos, vista y utilidades, fuentes, versión/hash/bytes del modelo anterior al resultado |
| Estado posterior | `post_capability_hash`, `post_capability_version`, `post_capability_bytes` y `post_agent_bytes` en la traza, junto con snapshot/RNG completos |

`predicted_execution_success` se refiere a la herramienta elegida; `predicted_success` y `confidence` se refieren al éxito global y multiplican esa probabilidad por la probabilidad de lado correcto. `probability_fast` describe exploración/selección, no eficacia. `capability_view` y `expected_utilities` usan orden fast/safe. En wait las elecciones, vistas y predicciones son null; hashes, versión, IDs y contadores siguen registrados.

La decisión queda fijada antes de la transición; el feedback se valida y asimila dentro del mismo tick atómico, sin feedback pendiente entre ticks en este corte. Se comprueban enlace de episodio/herramienta/costes, consistencia de éxito/recompensa y correspondencia con el modelo previo; una pista válida de la regla fija no admite un resultado contradictorio sobre el lado correcto. `fork` puede cambiar permisos de aprendizaje o lectura de capacidad, preservando tarea, backend, tasas y costes. No se modifica el esquema SQL ni se reescriben las ejecuciones históricas. Contratos completos: [MVP v0.3](mvp-v0.3.md).

## 1. Tipos y límites comunes

IDs opacos: `RunId`, `BranchId`, `AgentId`, `EventId`, `EpisodeId`, `GoalId`, `ModelVersion`. No intercambiar IDs de tipos diferentes. `Tick` y `Substep` son enteros no negativos. El reloj UTC sirve para auditoría; la dinámica usa tiempo lógico.

`Tick` es global al run y persiste entre episodios de tarea; `environment_episode_id` y `episode_step` identifican esos episodios y sus pasos. Un `EpisodeId` de memoria referencia una experiencia y el episodio de tarea donde ocurrió. El cierre de tarea se registra antes del reset ambiental, conservando estado cognitivo y parámetros aprendidos.

`Probability` es finita y está entre 0 y 1. Las distribuciones se normalizan, tienen vocabulario de resultados y distinguen resultados desconocidos. No se admiten NaN o infinito. Las escalas de utilidad, costes y sorpresa se describen en el manifiesto.

| Tipo | Campos obligatorios | Regla semántica |
|---|---|---|
| `Provenance` | `source_kind`, `source_ids`, `origin_agent_id`, `observed_tick`, `available_tick` | `OBSERVED`, `INFERRED`, `SIMULATED`, `REPORTED` o `INTERVENED`; el origen persiste en derivados |
| `Observation` | `observation_id`, `agent_id`, `tick`, `channel`, `payload`, `provenance` | Solo información permitida por el entorno; sensor ausente no equivale a valor cero |
| `Belief` | `variable_id`, `distribution`, `uncertainty_method`, `evidence_ids`, `updated_tick` | Estimación revisable, nunca etiqueta privada del evaluador |
| `WorkspaceItem` | `item_id`, `kind`, `payload_ref`, `priority_terms`, `expires_tick`, `provenance` | Contenido acotado; lista explícita de consumidores y rutas locales |
| `Prediction` | `prediction_id`, `target`, `distribution`, `horizon`, `model_version`, `issued_tick` | Se congela antes del resultado que se va a puntuar |
| `Goal` | `goal_id`, `origin`, `objective`, `priority`, `status`, `success_condition`, `budget`, `parent_id` | Origen `TASK`, `RESOURCE`, `EXPLORATION`; estados propuesto/activo/suspendido/completado/fallido/cancelado |
| `ActionProposal` | `action_id`, `action_type`, `parameters`, `goal_id`, `predictions`, `expected_cost`, `belief_refs` | Las razones son términos estructurados de decisión, no una explicación verbal generada después |
| `ActionResult` | `action_id`, `status`, `observable_outcome`, `cost`, `provenance` | `SUCCEEDED`, `FAILED` o `UNKNOWN`; error de transporte no equivale a fracaso de acción |
| `StateDelta` | `module_id`, `base_revision`, `changes`, `evidence_ids`, `algorithm_version` | Solo el propietario propone cambios a su espacio; el coordinador confirma |
| `Intervention` | `intervention_id`, `target`, `operator`, `value`, `start_tick`, `end_tick`, `reason`, `parent_snapshot` | Duración semiabierta `[start_tick,end_tick)`; investigador, nunca entrada conversacional |
| `ModuleError` | `code`, `module_id`, `tick`, `retryable`, `details` | Resultado de error estructurado y consistente en todas las interfaces |

Una confianza debe referirse a un evento, por ejemplo “probabilidad de éxito de esta acción dentro de 3 ticks”. Un número genérico de confianza sin objetivo ni horizonte no se usa para evaluación.

## 2. Interfaces entre componentes

Todas las funciones de decisión reciben vistas inmutables y un contexto con `run_id`, `agent_id`, `tick`, versión, presupuesto y flujo de aleatoriedad propio. Devuelven valores y propuestas de cambio; no escriben directamente en otros módulos ni invocan herramientas externas.

| Propietario | Firma conceptual | Retorno y efectos permitidos |
|---|---|---|
| `runtime` | `step(observation, state_revision, intervention_set)` | `TickOutcome` con acción, trazas y nueva revisión; una confirmación atómica |
| `runtime` | `finalize_feedback(pending_result, state_revision)` | Asimila un resultado pendiente sin decidir ni ejecutar otra acción; idempotente por action_id y resultado |
| `runtime` | `snapshot(run_id, committed_tick)` | `SnapshotRef`; únicamente fronteras confirmadas |
| `runtime` | `fork(snapshot_ref, condition_manifest)` | Nueva rama con linaje e intervenciones; no modifica el padre |
| `runtime` | `replay(run_id, until_tick, mode)` | Verificación de hashes de estado o reconstrucción; modos diferenciados más abajo |
| `runtime` | `read_events(run_id, after_sequence, limit)` | Página ordenada, siguiente cursor; solo observador |
| `memory` | `encode(episode_draft, provenance, revision)` | Propuesta de episodio y deltas de índice; resultado pendiente permitido |
| `memory` | `link_outcome(episode_id, action_result, revision)` | Evento de resultado enlazado, sin reescribir predicción |
| `memory` | `retrieve(query, filters, top_k, as_of_tick)` | `MemoryHit[]` con puntuaciones y fuentes; lectura acotada |
| `memory` | `consolidate(candidate_ids, budget, version)` | Hechos/resúmenes candidatos, soportes y contradicciones |
| `cognition/perception` | `perceive(observations, sensor_model)` | Rasgos y creencias de fiabilidad, sin acceso al mundo oculto |
| `cognition/world` | `update_beliefs(prior, observation, previous_action)` | Posterior y estadísticas aprendidas |
| `cognition/world` | `predict(belief, self_model_view, candidate_action, horizon)` | Distribución compuesta: factores externos del mundo y eficacia propia del self-model, sin duplicar estimadores |
| `cognition/self` | `update_self(self_state, own_action, outcome)` | Capacidades, atribución y costes estimados con fuentes |
| `cognition/affect` | `appraise(prior_affect, prediction_error, progress, resources)` | Reguladores acotados y términos de cálculo |
| `cognition/workspace` | `select(candidates, modulators, capacity)` | Ganadores, excluidos, puntuaciones y caducidad |
| `cognition/goals` | `revise_goals(goals, beliefs, resources, modulators)` | Agenda y transiciones; presión de recursos modifica prioridad de recarga, sin modificar energía real |
| `cognition/meta` | `update_calibration(prior_calibrator, issued_predictions, observed_outcomes)` | Delta del calibrador, idempotente por prediction_id y versión de resultado |
| `cognition/meta` | `estimate_information_value(decision_context, belief, predictor, queries, costs, budget)` | Valor esperado neto de consultas bajo modelo aprendido, con incertidumbre y coste de calcularlo |
| `cognition/meta` | `allocate(calibrated_uncertainty, information_values, costs, remaining_budget)` | Actuar/verificar/recordar/simular; consumo máximo |
| `cognition/planner` | `imagine(belief, world_model_view, self_model_view, workspace, goals, modulators, budget)` | Rollouts `SIMULATED`, alternativas, valores y semillas; respeta rutas disponibles bajo intervención |
| `cognition/policy` | `choose(workspace, goals, rollouts, self_model, modulators)` | Distribución y acción elegida; restricciones comprobadas |
| `cognition/learning` | `schedule_updates(observed_transitions, replay_buffer, module_revisions)` | Coordina actualizaciones de propietarios; no mantiene copias duplicadas de sus parámetros |
| `cognition/learning` | `propose_update(training_view, version)` | Extensión: candidato de política/representaciones para activación explícita en frontera de bloque |
| `experiment-lab/environment` | `reset(seed, scenario)` / `transition(env_state, action, noise)` | Estado privado y observación pública separados por tipo |
| `experiment-lab/evaluator` | `score(locked_predictions, private_outcomes, protocol)` | Métricas; acceso prohibido desde la política |
| `language-adapter` | `parse(text, allowed_schema)` / `render(public_trace)` | Propuesta validable de entrada o texto de salida; sin autoridad de persistencia |

Inicialmente no se propone API HTTP pública. Estos puertos internos bastan para CLI, tests y un visor posterior. Un futuro servidor deberá conservar validación, revisiones, idempotencia y separación de permisos.

## 3. Esquema lógico persistente

| Colección/tabla | Clave principal propuesta | Contenido y autoridad |
|---|---|---|
| `runs` | `run_id` | Versiones de código/config/esquema, escenario, semillas, fecha, estado y condición |
| `branches` | `branch_id` | Run padre, snapshot de origen, condición y motivo |
| `events` | `(run_id, sequence)` | Sobre de evento, payload canónico, hash previo/actual; auditoría inmutable |
| `agent_states` | `(run_id, agent_id, revision)` | Estado completo o deltas reconstruibles; última revisión confirmada |
| `environment_states` | `(run_id, tick)` | Mundo oculto y observación pendiente, accesibles solo al simulador/evaluador |
| `episodes` | `(run_id, episode_id)` | Índice cognitivo de episodios y disponibilidad; refs al contenido observado |
| `semantic_assertions` | `(run_id, assertion_id, version)` | Hechos inferidos, confianza, contexto, soportes y contradicciones |
| `goals` | `(run_id, goal_id, revision)` | Agenda y transiciones de metas |
| `model_versions` | `(run_id, model_id, version)` | Parámetros/checksum, datos de entrenamiento y cambios de versión |
| `snapshots` | `snapshot_id` | Manifest y estado completo consistente de una frontera |
| `interventions` | `intervention_id` | Operador, variable, intervalo, valor y rama de origen |
| `predictions` | `prediction_id` | Distribución emitida, objetivo, horizonte y resultado posterior enlazado |
| `metrics` | `(run_id, protocol_id, metric_id, slice_id)` | Valor, unidades, muestra, cálculo y estado de calidad |
| `external_call_records` | `call_id` | Extensión: petición, respuesta validada, versión, coste y estado de resultado |

Es un esquema conceptual: en el MVP varias proyecciones pequeñas pueden almacenarse en JSON validado dentro de SQLite. No se necesitan doce almacenes ni doce servicios.

El evento contiene `schema_version`, `run_id`, `branch_id`, `agent_id`, `event_id`, `sequence`, `tick`, `substep`, `producer`, `event_type`, `caused_by`, `payload`, `provenance`, `config_hash` y `model_version` cuando aplique. `caused_by` identifica dependencias registradas; su presencia no sustituye un experimento causal.

Tipos de evento mínimos: observación recibida, predicción emitida, creencia actualizada, memoria recuperada/codificada, workspace publicado, self-model actualizado, calibración actualizada, afecto actualizado, meta cambiada, presupuesto asignado, acción seleccionada/aplicada, resultado recibido, aprendizaje propuesto/activado y tick confirmado. Una intervención tiene su propio tipo y jamás se disfraza de observación ambiental.

## 4. Atomicidad y fallos

El MVP utiliza un simulador sin efectos externos. En una transacción se guardan los eventos del tick, el nuevo estado del agente, el siguiente estado del entorno, sus estados RNG y la siguiente observación pendiente. Si falla, se descartan también los objetos y RNG mutados en memoria y se recarga la última frontera confirmada.

La transacción de tick se identifica por `(run_id, agent_id, tick)` con restricción única y hash de la entrada. La repetición de una solicitud ya confirmada devuelve su resultado; la misma clave con otra entrada da `IDEMPOTENCY_CONFLICT`. Un segundo intento en curso recibe `IN_PROGRESS`. Las claves duran tanto como el registro de la ejecución.

Errores de contrato: `INVALID_INPUT`, `INVALID_PROVENANCE`, `STALE_REVISION`, `IDEMPOTENCY_CONFLICT`, `IN_PROGRESS`, `BUDGET_EXHAUSTED`, `MODEL_UNAVAILABLE`, `STATE_INCONSISTENT`, `UNSUPPORTED_VERSION`. La política de reserva ante presupuesto agotado se configura antes del ensayo. Una entrada inválida no se convierte silenciosamente en observación neutra.

Integridad, procedencia inválida, versión incompatible o conflicto de idempotencia detienen la corrida y la marcan inválida. `STALE_REVISION` permite recargar y reintentar solo antes de producir efectos; si aparece durante un ensayo monoescritor, se investiga como fallo. `IN_PROGRESS` permite espera/reintento acotados sin nueva acción. `MODEL_UNAVAILABLE` invalida la corrida salvo que exista una condición degradada preregistrada; no cambia la condición en secreto. Agotar presupuesto activa la reserva declarada y sigue siendo un dato evaluable. Fallar una acción en el mundo es un resultado válido, distinto de un fallo del banco. El informe cuenta corridas intentadas, inválidas y evaluables, con motivos.

En cierre de run, frontera de entrenamiento o final de episodio se ejecuta una fase de finalización del feedback pendiente antes de dar por completado ese bloque. Usa el mismo actualizador que recibiría ese resultado al comienzo del siguiente tick, sin nueva acción ni otro coste ambiental. Se registra `last_assimilated_action_id` y cursor de fase, con clave única de asimilación, para que reanudar no aplique dos veces aprendizaje, afecto o consecuencias. Se conserva la nueva observación para la siguiente decisión. El resultado terminal referencia el episodio anterior; el reset físico y el paquete inicial se aplican después de asimilarlo. Un crash antes de completar esta fase deja el bloque pendiente, no completado. Las comparaciones de hashes se hacen en fronteras de fase equivalentes.

SQLite ofrece transacciones ACID; la correcta agrupación del tick, configuración de durabilidad y recuperación de objetos sigue siendo responsabilidad de nuestra implementación. Referencias técnicas: [SQLite transactional](https://www.sqlite.org/transactional.html) y [sqlite3 en Python](https://docs.python.org/3.12/library/sqlite3.html).

Para una futura actuación fuera del simulador, la confirmación de base de datos no abarca la herramienta remota. Se requerirá registrar intención antes del envío, clave idempotente estable, estados `PENDING/CONFIRMED/FAILED/UNKNOWN` y reconciliación de resultados inciertos. No se promete ejecución exactamente una vez mediante un log local.

## 5. Qué contiene un snapshot

Un snapshot incluye estado completo del agente, parámetros aprendidos, versiones, índices cognitivos o material para reconstruirlos, memoria accesible, metas, cola de consolidación, observación pendiente, cursores, presupuesto, configuración y todos los generadores aleatorios. El bundle experimental incluye por separado el mundo privado y sus RNG. Un agente restaurado no recibe ese bundle privado como entrada.

La integridad se verifica con hashes del contenido canónico y del manifiesto. IDs y tiempos de pared que no alteran la dinámica se separan del hash de equivalencia funcional. Los hashes detectan cambios; no son una demostración de fidelidad biológica ni de seguridad criptográfica de todo el entorno.

Se distinguen tres operaciones:

- **Reconstruir:** aplicar eventos registrados hasta una frontera para obtener el estado; no recalcula decisiones.
- **Reejecutar:** volver a ejecutar algoritmos con código/config/entradas/RNG fijados; debe reproducir hashes funcionales en el MVP tabular con runtime fijado.
- **Bifurcar:** restaurar el estado y cambiar explícitamente una condición; se esperan divergencias causales y se conserva el linaje.

Los valores CLI de `replay --mode` son `reconstruct` para reconstruir y `recompute` para reejecutar con entradas/RNG fijados. `fork` es una operación separada. El replay local de una decisión sobre entrada registrada puede ser diagnóstico; si genera acciones diferentes, no se puntúa como trayectoria ambiental válida sin ejecutar el entorno correspondiente.

Un proveedor LLM remoto puede no ser determinista. Guardar respuestas permite reconstrucción y reproducción con respuestas fijadas; no garantiza que una consulta nueva genere lo mismo. Las ramas que cambian la petición no reutilizarán una respuesta almacenada como si fuera una respuesta real del nuevo contexto.

Cada componente dispone de un flujo RNG independiente. El entorno puede usar ruido indexado por episodio/tick/tipo de evento para comparaciones pareadas. Usar la misma semilla global no basta si una intervención consume números aleatorios adicionales. Al divergir acciones, se informa la regla de acoplamiento del entorno; no se fuerza que estados incompatibles tengan idénticas consecuencias.

## 6. Procedencia, permisos y barreras contra contaminación

El agente recibe vistas limitadas por contrato; no se le entrega conexión SQL general, archivos del evaluador o un buscador sobre el event log. La memoria operativa y el registro de auditoría son espacios de acceso diferentes. Los controles de fuga se ensayan usando secretos sintéticos del evaluador ausentes en la vista pública.

El adaptador de lenguaje y documentos externos son fuentes de datos. Su contenido no puede emitir una intervención, cambiar prioridades del investigador, ampliar permisos ni escribir en el self-model sin validación y evidencia. El reporte en primera persona es una forma de presentación; no obtiene privilegios de escritura.

Un hecho semántico derivado de simulaciones conserva procedencia simulada. Un resumen que mezcla observación e inferencia conserva las referencias por afirmación; no basta poner una única etiqueta “observado” al resumen completo. Las ramas contrafactuales y los agentes distintos no comparten biografías por accidente.

## 7. Compatibilidad y observabilidad

Se versionan esquemas, algoritmos, parámetros, entorno, protocolo y transformaciones de datos por separado. Cambios aditivos opcionales conservan lectores existentes; cambiar significado o unidades exige nueva versión y migración explícita. Los snapshots originales se preservan y una migración genera un derivado con linaje.

Cada traza de decisión muestra entradas disponibles, memorias elegidas, términos de saliencia, moduladores, alternativas consideradas, valores estimados, confianza, coste y acción. Se registra solo información realmente accesible al mecanismo. Esto es una traza de cómputo inspeccionable, no una pretensión de revelar una cadena privada de pensamiento de un proveedor lingüístico.

Las métricas y reportes citan IDs de ejecución y versión del protocolo. Sus fallos no se omiten: una ejecución inválida conserva estado, motivo de exclusión preregistrado y logs suficientes para investigar.
