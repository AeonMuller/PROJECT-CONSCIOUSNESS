# Especificación: cognition

Estado: arquitectura ampliada propuesta; [v0.2](docs/mvp-v0.2.md) implementa aprendizaje persistente de asociaciones binarias y [v0.3](docs/mvp-v0.3.md) un predictor operativo de eficacia de dos herramientas. No implementa todavía el self-model completo ni metacognición · 2026-10-05 · ID: `cognition` · depende de `runtime`, `memory`.

## Objetivo

Implementar un ciclo donde creencias, capacidad propia, afecto, metas y metacontrol modifiquen causalmente la decisión y el aprendizaje posterior. Proveer componentes sustituibles dentro de un coordinador con fases explícitas.

## Componentes y contratos

Percepción/interocepción; modelo del mundo; self-model; afecto/regulación; workspace; metas; metacontrol; imaginación; política; aprendizaje. Sus estados y entradas/salidas están en [arquitectura](docs/architecture.md) y sus firmas en [contratos](docs/interfaces-and-state.md). El lenguaje es un adaptador externo opcional.

Cada componente es dueño de su parte del estado. Sus salidas se pasan por valores o referencias versionadas y sus actualizaciones por `StateDelta`. El scheduler resuelve la retroalimentación temporal; los componentes no importan entre sí para mutar estado compartido.

## Corte ejecutable v0.3

`project_consciousness/capability.py` posee dos parámetros persistentes `q_fast` y `q_safe`, con prior 0.5 y actualización exponencial de tasa 0.2. Aprende exclusivamente de `execution_success` de la herramienta utilizada, después de fijar la predicción. `decision_correct` y éxito global son señales separadas; no se atribuye automáticamente un error de lado a una incapacidad de ejecución. La relación pista→lado se suministra fija para esta tarea, mientras la pista concreta debe recuperarse de memoria propia `OBSERVED` del episodio actual.

`capability_agent.py` calcula utilidad esperada como `P(lado correcto) * q_h - coste_h` y distribuye exploración epsilon=0.1 entre las herramientas. El selector recibe solo estimaciones visibles, costes, probabilidad de decisión correcta, epsilon y RNG. El bloqueo de lectura entrega `[0.5, 0.5]`, sin detener actualizaciones del modelo almacenado; congelar la escritura conserva íntegro ese modelo y permite continuar la memoria episódica.

La representación `self` usa nombres de herramientas y `generic` una lista de dos valores. Ambas tienen la misma información, actualización y selector; se espera equivalencia funcional por construcción, sin atribuir una ventaja al nombre self-model. Versión, hash y tamaño identifican el modelo anterior al feedback. Las sondas Brier y su agrupación de calibración pertenecen al evaluador, no a un calibrador interno o una nueva habilidad metacognitiva. Contratos completos y parámetros predefinidos: [MVP v0.3](docs/mvp-v0.3.md); motivos y alternativas: [ADR-0004](docs/decisions/0004-capability-predictor.md).

## Estructura y convenciones futuras

Paquete `src/project_consciousness/cognition/`, tests `tests/cognition/`. Ejemplo conceptual: `predict(belief, self_model_view, candidate_action, horizon) -> Prediction`. Tipos para probabilidad, procedencia y coste; cálculos acotados, streams RNG separados y términos de utilidad registrables.

## Aceptación y pruebas

- La distribución de acción se fija antes de aplicar la acción al entorno.
- Intervenir cada estado en un fixture sensible cambia el consumidor declarado; el fixture negativo no cambia por esa ruta.
- Un self-model revisa predicciones propias al cambiar resultados disponibles y puede seguir equivocado.
- Afecto modula parámetros registrados sin cambiar secretamente recompensas del evaluador o recursos reales.
- Metacontrol asigna esfuerzo o solicita información pagando el coste definido.
- Workspace respeta capacidad/caducidad y deja observar difusión y rutas locales alternativas.
- Rollouts usan exclusivamente el modelo aprendido, se etiquetan `SIMULATED` y respetan presupuesto.
- Aprendizaje produce versiones con linaje y se puede congelar sin congelar indebidamente la observación.

Pruebas de invariantes, presupuestos y mecanismo más experimentos E0–E9 descritos en [experimentos](docs/experiments.md). Comandos futuros en [MVP](docs/mvp.md).

## Límites

Siempre distinguir feedback observado de etiqueta privada. Revisar antes de añadir autoedición del código o aprendizaje de pesos de modelos externos. Nunca interpretar términos como valencia, self o imaginación como evidencia automática de sentir, identidad personal o vivencia subjetiva.
