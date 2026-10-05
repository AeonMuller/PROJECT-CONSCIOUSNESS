# Plan de implementación

## v0.2: aprendizaje persistente

Alcance autorizado en [MVP v0.2](../docs/mvp-v0.2.md). Tareas y verificación detalladas en [v0.2](v0.2.md).

1. Conservar motor v0.1 y fijar TaskConfig privado, contrato de learner y protocolo L1.
2. Implementar entorno de reversión y pruebas de ausencia de señal pública.
3. Implementar en paralelo learner/política y laboratorio L1 sobre los contratos acordados.
4. Integrar parámetros en snapshots, ramas y CLI; probar fallos, reinicios y reintentos.
5. Revisar interfaces y experimento independientemente; pasar suite completa antes de congelar fuentes.
6. Ejecutar piloto de 20 semillas con fuentes congeladas; conservar datos/denominadores e informe reproducible.
7. Actualizar guía de VS Code, resultados y límites. No publicar ni alterar historias previas.

Riesgos adicionales: filtración del calendario, confundir creencia y política, comparar agentes con estados iniciales distintos, congelar memoria por error, filtrar fallos del informe y llamar generalización a adaptación dentro de la misma tarea.

## v0.1 (completado)

1. Congelar el alcance E0/E1, contratos y tarea de pista demorada.
2. Implementar en paralelo entorno público/privado y memoria/agente con tests de invariantes.
3. Implementar runtime SQLite: atomicidad, snapshots, reanudación, forks y verificación.
4. Integrar laboratorio, CLI, manifiestos y exportación reproducible de informes.
5. Ejecutar tests, E0 de 1.000 ticks y piloto E1; revisar fallos y resultados.
6. Actualizar documentación para distinguir capacidades implementadas y propuestas.

Riesgos prioritarios: fuga del objetivo al agente, duplicación por reintento, RNG acoplado a política, memorias con procedencia falsa, comparación con recursos distintos y presentar cableado como descubrimiento sobre conciencia.
