# ADR-0003: aprender asociaciones con un modelo persistente acotado

Estado: aceptada · 2026-10-03.

## Contexto

La primera versión demuestra retención y uso causal de una pista, pero la asociación pista–acción está suministrada. El usuario autorizó continuar con aprendizaje, cambio no anunciado, reinicio y control congelado. El protocolo y contratos están en [MVP v0.2](../mvp-v0.2.md).

## Decisión

Añadir una política aprendiente optativa, con dos estimaciones de probabilidad izquierda condicionadas a pista y actualización exponencial tras feedback. Son parámetros persistentes separados de los registros episódicos. Elegir la acción con mayor éxito predicho y sortear solo empates permite separar nítidamente creencia y distribución de selección.

La estructura binaria exclusiva se proporciona: acción y éxito permiten deducir qué lado era correcto. La asociación específica se estima desde experiencias. Este supuesto limita la conclusión a esta tarea y no se extenderá implícitamente a entornos donde un fallo no identifica la alternativa correcta.

La configuración de la tarea se mantiene fuera de Config y de la interfaz del agente. Solo el mundo/evaluador tiene la regla inicial y el calendario de reversión. Los snapshots contienen ambos ámbitos para reproducibilidad; esto no constituye aislamiento contra código hostil dentro del proceso.

L1 entrena un número fijo de episodios y bifurca copias idénticas antes de la inversión: adaptive, frozen, sham y resumed. Frozen conserva íntegro el modelo y mantiene observación/memoria. Un control adicional sin aprendizaje desde el inicio estima el efecto durante adquisición. Todos los estados y decisiones se verifican mediante recompute.

## Alternativas consideradas

- Conteos acumulativos sin descuento: sencillos y útiles como futuro baseline, pero acumulan evidencia obsoleta tras una reversión. Esta entrega usa tasa constante declarada para investigar adaptación; no afirma optimalidad.
- Red neuronal/LLM: innecesarios para dos pistas y dos acciones; dificultarían atribuir los efectos iniciales y reproducir ejecuciones exactas.
- Inferencia de cambio latente: amplía la tarea e introduce otro mecanismo. La política actual no recibe ni detecta explícitamente un marcador de régimen.
- Aprender a partir del log del evaluador: ofrecería información histórica fuera del presupuesto del agente. Se aprende solo de pista recuperada, decisión y consecuencia pública autorizadas.

## Consecuencias

Es posible intervenir escritura de modelo sin retirar recuerdos. La versión/hash del modelo identifica el estado que produjo cada predicción. Se mide por separado el tamaño del modelo y del agente completo. Las predicciones guardadas antes del feedback permiten calcular Brier sin confundirlo con exploración o elección greedy.

La adaptación rápida puede entrar en tensión con retención; L1 no prueba retención A→B→A, metacognición, self-model ni generalización. Un resultado positivo será evidencia sobre este algoritmo y tarea diseñados.

No se cambia esquema SQL ni se transforman runs anteriores. El motor v0.1 se conserva en un archivo verificable. El guardado de fuentes/versiones obliga a usar ese motor para continuar o recomputar sus runs; reconstruct permite comprobar integridad con v0.2. Esta restricción es deliberada para evitar comparar historias bajo implementaciones distintas sin declararlo.
