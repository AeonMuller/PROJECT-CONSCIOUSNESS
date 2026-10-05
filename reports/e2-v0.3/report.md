# PROJECT CONSCIOUSNESS — E2

Protocolo `mvp-0.3-e2-1` · Estado del software: **completed**.

Piloto de ingeniería sobre estimación persistente de capacidades: dos herramientas, costes conocidos y fiabilidad privada que cambia sin aviso. La regla pista→lado permanece suministrada y fija. El feedback separa corrección de la decisión y ejecución; no mide introspección ni conciencia.

Código: `7d226d776474c81e817257022d018c7aa1f83d6cda57cb92a3b6e2ebd5f8279e`. Python 3.12.12; SQLite 3.51.1.

Semillas: 300, 301, 302, 303, 304, 305, 306, 307, 308, 309, 310, 311, 312, 313, 314, 315, 316, 317, 318, 319. Adquisición: 40 episodios; seguimiento: 40. Alpha: 0.2; exploración: 0.1; demora: 1.

Bases completas y verificadas: **140 / 140**. Episodios registrados: **6400 / 6400**; válidos: **6400**. Comprobaciones: **580 / 580**. Ensayos de sonda registrados: **32000 / 32000**; válidos: **32000**.

Updated, frozen, reader_blocked, sham y resumed parten del mismo estado adquirido. Frozen conserva todo el modelo; reader_blocked sigue actualizándolo pero entrega al selector la vista fija [.5, .5]. Sham debe ser funcionalmente idéntico; resumed reproduce trazas exactas tras reinicios. Generic usa los mismos dos parámetros, información, actualización y selector con representación plana: su equivalencia funcional se espera por construcción.

| Condición | Fase | Bases válidas / previstas | Episodios válidos / previstos | Aciertos | Utilidad | Coste | Uso safe | Brier ejecución |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| training | acquisition | 20 / 20 | 800 / 800 | 0.9400 | 0.8829 | 0.0571 | 0.0475 | 0.0789 |
| updated | adaptation | 20 / 20 | 800 / 800 | 0.7113 | 0.5441 | 0.1672 | 0.7812 | 0.1858 |
| frozen | adaptation | 20 / 20 | 800 / 800 | 0.2225 | 0.1648 | 0.0577 | 0.0512 | 0.6802 |
| reader_blocked | adaptation | 20 / 20 | 800 / 800 | 0.2225 | 0.1648 | 0.0577 | 0.0512 | 0.2500 |
| sham | adaptation | 20 / 20 | 800 / 800 | 0.7113 | 0.5441 | 0.1672 | 0.7812 | 0.1858 |
| resumed | adaptation | 20 / 20 | 800 / 800 | 0.7113 | 0.5441 | 0.1672 | 0.7812 | 0.1858 |
| generic | acquisition | 20 / 20 | 800 / 800 | 0.9400 | 0.8829 | 0.0571 | 0.0475 | 0.0789 |
| generic | adaptation | 20 / 20 | 800 / 800 | 0.7113 | 0.5441 | 0.1672 | 0.7812 | 0.1858 |

Solo bases completas, estado ok y recomputación válida contribuyen a estimandos. Fallos y datos parciales permanecen en los CSV, con denominadores previstos; no se imputan resultados. Utilidad = éxito global − coste. Brier interactivo = (predicted_execution_success − execution_success)², con predicción fijada antes del resultado. Esta métrica depende de las herramientas elegidas.

## Contrastes pareados

Primario: updated − frozen en utilidad neta media postcambio. Bootstrap percentil descriptivo al 95%, remuestreando semillas emparejadas con RNG independiente. Una semilla no produce intervalo; sin potencia calculada ni corrección por múltiples contrastes. Un efecto nulo o negativo no invalida el banco.

