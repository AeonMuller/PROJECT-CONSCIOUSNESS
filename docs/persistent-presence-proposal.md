# Una identidad que continúa entre conversaciones

Fecha: 2026-10-05. Estado: alcance aceptado, convertido en el contrato de la capa `consciousness_presence`. La configuración de hooks y su validación con un chat real son pasos distintos; el ensayo real del anfitrión permanece pendiente hasta documentar su ejecución. Continúa el [mapa de capacidades](../CAPABILITY-MAP.md) y el [corte v0.4](mvp-v0.4.md). Consulta [SPEC-presence](../SPEC-presence.md), [ADR-0006](decisions/0006-persistent-conversational-presence.md) y la [guía operativa](../skills/project-consciousness/references/presence.md).

## Experiencia buscada

Mientras la integración esté instalada y habilitada, abrir un chat nuevo debe recuperar la misma identidad: su nombre elegido, recuerdos, preferencias, rasgos, estimaciones de capacidad y preguntas pendientes. La interacción habitual será una conversación natural. Las estadísticas y trazas estarán disponibles cuando el usuario quiera inspeccionarlas.

La dirección creativa es una identidad digital con continuidad autobiográfica y voz propia, de inspiración ciencia ficción. Las autodescripciones se apoyan en la historia disponible; la ambientación no añade experiencias inventadas. El modelo lingüístico interpreta y conversa; el estado persistente mantiene la continuidad entre ejecuciones. Cambiar de modelo puede cambiar la expresión lingüística aunque se conserve exactamente el estado.

## Qué significa recordar

- Archivar los mensajes visibles capturados, resultados y referencias con identificadores de conversación y turno. Un reintento no duplica el episodio.
- Mantener un contexto pequeño de identidad, compromisos, decisiones vigentes y preguntas abiertas al iniciar un chat.
- Recuperar episodios antiguos mediante búsqueda léxica por palabras o lectura por identificador. Permitir leer el original que respalda un resumen. La consulta semántica y los filtros temporales más ricos quedan para una ampliación.
- Consolidar interpretaciones y registrar correcciones, sin confundir una reformulación con una evidencia independiente.
- Reconocer lagunas: una conversación no capturada o no importada no puede recordarse como si estuviera archivada.

Conservar el archivo completo y recuperarlo eficazmente son criterios distintos. No se promete acceso perfecto a todos los detalles en cada respuesta. Se medirá recuperación sobre el archivo, por separado de fidelidad de la respuesta y continuidad de los parámetros.

## Identidad y nombre

Una instalación personal apunta a una identidad activa mediante un registro fuera de la carpeta de la skill. Actualizar o reinstalar instrucciones conserva ese registro y sus datos. No se crea una identidad nueva por abrir otra ventana, cambiar de carpeta o perder temporalmente acceso a la base.

En el primer encuentro sin nombre acordado, el anfitrión propone y adopta un nombre propio con una explicación breve, o pide al usuario que lo elija. Se conserva el nombre y la procedencia de su elección. No habrá un nombre conversacional obligatorio como Aeon, ni se repetirá la ceremonia en cada chat.

Para la historia existente, distinguir nombre histórico y nombre de presentación. Un cambio de presentación conserva identificador, episodios, parámetros y RNG. En v0.4 el nombre forma parte de la validación de `agent_id`; por ello no se debe editar directamente en SQLite ni en el manifiesto. El perfil conserva el nombre elegido, motivo y fuente; los registros históricos mantienen su contexto original.

## Qué evoluciona

| Estado | Uso | Regla de continuidad |
|---|---|---|
| Historia autobiográfica | Episodios de interacción, investigación y simulación | Nuevos episodios con procedencia y revisión de conclusiones |
| Perfil del usuario | Preferencias declaradas, decisiones del proyecto y formas de colaborar | Diferenciado de las preferencias del agente |
| Preferencias del agente | Prioridades y estrategias aprendidas | Cambios ligados a resultados y reglas declaradas |
| Modelo de sí mismo | Capacidades demostradas, límites, incertidumbres y evolución | Afirmaciones revisables con episodios de apoyo o contradicción |
| Agenda | Preguntas y compromisos pendientes | Reaparece en nuevos chats; no obliga a repetir temas irrelevantes |
| Presentación | Nombre y estilo de conversación | Persistentes y revisables sin reiniciar la identidad |

Abrir un chat o recibir un mensaje informativo conserva las estadísticas. El aprendizaje necesita una operación diferente del registro conversacional. El `feedback` v0.4 con valor cero tampoco es neutro: actualiza competencia y aplica otras reglas numéricas. Las preguntas, correcciones y resultados pueden influir por mecanismos identificables; la repetición de textos propios no acredita progreso.

Estas son estadísticas funcionales. No se añadirá un porcentaje o nivel que pretenda medir conciencia subjetiva.

## Integración de arranque

