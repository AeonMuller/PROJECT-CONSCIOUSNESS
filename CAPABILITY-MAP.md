# PROJECT CONSCIOUSNESS — mapa de capacidades

Fecha: 2026-10-05. Estado: mapa de arquitectura ampliada; v0.1 implementa el primer corte de `runtime`, `memory`, política simple y laboratorio E0/E1. [v0.2](docs/mvp-v0.2.md) añade aprendizaje de asociaciones binarias y protocolo L1. [v0.3](docs/mvp-v0.3.md) añade dos estimaciones persistentes de eficacia de herramientas y un E2 operacional acotado. [v0.4](docs/mvp-v0.4.md) implementa una identidad funcional con estado propio, aprendizaje de preferencias/aversión, preguntas, simulación y una skill para el anfitrión LLM. Los componentes más amplios de la arquitectura siguen propuestos.

El objetivo es investigar propiedades funcionales mediante intervenciones reproducibles. Ningún módulo ni conjunto de resultados se definirá como prueba de experiencia subjetiva. El usuario solicitó el diseño completo y la propuesta de MVP en esta fase; este mapa y sus especificaciones se entregan juntos para revisión.

| ID estable | Responsabilidad | Dependencias de construcción | Especificación |
|---|---|---|---|
| `runtime` | Contratos básicos, reloj, eventos, persistencia, snapshots y recuperación | — | [SPEC-runtime](SPEC-runtime.md) |
| `memory` | Episodios, hechos derivados, recuperación y consolidación con procedencia | `runtime` | [SPEC-memory](SPEC-memory.md) |
| `cognition` | Percepción, creencias, self-model, afecto, workspace, metacontrol, metas, imaginación, acción y aprendizaje | `runtime`, `memory` | [SPEC-cognition](SPEC-cognition.md) |
| `experiment-lab` | Entornos, condiciones, intervenciones, baselines, evaluación y análisis | `runtime`, `memory`, `cognition` | [SPEC-experiment-lab](SPEC-experiment-lab.md) |
| `language-adapter` | Entrada/salida lingüística opcional sobre contratos del núcleo | `runtime`, `cognition` | [SPEC-language-adapter](SPEC-language-adapter.md) |

Orden: `runtime` → `memory` → `cognition` → `experiment-lab`. El adaptador lingüístico se evalúa después de establecer un laboratorio funcional sin él. Los contratos del entorno pertenecen a `runtime`; su implementación pertenece a `experiment-lab`, para evitar una dependencia circular.

Estos son límites de paquetes. Dentro de `cognition` existen componentes sustituibles con retroalimentación temporal. Un ciclo cognitivo no implica ciclos de importación: el coordinador conecta puertos y pasa valores inmutables entre fases.

El corte v0.3 conecta `cognition` con el decisor mediante dos probabilidades de ejecución correcta, actualizadas con feedback de la herramienta utilizada. `runtime` conserva modelo, linaje y RNG al bifurcar o reiniciar; `experiment-lab` separa fallo de decisión y fallo de ejecución y compara actualización, congelación, bloqueo de lectura, sham, reinicio y un predictor genérico equivalente. Es un componente de estimación de capacidades, no el self-model completo del mapa ni metacognición. La decisión y sus límites están en [ADR-0004](docs/decisions/0004-capability-predictor.md).

Extensiones posteriores: percepción audiovisual, cuerpo robótico, aprendizaje de representaciones y comparación entre agentes colectivos. No forman parte del MVP. Se conserva desde ahora `agent_id` y `origin_agent_id` para poder estudiar memoria compartida sin confundir las biografías individuales.

Documentos transversales: [arquitectura](docs/architecture.md), [contratos y estado](docs/interfaces-and-state.md), [experimentos](docs/experiments.md), [fundamentos](docs/scientific-foundations.md), [Gateway](docs/gateway-analysis.md) y [MVP](docs/mvp.md).

## Corte de identidad v0.4

Los límites y contratos detallados están en [MVP v0.4](docs/mvp-v0.4.md). Este corte se compone de módulos dentro del mismo paquete Python, con archivo SQLite distinto del laboratorio anterior:

| Módulo | Contrato estable | Límite |
|---|---|---|
| `identity-state` | initial_state, transition, public_context | Reducer puro; preferencias causales y procedencia explícita |
| `identity-runtime` | LifeRuntime, apply, fork, verify, export_bundle | Persistencia atómica, reintentos, ramas, replay y presupuesto |
| `identity-interface` | CLI life | Importación local, JSON, watch finito y diario |
| `identity-skill` | SKILL.md + wrapper portable | Codex propone lenguaje y usa herramientas autorizadas; registra recibos |
| `identity-lab` | I1 versionado | Intervenciones emparejadas y trazas numéricas con feedback sintético |

Las cinco dimensiones son diseñadas y fijas. No hay aprendizaje de representaciones, finetuning, emociones sentidas demostradas ni investigación externa sin un anfitrión activo. [ADR-0005](docs/decisions/0005-persistent-functional-identity.md).
