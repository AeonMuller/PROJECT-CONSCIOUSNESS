# Cambios

## 0.2.0 — 2026-10-03

- Política aprendiente opcional: dos probabilidades condicionadas a pista, actualizadas por experiencia y persistidas en SQLite.
- Tarea de asociación desconocida con inversión privada; configuración del mundo separada de la vista del agente.
- Predicciones del modelo previas al resultado, diferenciadas de probabilidades de selección; versiones, hashes, procedencia y costes del modelo registrados.
- Congelación de parámetros mediante fork, manteniendo observaciones y memoria; `fork --tick` opcional para usar el estado más reciente.
- Protocolo L1 con adquisición, adaptación, control congelado entrenado, control neutral, sham y reinicios; datos por episodio, curvas por bloques, bootstrap pareado e informe regenerable.
- 83 pruebas automatizadas, incluidas las 46 de v0.1. E0/E1 conservan la tarea/política fija y rechazan configuraciones de aprendizaje para evitar cambios silenciosos de interpretación.
- Copia verificable del motor v0.1. Sus datos no se migran: reconstruct funciona con el motor actual y resume/recompute exigen el código registrado.

Límites: estructura binaria y algoritmo de actualización suministrados; no demuestra generalización, retención entre tareas, self-model, metacognición ni conciencia. Protocolo y límites completos en [MVP v0.2](docs/mvp-v0.2.md).

## 0.1.0 — 2026-10-03

- Arquitectura conceptual, contratos, fundamentos y análisis crítico de Gateway.
- Tarea de pista demorada, memoria episódica con procedencia, política fija y controles de lectura/escritura.
- Runtime transaccional con snapshots completos, replay y ramas.
- Experimentos E0/E1 y 46 pruebas automatizadas; [resultados históricos](reports/README.md).