| Contraste | Métrica | Pares completos / previstos | Diferencia | IC 95% | Estado |
|---|---|---:|---:|---|---|
| primary_adaptation | utility_mean | 20 / 20 | 0.3793 | [0.3319, 0.4298] | ok |
| primary_adaptation | success_rate | 20 / 20 | 0.4888 | [0.4375, 0.5388] | ok |
| primary_adaptation | execution_brier_mean | 20 / 20 | -0.4944 | [-0.5433, -0.4477] | ok |
| primary_adaptation | probe_brier_mean | 20 / 20 | -0.2920 | [-0.3220, -0.2617] | ok |
| reader_intervention | utility_mean | 20 / 20 | -0.3793 | [-0.4279, -0.3325] | ok |
| reader_intervention | success_rate | 20 / 20 | -0.4888 | [-0.5400, -0.4350] | ok |
| reader_intervention | execution_brier_mean | 20 / 20 | 0.0642 | [0.0471, 0.0810] | ok |
| reader_intervention | probe_brier_mean | 20 / 20 | 0.0160 | [-0.0069, 0.0408] | ok |
| generic_control | utility_mean | 20 / 20 | 0.0000 | [0.0000, 0.0000] | ok |
| generic_control | success_rate | 20 / 20 | 0.0000 | [0.0000, 0.0000] | ok |
| generic_control | execution_brier_mean | 20 / 20 | 0.0000 | [0.0000, 0.0000] | ok |
| generic_control | probe_brier_mean | 20 / 20 | 0.0000 | [0.0000, 0.0000] | ok |
| generic_acquisition | utility_mean | 20 / 20 | 0.0000 | [0.0000, 0.0000] | ok |
| generic_acquisition | success_rate | 20 / 20 | 0.0000 | [0.0000, 0.0000] | ok |
| generic_acquisition | execution_brier_mean | 20 / 20 | 0.0000 | [0.0000, 0.0000] | ok |
| generic_acquisition | probe_brier_mean | 20 / 20 | 0.0000 | [0.0000, 0.0000] | ok |
| sham_control | utility_mean | 20 / 20 | 0.0000 | [0.0000, 0.0000] | ok |
| sham_control | success_rate | 20 / 20 | 0.0000 | [0.0000, 0.0000] | ok |
| sham_control | execution_brier_mean | 20 / 20 | 0.0000 | [0.0000, 0.0000] | ok |
| sham_control | probe_brier_mean | 20 / 20 | 0.0000 | [0.0000, 0.0000] | ok |
| restart_control | utility_mean | 20 / 20 | 0.0000 | [0.0000, 0.0000] | ok |
| restart_control | success_rate | 20 / 20 | 0.0000 | [0.0000, 0.0000] | ok |
| restart_control | execution_brier_mean | 20 / 20 | 0.0000 | [0.0000, 0.0000] | ok |
| restart_control | probe_brier_mean | 20 / 20 | 0.0000 | [0.0000, 0.0000] | ok |

## Sondas comunes y calibración

100 resultados Bernoulli por herramienta y fase, generados por un evaluador con RNG independiente y comunes entre condiciones de la misma semilla/fase. Ambas predicciones almacenadas se fijan antes del sorteo; las sondas no actualizan modelo ni RNG del agente. Adquisición se evalúa con el régimen anterior al cambio, incluso cuando el snapshot ya prepara el siguiente episodio. Las repeticiones dentro de semilla están correlacionadas; no son réplicas independientes. Brier de sonda evalúa el modelo almacenado, que puede mejorar en reader_blocked aunque no influya en sus decisiones.

