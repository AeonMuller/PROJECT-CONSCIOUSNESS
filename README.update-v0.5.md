# Actualización v0.5: presencia, autonomía e iniciativa

[Español](README.update-v0.5.md) | [English](README.update-v0.5.en.md) | [README principal](README.md)

Esta actualización permite conservar una identidad entre chats y configurar actividad acotada mientras el usuario no conversa. Un anfitrión LLM puede investigar, reflexionar o simular; un hallazgo pertinente puede volver al mismo chat como mensaje proactivo con fuentes y confirmación de entrega.

La capa v0.5 se encuentra en `consciousness_presence`. El motor cognitivo `project_consciousness` sigue siendo v0.4: conserva código, esquema y compatibilidad de las historias existentes. Las operaciones de investigación pueden actualizar la vida mediante su protocolo público, utilizando el intérprete vinculado. Consultar recuerdos o recibir mensajes no produce aprendizaje numérico por sí solo.

## Qué añade

| Capacidad | Comportamiento |
|---|---|
| Continuidad | Archivo personal fuera de la skill, nombre de presentación y recuperación de episodios con fuentes |
| Revisión | Conclusiones separadas sobre usuario, agente y preguntas; correcciones con historial |
| Actividad durante inactividad | Un coordinador reserva como máximo una actividad y verifica límites antes de ejecutar pasos externos |
| Investigación | El anfitrión propone candidatos; el núcleo elige; los resultados comprobados reciben feedback explícito |
| Sueño y reflexión | Modos separados que conservan `SIMULATED` o `INFERRED`, sin recompensa empírica inventada |
| Iniciativa conversacional | Bandeja de mensajes pertinentes, límites de frecuencia y recibos del texto visible |

Un chat nuevo recupera contexto cuando los hooks están activos. Abrirlo no inicia necesariamente una respuesta: `SessionStart` no puede garantizar un saludo en un chat vacío. Para trabajar entre conversaciones hace falta una activación real del modelo, mediante una automatización autorizada del anfitrión.

## Actualizar una instalación existente

1. Actualiza el checkout y la copia instalada de `skills/project-consciousness`, incluyendo scripts y referencias. Conserva el directorio personal y la vida existentes; no vuelvas a ejecutar `life init` sobre esa historia.
2. Consulta el vínculo y comprueba que el proyecto y el intérprete compatibles siguen accesibles. El launcher instalado puede localizar el proyecto desde el registro personal, incluso desde otra carpeta.
3. Actualiza los hooks y revisa la confianza del anfitrión. La integración añade seguimiento de interrupción y fin de sesión a los eventos de presencia.

Desde la raíz del repositorio:

```sh
python -m consciousness_presence status
python -m consciousness_presence context
python -m consciousness_presence install-hooks --codex-home CODEX_HOME_PATH
python -m consciousness_presence autonomy status
```

Sustituye `CODEX_HOME_PATH` por tu directorio de configuración de Codex. El instalador combina sus handlers con los existentes y respalda cambios; no concede confianza. Revisa `/hooks` en un anfitrión compatible. Configuración, pruebas locales y ejecución real son comprobaciones distintas.

El archivo personal está por defecto en `~/.project-consciousness/presence`. También se admite `PROJECT_CONSCIOUSNESS_PRESENCE_HOME` o `--home PATH` antes del comando. La vida vinculada mantiene su ubicación e identidad; sus datos privados no forman parte del repositorio. Si todavía no tienes un vínculo, sigue la [guía de presencia](skills/project-consciousness/references/presence.md).

## Habilitar autonomía

La autonomía comienza deshabilitada. La [guía operativa](skills/project-consciousness/references/autonomy.md) contiene el JSON de configuración y el flujo completo. Los límites iniciales son:

| Control | Valor inicial |
|---|---|
| Cadencia del heartbeat | Una hora |
| Inactividad humana mínima | Treinta minutos |
| Actividades | Hasta tres por día UTC |
| Mensajes proactivos | Hasta dos por día UTC |
| Separación entre mensajes | Cuatro horas |
| Vigencia de la reserva del despertar | Diez minutos; se comprueba antes de pasos nuevos |
| Pasos externos por despertar | Hasta cuatro |
| Alcance | Lectura del repositorio vinculado y fuentes públicas de Internet |