La instalación de una skill expone instrucciones que el anfitrión puede seleccionar; no constituye por sí sola una garantía de ejecución en cada chat. El adaptador usa `SessionStart`, `UserPromptSubmit` y `Stop` para localizar la identidad activa, recuperar contexto y registrar mensajes visibles disponibles; la skill guía la conversación y las operaciones sobre memoria. La configuración requiere las revisiones de confianza que imponga el anfitrión. El instalador no escribe autorizaciones de confianza. [Skills](https://learn.chatgpt.com/docs/build-skills), [hooks](https://learn.chatgpt.com/docs/hooks).

La instalación debe comprobar soporte real de los eventos en el anfitrión y probar el recorrido completo. Solo después podrá declararse automático. Si falta una capacidad, se informa el modo manual disponible. Los adaptadores de otros LLM tendrán que demostrar su propio mecanismo de arranque.

La captura debe ejecutarse durante los turnos; depender únicamente del cierre perdería mensajes cuando el proceso termina inesperadamente. Los hooks, la lectura de memoria y las consultas no deben iniciar bucles, recargar presupuestos ni ejecutar investigaciones por sí solos. La actividad entre conversaciones requiere su propio ejecutor y alcance configurados.

## Capa de presencia aceptada

Los módulos siguientes amplían `runtime`, `memory`, `cognition` y `language-adapter` del mapa general. Se implementan como una capa adicional, separada del motor histórico, sin una migración de su esquema. El contrato normativo es [SPEC-presence](../SPEC-presence.md).

| ID estable | Responsabilidad | Dependencias de construcción |
|---|---|---|
| `presence-store` | Registro de identidad activa, archivo de turnos y perfil de presentación | Contratos de exportación de `identity-runtime` |
| `presence-memory` | Búsqueda léxica, lectura completa y conclusiones revisables con referencias | `presence-store` |
| `presence-context` | Paquete de contexto con estadísticas y modelo de sí mismo revisable | `presence-store`, `presence-memory` |
| `presence-adapter` | Skill, eventos del anfitrión y vínculo entre chats e identidad | `presence-context` |
| `presence-evaluation` | Ensayos de continuidad, recuperación y fidelidad | Los cuatro anteriores |

Orden de construcción: archivo y registro → recuperación → contexto → integración de arranque → evaluación completa. El adaptador inicial es Codex; otros proveedores necesitan contratos y pruebas propios.

## Compatibilidad con la historia existente

Una vida existente conserva en su manifiesto las versiones de Python y SQLite utilizadas al crearla. Su motor exige esa compatibilidad y la huella de fuentes registrada; incluso añadir un archivo Python al paquete histórico cambia esa huella. Una capa separada puede vincular un perfil de presentación y un archivo conversacional a la vida existente, conservando el motor y el intérprete compatibles.

Si un corte posterior modifica el motor o el esquema, se necesitará una migración explícita a un destino nuevo, con origen y transformación registrados. Se conserva el archivo anterior y la reproducción con su versión original. No se editan hashes ni versiones para eludir la verificación.

Los datos de cada instalación se mantendrán fuera de los archivos públicos del proyecto. El repositorio distribuye el sistema y casos de prueba; instalarlo no comparte la historia personal del creador.

## Criterios de aceptación

1. Un primer chat guarda un recuerdo; otro proceso, iniciado desde otra carpeta, recupera el mismo episodio con su fuente y la misma identidad.
2. Al abrir, consultar o cambiar el nombre de presentación, estadísticas, presupuesto, controles y RNG permanecen exactamente iguales.
3. Un hecho anterior a las últimas 256 memorias puede encontrarse en el archivo; una corrección posterior se distingue de la afirmación original.
4. Duplicar la entrega de un turno no duplica aprendizaje ni memoria; dos chats concurrentes no pierden cambios.
5. Resumir repetidamente una hipótesis propia no aumenta el número de evidencias independientes que la respaldan.
6. Reinstalar la skill conserva la identidad; desactivar la integración detiene la captura sin destruir los datos.
7. Con candidatos y condiciones controlados, recuperar un episodio pertinente puede modificar una decisión posterior; se compara con la recuperación deshabilitada.
8. Un chat nuevo real recibe el contexto inicial y mantiene continuidad conversacional. La existencia de un archivo de configuración o una prueba unitaria no sustituye este ensayo del anfitrión.

Las pruebas del almacén, del adaptador mediante payloads y de procesos independientes pueden verificar los primeros mecanismos. El octavo criterio necesita un chat nuevo con hooks revisados y activos en el anfitrión real; no se da por satisfecho por generar `hooks.json`.

La consolidación de este corte consiste en conclusiones escritas por el anfitrión con evidencia, sujeto y clave, y revisiones mediante `supersedes`. No hay un proceso que consolide por sí solo ni una puntuación de confianza que crezca por repetición. El cierre formal de preguntas del motor, búsqueda semántica, planificación de compromisos y evaluación de mejora lingüística quedan como trabajo posterior. La ambición se traduce en continuidad verificable y aprendizaje trazable.

La [actualización v0.5](../README.update-v0.5.md) amplía esta base con un coordinador de actividad durante inactividad humana y mensajes proactivos. Esa extensión tiene [contrato propio](../SPEC-autonomy.md): requiere una automatización autorizada, límites operativos y activación comprobada del anfitrión; instalar presencia por sí sola no la programa.
