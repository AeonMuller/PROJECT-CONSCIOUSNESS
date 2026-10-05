# PROJECT CONSCIOUSNESS — E0

Protocolo `mvp-0.1-e0-e1-1` · Estado: **passed**.

Este informe evalúa propiedades funcionales en una tarea diseñada por ingeniería. La asociación entre pista y acción está programada; no demuestra aprendizaje de esa asociación ni conciencia.

Código: `d4cb0bc15de5f207efb47b111adc3be555aed31b8195074cf9423587cd5a8655`. Python 3.12.12; SQLite 3.51.1.

Se planificaron 1000 acciones por ejecución; cierres y reaperturas en ticks 1, 333, 500, 999.

| Ejecución | Acciones confirmadas / previstas | Verificación | Estado |
|---|---:|---|---|
| continuous | 1000 / 1000 | True | ok |
| resumed | 1000 / 1000 | True | ok |

Trazas completas iguales: **True**. Ticks divergentes: `[]`.

Continuidad con cierres reales y recomputación. Fallos de commit e idempotencia se cubren en tests del runtime.

## Datos auditables

`manifest.json` conserva protocolo, configuración y versiones. `metrics.csv` conserva denominadores, costes y fallos. `comparisons.csv` conserva contrastes. `summary.json` conserva estado y recuentos. Las bases SQLite de `runs/` conservan las trazas completas y snapshots. En E1, `causal_contrasts.csv` y `branches/` conservan las intervenciones locales. Este informe puede regenerarse a partir de las exportaciones sin ejecutar el agente.
