# Cambios

## Capa de presencia 0.5.0 — 2026-10-05

- Archivo conversacional persistente, búsqueda, nombre de presentación y conclusiones revisables con fuentes. Los datos personales viven fuera de la skill y de Git.
- Recuperación de recuerdos históricos mediante un puente al motor v0.4, cuyo código, versión y esquema permanecen intactos.
- Integración opcional de cinco hooks de Codex; instalación con respaldo, sin conceder confianza automáticamente.
- Coordinador de actividad durante inactividad: reservas, límites diarios, presupuesto, pausa, regreso humano y conciliación de efectos inciertos.
- Investigación elegida por el núcleo, sueños y reflexión con procedencia separada; bandeja de mensajes proactivos con confirmación del texto visible.
- **232 pruebas aprobadas**; las **41 pruebas de autonomía** pasaron también con el intérprete vinculado a la vida existente.
- README de actualización en [español](README.update-v0.5.md) e [inglés](README.update-v0.5.en.md), contratos y [reporte de validación](docs/autonomy-validation.md).

Límites: la instalación y la programación están verificadas por separado; la activación desatendida y la entrega reales aún requieren observar al anfitrión. Abrir un chat vacío no garantiza un saludo. La selección de modo y las herramientas dependen del LLM; las simulaciones no aportan evidencia empírica ni demuestran experiencia subjetiva.

## 0.4.0 — 2026-10-05

- Identidad persistente separada del laboratorio anterior: prioridades y rasgos iniciales aleatorios reproducibles, aprendizaje de preferencias/competencia y aversiones recuperables.
- Selector numérico con términos auditables, preguntas causales por dominio, recibos externos y reconciliación de resultados desconocidos.
- Memorias OBSERVED/REPORTED/INFERRED/SIMULATED, referencias, biblioteca acotada, reflexión y sueños locales sin promoción a evidencia empírica.
- LifeRuntime transaccional: idempotencia, control de revisión, recuperación, dos escritores, ramas, verificación y exportación atómica.
- CLI `life`, ciclos locales finitos, watch interrumpible, pausa persistente, créditos y señal de parada.
- Skill para Codex con wrapper portátil, metadatos y guía; instalada y comprobada en este entorno. La investigación externa usa al anfitrión activo.
- Protocolo I1 predefinido con seis ramas emparejadas y feedback sintético. Los experimentos v0.1–v0.3 permanecen disponibles.
- **163 pruebas aprobadas**, incluyendo las 121 anteriores; revisión independiente y demostración real de Codex → elección → fuente primaria → feedback → reflexión/sueño → diario/recompute.
- Piloto I1: 20 semillas, 140 bases, 3.540 eventos, 1.200 elecciones de seguimiento, 6.000 filas de puntuación y 401/401 comprobaciones. Neutralizar preferencias cambió 9/20 primeras elecciones; freeze conservó sus parámetros y reiniciar reprodujo estados/eventos funcionales.

Límites: cinco dimensiones fijas; aprendizaje por reglas, sin modificar pesos del LLM; sueños por plantillas locales; preguntas sin operación de cierre; investigación externa dependiente del anfitrión. No demuestra personalidad humana ni experiencia subjetiva. [Contrato](docs/mvp-v0.4.md), [guía](docs/codex-identity-quickstart.md).

## 0.3.0 — 2026-10-05

- Política `capability`: dos estimaciones persistentes de fiabilidad de ejecución que modifican la elección de herramienta según utilidad y coste.
- Entorno con degradación privada de una herramienta y feedback separado de corrección de la decisión y éxito de ejecución. Ruido del mundo independiente de la herramienta elegida.
- Intervenciones de lectura y actualización independientes, congelación del modelo íntegro y comparador genérico con la misma información y matemática.
- Protocolo E2: adquisición, cinco ramas, comparador genérico, reinicios, sondas comunes sin entrenamiento, calibración y bootstrap emparejado por semilla. Conserva datos parciales y denominadores ante fallos de ejecución y verificación con estructura legible.
- CLI y configuraciones para ejecutar, inspeccionar, bifurcar y reproducir capacidades; predicciones fijadas antes del feedback, hashes y costes registrados.
- 121 pruebas aprobadas: 38 nuevas y las 83 anteriores. Revisión independiente de agente, entorno e informe; reconstruct de una base v0.2 comprobado con el motor nuevo.
- Piloto completo E2: 140 bases, 6.400 episodios, 32.000 ensayos de sonda y 580 comprobaciones válidas. Mejora de utilidad updated−frozen 0,3793, IC descriptivo 95 % [0,3319; 0,4298]; genérico funcionalmente idéntico. [Resultados y límites](reports/README.md).
- v0.2 registrada en el commit local `8a7900b` y etiqueta `v0.2.0`, con preservación de bytes de fuentes y evidencia.

Límites: E2 implementa un predictor operativo acotado; el genérico es funcionalmente equivalente por construcción. No implementa aprendizaje conjunto del mundo y capacidades, incertidumbre de segundo orden, identidad, metacognición ni conciencia. Véase [MVP v0.3](docs/mvp-v0.3.md).

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
