# PROJECT CONSCIOUSNESS — L1

Protocolo `mvp-0.2-l1-1` · Estado del software: **completed**.

Este piloto evalúa aprendizaje de una asociación y adaptación después de una inversión privada. La tarea binaria, la regla de actualización y la política de elección están programadas. No mide conciencia.

Código: `2cd503f48a730e38e810673883df8a73b4570149c6091a16071df1df6dea7f43`. Python 3.12.12; SQLite 3.51.1.

Semillas: 200, 201, 202, 203, 204, 205, 206, 207, 208, 209, 210, 211, 212, 213, 214, 215, 216, 217, 218, 219. Adquisición: 40 episodios; seguimiento: 40. Alpha: 0.25; demora: 3.

Bases completas y verificadas: **120 / 120**. Episodios registrados: **5600 / 5600**; episodios de bases válidas: **5600**. Comprobaciones: **340 / 340**.

Training aprende desde un prior neutral. Adaptive, frozen, sham y resumed parten del mismo snapshot entrenado; frozen desactiva solo la actualización. Untrained_frozen conserva el prior neutral desde el inicio. Resumed cierra y reabre antes de su primera elección y a mitad del seguimiento. Sham y resumed deben reproducir todas las trazas de adaptive.

| Condición | Fase | Bases válidas / previstas | Episodios válidos / previstos | Aciertos válidos | Brier del modelo | Últimos 10, aciertos | Actualizaciones válidas |
|---|---|---:|---:|---:|---:|---:|---:|
| training | acquisition | 20 / 20 | 800 / 800 | 0.9762 | 0.0286 | 1.0000 | 800 |
| adaptive | adaptation | 20 / 20 | 800 / 800 | 0.8500 | 0.1136 | 1.0000 | 800 |
| frozen | adaptation | 20 / 20 | 800 / 800 | 0.0000 | 0.9943 | 0.0000 | 0 |
| sham | adaptation | 20 / 20 | 800 / 800 | 0.8500 | 0.1136 | 1.0000 | 800 |
| resumed | adaptation | 20 / 20 | 800 / 800 | 0.8500 | 0.1136 | 1.0000 | 800 |
| untrained_frozen | acquisition | 20 / 20 | 800 / 800 | 0.5012 | 0.2500 | 0.4900 | 0 |
| untrained_frozen | adaptation | 20 / 20 | 800 / 800 | 0.4788 | 0.2500 | 0.4850 | 0 |

Los estimandos usan únicamente bases completas, con estado ok y recomputación válida. Fallos y datos parciales permanecen en los CSV, pero no constituyen evidencia funcional. Los denominadores previstos permanecen visibles; no se imputan episodios ausentes. Brier usa `(predicted_target_left − etiqueta_left)²`, registrado antes del feedback; probability_left describe selección de acciones y no se usa como predicción del modelo.

## Contrastes pareados

El primario es adaptive − frozen en aciertos postcambio. Bootstrap percentil descriptivo al 95%, remuestreando semillas emparejadas; RNG estadístico independiente. Una sola semilla no produce intervalo. Sin cálculo de potencia ni corrección por múltiples contrastes.

| Contraste | Métrica | Pares completos / previstos | Diferencia | IC 95% | Estado |
|---|---|---:|---:|---|---|
| primary_adaptation | success_rate | 20 / 20 | 0.8500 | [0.8500, 0.8500] | ok |
| primary_adaptation | brier_mean | 20 / 20 | -0.8808 | [-0.8824, -0.8785] | ok |
| acquisition_learning | success_rate | 20 / 20 | 0.4750 | [0.4337, 0.5137] | ok |
| acquisition_learning | brier_mean | 20 / 20 | -0.2214 | [-0.2214, -0.2214] | ok |
| sham_control | success_rate | 20 / 20 | 0.0000 | [0.0000, 0.0000] | ok |
| sham_control | brier_mean | 20 / 20 | 0.0000 | [0.0000, 0.0000] | ok |
| restart_control | success_rate | 20 / 20 | 0.0000 | [0.0000, 0.0000] | ok |
| restart_control | brier_mean | 20 / 20 | 0.0000 | [0.0000, 0.0000] | ok |

## Evolución por bloques

Bloques consecutivos de hasta diez episodios dentro de cada fase; media entre semillas válidas.

