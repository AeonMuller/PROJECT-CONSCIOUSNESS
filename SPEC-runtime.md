# Especificación: runtime

Estado: contrato ampliado; subconjunto implementado en [v0.1](docs/mvp-v0.1.md), ampliado con snapshots de aprendizaje y tarea privada en [v0.2](docs/mvp-v0.2.md) · 2026-10-03 · ID del [mapa](CAPABILITY-MAP.md): `runtime`.

## Objetivo

Hacer que el estado cognitivo persista, sea reconstruible y pueda bifurcarse sin mezclar condiciones. Proveer tipos básicos, reloj lógico, puertos de entorno, único escritor y control de presupuesto. Dependencias de construcción: ninguna.

## Contratos y propiedad

Propietario de manifiestos, eventos, revisiones, snapshots, RNG y confirmación de ticks. Interfaces `step`, `snapshot`, `fork`, `replay` y `read_events` definidas en [contratos](docs/interfaces-and-state.md). Recibe módulos por puertos; no importa el laboratorio concreto. El estado oculto del mundo pertenece al bundle del evaluador.

## Estructura y convenciones futuras

Paquete propuesto `src/project_consciousness/runtime/`; tests propuestos `tests/runtime/`. Python con nombres `snake_case`, tipos explícitos, valores inmutables entre fases y errores estructurados. Ejemplo de contrato, no código: `step(observation, state_revision, intervention_set) -> TickOutcome`. Evitar variables globales mutables y reloj de pared en la dinámica.

## Aceptación y pruebas

- Reanudar un run en fronteras preseleccionadas reproduce hashes funcionales de la ejecución ininterrumpida en runtime fijado.
- Inyectar fallo antes/durante/después de confirmación no duplica acciones ni mezcla revisiones.
- Misma clave de tick y misma entrada devuelve el resultado; entrada distinta rechaza conflicto.
- Snapshot conserva RNG de todos los componentes y la observación pendiente.
- Un fork no modifica padre, memorias o parámetros de otra rama.

CLI operativa y tests de v0.1 en [README](README.md); alcance ampliado en [MVP](docs/mvp.md). No se exige porcentaje de cobertura arbitrario: se cubren las fronteras de fallo e invariantes anteriores.

## Límites

Siempre registrar configuración y versiones. Revisar el diseño antes de introducir acciones externas o un almacén distribuido. Nunca exponer tablas privadas del evaluador al agente ni prometer atomicidad de efectos remotos mediante SQLite. Las futuras migraciones preservan snapshots originales y crean derivados verificables.
