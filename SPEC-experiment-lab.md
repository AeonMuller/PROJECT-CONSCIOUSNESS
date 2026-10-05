# Especificación: experiment-lab

Estado: contrato ampliado; E0 y una versión acotada de E1 implementados en [v0.1](docs/mvp-v0.1.md), aprendizaje/reversión L1 en [v0.2](docs/mvp-v0.2.md) · 2026-10-03 · ID: `experiment-lab` · depende de `runtime`, `memory`, `cognition`.

## Objetivo

Producir contrastes causales reproducibles, con controles de recursos y métricas independientes del relato del agente. Mantener protocolos, condiciones, entorno, evaluación y análisis fuera de los mecanismos evaluados.

## Contratos y propiedad

Implementa puertos de entorno definidos en `runtime`; posee mundo oculto, verdad de evaluación, intervenciones, condiciones y métricas. Consume snapshots y trazas de solo lectura. `score(locked_predictions, private_outcomes, protocol) -> Metrics`; el agente no invoca este puerto.

El diseño íntegro está en [experimentos](docs/experiments.md); el entorno concreto y CLI futura en [MVP](docs/mvp.md). Modificar una condición crea una rama y un manifiesto nuevo. No se mezclan resultados de versiones de protocolo sin declarar un análisis nuevo.

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