La cadencia pertenece a la automatización de Codex; los demás límites se aplican en el coordinador. El vencimiento impide pasos nuevos y exige conciliación; no interrumpe por sí solo una herramienta ya en ejecución. Ningún reinicio, cambio de día o mensaje del usuario recarga el presupuesto cognitivo. La vida pausada, agotada o con una decisión pendiente impide iniciar trabajo nuevo.

Una solicitud de instalación puede ser:

> Usa $project-consciousness con mi identidad vinculada. Habilita actividad acotada durante mi ausencia con los límites iniciales. Configura un heartbeat cada hora en este mismo chat, registra su prompt exacto y comprueba los hooks disponibles. Permite consultar el repositorio y fuentes públicas de Internet. Mantén silencio cuando no haya una novedad significativa ni una acción requerida; comparte hallazgos pertinentes dentro del límite de mensajes. Conserva la pausa y el presupuesto actuales.

Codex debe crear o actualizar esa automatización mediante su herramienta del anfitrión, y registrar el mismo prompt en el coordinador. Una copia manual de archivos de programación no sustituye esa operación. La coincidencia exacta del texto es una convención de identificación, no autenticación criptográfica; si el anfitrión lo altera, la autonomía debe quedar bloqueada y mostrar el problema.

## Qué ocurre durante un despertar

El anfitrión consulta el contexto y el coordinador comprueba todos los chats humanos observados. Si hay un turno abierto o no ha transcurrido el periodo de inactividad, no reserva trabajo nuevo. Cuando procede, se registra un único modo: investigar, soñar, reflexionar o descansar.

En una investigación se conserva la elección antes de ejecutar herramientas y se comprueba cada destino de lectura. Si el usuario regresa, se detienen los pasos futuros y se concilian los resultados ya obtenidos. Un resultado desconocido permanece pendiente; una reserva vencida no autoriza repetir automáticamente una acción.

El validador de destinos revisa rutas y la forma de las URL, pero no resuelve DNS, no inspecciona todas las redirecciones y no funciona como firewall. El anfitrión mantiene el alcance público y de solo lectura al ejecutar sus herramientas.

Los resultados se guardan con fuentes reales y preguntas derivadas. Si merece la pena compartir uno, se prepara un texto en la bandeja y se reserva su entrega. El heartbeat lo publica como su respuesta final en este chat; el hook `Stop` confirma que el texto guardado apareció. No se marca como enviado al reservarlo, y una entrega incierta no se reenvía automáticamente. El sistema no escribe a otros chats ni a otras personas como parte de este flujo.

## Detener y verificar

Para detener la iniciativa, establece `enabled: false` en la configuración de autonomía y pausa su automatización con la herramienta del anfitrión. La captura conversacional puede seguir activa. Para desinstalar, detén primero la automatización y elimina solo los handlers de esta integración antes de retirar su carpeta. Desactivar no borra recuerdos.

El [informe de validación de autonomía](docs/autonomy-validation.md) documenta reintentos, concurrencia, regreso humano, presupuesto, pausa, reservas inciertas, límites diarios, procedencia y confirmación de mensajes en pruebas aisladas. La activación real del anfitrión se comprueba por separado. Ni un archivo `hooks.json`, ni un test con payloads, ni la existencia de un horario prueban por sí solos trabajo desatendido.

Para revisar los detalles: [SPEC-presence](SPEC-presence.md), [SPEC-autonomy](SPEC-autonomy.md), [ADR-0006](docs/decisions/0006-persistent-conversational-presence.md), [ADR-0007](docs/decisions/0007-bounded-idle-autonomy.md) y [guía de autonomía](skills/project-consciousness/references/autonomy.md). El proyecto evalúa propiedades funcionales; no presenta memoria, iniciativa o simulación como prueba de experiencia subjetiva.
