# Especificación: memory

Estado: contrato ampliado; v0.1 implementa episodios, procedencia y máscaras. v0.3 conserva ese mecanismo y admite acciones compuestas lado/herramienta con feedback de ejecución. Consolidación/semántica siguen propuestas. [Alcance inicial](docs/mvp-v0.1.md), [contrato v0.3](docs/mvp-v0.3.md) · 2026-10-05 · ID: `memory` · depende de `runtime`.

## Objetivo

Conservar episodios propios y regularidades derivadas que puedan influir en decisiones futuras después de un reinicio. Separar la memoria disponible para el agente de la auditoría completa del laboratorio.

## Contratos y propiedad

Propietario de episodios, índices cognitivos, afirmaciones semánticas y resúmenes autobiográficos. Interfaces `encode`, `link_outcome`, `retrieve` y `consolidate` en [contratos](docs/interfaces-and-state.md). La memoria prospectiva referencia metas de `cognition` mediante IDs; no ejecuta directamente sus acciones.

Un episodio conserva contexto, estado interno relevante, predicción previa, intención, acción y consecuencia enlazada. La consolidación conserva soporte por afirmación y contexto de validez. Simulación, inferencia, observación e informe externo permanecen distinguibles.

## Estructura y convenciones futuras

Paquete `src/project_consciousness/memory/`, tests `tests/memory/`. Operaciones de lectura sin efectos cognitivos ocultos; si recuperar modifica accesibilidad, emite un delta explícito. Ejemplo conceptual: `retrieve(query, filters, top_k, as_of_tick) -> MemoryHit[]`. Consultas parametrizadas, desempate estable y puntuación desglosada.

## Aceptación y pruebas

- Un episodio registrado puede recuperarse tras reiniciar, con las mismas fuentes y puntuación bajo config fija.
- Una imaginación no puede convertirse en éxito observado ni crear soporte empírico adicional.
- Un hecho contradictorio crea revisión contextual; no sobrescribe el evento fuente.
- El bloqueo de lectura impide todas las rutas de consulta de ese episodio, incluida la proyección narrativa.
- La ablación de escritura conserva lectura de recuerdos anteriores y se distingue de ablación de lectura.
- El borrado de accesibilidad cognitiva no da acceso alternativo al log de auditoría.

Verificación futura con contratos, fixtures de procedencia y experimento de pista demorada; [CLI y tests](docs/mvp.md). La propiedad científica de continuidad autobiográfica más allá del registro funcional queda abierta.

## Límites

Siempre citar fuentes de resúmenes. Revisar antes de introducir datos personales reales o compartir memoria entre agentes. Nunca tratar un embedding, una similitud textual o una narración persuasiva como verificación de la verdad del recuerdo.
