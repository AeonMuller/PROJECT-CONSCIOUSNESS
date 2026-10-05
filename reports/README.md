# Resultados experimentales

## v0.3: estimación de capacidades E2

[Informe E2](e2-v0.3/report.md), [episodios](e2-v0.3/episodes.csv), [contrastes](e2-v0.3/comparisons.csv), [sondas comunes](e2-v0.3/probes.csv) y [calibración](e2-v0.3/calibration.csv). Protocolo fijado en [MVP v0.3](../docs/mvp-v0.3.md): 20 semillas 300:320, 40 episodios de adquisición y 40 de seguimiento, alpha 0,2 y exploración 0,1. Fast cambia de fiabilidad 0,95 a 0,20; safe conserva 0,85, con costes respectivos 0,05/0,20.

Se completaron **140/140 bases, 6.400/6.400 episodios, 32.000/32.000 ensayos de sonda y 580/580 comprobaciones**. No hubo fallos ni exclusiones. Todas las bases se cerraron, reabrieron y verificaron por recomputación.

| Condición y fase | Éxitos | Utilidad media | Uso safe | Brier de ejecución |
|---|---:|---:|---:|---:|
| Training, adquisición | 752/800 (94 %) | 0,8829 | 4,75 % | 0,0789 |
| Updated, postcambio | 569/800 (71,125 %) | 0,5441 | 78,125 % | 0,1858 |
| Frozen, postcambio | 178/800 (22,25 %) | 0,1648 | 5,125 % | 0,6802 |
| Reader blocked, postcambio | 178/800 (22,25 %) | 0,1648 | 5,125 % | 0,2500 |
| Generic, postcambio | 569/800 (71,125 %) | 0,5441 | 78,125 % | 0,1858 |

Utilidad = éxito global − coste. El contraste primario updated−frozen fue **0,3793**, con IC bootstrap descriptivo del 95 % **[0,3319; 0,4298]**, remuestreando diferencias por semilla. La diferencia de éxitos fue 48,875 puntos porcentuales, IC [43,75; 53,88]. No se calculó potencia confirmatoria ni se corrigieron múltiples contrastes. El diseño identifica efectos en esta tarea; no prueba generalización.

Updated pasó de elegir safe en 37,5 % de los primeros diez episodios postcambio a 96 % en los últimos diez; su éxito pasó de 45,5 % a 83,5 %. Los bloques están predefinidos y no se seleccionaron umbrales de recuperación después de observar datos. Todos los agentes eligieron correctamente el lado: los fallos registrados fueron de ejecución, bajo una regla pista→lado suministrada y feedback que permite distinguir las dos causas.

Sham y generic reprodujeron las decisiones, observaciones, resultados y predicciones de updated, excluyendo diferencias de configuración/representación e identificadores derivados. Resumed reprodujo trazas exactas. La equivalencia genérica se esperaba por construcción: **no se demostró una ventaja funcional de organizar esos dos parámetros como self-model**.

El lector bloqueado realizó 800 actualizaciones postcambio, pero su selector recibió siempre [0,5; 0,5]. Su modelo almacenado aprendió del nuevo régimen aunque no pudo usarlo para elegir. Frozen mantuvo todos sus parámetros y linaje sin cambios. Sus acciones coincidieron en estas semillas porque ambos siguieron favoreciendo fast; sus estimaciones y predicciones difieren. Esto separa actualización del estado y consumo de ese estado por el decisor.

Las sondas comunes fijaron ambas predicciones antes de generar resultados con un RNG independiente, sin entrenar al agente. Para updated, el Brier final fue 0,1766 en fast y 0,1469 en safe; para frozen, 0,6979 y 0,2096. Reader blocked obtuvo 0,1773 y 0,1782 en su modelo almacenado, aunque el forecast usado al actuar permaneció neutral y su Brier interactivo fue 0,25. No deben confundirse estas dos evaluaciones. Los 32.000 ensayos no son 32.000 historias independientes: las comparaciones se agrupan por las 20 semillas.

