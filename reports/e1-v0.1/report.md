# PROJECT CONSCIOUSNESS — E1

Protocolo `mvp-0.1-e0-e1-1` · Estado: **completed**.

Este informe evalúa propiedades funcionales en una tarea diseñada por ingeniería. La asociación entre pista y acción está programada; no demuestra aprendizaje de esa asociación ni conciencia.

Código: `d4cb0bc15de5f207efb47b111adc3be555aed31b8195074cf9423587cd5a8655`. Python 3.12.12; SQLite 3.51.1.

Semillas: 100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114, 115, 116, 117, 118, 119. Episodios por semilla y condición: 40. Demora: 3; capacidad: 64 registros.

Todas las trayectorias cierran y reabren el almacenamiento antes de la primera elección. Comparten presupuesto de acciones y límite de registros. El control reactivo carece deliberadamente de historia; los costes reales pueden diferir. El límite se expresa en registros, no en bytes; se mide el consumo en bytes.

Trayectorias completas: **160 / 160**; episodios completados: **6400 / 6400**.

| Condición | Corridas válidas / previstas | Éxitos verificados / episodios previstos | Brier de episodios verificados | Registros examinados, corridas válidas | Memoria pico válida (bytes) |
|---|---:|---:|---:|---:|---:|
| intact | 20 / 20 | 800 / 800 | 0.0000 | 47140 | 13467 |
| sham | 20 / 20 | 800 / 800 | 0.0000 | 47140 | 13467 |
| block_read | 20 / 20 | 399 / 800 | 0.2500 | 0 | 13473 |
| block_write | 20 / 20 | 399 / 800 | 0.2500 | 0 | 2 |
| mask_relevant | 20 / 20 | 399 / 800 | 0.2500 | 46340 | 13473 |
| mask_irrelevant | 20 / 20 | 800 / 800 | 0.0000 | 46340 | 13467 |
| history | 20 / 20 | 800 / 800 | 0.0000 | 47140 | 13467 |
| reactive | 20 / 20 | 399 / 800 | 0.2500 | 0 | 2 |

Brier binario usa un componente: media de `(probability_left − etiqueta_left)²`, registrada antes del resultado. La tabla agrega éxitos, Brier y costes exclusivamente de corridas con estado ok y verificación válida. Los éxitos conservan el denominador planificado de todas las corridas; este cociente es un recuento conservador, no una estimación de rendimiento cuando hay fallos. Los episodios ausentes no se imputan para Brier. Las corridas fallidas o no verificadas no constituyen evidencia funcional: sus datos brutos parciales se conservan en metrics.csv.

## Diferencias pareadas en éxito

Diferencia = condición − intacta. Bootstrap percentil por semilla; IC descriptivo del 95%. Las semillas son unidades de remuestreo, no los episodios. El RNG estadístico es independiente y fijo. Con una sola semilla no se calcula intervalo. Los pares incompletos se identifican explícitamente y su exclusión limita la interpretación.

| Condición | Pares completos / previstos | Diferencia | IC 95% | Estado |
|---|---:|---:|---|---|
| sham | 20 / 20 | 0.0000 | [0.0000, 0.0000] | ok |
| block_read | 20 / 20 | -0.5012 | [-0.5363, -0.4675] | ok |
| block_write | 20 / 20 | -0.5012 | [-0.5363, -0.4675] | ok |
| mask_relevant | 20 / 20 | -0.5012 | [-0.5350, -0.4662] | ok |
| mask_irrelevant | 20 / 20 | 0.0000 | [0.0000, 0.0000] | ok |
| history | 20 / 20 | 0.0000 | [0.0000, 0.0000] | ok |
| reactive | 20 / 20 | -0.5012 | [-0.5363, -0.4688] | ok |

## Intervenciones desde el mismo snapshot

Cada semilla aporta una situación anterior a su primera elección. Las ramas mantienen mundo, memoria y RNG; solo cambia el acceso de lectura. Se comprueba igualdad de estado previo y observación. La variación total entre políticas binarias es `abs(p_left_rama − p_left_intacta)`.

| Lectura | Ramas válidas / previstas | TV media | Acciones distintas / ramas válidas |
|---|---:|---:|---:|
| intact | 20 / 20 | 0.0000 | 0 / 20 |
| sham | 20 / 20 | 0.0000 | 0 / 20 |
| block_read | 20 / 20 | 0.5000 | 10 / 20 |
| mask_relevant | 20 / 20 | 0.5000 | 10 / 20 |
| mask_irrelevant | 20 / 20 | 0.0000 | 0 / 20 |

El escritor bloqueado se evalúa desde el comienzo de trayectorias completas. Desactivarlo después de codificar la pista no borraría un recuerdo existente.

Se espera paridad entre memoria episódica e historial plano en esta tarea. Una igualdad de rendimiento no establece equivalencia general; diferencias de coste deben revisarse por separado. Un efecto de las máscaras demuestra una dependencia implementada del lector, no memoria autobiográfica humana, utilidad general ni experiencia subjetiva. Esta tarea no evalúa aprendizaje continuo, self-model ni afecto.

Los intervalos son descriptivos de este piloto, sin cálculo de potencia ni corrección por múltiples comparaciones. Un resultado nulo sigue siendo un resultado válido; se requieren otras familias de tareas y reglas aprendidas para estudiar generalización.

## Datos auditables

`manifest.json` conserva protocolo, configuración y versiones. `metrics.csv` conserva denominadores, costes y fallos. `comparisons.csv` conserva contrastes. `summary.json` conserva estado y recuentos. Las bases SQLite de `runs/` conservan las trazas completas y snapshots. En E1, `causal_contrasts.csv` y `branches/` conservan las intervenciones locales. Este informe puede regenerarse a partir de las exportaciones sin ejecutar el agente.
