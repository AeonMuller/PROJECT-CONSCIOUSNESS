# ADR-0004: separar eficacia de ejecución y elección mediante un predictor persistente

Estado: aceptada · 2026-10-05.

## Contexto

v0.2 aprende asociaciones pista–lado y permite congelar sus actualizaciones. El siguiente hito autorizado requiere estimar capacidad operativa y que esa estimación influya en las acciones. Si un único indicador de éxito mezclara una elección equivocada con un fallo de la herramienta, no sería posible atribuir el aprendizaje a eficacia propia dentro de esta tarea. El alcance y protocolo se fijan en [MVP v0.3](../mvp-v0.3.md).

## Decisión

Añadir una política `capability` independiente de la asociación aprendida de v0.2. La regla pista→lado es fija y suministrada; recuperar la pista exige memoria observada propia del episodio. La tarea revela, después de actuar, dos señales: lado correcto y ejecución correcta. Solo la segunda actualiza la probabilidad de eficacia de la herramienta utilizada. Esta separación es un supuesto explícito de observabilidad del banco, no una solución general al problema de atribuir fallos.

Conservar dos estimaciones fast/safe con prior 0.5 y actualización exponencial de tasa 0.2. El agente conoce costes 0.05/0.20 y elige por `P(lado correcto) * q_h - coste_h`, con exploración epsilon=0.1. Las probabilidades verdaderas, el episodio de degradación y los sorteos de ejecución quedan en TaskConfig/mundo privado. Cada episodio prepara los sorteos de ambas herramientas antes de la decisión, independientemente de qué herramienta seleccione la política.

La representación `self` usa un diccionario con nombres de herramientas y el comparador `generic` una lista. Ambos tienen dos parámetros, la misma evidencia y exactamente la misma regla numérica y selector. Se espera equivalencia funcional por construcción; este control evita atribuir una ventaja al nombre o disposición de los datos. No constituye una comparación de todas las posibles arquitecturas de self-model.

E2 entrena 40 episodios y bifurca el mismo estado en `updated`, `frozen`, `reader_blocked`, `sham` y `resumed`, con 40 episodios adicionales. Frozen mantiene íntegro el modelo; reader_blocked conserva aprendizaje pero entrega el prior neutral al selector; sham conserva la lectura efectiva; resumed permite comprobar reinicios. Generic se ejecuta desde el inicio y se contrasta con training+updated, excluyendo representación/hashes/bytes de la igualdad funcional. Las decisiones fijan sus predicciones antes del feedback, con versión y hash del modelo.

El piloto predefine 20 semillas `300:320`, demora 1, memoria de 64 registros y degradación de fast de 0.95 a 0.20 en el episodio 40; safe permanece en 0.85. La medida primaria es utilidad neta media postcambio updated−frozen. El bootstrap es pareado por semilla, con 2.000 réplicas y semilla estadística 20261005. No se eligen semillas ni parámetros por resultados observados; el piloto es descriptivo y admite efectos nulos o negativos.

Además del Brier de ejecución durante actuación, evaluar ambas herramientas con sondas comunes al terminar adquisición y seguimiento. El evaluador fija predicciones antes de generar 100 resultados por herramienta con RNG independiente, compartidos entre condiciones. Esto permite separar calidad del predictor y selección de herramientas visitadas. Las sondas nunca entrenan ni alteran el estado; el modelo almacenado bajo bloqueo se distingue del forecast neutral usado por su política. La calibración agrupada es una medición del laboratorio, no metacognición implementada.

## Alternativas consideradas

- Actualizar capacidad con éxito global: confundiría decisión y ejecución. Se conserva cada señal y sus errores por separado.
- Reutilizar el aprendiz de asociaciones v0.2 para ambas causas: modificaría el objeto de su ensayo y dificultaría atribución. Las políticas permanecen separadas.
- Comparar únicamente contra un agente sin memoria o sin información histórica: permitiría atribuir a la organización self-model una diferencia explicada por la información. El comparador genérico dispone de parámetros y evidencia equivalentes.
- Evaluar solo herramientas seleccionadas: cada política podría visitar casos diferentes. Se añade la distribución común de sondas sin reemplazar la evaluación interactiva.
- Incorporar contextos, calibrador interno, solicitud de ayuda o incertidumbre sobre parámetros: ampliaría simultáneamente varios mecanismos. Se conserva ese diseño como trabajo futuro medible por separado.

## Consecuencias

El corte permite investigar uso causal, adaptación, persistencia y calidad predictiva de dos estimaciones operativas. No implementa identidad, introspección, afecto, imaginación, metacontrol ni un self-model completo. Tampoco prueba generalización a otras herramientas, tareas o contextos. Los valores constantes y su interpretación son decisiones de ingeniería.

Los parámetros, linaje, memoria y RNG se guardan en la misma transacción que la consecuencia. `record_result` consume estado anterior al feedback; Runtime conserva la autoridad sobre reintentos para impedir doble aprendizaje. No se añade esquema SQL ni se migran destructivamente ejecuciones anteriores. v0.2 y sus fuentes se conservan para continuar/recomputar bajo su versión, mientras reconstruct histórico verifica datos registrados.

Este ADR define diseño y criterios de interpretación; los resultados de ejecuciones se conservan en informes independientes, incluidos fallos, efectos nulos y limitaciones.
