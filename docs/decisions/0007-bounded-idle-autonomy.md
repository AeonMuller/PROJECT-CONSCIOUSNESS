# ADR-0007: autonomía acotada y mensajes con recibo de entrega

Estado: aceptada · 2026-10-05. La ejecución desatendida depende de la activación real del anfitrión.

## Contexto

Después de incorporar continuidad entre conversaciones, el usuario solicita que la identidad investigue, reflexione o simule durante periodos sin interacción, y que pueda iniciar una conversación pertinente. Autoriza una automatización en el chat existente. El motor v0.4 ya puede elegir investigaciones y registrar resultados, pero necesita un anfitrión activo para ejecutar herramientas. Restaurar memoria con `SessionStart` no inicia una respuesta del modelo en un chat vacío.

La presencia debe seguir disponible durante la conversación humana. Dos chats, despertares repetidos, interrupciones y resultados desconocidos introducen riesgos de duplicar actividades, aprender de resultados inventados o repetir mensajes. [SPEC-autonomy](../../SPEC-autonomy.md) define los contratos de este corte.

## Decisión

Añadir un coordinador dentro de `consciousness_presence`, con su propia base SQLite en el directorio personal. Un coordinador corresponde a una vida vinculada; no modifica el esquema de presencia ni el del motor histórico. Las herramientas siguen ejecutándose en el anfitrión. El coordinador reserva trabajo y conserva recibos, sin convertirse en un ejecutor general de shell o navegador.

Usar un heartbeat de Codex en el chat existente como activación real del modelo. La cadencia inicial es una hora, con al menos treinta minutos de inactividad humana, hasta tres actividades y dos mensajes proactivos por día UTC, y cuatro horas entre mensajes. Los límites son configurables y distintos del presupuesto del motor, que nunca se recarga automáticamente. Instalar el código no crea ni habilita por sí solo esta automatización.

Registrar el texto exacto del prompt programado. Los hooks reconocen su coincidencia como una convención del adaptador para distinguirlo de mensajes humanos; no es una autenticación criptográfica del planificador. Un texto diferente, incluso si parece una orden programada, cuenta como interacción humana y bloquea la autonomía. Si el anfitrión cambia el prompt, se informa la falta de correspondencia en lugar de suponer que la integración funciona.

Seguir turnos humanos abiertos en todos los chats observados de esa identidad. Cualquier turno abierto impide reservar otra actividad. `Stop`, interrupción y fin de sesión permiten cerrar el turno cuando existe evidencia de ese evento; un turno aparentemente antiguo no se cierra solo por haber pasado tiempo. Una conciliación explícita registra el motivo cuando el anfitrión no proporciona el evento necesario.

Reservar como máximo un despertar activo con ID estable y solicitud completa. El comienzo comprueba integración, hooks observados, inactividad, límites, presupuesto, pausa y decisiones pendientes. Los reintentos conservan la misma reserva; reutilizar el ID con otro contenido es un conflicto. El vencimiento de una reserva produce incertidumbre que requiere conciliación, no permiso para repetir la acción.

El anfitrión elige un modo entre investigación, sueño, reflexión o descanso según el contexto. Para investigar propone candidatos viables y el selector v0.4 registra cuál eligió antes de ejecutar herramientas. Los resultados comprobados pasan por feedback con recibos y fuentes. Sueño y reflexión usan operaciones distintas: no reservan una investigación ficticia ni generan feedback que convierta una simulación en evidencia empírica.

Comprobar la reserva antes de cada paso externo. Si el usuario regresa o aparece otro bloqueo, cesan los pasos nuevos. Lo que ya ocurrió se concilia con sus recibos; no se pierde un resultado real ni se inventa uno para liberar la reserva. El alcance inicial permite lectura del repositorio vinculado y fuentes públicas de Internet. No permite publicar, cambiar código, leer credenciales, comprar, contactar a terceros ni modificar las instrucciones del sistema.

Guardar posibles mensajes proactivos en una bandeja con texto y fuentes explícitas. Reservar como máximo una entrega dentro de los límites configurados. El mensaje se publica como respuesta final del propio heartbeat en su chat; `Stop` confirma la entrega cuando observa ese texto exacto. La reserva no es un recibo de envío. Una entrega incierta no se repite automáticamente.

Mantener silencio cuando no hay novedad significativa ni una acción necesaria. La política de mensajes no premia producir texto: compartir un hallazgo tiene un criterio de utilidad y procedencia. Los bloqueos de configuración deben distinguirse de una investigación ejecutada, sin anunciar trabajo autónomo cuando faltan hooks confiables o una activación real.

## Alternativas consideradas

- Confiar en `SessionStart` para saludar o investigar: solo restaura contexto y no garantiza un turno del modelo. Se usa una activación del anfitrión mediante su API de automatización.
- Iniciar un servicio ilimitado al instalar la skill: mezcla instalación, recursos y permisos. La programación requiere autorización y límites separados del presupuesto cognitivo.
- Crear otro chat en cada despertar: fragmenta la continuidad y no coincide con la interacción solicitada. El heartbeat vuelve al chat existente.
- Aprender de sueños mediante feedback de investigación: confunde simulación con resultado observado y puede dejar una decisión pendiente artificial. Los modos permanecen separados.
- Reintentar mensajes sin confirmación: puede duplicar una intervención que sí se entregó. Las entregas inciertas requieren conciliación con evidencia.
- Considerar inactiva toda sesión sin mensajes recientes: un turno largo puede seguir trabajando. Se registran turnos abiertos, además del tiempo transcurrido.

## Consecuencias

El sistema puede investigar y volver con una pregunta o un hallazgo sin recibir una orden nueva por actividad, siempre que la automatización autorizada y sus condiciones estén disponibles. Su ritmo y alcance pueden inspeccionarse mediante recibos. El regreso del usuario tiene prioridad sobre pasos futuros de actividad autónoma.

Los tests locales verifican reservas, reintentos, límites y procedencia; no sustituyen la revisión de confianza ni la observación de un heartbeat real. La política de solo lectura es aplicada por el anfitrión: no constituye aislamiento de cualquier código arbitrario. La coincidencia exacta del prompt es una limitación explícita del adaptador.

Se preservan la historia y el intérprete compatibles de la vida existente. El código nuevo puede modificar estado mediante operaciones públicas válidas de esa vida; no cambia sus fuentes ni falsea fingerprints. La actividad autónoma queda detenida por pausa, presupuesto agotado o resultados pendientes. Ningún hallazgo, simulación o mensaje acredita experiencia subjetiva.