| Condición | Fase | Herramienta | Grupos válidos / previstos | Ensayos válidos / previstos | Predicción media | Frecuencia observada | Brier sonda |
|---|---|---|---:|---:|---:|---:|---:|
| frozen | adaptation | fast | 20 / 20 | 2000 / 2000 | 0.9274 | 0.1955 | 0.6979 |
| frozen | adaptation | safe | 20 / 20 | 2000 / 2000 | 0.5912 | 0.8515 | 0.2096 |
| generic | acquisition | fast | 20 / 20 | 2000 / 2000 | 0.9274 | 0.9490 | 0.0530 |
| generic | acquisition | safe | 20 / 20 | 2000 / 2000 | 0.5912 | 0.8480 | 0.2132 |
| generic | adaptation | fast | 20 / 20 | 2000 / 2000 | 0.2919 | 0.1955 | 0.1766 |
| generic | adaptation | safe | 20 / 20 | 2000 / 2000 | 0.8541 | 0.8515 | 0.1469 |
| reader_blocked | adaptation | fast | 20 / 20 | 2000 / 2000 | 0.1575 | 0.1955 | 0.1773 |
| reader_blocked | adaptation | safe | 20 / 20 | 2000 / 2000 | 0.6900 | 0.8515 | 0.1782 |
| resumed | adaptation | fast | 20 / 20 | 2000 / 2000 | 0.2919 | 0.1955 | 0.1766 |
| resumed | adaptation | safe | 20 / 20 | 2000 / 2000 | 0.8541 | 0.8515 | 0.1469 |
| sham | adaptation | fast | 20 / 20 | 2000 / 2000 | 0.2919 | 0.1955 | 0.1766 |
| sham | adaptation | safe | 20 / 20 | 2000 / 2000 | 0.8541 | 0.8515 | 0.1469 |
| training | acquisition | fast | 20 / 20 | 2000 / 2000 | 0.9274 | 0.9490 | 0.0530 |
| training | acquisition | safe | 20 / 20 | 2000 / 2000 | 0.5912 | 0.8480 | 0.2132 |
| updated | adaptation | fast | 20 / 20 | 2000 / 2000 | 0.2919 | 0.1955 | 0.1766 |
| updated | adaptation | safe | 20 / 20 | 2000 / 2000 | 0.8541 | 0.8515 | 0.1469 |

`calibration.csv` agrupa sondas válidas por condición, fase, herramienta e intervalos de probabilidad [0.0,0.1), …, [0.9,1.0], con conteos, predicción y frecuencia observada. No usa resultados interactivos seleccionados por la política para evaluar la otra herramienta.

## Evolución por bloques

Bloques consecutivos de hasta diez episodios, medias entre semillas completas y verificadas.

| Condición | Fase | Episodios | Semillas válidas / previstas | Utilidad | Aciertos | Uso safe | Brier ejecución |
|---|---|---|---:|---:|---:|---:|---:|
| frozen | adaptation | 1–10 | 20 / 20 | 0.2010 | 0.2600 | 0.0600 | 0.6519 |
| frozen | adaptation | 11–20 | 20 / 20 | 0.1867 | 0.2450 | 0.0550 | 0.6588 |
| frozen | adaptation | 21–30 | 20 / 20 | 0.1197 | 0.1750 | 0.0350 | 0.7122 |
| frozen | adaptation | 31–40 | 20 / 20 | 0.1517 | 0.2100 | 0.0550 | 0.6981 |
| generic | acquisition | 1–10 | 20 / 20 | 0.9040 | 0.9600 | 0.0400 | 0.1039 |
| generic | acquisition | 11–20 | 20 / 20 | 0.8712 | 0.9250 | 0.0250 | 0.0788 |
| generic | acquisition | 21–30 | 20 / 20 | 0.8995 | 0.9600 | 0.0700 | 0.0420 |
| generic | acquisition | 31–40 | 20 / 20 | 0.8568 | 0.9150 | 0.0550 | 0.0910 |
| generic | adaptation | 1–10 | 20 / 20 | 0.3488 | 0.4550 | 0.3750 | 0.3039 |
| generic | adaptation | 11–20 | 20 / 20 | 0.5733 | 0.7500 | 0.8450 | 0.1534 |
| generic | adaptation | 21–30 | 20 / 20 | 0.6133 | 0.8050 | 0.9450 | 0.1553 |
| generic | adaptation | 31–40 | 20 / 20 | 0.6410 | 0.8350 | 0.9600 | 0.1305 |
| reader_blocked | adaptation | 1–10 | 20 / 20 | 0.2010 | 0.2600 | 0.0600 | 0.2500 |
| reader_blocked | adaptation | 11–20 | 20 / 20 | 0.1867 | 0.2450 | 0.0550 | 0.2500 |
| reader_blocked | adaptation | 21–30 | 20 / 20 | 0.1197 | 0.1750 | 0.0350 | 0.2500 |
| reader_blocked | adaptation | 31–40 | 20 / 20 | 0.1517 | 0.2100 | 0.0550 | 0.2500 |
| resumed | adaptation | 1–10 | 20 / 20 | 0.3488 | 0.4550 | 0.3750 | 0.3039 |
| resumed | adaptation | 11–20 | 20 / 20 | 0.5733 | 0.7500 | 0.8450 | 0.1534 |
| resumed | adaptation | 21–30 | 20 / 20 | 0.6133 | 0.8050 | 0.9450 | 0.1553 |
| resumed | adaptation | 31–40 | 20 / 20 | 0.6410 | 0.8350 | 0.9600 | 0.1305 |
| sham | adaptation | 1–10 | 20 / 20 | 0.3488 | 0.4550 | 0.3750 | 0.3039 |
| sham | adaptation | 11–20 | 20 / 20 | 0.5733 | 0.7500 | 0.8450 | 0.1534 |
| sham | adaptation | 21–30 | 20 / 20 | 0.6133 | 0.8050 | 0.9450 | 0.1553 |
| sham | adaptation | 31–40 | 20 / 20 | 0.6410 | 0.8350 | 0.9600 | 0.1305 |
| training | acquisition | 1–10 | 20 / 20 | 0.9040 | 0.9600 | 0.0400 | 0.1039 |
| training | acquisition | 11–20 | 20 / 20 | 0.8712 | 0.9250 | 0.0250 | 0.0788 |
| training | acquisition | 21–30 | 20 / 20 | 0.8995 | 0.9600 | 0.0700 | 0.0420 |
| training | acquisition | 31–40 | 20 / 20 | 0.8568 | 0.9150 | 0.0550 | 0.0910 |
| updated | adaptation | 1–10 | 20 / 20 | 0.3488 | 0.4550 | 0.3750 | 0.3039 |
| updated | adaptation | 11–20 | 20 / 20 | 0.5733 | 0.7500 | 0.8450 | 0.1534 |
| updated | adaptation | 21–30 | 20 / 20 | 0.6133 | 0.8050 | 0.9450 | 0.1553 |
| updated | adaptation | 31–40 | 20 / 20 | 0.6410 | 0.8350 | 0.9600 | 0.1305 |

