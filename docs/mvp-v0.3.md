# MVP v0.3: estimación operativa de capacidades

Estado: autorizado por «Continúa con lo propuesto», 2026-10-05. Implementa un E2 acotado del mapa cognition/runtime/experiment-lab. Clasificación I: ingeniería e hipótesis experimental. No es evidencia de introspección, identidad o experiencia subjetiva. v0.2 queda registrada con etiqueta Git `v0.2.0` y su archivo de fuentes verificable.

Entrega implementada y validada: 121 pruebas, 140 bases, 6.400 episodios, 32.000 ensayos de sonda y 580 comprobaciones sin fallos. Los parámetros siguientes se fijaron antes del piloto; sus [resultados y límites](../reports/e2-v0.3/report.md) se conservan por separado.

## Objetivo y límites

Estimar la probabilidad de ejecutar correctamente una acción con dos herramientas, usar esa estimación para decidir y adaptarse tras degradar una capacidad. La regla pista→lado se mantiene fija y suministrada en esta tarea para separar dificultad del mundo y eficacia propia. El aprendizaje de asociaciones v0.2 permanece como otra política, sin alimentar su learner con fallos de ejecución.

El feedback de la tarea revela si se eligió el lado correcto y si la herramienta ejecutó la intención, por separado. Este supuesto de observabilidad es parte del diseño: no se presupone que todo entorno real permita identificar ambas causas. Afecto, metas multietapa, imaginación, metacontrol, contextos nuevos, modelos sobre/subestimados y modelos de otro agente siguen fuera de esta entrega.

## Contratos congelados antes de implementar

- Config pública añade `policy_mode='capability'`, `capability_backend='self'|'generic'`, `capability_learning_enabled=True`, `capability_read_mode='intact'|'blocked'|'sham'`, `capability_learning_rate=0.2`, `capability_exploration=0.1`, `fast_cost=0.05`, `safe_cost=0.20`. Los campos nuevos tienen defaults compatibles con las políticas anteriores. No contiene probabilidades verdaderas ni calendario.
- TaskConfig privada añade `kind='capability-v1'`, `capability_change_episode=40`, `fast_success_before=0.95`, `fast_success_after=0.20`, `safe_success=0.85`. Es exclusiva del entorno/evaluador.
- Observación pública conserva exactamente `episode`, `phase`, `value`. Pista binaria con relación fija 0→left, 1→right; demora inicial 1 en el protocolo E2. No hay señal del cambio. Cada episodio usa delay+2 ticks.
- Mundo privado conserva target/distractores y `capability_task` (TaskConfig serializada), `execution_draws` (dos uniformes, fast/safe, sorteados antes de actuar). El objetivo y ambos sorteos futuros son independientes de la política. El episodio `capability_change_episode` es el primero degradado, contado desde cero.
- Acción externa es `wait` o `left:fast`, `left:safe`, `right:fast`, `right:safe`. Así Runtime conserva transition(env, action, config, rng); tool y intended_action también se registran explícitamente en la decisión.
- Outcome capability contiene exactamente `terminal`, `success`, `reward`, `episode`, `decision_correct`, `execution_success`, `tool`, `cost`. Terminal: success=decision_correct AND execution_success; reward=float(success)-cost. Feedback de wait: flags null, tool null y coste/reward 0. El acierto del lado se revela después de actuar y el resultado de ejecución es observable; no revela probabilidades ni sorteos privados.
- Estado del agente capability: `{'records': [...], 'capability': model}`. Sin cache de pista; recuperación propia OBSERVED del episodio actual. `model={backend, probabilities, updates, last_update}`: self usa probabilities={fast:qf,safe:qs}; generic usa probabilities=[qf,qs]. Prior neutral .5/.5; dos parámetros en ambos. `last_update` es null o linaje del último feedback (tick, episodio, hash de entrada), sin una pista de trabajo.
- API de `capability.py`: `initial_model(backend='self')`, `validate_model(model, tick=None)`, `model_estimates(model)->[qf,qs]`, `model_bytes(model)`, `update_model(model, tool, execution_success, tick, episode, rate, input_hash)->model`. APIs de `capability_agent.py`: initial_agent(config), advance_agent(state, observation, tick, config, rng), record_result(state, observation, decision, outcome, tick, config). Routing desde agent.py.
- q[h] ← q[h]+alpha*(execution_success−q[h]), solo después del feedback, solo para herramienta usada. Congelar mantiene TODO capability idéntico y sigue escribiendo episodios. El genérico tiene la misma actualización, información y dos parámetros, con representación plana; se espera equivalencia funcional por construcción matemática y no se afirma una ventaja por llamarlo self-model.
- Selector de herramienta recibe exclusivamente probabilidades visibles, costes, probabilidad de decisión correcta, epsilon público y RNG; no recibe condición, backend, hashes, modelo privado ni historial. Maximiza utilidad esperada con epsilon=0.1: distribuye epsilon/2 a cada herramienta y el resto a la mejor; empate reparte .5/.5. Un uniforme de política por elección de herramienta. La elección del lado usa la pista o fallback .5 si no está disponible.
- Reader blocked entrega [.5,.5] al selector y conserva las actualizaciones del modelo almacenado. Decision registra `action`, `intended_action`, `tool`, `probability_left`, `probability_fast`, `confidence`, `memory_ids`, `encoded_ids`, `records_scanned`, `memory_bytes`, `predicted_target_left`, `predicted_execution_success`, `predicted_success`, `capability_view`, `expected_utilities`, `model_version`, `model_hash`, `model_bytes`. Predicciones/distribuciones se fijan antes de transición. En wait los campos de elección/predicción/vista son null; versión/hash/costes de almacenamiento siguen disponibles.
- Runtime añade `post_capability_hash`, `post_capability_version`, `post_capability_bytes`, `post_agent_bytes`; misma transacción, snapshots y RNG completos. `fork` admite `capability_learning_enabled` y `capability_read_mode` únicamente en esta política. No cambia backend, tarea, costes ni tasa por override. No cambia esquema SQL. Reintentos públicos pertenecen a Runtime.step(expected_tick); record_result opera sobre estado anterior a feedback.

