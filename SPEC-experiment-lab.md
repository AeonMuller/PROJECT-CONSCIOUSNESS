# Especificación: experiment-lab

Estado: contrato ampliado; E0 y una versión acotada de E1 implementados en [v0.1](docs/mvp-v0.1.md), aprendizaje/reversión L1 en [v0.2](docs/mvp-v0.2.md) y un E2 operacional de eficacia de herramientas en [v0.3](docs/mvp-v0.3.md) · 2026-10-05 · ID: `experiment-lab` · depende de `runtime`, `memory`, `cognition`.

## Objetivo

Producir contrastes causales reproducibles, con controles de recursos y métricas independientes del relato del agente. Mantener protocolos, condiciones, entorno, evaluación y análisis fuera de los mecanismos evaluados.

## Contratos y propiedad

Implementa puertos de entorno definidos en `runtime`; posee mundo oculto, verdad de evaluación, intervenciones, condiciones y métricas. Consume snapshots y trazas de solo lectura. `score(locked_predictions, private_outcomes, protocol) -> Metrics`; el agente no invoca este puerto.

El diseño íntegro está en [experimentos](docs/experiments.md); el entorno concreto y CLI futura en [MVP](docs/mvp.md). Modificar una condición crea una rama y un manifiesto nuevo. No se mezclan resultados de versiones de protocolo sin declarar un análisis nuevo.

## E2 ejecutable de v0.3

`project_consciousness/capability_experiment.py` y `configs/e2-capabilities.toml` definen un piloto de 20 semillas `300:320`, 40 episodios de adquisición y 40 de seguimiento, fijado antes de evaluar. La herramienta fast pasa de eficacia 0.95 a 0.20 en el episodio 40; safe conserva 0.85. El agente conoce los costes 0.05/0.20 y recibe feedback separado de decisión/ejecución, pero no conoce eficacias verdaderas ni calendario. Los sorteos de ambas herramientas se preparan antes de decidir, con RNG del mundo independiente de la política.

Desde el mismo estado aprendido se bifurcan `updated`, `frozen`, `reader_blocked`, `sham` y `resumed`. Un `generic` plano se entrena desde el inicio y se compara con la trayectoria training+updated: su equivalencia matemática es un control, no una hipótesis de superioridad. Se verifican reproducción, origen de ramas, invariantes de congelación/bloqueo y controles sin efecto. El estimando primario es utilidad media postcambio updated−frozen; el bootstrap pareado utiliza la semilla como unidad, con 2.000 réplicas y semilla estadística 20261005.

El Brier durante actuación puntúa forecasts anteriores al feedback de la herramienta elegida. Para evitar comparar solo herramientas visitadas distintas, las sondas comunes fijan las dos predicciones almacenadas y generan 100 resultados por herramienta con RNG independiente, compartidos entre condiciones de la misma fase y semilla. Las sondas no entrenan; el Brier del modelo almacenado bloqueado se distingue del forecast neutral que efectivamente lee su política. Se conserva el número previsto de bases/episodios, además de válidos y fallidos; resultados nulos o negativos son admisibles. Los informes de ejecución se publican por separado y no se anticipan aquí.

## Estructura y convenciones futuras

Paquete `src/project_consciousness/experiment_lab/`, tests `tests/experiment_lab/`, configuraciones `configs/`. Nombres de condiciones explícitos, rangos de semillas semiabiertos, unidades y tamaños muestrales presentes en cada métrica. No omitir ejecuciones fallidas.

## Aceptación y pruebas

- E0 comprueba restauración y frontera de información antes de interpretar efectos.
- Una condición sham ejecuta la infraestructura de intervención sin cambiar el mecanismo.
- Baselines reciben información y presupuesto documentados; se mide cómputo utilizado además del permitido.
- Ninguna salida previa al resultado contiene etiquetas futuras o privadas.
- El informe puede regenerarse a partir del manifiesto y métricas, identifica unidad independiente y muestra incertidumbre.
- Resultados nulos y adversos se conservan; no se seleccionan solo semillas favorables.

## Límites

Siempre fijar hipótesis, métrica primaria, exclusiones y stopping rule antes de evaluación confirmatoria. Revisar antes de convertir un piloto en afirmación confirmatoria o de incluir participantes humanos. Nunca agregar métricas funcionales en un número presentado como conciencia.