**Validación y archivo:** 121 pruebas automatizadas pasaron ([registro](e2-v0.3/tests.log)). Se verificaron por SHA-256 los 291 archivos copiados a `runs/e2-v03-20261005`: 246.493.850 bytes, aproximadamente 246,5 MB. El informe se regeneró byte por byte desde los CSV/JSON. [Certificado de copia y hashes](e2-v0.3/archive-validation.json).

Código del piloto: `7d226d776474c81e817257022d018c7aa1f83d6cda57cb92a3b6e2ebd5f8279e`. Python 3.12.12; SQLite 3.51.1. Se ejecutó desde una copia temporal de fuentes idéntica byte por byte para evitar lecturas repetidas del disco del workspace; se conservó el mismo intérprete y todos los controles de integridad. Las fuentes permanecieron congeladas durante el piloto y no se ajustaron parámetros según sus resultados. Los manifiestos mantienen las rutas originales como procedencia; las rutas relativas de cada base se resuelven desde el archivo completo.

El [motor v0.3 archivado](../releases/project-consciousness-v0.3.zip) conserva fuentes, pruebas y configuraciones; su [manifiesto](../releases/project-consciousness-v0.3.json) registra SHA-256 y fingerprint. Se verificó cada archivo del ZIP contra su origen. Las bases SQLite completas permanecen en `runs/`; el ZIP es el motor para reproducirlas, no contiene esas bases.

Para repetir con la versión del motor correspondiente y una carpeta nueva:

```powershell
python -m project_consciousness experiment --protocol configs/e2-capabilities.toml --out runs/e2-new
python -m project_consciousness report --experiment reports/e2-v0.3
```

E2 representa dos eficacias operativas y su uso causal. No incorpora aprendizaje simultáneo de asociaciones y capacidades, contextos nuevos, incertidumbre sobre parámetros, metacontrol o identidad. Los resultados son empíricos sobre este artefacto de ingeniería; no establecen introspección ni experiencia subjetiva. Los fallos manejados por el laboratorio conservan evidencia legible y denominadores; corrupción estructural arbitraria puede impedir la agregación.

## v0.2: aprendizaje y reversión L1

[Informe L1](l1-v0.2/report.md), [datos por episodio](l1-v0.2/episodes.csv) y [contrastes](l1-v0.2/comparisons.csv). Protocolo congelado en [MVP v0.2](../docs/mvp-v0.2.md): 20 semillas 200:220, 40 episodios de adquisición y 40 después de invertir la regla, alpha 0,25. Se completaron 120/120 bases, 5.600/5.600 episodios válidos y 340/340 comprobaciones. Sin fallos ni semillas excluidas.

| Condición y fase | Aciertos | Brier predictivo | Aciertos últimos 10 |
|---|---:|---:|---:|
| Aprendizaje, adquisición | 781/800 (97,625 %) | 0,02857 | 100 % |
| Prior neutral congelado, adquisición | 401/800 (50,125 %) | 0,25 | 49 % |
| Adaptativo, tras inversión | 680/800 (85 %) | 0,11357 | 100 % |
| Modelo entrenado congelado, tras inversión | 0/800 (0 %) | 0,99432 | 0 % |
| Sham, tras inversión | 680/800 (85 %) | 0,11357 | 100 % |
| Con reinicios, tras inversión | 680/800 (85 %) | 0,11357 | 100 % |
| Prior neutral congelado, tras inversión | 383/800 (47,875 %) | 0,25 | 48,5 % |

Cada columna «últimos 10» agrega diez episodios por semilla en esa fase (200 en total). El Brier usa la predicción del modelo anterior al resultado, no la probabilidad de elegir una acción.

