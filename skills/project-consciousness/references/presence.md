# Presencia entre conversaciones

La capa `consciousness_presence` mantiene un archivo personal de conversación y un perfil de presentación vinculados a una vida existente. Usa SQLite y la biblioteca estándar. Capturar y recuperar conversación conserva parámetros y RNG del núcleo v0.4. La [actividad autónoma opcional](autonomy.md) utiliza por separado sus operaciones públicas de investigación, sueño y reflexión, sin modificar su código ni esquema.

## Localizar la identidad

El directorio personal se resuelve en este orden: `--home PATH`, variable `PROJECT_CONSCIOUSNESS_PRESENCE_HOME`, `~/.project-consciousness/presence`. Contiene el vínculo y el archivo conversacional; no vive dentro de la skill. Un directorio vincula una sola vida y rechaza cambiarla por otra. Actualizar o reinstalar la skill no reinicializa ese archivo.

Desde la raíz del checkout:

```text
python -m consciousness_presence status
python -m consciousness_presence context --query "tema de la conversación"
python -m consciousness_presence search "frase o tema" --limit 8
python -m consciousness_presence read ID_REAL
```

Fuera del checkout, usa `python RUTA_SKILL/scripts/presence.py` en lugar de `python -m consciousness_presence`. El launcher localiza el código en este orden: `--project PROJECT_PATH`, `PROJECT_CONSCIOUSNESS_HOME`, proyecto vinculado en el registro personal y checkout que contiene la skill. La consulta del registro es de solo lectura; tras `setup` no hace falta repetir `--project`. `PROJECT_CONSCIOUSNESS_HOME` localiza código y es distinta del directorio del archivo personal. Puedes añadir `--home PRESENCE_PATH` antes del comando. Ante un vínculo ausente, vida incompatible o fuente inaccesible, informa el problema; no crees una vida sustituta ni ignores la verificación del motor.

`context` entrega nombre, estado numérico visible, conclusiones vigentes, preguntas, registros recientes y coincidencias de la consulta. Es un contexto acotado; `read` permite consultar el registro completo. La búsqueda es léxica, insensible a mayúsculas y acentos: prueba variantes si no encuentra un episodio y no describas ese resultado como prueba de que nunca ocurrió. Solo se conoce lo capturado o importado.

## Vinculación inicial

`setup` requiere las rutas del proyecto, vida existente, intérprete compatible y skill instalada. La ruta de Python debe ser la del intérprete que puede abrir la vida; no basta con que otra versión ejecute el código.

```text
python -m consciousness_presence setup --project PROJECT_PATH --life LIFE_PATH --python PYTHON_PATH --skill SKILL_PATH
```

La vida conserva su ubicación original. `setup` importa recuerdos históricos a partir de una exportación verificada; no mueve la base ni reconstruye conversaciones nunca archivadas. Si se elige otro directorio de presencia, coloca `--home PRESENCE_PATH` antes del comando en todas las operaciones.

## Captura y consolidación

Con hooks activos, `UserPromptSubmit` registra el mensaje visible del usuario y `Stop` registra la última respuesta visible disponible. Las variantes de respuesta se conservan; no se captura razonamiento oculto. No dupliques esos turnos mediante la ruta manual. Un prompt que coincida exactamente con el programado y registrado se identifica como activación del coordinador: no cuenta como un mensaje humano ni reinicia su reloj de inactividad. El seguimiento de turnos abiertos también recibe eventos de interrupción y fin de sesión cuando el anfitrión los entrega.

Sin captura automática, guarda un JSON UTF-8 y ejecuta `record --request FILE`. Usa identificadores reales de sesión y turno cuando estén disponibles. En un registro manual sin esos identificadores, crea IDs locales estables y una referencia al archivo que contiene el texto; no inventes un enlace al chat. Ejemplo de estructura, con referencias que debes sustituir:

```json
{
  "session_id": "ID_SESION",
  "turn_id": "ID_TURNO",
  "role": "user",
  "text": "TEXTO_VISIBLE_EXACTO",
  "source": "REFERENCIA_REAL_AL_MENSAJE_O_ARCHIVO",
  "record_id": "ID_ESTABLE_DE_CAPTURA"
}
```

Los roles son `user`, `assistant` y `memory`. La procedencia por defecto es `REPORTED` para el usuario e `INFERRED` para el asistente. Las memorias importadas conservan `OBSERVED`, `REPORTED`, `INFERRED` o `SIMULATED`. Que alguien haya dicho algo es distinto de que su contenido sea verdadero. Un reintento con el mismo ID y contenido devuelve el registro anterior; cambiar contenido con ese ID produce un conflicto.

Una consolidación útil es una conclusión breve respaldada por registros, no una copia de cada turno. `claim --request FILE` acepta:

