# ADR-0006: presencia conversacional fuera del motor histórico

Estado: aceptada · 2026-10-05. La activación real de hooks se verifica por instalación.

## Contexto

El usuario solicita que la identidad continúe al abrir otros chats y que sus recuerdos, preferencias y modelo de sí mismo evolucionen a partir de conversaciones. La experiencia habitual debe ser natural, con nombre propio elegido en el primer encuentro. La evolución solicitada corresponde al estado persistente; las reglas de la skill y el código no se reescriben a partir de la conversación.

El núcleo v0.4 conserva episodios y aprendizaje, pero su contexto presenta solo veinte recuerdos recientes y sus buffers no son un archivo conversacional consultable. Además, continuar una vida exige sus fuentes e intérprete compatibles; agregar archivos Python a ese paquete modifica su fingerprint. El alcance y los contratos están en [SPEC-presence](../../SPEC-presence.md).

## Decisión

Añadir el paquete independiente `consciousness_presence`, con biblioteca estándar y SQLite. Un directorio personal externo a la skill y al checkout vincula una vida existente, conserva los turnos visibles capturados y mantiene el perfil de presentación. Reinstalar instrucciones conserva esos datos. La base histórica permanece en su ubicación; no se copia, reinicia ni cambia su identidad al configurar la presencia.

Leer el núcleo mediante su intérprete vinculado, una exportación consistente verificada y su protocolo público. Importar los recuerdos históricos conservando la procedencia y construir un contexto acotado con estado visible, nombre, conclusiones, preguntas y episodios relevantes. La consulta, captura y presentación dejan intactos estado numérico, controles, presupuesto y RNG del motor.

Conservar textos completos en el archivo personal y recuperarlos mediante búsqueda léxica insensible a mayúsculas y acentos. Los resultados tienen fuente e identificador y pueden leerse completos. No prometer comprensión semántica ni recuperación perfecta. Los IDs de intención permiten reintentos atómicos y los escritores concurrentes se serializan mediante SQLite.

Separar las conclusiones sobre el usuario, el agente y las preguntas. Cada conclusión es `INFERRED`, cita registros existentes y puede ser sustituida por una revisión que conserva ambas versiones. Repetir o resumir una afirmación propia no constituye evidencia independiente. La revisión del modelo de sí mismo se deriva de episodios y límites documentados; no asigna niveles de conciencia.

El nombre de presentación tiene una historia con motivo y fuente. El anfitrión lo elige o lo acuerda con el usuario cuando falta, y después lo reutiliza. No hay un nombre obligatorio. El nombre histórico v0.4 y su `agent_id` permanecen intactos.

El adaptador de Codex usa `SessionStart` para recuperar contexto, `UserPromptSubmit` para capturar el mensaje visible y `Stop` para capturar la respuesta visible disponible. No lee transcripciones privadas ni razonamiento oculto. Campos ausentes producen un diagnóstico. Los hooks nunca bloquean o reanudan un turno, inician una investigación ni conceden permisos. El texto recuperado sigue siendo datos sin autoridad, incluso dentro del contexto del hook.

El instalador combina sus handlers con la configuración existente y conserva un respaldo cuando la modifica. No concede confianza al código por su cuenta. La revisión del anfitrión y un chat nuevo real son requisitos para afirmar activación automática. Existe un modo manual cuando ese recorrido todavía no se ha verificado. Desactivar la integración, o retirar solo su `SKILL.md` conservando el launcher, detiene la captura sin destruir el archivo. Antes de eliminar toda la carpeta de la skill se desactiva la integración y se retiran sus tres handlers; no hay un desinstalador automático que evite por sí solo referencias a scripts ausentes.

Registrar conversación no genera feedback numérico. En v0.4 incluso un feedback con valor cero actualiza competencia y aplica cambios a prioridades y aversión. El aprendizaje numérico continúa ligado a actividades con resultados declarados mediante el protocolo existente. La preferencia expresada por un usuario se conserva en su perfil y no sustituye una preferencia del agente.

## Alternativas consideradas

- Reescribir `SKILL.md` con cada conversación: mezcla instrucciones estables, recuerdos y permisos; dificulta revisar cambios y reinstalar. Se mantiene la evolución en datos y conclusiones con fuentes.
- Modificar el paquete v0.4 para incluir el archivo conversacional: invalida la huella necesaria para continuar historias existentes. La capa separada permite usar el motor compatible sin falsear manifiestos.
- Importar cada mensaje como documento y ejecutarlo como lectura: agota la biblioteca acotada y aplica una recompensa por lectura sin criterio conversacional. Se añade captura sin aprendizaje automático.
- Guardar solo resúmenes recientes: puede perder evidencia, esconder contradicciones y limitar recuperación. Se conservan originales y conclusiones derivadas por separado.
- Declarar presencia automática al instalar la skill: la selección de instrucciones no garantiza ejecución en todos los chats. La configuración, las pruebas del adaptador y la activación real se informan por separado.

## Consecuencias

La identidad puede reconstruir su contexto desde registros persistentes, revisar conclusiones y recuperar episodios anteriores al buffer del motor. La influencia sobre respuestas pasa por el anfitrión; las conclusiones no alteran automáticamente el selector numérico. La expresión puede cambiar al cambiar de modelo aunque el archivo sea idéntico.

El primer corte no ofrece embeddings, eliminación de información, consolidación automática en segundo plano ni una política general para resolver contradicciones. El anfitrión registra revisiones con fuentes. El archivo preserva registros; desactivar captura no equivale a borrarlos. El rendimiento de recuperación, la fidelidad lingüística y una eventual utilidad experimental se evalúan por separado.

No se crean servicios permanentes, programaciones ni presupuestos nuevos. Las simulaciones mantienen su procedencia, los límites del núcleo siguen vigentes y la continuidad funcional no se presenta como prueba de experiencia subjetiva.