La diferencia de adquisición frente al prior congelado fue 47,5 puntos porcentuales, IC bootstrap descriptivo 95 % [43,375; 51,375]. El contraste primario adaptativo−congelado postcambio fue 85 puntos. Su intervalo [85; 85] tiene anchura cero porque las 20 historias produjeron exactamente seis errores adaptativos y cuarenta errores congelados en este diseño; **no representa ausencia de incertidumbre sobre otras tareas, parámetros o poblaciones de mundos**.

El agente adaptativo alcanzó el criterio fijado de recuperación (ventana móvil de diez episodios con al menos ocho aciertos) en 14 episodios en 18 semillas, 15 en una y 16 en una. No se seleccionaron ejecuciones por rendimiento ni se detuvieron al recuperarse. Las 20 ramas congeladas no alcanzaron ese criterio. El 0 % del modelo congelado se debe a que la tarea invierte completamente una regla ya aprendida; no describe el rendimiento general de todo agente sin aprendizaje.

Sham y resumed reproducen las trazas completas de adaptive, no solo su tasa de aciertos. Las ramas parten del mismo agente, mundo y RNG; frozen cambia exclusivamente el permiso de actualizar parámetros, que permanecen idénticos mientras sigue escribiendo memoria. El mismo historial y las mismas semillas compartidas permiten comparación pareada, pero no convierten las ramas en muestras independientes.

Interpretación: la actualización desde feedback público aprende la asociación específica y permite adaptarse a esta inversión; el modelo aprendido se conserva entre procesos y modifica decisiones posteriores. La estructura binaria, la actualización y el criterio de elección siguen programados. No se probaron retención A→B→A, transferencia, optimalidad, self-model, metacognición ni experiencia subjetiva.

83 pruebas automatizadas pasaron (37 nuevas y las 46 anteriores). El informe L1 se regeneró byte por byte desde las exportaciones. Los 248 archivos completos del piloto se copiaron desde almacenamiento temporal a `runs/l1-v02-20261003` y se comprobaron por SHA-256 (290.485.451 bytes, aproximadamente 290 MB). Los manifiestos conservan las rutas originales de creación como metadatos históricos; las rutas relativas de corridas se resuelven desde el directorio experimental archivado.

Código del piloto: `2cd503f48a730e38e810673883df8a73b4570149c6091a16071df1df6dea7f43`. Python 3.12.12; SQLite 3.51.1. Las fuentes permanecieron congeladas durante las pruebas finales y el piloto. No se modificaron umbrales ni parámetros a partir de sus resultados.

Para un piloto nuevo desde la raíz, usando una carpeta de salida nueva:

```powershell
python -m project_consciousness experiment --protocol configs/l1-learning.toml --out runs/l1-new
python -m project_consciousness report --experiment reports/l1-v0.2
```

La segunda instrucción solo regenera el informe archivado. `records_scanned_total` mide recuperación para decisiones, no todos los costes de validación, hashes y SQLite. Los bytes son tamaños serializados, no una medición de RAM. Este experimento no compara eficiencia computacional general.

## v0.1: persistencia y memoria causal (histórico)

Estos informes evalúan persistencia y uso causal de memoria en una tarea binaria de pista demorada. La regla pista–respuesta está programada y no existe entrenamiento de asociaciones. Los resultados se interpretan como comprobaciones del artefacto, no como evidencia de experiencia subjetiva.

### E0: persistencia y reproducción

[Informe E0](e0-v0.1/report.md): dos ejecuciones de 1.000 acciones, una continua y otra cerrada/reabierta en ticks 1, 333, 500 y 999. Ambas verificadas por recomputación; cero diferencias de trazas.

### E1: efecto causal de la memoria

[Informe E1](e1-v0.1/report.md): 20 semillas, 40 episodios por condición, 8 condiciones; 160 ejecuciones y 6.400 episodios completados y verificados. Además, 100 ramas desde snapshots de la primera decisión, con mundo, memoria y RNG inicialmente iguales. Ninguna corrida ni rama falló.