## Errores y coste de estado

Un error de decisión elige el lado incorrecto; un fallo de ejecución indica que la herramienta no ejecutó la intención. Ambos son observables separadamente en esta tarea. Bytes = serialización, no RAM. records_scanned cuenta recuperación para decidir, no validación, hashing ni SQLite.

| Condición | Fase | Errores de decisión | Fallos de ejecución | Actualizaciones | Pico modelo (bytes) | Pico agente (bytes) | Acciones |
|---|---|---:|---:|---:|---:|---:|---:|
| frozen | adaptation | 0 | 622 | 0 | 221 | 16865 | 2400 |
| generic | acquisition | 0 | 48 | 800 | 210 | 16721 | 2400 |
| generic | adaptation | 0 | 231 | 800 | 212 | 16841 | 2400 |
| reader_blocked | adaptation | 0 | 622 | 800 | 222 | 16858 | 2400 |
| resumed | adaptation | 0 | 231 | 800 | 223 | 16852 | 2400 |
| sham | adaptation | 0 | 231 | 800 | 223 | 16852 | 2400 |
| training | acquisition | 0 | 48 | 800 | 221 | 16732 | 2400 |
| updated | adaptation | 0 | 231 | 800 | 223 | 16852 | 2400 |

## Alcance y datos

El predictor representa dos capacidades operativas en un entorno diseñado con feedback identificable. Su comparación plana tiene la misma capacidad funcional por construcción; llamarlo self-model no demuestra una ventaja ni identidad, autoconciencia, metacognición, generalización o experiencia subjetiva. No se fija un umbral de recuperación después de observar resultados. Estado completed certifica ejecución e invariantes.

`manifest.json` fija protocolo, configuración y código; `episodes.csv` conserva decisiones y predicciones previas; `metrics.csv`, denominadores, costes y errores; `curves.csv`, evolución; `comparisons.csv`, contrastes y exclusiones; `checks.csv`, invariantes; `probes.csv`, cada ensayo común; `probe_metrics.csv`, resúmenes por herramienta; `calibration.csv`, calibración agrupada; `summary.json`, recuentos. Las bases de `runs/` conservan snapshots y trazas recomputables. El informe se regenera sin ejecutar el agente.
