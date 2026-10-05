# Especificación: cognition

Estado: arquitectura ampliada propuesta; [v0.2](docs/mvp-v0.2.md) implementa únicamente aprendizaje persistente de asociaciones binarias y elección a partir de sus predicciones · 2026-10-03 · ID: `cognition` · depende de `runtime`, `memory`.

## Objetivo

Implementar un ciclo donde creencias, capacidad propia, afecto, metas y metacontrol modifiquen causalmente la decisión y el aprendizaje posterior. Proveer componentes sustituibles dentro de un coordinador con fases explícitas.

## Componentes y contratos

Percepción/interocepción; modelo del mundo; self-model; afecto/regulación; workspace; metas; metacontrol; imaginación; política; aprendizaje. Sus estados y entradas/salidas están en [arquitectura](docs/architecture.md) y sus firmas en [contratos](docs/interfaces-and-state.md). El lenguaje es un adaptador externo opcional.

Cada componente es dueño de su parte del estado. Sus salidas se pasan por valores o referencias versionadas y sus actualizaciones por `StateDelta`. El scheduler resuelve la retroalimentación temporal; los componentes no importan entre sí para mutar estado compartido.

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