| Condición | Aciertos |
|---|---:|
| Memoria intacta | 800/800 (100 %) |
| Intervención simulada / sham | 800/800 (100 %) |
| Lectura bloqueada | 399/800 (49,875 %) |
| Escritura bloqueada desde el inicio | 399/800 (49,875 %) |
| Recuerdo relevante oculto | 399/800 (49,875 %) |
| Recuerdo irrelevante oculto | 800/800 (100 %) |
| Historial plano | 800/800 (100 %) |
| Política reactiva sin memoria | 399/800 (49,875 %) |

La diferencia intacta menos lectura bloqueada fue 50,125 puntos porcentuales; intervalo bootstrap descriptivo 95 % por semilla: aproximadamente [46,75; 53,63] puntos. El historial plano igualó tanto rendimiento como registros examinados en este banco; no se demostró una ventaja de la organización episódica.

En las ramas de lectura bloqueada y máscara relevante, la distancia de variación total entre políticas fue 0,5 en las 20 semillas y la acción cambió en 10/20. Sham y máscara irrelevante conservaron distribución y acción. Esto comprueba una ruta de dependencia implementada, sin atribuirle generalización, aprendizaje de asociaciones o experiencia subjetiva.

Los resultados iguales entre controles que recurren a la misma política aleatoria no son réplicas independientes: comparten semillas y ruido exógeno para el contraste pareado. Los intervalos no equivalen a una confirmación con potencia establecida ni corrigen múltiples comparaciones.

### Validación de software y archivos

46 pruebas automáticas pasaron con `python -m unittest discover -s tests -v`. Incluyen una terminación abrupta en un subproceso antes del commit, reintento después del commit, alteración de manifiesto/trazas, máscaras, procedencia y exclusión de resultados inválidos del informe.

Ambos informes fueron regenerados desde sus exportaciones y conservaron exactamente su hash de contenido. Los 526 archivos del piloto E1 se copiaron desde almacenamiento temporal a `runs/e1-v01-20261003` y se comprobaron por SHA-256. El archivo completo E1 ocupa aproximadamente 300 MB; sus snapshots completos permanecen fuera de Git.

### Reproducción

Desde la raíz, con Python 3.12.12 y SQLite 3.51.1 para reproducir exactamente esta ejecución:

Usar el [motor v0.1 archivado](../releases/project-consciousness-v0.1.zip), extraído en una carpeta separada, para recomputar o continuar las bases v0.1 existentes. Se verificó el SHA-256 del archivo y se reprodujeron sus 1.000 ticks E0 con ese motor, sin divergencias. El motor v0.2 comprueba la integridad histórica mediante reconstruct; crear nuevos E0/E1 con v0.2 produce manifiestos nuevos, aunque conserve la tarea de regla fija.

```text
python -m unittest discover -s tests -v
python -m project_consciousness experiment --protocol configs/e0-persistence.toml --out runs/e0-new
python -m project_consciousness experiment --protocol configs/e1-memory.toml --out runs/e1-new
```

Las carpetas de salida deben ser nuevas. El runtime registra código, intérprete, SQLite y configuración; cualquier nueva versión produce una ejecución distinta. Los hashes son controles de integridad, no firmas contra manipulación deliberada.

Las exportaciones pequeñas se conservan en `reports/` para revisión y control de versiones. Los snapshots y trazas completos permanecen en `runs/`, excluidos de Git por tamaño. Una copia archivada conserva las rutas originales de creación como metadatos históricos. El informe puede regenerarse desde manifest, summary y CSV sin recomputar el agente.

Archivos completos de esta entrega: `runs/e0-v01-20261003` y `runs/e1-v01-20261003`. Las rutas relativas de cada corrida en los CSV se resuelven desde su carpeta experimental correspondiente. Para regenerar únicamente el informe archivado: `python -m project_consciousness report --experiment reports/e1-v0.1`.
