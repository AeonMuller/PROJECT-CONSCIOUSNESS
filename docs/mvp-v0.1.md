# MVP v0.1: persistencia y memoria causal

Implementación autorizada por «Continúa con tu propuesta». Esta entrega materializa el primer alcance recomendado: E0 y una versión acotada de E1. La arquitectura completa de `mvp.md` sigue siendo la hoja de ruta; no se atribuyen a v0.1 self-model, afecto, aprendizaje de asociaciones, imaginación ni metacognición.

## Hipótesis y tarea congeladas antes de ejecutar

El agente observa una pista binaria que indica en qué lado está un recurso, recibe `delay` distractores independientes y elige izquierda/derecha cuando la observación actual ya no contiene la pista. El significado de la pista es una regla suministrada, no aprendida. Una política que retiene el episodio debería acertar; bloquear su lectura debería reducir su éxito al azar. La ventaja sobre historial plano es una pregunta separada y no se espera en esta tarea sencilla.

Cada episodio tiene `delay + 2` acciones: esperar al observar pista, esperar ante cada distractor y elegir. Los objetivos y distractores se sortean independientemente de la política, con generadores separados. La elección consume una acción y termina el episodio; su resultado se registra antes de iniciar el siguiente. Tick global continuo. Los snapshots se guardan después de cada acción y de asimilar el resultado en una única transacción, por lo que no queda feedback pendiente al reiniciar.

El agente recibe únicamente `episode`, `phase` y `value` de una observación pública. En elección, `value` es null. No recibe semilla, estado del mundo, objetivo oculto, conexión SQL o log técnico. El aislamiento es de interfaces dentro de un proceso, no una sandbox frente a código hostil.

## Contratos implementables

Paquete directamente en `project_consciousness/` para ejecutar `python -m project_consciousness` desde el checkout sin instalar dependencias. Python >=3.12, biblioteca estándar y unittest. Este layout simplifica el arranque inicial frente al `src/` propuesto para la arquitectura ampliada.

- `Config(delay=3, capacity=64, agent_mode='episodic', read_mode='intact', write_enabled=True)`; sin semillas ni datos privados.
- Entorno: `initial_environment(config, rng) -> dict`, `observe(env, config) -> dict`, `transition(env, action, config, rng) -> (next_env, outcome)`.
- Agente: `initial_agent() -> dict`, `advance_agent(state, observation, tick, config, rng) -> (next_agent, decision)`; solo esta vista pública.
- `record_result(state, observation, decision, outcome, tick, config) -> next_agent` enlaza acción/consecuencia observada, sin exponer el siguiente mundo.
- Runtime: `Runtime.create(path, seed, config)`, `Runtime.open(path)`, `step(expected_tick=None, fail_at=None)`, `run(ticks)`, `snapshot(tick=None)`, `fork(path, tick, overrides)`, `verify(mode)` y `close()`.
- `path` es directorio con `run.sqlite` y `manifest.json`. `step` retorna una traza con claves `tick`, `observation`, `decision`, `outcome`, `state_hash`. `snapshot` retorna bundle serializable completo.
- Bundle: `tick` (número de acciones confirmadas), `agent`, `environment`, `rng` (`world`, `policy`), `config`. La siguiente acción usa tick actual; se confirma snapshot con tick+1.
- `verify` valida siempre hashes/secuencia; modo `recompute` también recalcula cada transición desde snapshot inicial. Resultado `{'valid': bool, 'ticks': int, 'mode': str, 'errors': [...]}`.

Registros de memoria: `record_id`, `episode`, `tick`, `kind` (`cue`, `distractor`, `outcome`), `value`, `source_kind`, `origin_agent_id`, `source_id`, y payload de resultado cuando corresponda. Identidad propia `agent-0`. Registros imaginados o ajenos nunca acreditan una pista observada propia. No hay caché de pista fuera de `records`. Historial plano usa el mismo límite y observaciones, con lectura lineal independiente.

Decision: `action` (`wait`, `left`, `right`), `probability_left` y `confidence` (null fuera de elección), `memory_ids`, `encoded_ids`, `records_scanned`, `memory_bytes`. La distribución se registra antes de ejecutar el entorno. Sin recuerdo, probabilidad izquierda=0.5 y se sortea con RNG propio. No se entrega la etiqueta de la condición al selector de acción; los modos de lectura solo controlan el acceso a registros.

## Condiciones y evaluación

`intact`, `sham`, `block_read`, `block_write`, `mask_relevant`, `mask_irrelevant`, `history`, `reactive`. Las máscaras se aplican por episodio: la relevante retira pistas, la irrelevante un distractor de tamaño comparable. Los ensayos de procedencia usan registros sintéticos con fuente simulada/ajena mediante tests, no afirman una facultad general de monitorización de realidad. El factorial semántico y trasplantes autobiográficos completos de E1 quedan fuera de v0.1.

E0: 1.000 ticks, interrupciones/restauraciones y reproducción de cada hash; fallos inyectados antes del commit y después del commit; idempotencia por tick. E1: piloto de 20 semillas 100:120, 40 episodios por condición, demora 3 y capacidad 64. El manifiesto captura configuración, protocolo, versión del código, Python y SQLite. Diferencias pareadas y bootstrap por semilla con RNG estadístico separado, IC descriptivo 95%; no confirmación con potencia calculada. Se conserva éxito, Brier, memoria/coste y denominadores. No se reclama superioridad frente al historial plano ni conciencia.

El piloto también compara ramas desde el mismo snapshot anterior a elección, con lectura intacta, sham y máscaras. El escritor se evalúa en corridas desde el inicio; deshabilitarlo después de codificar no elimina recuerdos previos. El informe distingue estos dos diseños.

## Persistencia, fallos y aceptación

SQLite conserva manifiesto con hash propio, snapshot inicial y snapshots comprimidos por tick, junto a traza/evento de transición con hash anterior y hash de contenido. Snapshot contiene ambos RNG y mundo privado; solo runtime/evaluador puede leerlo. Una transacción confirma registro, snapshot y cabecera. Reintentar un tick ya confirmado devuelve su traza sin reaplicar acción; un tick futuro o una revisión fuera de secuencia se rechaza. Crear/fork nunca sobrescribe un directorio existente.

El acceso experimental a snapshots requiere el mismo código y runtime para recomputar o continuar. `reconstruct` sigue disponible para comprobar integridad si las fuentes han cambiado. La traza también mide bytes y cantidad de registros posteriores al resultado, para no subestimar el pico de memoria con muestras previas a la acción.

La exportación de informes es derivada: su fallo no revierte ni duplica una acción confirmada. Los archivos auditables no son firmados contra un atacante; sus hashes detectan corrupción y cambios accidentales, no prueban inviolabilidad.

Aceptación: tests de contratos, procedencia y no filtración; recuperación y replay; forks sin modificar padre; CLI real; piloto E0/E1 generado y revisado. No se requiere que una hipótesis comparativa resulte positiva para que el banco funcione.
