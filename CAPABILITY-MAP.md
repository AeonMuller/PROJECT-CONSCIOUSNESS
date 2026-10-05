# PROJECT CONSCIOUSNESS — mapa de capacidades

Fecha: 2026-10-05. Estado: mapa de arquitectura ampliada; v0.1 implementa el primer corte de `runtime`, `memory`, política simple y laboratorio E0/E1. [v0.2](docs/mvp-v0.2.md) añade aprendizaje de asociaciones binarias y protocolo L1. [v0.3](docs/mvp-v0.3.md) añade dos estimaciones persistentes de eficacia de herramientas y un E2 operacional acotado. [v0.4](docs/mvp-v0.4.md) implementa una identidad funcional con estado propio, aprendizaje de preferencias/aversión, preguntas, simulación y una skill para el anfitrión LLM. La [capa v0.5](README.update-v0.5.md) incorpora presencia entre chats y autonomía acotada sin cambiar ese motor. Los componentes más amplios de la arquitectura siguen propuestos.

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

## Capa de continuidad entre conversaciones

La [identidad persistente entre chats](docs/persistent-presence-proposal.md) añade el paquete independiente `consciousness_presence`, regido por [SPEC-presence](SPEC-presence.md) y [ADR-0006](docs/decisions/0006-persistent-conversational-presence.md). Una instalación vincula una vida existente y conserva un archivo personal fuera de la skill. Esta capa no cambia las fuentes ni el esquema del motor v0.4.

| ID estable | Responsabilidad | Límite |
|---|---|---|
| `presence-store` | Vínculo de identidad, turnos idempotentes, perfil y conclusiones en SQLite | Un directorio por vida; conserva textos completos; no actualiza parámetros del núcleo |
| `presence-memory` | Recuperación por palabras, lectura por ID y revisión de conclusiones con evidencia | Búsqueda léxica; el anfitrión consolida; repeticiones no crean evidencia independiente |
| `presence-context` | Estado visible, nombre, preguntas, conclusiones y episodios pertinentes | Contexto acotado; conserva controles, presupuesto y RNG del núcleo |
| `presence-adapter` | Launcher, skill e integración SessionStart/UserPromptSubmit/Stop | Captura mensajes visibles disponibles; requiere revisión de confianza del anfitrión |
| `presence-evaluation` | Ensayos de continuidad, recuperación, reintentos y conservación del estado | Las pruebas del adaptador no sustituyen un chat real con hooks activos |

El nombre de presentación se elige o acuerda en el primer encuentro y puede revisarse sin cambiar el nombre histórico. El perfil del usuario, el modelo del agente y las preguntas son conclusiones separadas con fuentes. La influencia sobre respuestas pasa por el contexto del anfitrión; el aprendizaje numérico sigue requiriendo resultados del protocolo v0.4. No hay autoedición de la skill, recompensas por mensaje ni actividad programada por defecto.

La [guía de presencia](skills/project-consciousness/references/presence.md) cubre el modo manual, la vinculación y la preparación de hooks. La activación automática y la continuidad en un chat nuevo real se deben verificar en cada instalación; no se declaran logradas al escribir su configuración.

## Autonomía e iniciativa v0.5

La capa de presencia añade actividad programada acotada conforme a [SPEC-autonomy](SPEC-autonomy.md) y [ADR-0007](docs/decisions/0007-bounded-idle-autonomy.md). El motor v0.4 mantiene sus fuentes y esquema; el adaptador aplica sus operaciones públicas con el intérprete compatible de la vida existente.

| ID estable | Responsabilidad | Límite |
|---|---|---|
| `autonomy-coordinator` | Configuración, inactividad humana, turnos abiertos, reservas y recibos persistentes | Un despertar activo; pausa, presupuesto, límites y resultados inciertos bloquean trabajo nuevo |
| `autonomy-activity` | Modos de investigación, sueño, reflexión y descanso; puente idempotente al núcleo | El anfitrión ejecuta herramientas; solo investigación usa elección y feedback empírico |
| `autonomy-delivery` | Bandeja con texto y fuentes, límite diario, cooldown y confirmación | Una reserva no acredita envío; no se reintenta automáticamente una entrega incierta |
| `autonomy-host` | Heartbeat del chat y seguimiento de inicio, prompt, cierre e interrupción | Requiere autorización, hooks confiables y un prompt programado registrado exactamente |
| `autonomy-evaluation` | Concurrencia, reintentos, regreso humano, límites y procedencia | La ejecución desatendida real se comprueba por separado de los tests locales |

Los valores iniciales son una activación por hora, treinta minutos de inactividad humana, hasta tres actividades y dos mensajes por día UTC, y cuatro horas entre mensajes. La cadencia pertenece a la automatización del anfitrión; los límites pertenecen al coordinador. No se recarga el presupuesto del motor. La lectura del repositorio vinculado y de Internet público define el alcance inicial, aplicado por el anfitrión.

La [guía de actualización](README.update-v0.5.md) explica la instalación y la [guía de autonomía](skills/project-consciousness/references/autonomy.md), el flujo operativo. Restaurar contexto mediante `SessionStart` no inicia por sí solo una conversación ni demuestra trabajo durante la ausencia del usuario.
