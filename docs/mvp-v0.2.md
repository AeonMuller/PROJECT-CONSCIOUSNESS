# MVP v0.2: aprendizaje persistente y reversión

Estado: alcance aceptado por «Continúa con esa implementación». Hipótesis de ingeniería, no una prueba de conciencia. Amplía cognition, runtime y experiment-lab del mapa existente. Protocolo L1, subconjunto acotado de E5/E8; E2 sigue reservado al self-model.

## Objetivo y límites

Aprender una asociación binaria desconocida a partir de consecuencias, conservar los parámetros entre procesos y adaptarse tras una inversión privada. Mantener la tarea de pista demorada y la política fija v0.1 como opción predeterminada. No añadir self-model, metacognición, afecto, LLM, aprendizaje de pesos externos ni afirmaciones de transferencia/retención entre tareas.

La estructura binaria (exactamente una acción correcta), la regla de actualización y el criterio de elección se programan. La correspondencia particular pista–acción se aprende. Congelar parámetros no congela observaciones ni escritura de memoria.

## Contratos

- `Config` conserva campos anteriores y añade `policy_mode='fixed'|'learned'`, `learning_enabled: bool=True`, `learning_rate: float=0.25`. Solo configuración pública; no contiene regla ni calendario.
- `TaskConfig(kind='delayed-cue-v1'|'reversal-v1', reversal_episode=40, initial_mapping=None|0|1)` pertenece al entorno/evaluador. `None` sortea regla inicial en creación; no llega al agente. El manifiesto y snapshot privados permiten auditarla.
- `Runtime.create(path, seed, config, task=None)`. `initial_environment(config, rng, task=None)` conserva el contrato v0.1. En v0.2 el mundo privado incluye pista, regla inicial y episodio de inversión. Observación pública sin cambios: `episode`, `phase`, `value`.
- Episodio empieza en cero. En `reversal_episode` y posteriores el objetivo es pista XOR regla_inicial XOR 1; antes es pista XOR regla_inicial. El número y contenido de observaciones no dependen de la acción. El agente no recibe aviso ni config de tarea.
- `initial_agent(config=None)` conserva `{'records': []}` en política fija; aprendiente añade `learner`. El modelo contiene dos estimaciones de `P(target=left|cue)`, iniciales 0.5, contador de actualizaciones y linaje de última evidencia. No conserva una pista de trabajo fuera de records.
- `advance_agent` recupera una pista propia observada del episodio actual; el decisor aprende/actúa solo con esa evidencia. Política greedy: elige izquierda si q>0.5, derecha si q<0.5, y sortea un empate. Sin pista usa creencia y política 0.5.
- Decisión aprendiente añade `predicted_target_left`, `predicted_success`, `model_version`, `model_hash`, `learning_evidence` (pista/ID efectivamente leídos, o null). `probability_left` sigue siendo probabilidad de SELECCIÓN, distinta de la predicción q.
- `record_result` actualiza solo tras una elección terminal, con éxito booleano y evidencia válida enlazada a esa decisión: y=1 si (izquierda y éxito) o (derecha y fallo), de lo contrario 0; q[c] ← q[c]+alpha*(y-q[c]). Con lector bloqueado, fuente imaginada/ajena o pista ausente no aprende. No se infiere el objetivo de metadatos privados. Actualización idempotente por tick/evidencia.
- Estado aprendido serializable en snapshot y en la misma transacción que acción/resultado. Traza incluye hash/versión y bytes de modelo posteriores, además de bytes totales del agente. Congelar deja invariante TODO learner.
- Los reintentos públicos pasan por `Runtime.step(expected_tick)`, que devuelve la transacción confirmada para todas las condiciones. `record_result` es un paso interno sobre el estado anterior al feedback. El learner protege además su última actualización real; esto no promete que repetir directamente `record_result` sobre un estado posterior congelado siga funcionando si el resultado ya expulsó la pista requerida.
- `fork` permite además `learning_enabled`; no permite cambiar tarea, regla, tasa de aprendizaje ni tipo de política. Las ramas mantienen mundo, registros, parámetros y RNG, salvo override declarado.
- CLI `fork --tick` pasa a ser opcional: si se omite usa el último snapshot confirmado, igual que `Runtime.fork`.

## Protocolo L1 congelado antes de medir

20 semillas 200:220, 40 episodios de adquisición, inversión al episodio 40 y 40 de seguimiento, demora 3, capacidad 64, alpha 0.25. Orden de condiciones fijo y declarado; mundo/política con streams separados, costes deterministas sin depender de latencia. Bootstrap pareado por semilla, 2.000 réplicas y semilla estadística 20261003. Piloto descriptivo, sin afirmación confirmatoria ni potencia calculada.

Por semilla:

