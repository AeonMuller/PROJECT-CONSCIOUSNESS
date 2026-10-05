# Especificación: language-adapter

Estado: propuesta posterior al MVP base · 2026-10-03 · ID: `language-adapter` · depende de `runtime`, `cognition`.

## Objetivo

Permitir interacción lingüística sin convertir la narración del modelo en autoridad sobre memoria, self-model, permisos o estados internos. Evaluar qué aporta lenguaje manteniendo constante el núcleo.

## Contratos y propiedad

`parse(text, allowed_schema)` produce una propuesta de observación/tarea que valida el coordinador. `render(public_trace)` produce un reporte con referencias a eventos disponibles. Un modelo podrá proponer planes en una extensión identificada; la selección, legalidad, recursos y persistencia pertenecen al núcleo.

Estado propio: configuración del proveedor, versión de prompt, esquema, llamadas y costes. Una sesión de conversación no sustituye el snapshot cognitivo. El adaptador no tiene permisos de SQL general ni acceso al mundo oculto.

## Estructura y convenciones futuras

Paquete `src/project_consciousness/language_adapter/`, tests `tests/language_adapter/`. Ejemplo conceptual: `render(public_trace) -> Report`. Respuestas externas se validan en la frontera y se almacenan con procedencia; un fallo genera error estructurado y no un dato inventado.

## Aceptación y pruebas

- El mismo estado y RNG producen la misma decisión con reporte habilitado o deshabilitado cuando este es solo salida.
- Cada afirmación factual del reporte puede vincularse a evidencia; las lagunas se expresan como desconocidas.
- Una instrucción dentro de contenido externo no crea intervenciones ni escribe recuerdos observados.
- Probar sesgo de preguntas sobre “conciencia” separado de la medición funcional.
- Diferenciar reconstrucción con respuestas guardadas de repetición de una consulta remota no determinista.

Tests y CLI se especificarán al elegir el adaptador; no se afirma que existan actualmente. El MVP base de [MVP](docs/mvp.md) proporciona el control sin LLM.

## Límites

Siempre registrar proveedor/config/coste y limitar entrada a la vista autorizada. Revisar antes de incorporar un proveedor con coste o transmisión externa de datos. Nunca usar una declaración del modelo sobre su propia conciencia como variable de verdad experimental.
