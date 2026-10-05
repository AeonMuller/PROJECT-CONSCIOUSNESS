# ADR-0002: primera entrega con pista demorada

Estado: aceptado para el alcance v0.1 autorizado en esta conversación. La aprobación de implementación de este corte no constituye una validación de sus hipótesis científicas.

## Contexto y decisión

La primera propuesta de ejecución priorizó persistencia y memoria causal. Se implementa una tarea binaria de pista demorada, suficientemente pequeña para aislar acceso a historia y probar E0/E1. El mundo de rutas y los mecanismos de autorregulación quedan como ampliación.

El significado de la pista está programado. Por ello, una mejora sobre memoria bloqueada comprueba que la información retenida influye en la decisión; no demuestra aprendizaje de asociaciones ni ventaja sobre otras organizaciones de memoria. El historial plano es un control obligatorio y puede igualar al agente episódico.

## Ajustes concretos frente a la arquitectura completa

- Paquete en la raíz para ejecutar directamente con Python sin instalar dependencias. Se puede migrar a `src/` cuando el empaquetado aporte valor.
- Estado cognitivo limitado a registros episódicos; no se mantiene una copia oculta de la pista en otro componente.
- Cada tick registra observación, decisión previa al resultado, consecuencia, memoria posterior, mundo y ambos RNG. El feedback queda asimilado antes de confirmar el tick; no existe una cola pendiente en v0.1.
- Un evento de transición contiene la traza y snapshot completo comprimido. La reconstrucción restaura estos payloads y comprueba sus hashes; la recomputación ejecuta otra vez cada transición. No hay aún reductores de eventos por cada módulo de la arquitectura ampliada.
- SQLite es la autoridad para manifiesto, eventos y estado. Los JSON/CSV/informes son exportaciones derivadas. Los hashes comprueban integridad accidental, no autentican frente a un adversario capaz de modificar datos y hashes.
- Las ramas conservan memoria, mundo y RNG, cambiando solo campos de acceso/política autorizados. La ablación de escritura se ensaya desde el inicio, no se interpreta como borrado de recuerdos previos.
- El agente se aísla del evaluador mediante interfaces y vistas de datos. Esta implementación local no es una frontera de seguridad frente a código hostil dentro del mismo proceso.

## Validación y siguiente límite

Se requieren pruebas de reinicio, interrupción abrupta, idempotencia, corrupción de procedencia, procedencia de recuerdos y ausencia de datos privados en la observación. E0 compara trazas completas; E1 produce contrastes por semilla y ramas desde el mismo snapshot. Los intervalos del piloto son descriptivos.

La siguiente capacidad deberá incorporar reglas aprendidas o contextos nuevos, para investigar adaptación y generalización que esta tarea programada todavía no mide. El tamaño del efecto en v0.1 no justifica por sí solo añadir atribuciones sobre experiencia subjetiva.