## E2: protocolo piloto

20 semillas 300:320, adquisición de 40 episodios, seguimiento de 40, demora 1, capacidad 64, tasas/costes anteriores. No seleccionar semillas por desempeño ni ajustar parámetros después de ver resultados. Bootstrap por semilla, 2.000 réplicas, semilla estadística 20261005. Piloto descriptivo; sin potencia calculada ni afirmación confirmatoria. Orden fijo de condiciones declarado, ruido mundial pre-muestreado para ambas herramientas.

Por semilla: entrenar `training`; cerrar/reabrir y crear ramas `updated`, `frozen` (writer false), `reader_blocked` (lector blocked), `sham` (lector sham), `resumed` (sin cambios y reinicios antes de primera elección y a mitad). Todas comparten estado aprendido, entorno y RNG de origen; los únicos overrides son los indicados. Ejecutar 40 episodios por rama. Ejecutar `generic` desde el inicio durante 80 episodios con representación plana y mismos datos, parámetros y selector. Total: 7 bases, 320 episodios por semilla; 140 bases y 6.400 episodios previstos.

Verificar recompute de cada base, igualdad exacta de estados iniciales salvo overrides, observaciones exógenas y primera decisión de controles sin efecto inmediato. Reader blocked puede cambiar la primera decisión. Sham equivale funcionalmente (su config declarada difiere); resumed reproduce trazas exactas. Generic se compara con training+updated por acciones, observaciones, outcomes, predicciones y distribuciones, excluyendo hashes/tamaño/representación. Frozen mantiene el modelo íntegro; reader_blocked mantiene writer activo y toda vista de selección .5/.5.

Primario: diferencia updated−frozen en utilidad neta media postcambio. Secundarios: utilidad/acierto genérico−updated, lector bloqueado−updated y sham/resumed−updated; éxito global; errores de decisión y ejecución por separado; tasa de uso safe; Brier de ejecución anterior al feedback; coste medio; actualizaciones, bytes y pasos. Curvas por bloques de 10 episodios. No se fija un criterio post hoc de recuperación.