1. Entrenar `training` durante 40 episodios desde prior neutral sin seleccionar runs por desempeño.
2. Cerrar/reabrir, y bifurcar el mismo snapshot al principio del episodio 40 en `adaptive`, `frozen`, `sham` y `resumed`. Frozen solo deshabilita learning_enabled; sham pasa override explícito True. Las primeras decisiones deben coincidir; divergencia posterior puede deberse al feedback aprendido.
3. Ejecutar 40 episodios por rama. Resumed cierra/reabre tras cuatro ticks (antes de elegir) y a mitad del seguimiento; sus trazas completas deben coincidir con adaptive.
4. Crear `untrained_frozen` desde misma semilla y mundo, prior neutral y aprendizaje apagado desde el inicio, durante 80 episodios. Compara adquisición, no sustituye al control frozen entrenado.
5. Verificar recompute de las seis bases por semilla, igualdad de estados iniciales salvo config, congelación exacta, igualdad sham/resumed y secuencia pública exógena compartida. No excluir historias por bajo rendimiento.

Primario: diferencia adaptive−frozen de aciertos durante los 40 episodios posteriores al cambio. Secundarios: training−untrained_frozen durante adquisición, Brier de `predicted_target_left` anterior al feedback, aciertos/Brier por bloques de 10 y últimos 10, número de actualizaciones, almacenamiento y pasos. Recuperación: primer final de ventana móvil de 10 episodios postcambio con al menos 8 aciertos, o censurado al horizonte; no implica estabilidad ni generalización.

No usar Brier de probability_left para evaluar el modelo. El evaluador deriva la etiqueta binaria de acción/éxito y nunca retroalimenta métricas ni etiquetas de régimen al agente. Datos incompletos/fallidos se conservan pero no entran en estimandos funcionales; denominadores planificados y exclusiones visibles.

`records_scanned_total` suma registros examinados por la recuperación que produce decisiones. No incluye validación de contratos, serialización, hashes ni trabajo de SQLite y no representa un presupuesto completo de cómputo. Los tamaños en bytes describen estado serializado; el archivo de auditoría/snapshots se conserva aparte y no es memoria accesible al agente. L1 no establece una ventaja de eficiencia computacional.

## Archivos, comandos y estilo

Módulo nuevo `learning.py`, laboratorio `learning_experiment.py`, pruebas `test_learning*.py`; integración en módulos existentes. Python >=3.12, stdlib, funciones sobre copias y `LabError` para entradas inválidas. Sin cambios de esquema SQL. Config plana v0.1 sigue aceptada; nueva config de run con secciones `[agent]` y `[task]`. Protocolo con `[experiment]`, `[agent]` y `[task]`.

```powershell
python -m unittest discover -s tests -v
python -m project_consciousness run --config configs/mvp-v02.toml --seed 17 --ticks 200 --out runs/learning-demo
python -m project_consciousness resume --run runs/learning-demo --ticks 200
python -m project_consciousness replay --run runs/learning-demo --mode recompute --verify
python -m project_consciousness experiment --protocol configs/l1-learning.toml --seeds 200:203 --out runs/learning-pilot
python -m project_consciousness report --experiment runs/learning-pilot
```

## Aceptación, plan y compatibilidad

Orden: contratos/entorno → learner/política → persistencia/CLI → laboratorio → revisión independiente → suite y piloto → informe/guía. Trabajar en paralelo solo sobre archivos asignados distintos.

Pruebas: neutralidad ante ambos mappings; inversión exacta sin señal pública; independencia del mundo; cambio de parámetros solo desde feedback válido y posterior a predicción; congelación exacta; ausencia de lectura alternativa; restart/replay/atomicidad/idempotencia aprendientes; invariantes de ramas; exclusión de fallos; CLI y reporte regenerable. E0/E1 originales rechazan policy aprendiente; no redefinir silenciosamente sus métricas. Pasar pruebas demuestra funcionamiento del banco; obtener un efecto positivo no es condición para esconder un resultado nulo.

Siempre: preservar datos anteriores, registrar hashes y fallos, comprobar tests/regresiones, documentar límites. Consultar solo para ampliar fuera de esta autorización (servicios externos, publicación, cambios destructivos). Nunca: usar datos ocultos en el agente, retocar protocolo tras resultados sin declarar exploración, atribuir experiencia subjetiva.

El fingerprint impide continuar/recomputar runs de otro código: los datos v0.1 siguen íntegros y permiten reconstruct. `releases/project-consciousness-v0.1.zip` conserva fuentes, tests y configs anteriores junto a SHA256; extraer en carpeta separada y usar el mismo Python/SQLite para recomputarlos. Nuevas ejecuciones v0.2 usan directorios nuevos. No se migra ni sobreescribe una historia científica.