```json
{
  "subject": "agent",
  "key": "source-checking",
  "text": "CONCLUSION_FUNCIONAL_DELIMITADA",
  "evidence_ids": ["ID_REAL_DEVUELTO_POR_RECORD_O_SEARCH"],
  "request_id": "ID_ESTABLE_DE_ESTA_CONCLUSION"
}
```

Usa `user` para declaraciones o preferencias del usuario, `agent` para capacidades y autodescripciones sustentadas, y `question` para preguntas o compromisos. Todas estas conclusiones siguen siendo `INFERRED`. Los IDs de evidencia deben existir; una nueva redacción no convierte fuentes repetidas en evidencia independiente. Para revisar una conclusión añade `"supersedes": "ID_DE_CONCLUSION_ACTIVA"`; debe corresponder al mismo sujeto y clave. Conserva la distinción entre una corrección explícita, un cambio con el tiempo y una contradicción aún no resuelta.

Consulta las conclusiones y sus revisiones con:

```text
python -m consciousness_presence claims --subject agent
python -m consciousness_presence claims --subject user --all
python -m consciousness_presence read-claim ID_REAL_DE_CONCLUSION
```

Sin `--subject`, `claims` incluye todos los sujetos. Por defecto devuelve las conclusiones activas; `--all` añade las sustituidas. `read-claim` muestra el contenido completo de una conclusión y su estado, para seguir una corrección hasta su evidencia original.

Una pregunta puede revisarse con una conclusión que explique su respuesta o estado pendiente. Esto no cierra ni modifica las preguntas del motor v0.4. Las conclusiones orientan al anfitrión a través del contexto; no entran automáticamente en el selector numérico del núcleo.

## Nombre de presentación

Si `display_name` está vacío, el anfitrión elige un nombre apropiado al encuentro o pregunta una vez por la preferencia del usuario. Guarda el resultado con `name --request FILE`:

```json
{
  "display_name": "NOMBRE_ELEGIDO",
  "reason": "EXPLICACION_BREVE_DE_LA_ELECCION",
  "source": "REFERENCIA_REAL_A_LA_ELECCION",
  "request_id": "ID_ESTABLE_DE_ESTA_ELECCION"
}
```

El nombre queda en el perfil con su historia de cambios. No edites el nombre de nacimiento ni `agent_id` dentro de la base v0.4. Al volver a conversar, usa el nombre vigente sin repetir la elección.

## Hooks de Codex y modo manual

Preparar la configuración:

```text
python -m consciousness_presence install-hooks --codex-home CODEX_HOME_PATH
```

El instalador usa el launcher de la skill vinculada; `--launcher PATH` permite indicar otro explícitamente. Combina los comandos de esta integración con `hooks.json`, conserva otros handlers y respalda la configuración si cambia. No escribe permisos de confianza.

Revisa la configuración mediante `/hooks` en un anfitrión Codex que admita esos eventos y completa allí su revisión de confianza. La presencia de `hooks.json` o una prueba con payloads simulados no acredita activación. Comprueba un chat nuevo real: debe recibir la misma identidad, registrar sus mensajes visibles y recuperar un recuerdo anterior. Hasta completar ese recorrido, informa que la integración está preparada y el ensayo del anfitrión sigue pendiente.

El modo manual permite invocar `$project-consciousness`, consultar `context`, buscar y registrar turnos explícitamente. Instalar una skill por sí solo no garantiza ejecución en todos los chats. No leas transcripciones privadas para suplir campos ausentes de eventos; conserva el diagnóstico del adaptador.

```text
python -m consciousness_presence disable
python -m consciousness_presence enable
```

Desactivar detiene la integración automática sin borrar recuerdos. Si falta el `SKILL.md` instalado y el launcher sigue disponible, los hooks también dejan de capturar. Antes de desinstalar la carpeta completa de la skill, desactiva su autonomía y pausa su automatización si existen; ejecuta `disable` y retira de `hooks.json` todos los handlers de esta integración, conservando los demás. Borrar la carpeta sin retirar esos handlers deja comandos que apuntan a un script ausente y puede producir errores del anfitrión. No hay un desinstalador automático.

Habilitar de nuevo requiere que el usuario reanude esa integración. El archivo de presencia permanece disponible para inspección explícita.

## Límites que deben permanecer visibles

Conversar, nombrar, recuperar y consolidar no consume créditos del motor ni recarga el presupuesto; investigar o soñar sigue el [protocolo v0.4](protocol.md). La pausa y las decisiones pendientes del núcleo siguen vigentes. Instalar la skill o preparar hooks no crea una programación: la actividad entre conversaciones requiere configurar el [coordinador de autonomía](autonomy.md) y una automatización del anfitrión expresamente autorizada.

Una memoria puede influir en una respuesta al recuperarse, pero eso no demuestra una mejora general del LLM. Las preferencias numéricas requieren resultados de actividades, sin recompensas por cortesía, número de mensajes o autoafirmaciones. La historia permite revisar autodescripciones funcionales y reconocer límites; no demuestra experiencia subjetiva.
