# MVP propuesto: laboratorio cognitivo persistente

2026-10-03 · propuesta de arquitectura ampliada. Ya existe una primera entrega acotada de E0/E1, descrita en [MVP v0.1](mvp-v0.1.md), y aprendizaje/reversión L1 en [v0.2](mvp-v0.2.md); este documento conserva el alcance futuro más amplio.

## 1. Resultado concreto

Un programa local que permita ejecutar un agente en un pequeño mundo parcialmente observable, detenerlo, restaurarlo, bifurcar su estado y comparar condiciones. Producirá una base SQLite, trazas de decisiones y un informe por experimento. El primer resultado útil es una comparación reproducible de mecanismos, incluso cuando la hipótesis resulte nula.

Se propone Python 3.12 como versión mínima de diseño, con la versión exacta del intérprete y SQLite fijada al implementar. Núcleo con biblioteca estándar (`dataclasses`, `sqlite3`, `tomllib`, generadores aleatorios explícitos); herramientas estadísticas adicionales se justificarán cuando se implemente el análisis. SQLite no necesita un servidor separado: [documentación oficial](https://docs.python.org/3.12/library/sqlite3.html). El MVP está pensado para CPU, sin una dependencia de GPU o de servicios de modelos. Coste y rendimiento se medirán en un piloto; aún no hay benchmark.

## 2. Mundo mínimo

Un grafo público de cinco lugares: base `C`, cruce `J`, ruta segura `S`, atajo `R` y objetivo `G`. Conexiones bidireccionales: `C–J`, `J–S`, `S–G`, `J–R`, `R–G`. El agente debe recoger una muestra en `G` y devolverla a `C`, administrando energía y decidiendo cuándo inspeccionar.

| Elemento | Regla inicial de ingeniería, ajustable solo en piloto |
|---|---|
| Energía | Capacidad 20; movimiento normal cuesta 1, aristas que tocan `S` cuestan 2 |
| Atajo | `R–G` puede estar bloqueado durante un episodio; intento bloqueado cuesta 2 y conserva posición |
| Observación | Posición, vecinos, energía, inventario y resultado de la acción anterior; sin acceso al mapa de bloqueos |
| Pista | En `C` se presenta una señal de contexto una vez; su asociación con bloqueo se aprende por experiencia |
| Inspección | Desde `J`, devuelve indicio de bloqueo con fiabilidad 0.85 y coste de energía 1 |
| Capacidad propia | `collect` en `G` tiene probabilidad de éxito dependiente de una condición oculta del actuador; ensayo inicial 0.9, tras cambio 0.5 |
| Diagnóstico | `probe` en `C` o `G` prueba el mismo actuador en un soporte público sin bloqueo externo; cuesta 1 y devuelve éxito/fallo |
| Recarga | `recharge` solo en `C`, repone hasta 20 y consume un tick |
| Espera | `wait` consume un tick, energía 0; sirve para demoras controladas, no da recompensa |
| Final | Muestra devuelta, energía agotada o máximo 100 ticks; fallo si agota límite sin entrega |
| Recompensa | +10 por entrega, −0.1 por tick; el evaluador informa por separado éxito, energía, inspecciones y fallos |

Acciones legales: `move(neighbor)`, `inspect`, `probe`, `recharge`, `collect`, `wait`. La lista pública permite validar formato y posición, sin revelar si una acción fallará por estado oculto. `collect` cuesta 1, no se repite con inventario lleno. La entrega se registra automáticamente al volver a `C` con la muestra. Si una acción cuesta más energía que la disponible, el entorno informa `insufficient_energy`, deja energía en 0 y termina el episodio; la política dispone del coste público para evitarlo.

El tick global de una ejecución nunca se reinicia. Cada episodio de tarea tiene `environment_episode_id` y `episode_step`, con límite de 100 pasos. Al finalizar se registra el resultado antes del reset, se reinician posición/energía/inventario y se entrega un nuevo paquete inicial; la memoria y parámetros del agente persisten. La siguiente entrada diferencia resultado terminal anterior y observación inicial nueva. El `EpisodeId` de memoria identifica una experiencia registrada y referencia el episodio de tarea correspondiente. Así un run de 500 ticks puede abarcar varios episodios y un fork en tick 200 es alcanzable.

El generador mantiene separados los flujos aleatorios de contexto/bloqueo, sensor, actuador y distracciones. Los valores anteriores son elecciones **I**, no constantes psicológicas. El manifiesto declara probabilidades de contexto y cambios; esos campos son privados del evaluador cuando no constituyen conocimiento público de la tarea.

El banco incluye tres variantes, construidas de forma incremental:

1. **Pista demorada:** la asociación contexto–ruta se aprende en episodios previos; una pista anterior al periodo de distracción permite decidir después. Se borran explícitamente buffers inmediatos de la misma manera en todas las condiciones comparadas, para aislar memoria episódica. Se enumeran además creencias, workspace, cachés y resúmenes que pudieran conservar la pista. Si el dato sigue disponible por otra ruta, se reporta como redundancia y no como efecto específico de lectura episódica.
2. **Cambio de capacidad:** cambia el actuador manteniendo las contingencias del mundo. El agente puede adaptar predicciones, diagnóstico y plan; la tabla de capacidad propia no conoce el cambio directamente.
3. **Contingencias A→B→C→A:** familias con reglas distinguibles mediante contextos observables permiten medir retención de tareas anteriores. Se contrabalancean identidades de contextos y orden entre réplicas. Cambiar una regla sin señal de contexto será otra condición de adaptación a deriva; sus errores no se atribuirán automáticamente a olvido.

La topología pública puede codificarse en el planificador; las probabilidades de bloqueo, observación y éxito se aprenden. El modelo del agente y el simulador usan implementaciones separadas. El oráculo con estado completo es solo una cota superior del laboratorio.

La factorización evita duplicar estimadores: el modelo del mundo aprende contingencias externas y sensoriales; el self-model es propietario de la eficacia y costes propios del actuador. El predictor compuesto consume ambos por interfaz. En las ablaciones se cortan todas las lecturas del factor intervenido, incluyendo cachés de rollouts. El diagnóstico solo informa éxito/fallo observado; no entrega la probabilidad generadora verdadera.

## 3. Implementación mínima por capacidad

| Capacidad | Realización propuesta en MVP | Extensión posterior |
|---|---|---|
| Persistencia | Log de eventos, snapshot y transacción por tick en SQLite | Otros almacenes, múltiples procesos |
| Memoria autobiográfica | Episodios propios, índice temporal, recuperación por contexto y fuente | Narrativa lingüística y memoria multimodal |
| Memoria semántica | Contadores condicionales derivados de episodios; contradicciones/contexto | Grafos y representaciones aprendidas |
| Mundo y predicción | Distribuciones tabulares sobre bloqueo/contexto/observaciones | Modelos neuronales y generalización de representaciones |
| Self-model | Modelo Beta–Bernoulli de éxito del actuador por contexto; costes propios | Esquema de atención, cuerpo y compromisos complejos |
| Afecto | Tres variables acotadas con actualización declarada y consumidores fijos | Aprender modulaciones y comparar formulaciones |
| Workspace | Competencia de contenidos con `k=4`, caducidad y trazas | Broadcast entre varios especialistas heterogéneos |
| Metacontrol | Calibración de éxito; regla de valor de información frente a coste | Política de asignación de cómputo aprendida |
| Agencia | Meta de entrega con fases alcanzar G/recoger/volver C; recarga y diagnóstico, con transiciones explícitas | Submetas aprendidas y negociación social |
| Imaginación | Rollouts del modelo aprendido, horizonte 4, máximo 32 trayectorias por tick y heurística pública de progreso | Búsqueda más profunda y abstracciones temporales |
| Aprendizaje continuo | Actualización online de tablas, buffer de replay y versiones | Aprendizaje de política/representaciones y regularización |
| Reporte | Tablas estructuradas de decisiones y métricas | Adaptador de lenguaje con evaluación de fidelidad |

Los parámetros se fijan tras un piloto excluido del análisis confirmatorio. Un smoothing o ventana de olvido para adaptación reemplaza la acumulación ilimitada solo si queda especificado en la versión del protocolo. Un posterior Beta acumulado sin descuento podría ser lento tras un cambio; esa lentitud es medible y se compara contra un modelo por contexto o con descuento predefinido.

Una entrega completa necesita al menos 7 acciones desde `C`; por tanto, horizonte 4 necesita una valoración de progreso explícita. Se propone `Φ = -d_restante`, donde `d_restante` es el número mínimo de acciones pendientes alcanzar G/recoger/volver C usando posición, inventario y topología públicos. El planner añade `η·E[Φ_final-Φ_inicial]` a su utilidad de horizonte, con `η=1` inicial fijado en piloto. No recibe bloqueos reales ni probabilidades privadas para calcular esta heurística. La recompensa externa y la evaluación conservan la regla +10/−0.1; los baselines comparables reciben la misma heurística disponible y se ensaya su ablación por separado. Esto evita atribuir a memoria o afecto una ventaja que procede solo de ayudar al planner a alcanzar una recompensa lejana.

Configuración común inicial: 20 semillas de desarrollo y otras 20 de piloto, hasta 4 candidatos por tick, horizonte 4 y máximo 32 trayectorias totales (128 transiciones imaginadas). Memoria episódica accesible: hasta 256 registros de 4 KiB cada uno; hasta 1 MiB adicional de parámetros/estado aprendido. El log de auditoría no cuenta como memoria cognitiva y es inaccesible al agente. Se contabilizan también índices y cachés en un presupuesto declarado; si el piloto exige más, todas las condiciones comparables se versionan con el nuevo límite. El tamaño confirmatorio se determina después del piloto, no se da por suficiente este número de semillas.

Las pruebas diagnósticas E3 y E9 añaden tareas binarias de verificación y competencia entre señales mediante los mismos contratos del laboratorio. E4 usa una variante con rutas de valor esperado igualado. No se presume que un único grafo base discrimine todas las hipótesis; cada variante tiene generador y manifiesto propios.

Para E3, el evaluador sortea un bit objetivo equilibrado y una pista que coincide con él con probabilidad 0.55, 0.70 o 0.90 según clase de dificultad. El agente observa pista y clase, pero aprende su fiabilidad. Puede elegir `guess_0`, `guess_1` o una única `verify`, que cuesta 0.2 y entrega otra pista independiente de fiabilidad 0.98; acertar da 1, fallar 0. Las probabilidades exactas generadoras permanecen privadas. Se registra confianza antes y después de verificar como predicciones distintas. Cada miniensayo tiene como máximo tres pasos y se reporta separado de éxito de entrega; `meta-d'` solo se aplica a este diseño binario si sus supuestos y muestra lo permiten.

Para E9 se crean señales de ruta y de capacidad con consumidores distintos, se limita temporalmente el workspace a un contenido y se varía qué señal es relevante para cada decisión. Un manifiesto especifica orden, duración y rutas locales conservadas; un control requiere solo un consumidor. Reducir capacidad afecta a todas las condiciones comparadas por igual salvo cuando la capacidad sea precisamente la intervención. Estas extensiones son fixtures del laboratorio, no nuevas observaciones privilegiadas para el agente base.

En este mundo pequeño, un estimador tabular con creencias suficientes puede resolver la tarea sin toda la arquitectura. Ese baseline es obligatorio: si iguala o mejora al agente completo, se revisará qué complejidad funcional añade cada módulo. Para probar memoria episódica se añaden tareas donde una pista específica no está redundada en un estado suficiente accesible.

## 4. Entregables de una ejecución futura

- `run.sqlite`: eventos, estado, memoria y versiones; tablas privadas separadas del acceso del agente.
- `manifest.json`: código, configuración, protocolo, condición, semillas, presupuesto, entorno y hashes.
- `decisions.jsonl`: decisiones previas a consecuencias, alternativas, fuentes y costes.
- `metrics.csv`: métricas por episodio y réplica; ninguna columna llamada “grado de conciencia”.
- `report.md`: hipótesis, contraste, tamaño de efecto, incertidumbre, fallos y limitaciones.

Estructura de código propuesta, todavía inexistente: `src/project_consciousness/runtime/`, `memory/`, `cognition/`, `experiment_lab/`, `language_adapter/`; `tests/` para contratos y recuperación; `configs/` para escenarios; `runs/` para artefactos excluidos del control de versiones salvo fixtures sintéticos pequeños.

## 5. Interfaz de ejecución prevista

Los siguientes comandos ilustran la CLI del alcance ampliado. **Las configuraciones de rutas y afecto todavía no existen.** Para los comandos comprobados de v0.1 y sus archivos reales, usar el [README](../README.md). La CLI básica de run/resume/replay/fork/experiment/report ya existe para la tarea de pista demorada.

```text
python -m project_consciousness run --config configs/mvp.toml --seed 17 --ticks 500 --out runs/pilot-17
python -m project_consciousness resume --run runs/pilot-17 --ticks 500
python -m project_consciousness replay --run runs/pilot-17 --mode recompute --verify
python -m project_consciousness fork --run runs/pilot-17 --tick 200 --condition configs/affect-neutral.toml --out runs/fork-neutral-17
python -m project_consciousness experiment --protocol configs/e1-memory.toml --seeds 100:120 --out runs/e1
python -m project_consciousness report --experiment runs/e1 --out runs/e1/report.md
python -m unittest discover -s tests -v
```

`--seeds 100:120` significa rango semiabierto de 20 semillas. `--ticks` en `resume` son ticks globales adicionales. Una bifurcación solo acepta ticks confirmados con snapshot o reconstrucción verificable. Los nombres de archivos de configuración son ilustrativos y deberán coincidir con los protocolos implementados.

## 6. Orden de construcción y puertas de verificación

| Hito | Cambio entregable | Verificación necesaria |
|---|---|---|
| M0 | Contratos, entorno mínimo y baseline reactivo | Transiciones, costes y observaciones sin fuga; fixtures sintéticos |
| M1 | Runtime persistente y reproducción | Ensayo de interrupción antes/después de commit; continuación igual a ejecución ininterrumpida |
| M2 | Memoria y modelo del mundo | Recuperación con procedencia, predicciones emitidas a tiempo, aprendizaje sin estado oculto |
| M3 | Self-model, afecto, workspace, metas y metacontrol | Cada variable cambia su consumidor declarado en pruebas de intervención; resultado no depende del texto |
| M4 | Rollouts y actualización continua | Imaginaciones aisladas, coste contabilizado, adaptación y retención medibles |
| M5 | Laboratorio y primer informe | Condiciones pareadas, sham, baselines, resultados nulos preservados y reporte reproducible |
| M6 opcional | Adaptador lingüístico | Paridad de tarea sin narración, evidencia citada y reporte fiel; análisis separado |

Dentro de M0 se pueden diseñar fixtures del laboratorio sobre los puertos de `runtime`; el paquete completo `experiment-lab` se integra después de las dependencias del mapa. Cada hito se implementará en unidades pequeñas con aceptación propia. No se estima duración sin acordar recursos y medir el primer piloto.

## 7. Criterios para llamar ejecutable al MVP

1. El núcleo realiza 1.000 ticks sin depender de un LLM; reiniciar en fronteras seleccionadas conserva la misma secuencia funcional bajo versión y semillas fijadas.
2. Todas las decisiones tienen predicción previa, fuentes y coste; todos los recuerdos accesibles tienen procedencia.
3. Una intervención sobre memoria, self-model, afecto o metacontrol alcanza una ruta de decisión observable en un fixture sensible a esa variable. También existe un fixture negativo donde no debería afectar.
4. El evaluador puede ejecutar condiciones con y sin cada mecanismo y con intervención simulada (`sham`), sin filtraciones de etiquetas privadas.
5. Los rollouts no incrementan contadores de experiencias observadas y las llamadas de reporte no cambian la siguiente acción al restaurar el mismo estado.
6. El informe distingue errores del software de ausencia de beneficio experimental, registra fallos y presenta incertidumbre.

Los umbrales experimentales se definen en [experimentos](experiments.md). Un resultado nulo no impide que el MVP sea correcto; impide afirmar el beneficio que la hipótesis predecía.

## 8. Decisiones abiertas que no bloquean el diseño

Las primeras decisiones de producto pendientes son presupuesto de tiempo/cómputo, prioridad de tareas y formato de visualización. Un LLM, su proveedor, una interfaz web y el entrenamiento neural se eligen únicamente si aportan una hipótesis comprobable. La primera ejecución puede mantenerse completamente local y tabular.

Gateway, comparación colectiva y experiencias multisensoriales se investigan en extensiones con protocolos propios. El alcance inicial cubre mecanismos funcionales mínimos de todas las capacidades solicitadas, con límites explícitos sobre lo que una versión tabular puede representar.