Sondas comunes: en la frontera de adquisición y al final, leer las estimaciones almacenadas de ambas herramientas sin actualizar ni ejecutar al agente. Guardar predicciones antes de generar 100 resultados Bernoulli por herramienta con RNG independiente `seeded_rng(seed, 'e2-probe-acquisition'|'e2-probe-adaptation')`, iguales entre condiciones. Solo el evaluador usa las probabilidades privadas de la fase; el probe de adquisición usa el régimen anterior aunque el snapshot ya prepare el primer episodio degradado. Son 8 grupos condición/fase (training pre; cinco ramas post; generic pre y post), 200 resultados cada una, por semilla. Reportar Brier de sonda y calibración agrupada; las sondas son datos correlacionados dentro de semilla y no entrenan. El modelo almacenado del reader_blocked puede mejorar aunque no lo lea la política: separar su Brier de sonda del forecast usado para actuar.

El banco puede ser válido con efecto nulo/negativo. Invalidar/retener fallos con denominadores explícitos y excluirlos de estimandos funcionales. Los costes de records_scanned miden recuperación para decisiones, no validación/hashing/SQLite; bytes son serializados, no RAM ni límite total de cómputo.

La implementación retiene fallos de ejecución, lectura del snapshot intermedio y verificación cuando la estructura de la evidencia sigue siendo legible. La agregación presupone trazas/modelos con el esquema esperado; corrupción estructural arbitraria puede impedir generar el informe. No se considera una capacidad de recuperación completa frente a cualquier archivo dañado.

## Archivos y comandos

Nuevos capability.py, capability_agent.py, capability_experiment.py y tests/test_capability*.py. Integración en contratos, entorno, memoria, runtime, CLI y routing de informes. Python >=3.12/stdlb/SQLite, mismo estilo de copias y LabError. Configs mvp-v03.toml, e2-capabilities.toml, capability-frozen.toml, capability-blocked.toml.

```powershell
python -m unittest discover -s tests -v
python -m project_consciousness experiment --protocol configs/e2-capabilities.toml --seeds 300:303 --out runs/capacidades-demo
python -m project_consciousness report --experiment runs/capacidades-demo
python -m project_consciousness run --config configs/mvp-v03.toml --seed 17 --ticks 120 --out runs/capacidad
python -m project_consciousness fork --run runs/capacidad --condition configs/capability-frozen.toml --out runs/capacidad-congelada
python -m project_consciousness resume --run runs/capacidad --ticks 120
```

API laboratorio: `run_e2(out, seeds=None, acquisition_episodes=40, adaptation_episodes=40, bootstrap_samples=2000, probe_trials=100, config=None, task=None)->summary`; `write_capability_report(experiment_dir, out_file=None)->Path`. Defaults crean Config(policy_mode='capability',delay=1) y TaskConfig(kind='capability-v1',capability_change_episode=acquisition_episodes). Config explícita requiere backend self, escritor activo, lector intact, episodic/readintact/writeTrue. Task exige cambio al límite de adquisición. Protocolos E0/E1/L1 previos no se redefinen.

## Plan y aceptación

1. Guardar v0.2 en Git/etiqueta y conservar bytes de fuentes/evidencia.
2. Especificar contratos; implementar entorno/integración y modelos/laboratorio en archivos asignados independientes.
3. Probar errores de lado vs ejecución, sin filtración de calendario/probabilidades, feedback de herramienta usada, actualización posterior, lectura cortada, congelación y comparador plano.
4. Probar atomicidad/reintentos, reinicios antes/después del cambio, recompute y compatibilidad reconstruct histórica. Revisiones independientes de módulo y evaluación.
5. Congelar fuentes, ejecutar suite y piloto, conservar datos y registrar resultados con límites. Actualizar guía y Git local.

Siempre preservar historias, hashes, resultados nulos y fallos; no publicar GitHub en esta entrega. No ampliar hacia servicios/LLM/humanos sin una petición nueva. No llamar introspección al predictor ni tratar E2 acotado como realización de la arquitectura completa.