| Condición | Fase | Episodios de fase | Semillas válidas / previstas | Aciertos | Brier |
|---|---|---|---:|---:|---:|
| training | acquisition | 1–10 | 20 / 20 | 0.9050 | 0.1038 |
| training | acquisition | 11–20 | 20 / 20 | 1.0000 | 0.0098 |
| training | acquisition | 21–30 | 20 / 20 | 1.0000 | 0.0006 |
| training | acquisition | 31–40 | 20 / 20 | 1.0000 | 0.0001 |
| adaptive | adaptation | 1–10 | 20 / 20 | 0.4000 | 0.4212 |
| adaptive | adaptation | 11–20 | 20 / 20 | 1.0000 | 0.0302 |
| adaptive | adaptation | 21–30 | 20 / 20 | 1.0000 | 0.0026 |
| adaptive | adaptation | 31–40 | 20 / 20 | 1.0000 | 0.0003 |
| frozen | adaptation | 1–10 | 20 / 20 | 0.0000 | 0.9948 |
| frozen | adaptation | 11–20 | 20 / 20 | 0.0000 | 0.9941 |
| frozen | adaptation | 21–30 | 20 / 20 | 0.0000 | 0.9947 |
| frozen | adaptation | 31–40 | 20 / 20 | 0.0000 | 0.9936 |
| untrained_frozen | acquisition | 1–10 | 20 / 20 | 0.5300 | 0.2500 |
| untrained_frozen | acquisition | 11–20 | 20 / 20 | 0.4900 | 0.2500 |
| untrained_frozen | acquisition | 21–30 | 20 / 20 | 0.4950 | 0.2500 |
| untrained_frozen | acquisition | 31–40 | 20 / 20 | 0.4900 | 0.2500 |
| untrained_frozen | adaptation | 1–10 | 20 / 20 | 0.4300 | 0.2500 |
| untrained_frozen | adaptation | 11–20 | 20 / 20 | 0.4850 | 0.2500 |
| untrained_frozen | adaptation | 21–30 | 20 / 20 | 0.5150 | 0.2500 |
| untrained_frozen | adaptation | 31–40 | 20 / 20 | 0.4850 | 0.2500 |

## Recuperación y coste

Recuperación = primer final de una ventana móvil de diez episodios postcambio con al menos ocho aciertos. No alcanzar esa ventana queda censurado al horizonte y no implica estabilidad posterior. No se detiene anticipadamente ninguna ejecución.

| Condición | Recuperadas / válidas | Episodios de recuperación, solo recuperadas | Censuradas | Pico agente (bytes) | Acciones válidas |
|---|---:|---|---:|---:|---:|
| adaptive | 20 / 20 | 14, 14, 14, 14, 14, 14, 14, 14, 14, 14, 14, 14, 16, 14, 14, 14, 14, 15, 14, 14 | 0 | 13710 | 4000 |
| frozen | 0 / 20 | — | 20 | 13717 | 4000 |
| sham | 20 / 20 | 14, 14, 14, 14, 14, 14, 14, 14, 14, 14, 14, 14, 16, 14, 14, 14, 14, 15, 14, 14 | 0 | 13710 | 4000 |
| resumed | 20 / 20 | 14, 14, 14, 14, 14, 14, 14, 14, 14, 14, 14, 14, 16, 14, 14, 14, 14, 15, 14, 14 | 0 | 13710 | 4000 |
| untrained_frozen | 8 / 20 | 20, 32, 24, 31, 36, 29, 10, 39 | 12 | 13547 | 4000 |

## Alcance y datos

Una diferencia favorable demuestra adaptación implementada a esta inversión; no establece transferencia entre tareas, retención de reglas antiguas, aprendizaje abierto, metacognición, self-model ni experiencia subjetiva. La misma estructura y semillas compartidas hacen que los controles no sean réplicas independientes. El estado completed certifica ejecución e invariantes, no exige un resultado científico positivo.

`manifest.json` fija configuración, protocolo, semillas y código. `episodes.csv` conserva resultados y predicciones previas al feedback; `metrics.csv`, costes, denominadores y errores; `curves.csv`, bloques; `comparisons.csv`, contrastes y exclusiones; `checks.csv`, invariantes; `summary.json`, recuentos. Las bases de `runs/` conservan snapshots y trazas recomputables. El informe se regenera a partir de estas exportaciones sin ejecutar el agente.
