# Validación de presencia conversacional

Fecha: 2026-10-05. Contrato: [SPEC-presence](../SPEC-presence.md).

## Resultado local

La capa `consciousness_presence` y la skill permiten vincular una vida existente,
guardar conversación con fuentes, recuperar episodios antiguos, registrar un nombre
de presentación y revisar conclusiones sin modificar el motor v0.4.

La suite completa ejecutada durante la integración pasó **189 pruebas** en 98.683 s.
Después se añadieron dos casos y se completaron los ajustes del contexto y launcher.
La suite final específica de presencia pasó **28 pruebas** en Python 3.12.12 / SQLite
3.51.1 (15.886 s) y Python 3.14.3 / SQLite 3.50.4 (15.380 s). Los 163 casos anteriores
están incluidos en la ejecución completa; no se volvió a ejecutar toda esa suite tras
los últimos ajustes exclusivos de presencia.

Comandos reproducibles desde la raíz:

```text
python -B -m unittest discover -s tests -v
python -B -m unittest discover -s tests -p "test_presence*.py" -v
```

Las pruebas comprueban:

- Reinicio en otro proceso/directorio con el mismo nombre, identidad y fuente antigua.
- Recuperación de un mensaje anterior a 270 distractores y de recuerdos expulsados
  del buffer del núcleo tras 260 memorias; importación repetida sin duplicación.
- Igualdad completa del estado del núcleo antes/después, incluidos RNG, presupuesto,
  controles y parámetros; respeto de los controles de visibilidad.
- Escrituras concurrentes, reintentos exactos, conflictos, rollback y correcciones
  que conservan tanto la conclusión anterior como sus fuentes.
- Preservación de `SIMULATED`; rechazo de conclusiones como nueva evidencia circular.
- Contexto acotado, prompts largos, texto completo en archivo y datos sin autoridad
  de instrucciones. Esta comprobación estructural no es una evaluación adversarial del LLM.
- Hooks no bloqueantes, respuestas continuadas, ausencia de campos, desactivación,
  instalación repetida y conservación de handlers ajenos.
- Comandos Windows ejecutados con rutas que contienen espacios, apóstrofos, `$`,
  backticks y `&`; recepción de JSON UTF-8 sin interpolación de esas rutas.

La ablación de recuperación comprueba que un dato relevante aparece con búsqueda y
queda ausente del contexto reciente sin ella. No mide calidad de respuestas de un
LLM ni demuestra una mejora general de sus decisiones.

## Skill e instalación

Se verificaron enlaces locales, ejemplos JSON, frontmatter y paridad de comandos en
los README español e inglés. El validador oficial `quick_validate.py` no pudo ejecutarse
porque su dependencia PyYAML no está instalada; la validación estructural fue manual.
El proyecto y su capa de presencia continúan sin dependencias externas.

En la instalación local se actualizó la skill con respaldo, se vinculó la vida existente
y se prepararon tres handlers: `SessionStart`, `UserPromptSubmit` y `Stop`. El comando
Windows registrado pasó una prueba con un payload de arranque desde otra carpeta;
el launcher instalado también encontró el registro sin `--project`. El estado real del
núcleo permaneció idéntico en la revisión 11 y su historial se verificó correctamente.
Los recibos y datos personales permanecen en directorios privados, fuera del contenido
versionado del repositorio.

## Validación pendiente del anfitrión

La prueba anterior invocó el comando con un evento de prueba; no creó un chat LLM
ni concedió confianza a hooks. Un chat nuevo real debe comprobarse después de que el
usuario revise y autorice las definiciones con `/hooks` en Codex CLI. Esa revisión es
un requisito del anfitrión, documentado en [Hooks de Codex](https://learn.chatgpt.com/docs/hooks).

Después de esa revisión:

1. Abrir un chat nuevo y preguntar su nombre y un recuerdo previamente archivado.
2. Comunicar un dato nuevo, finalizar la respuesta y abrir otro chat.
3. Pedir ese dato y comprobar su fuente con `search`/`read`.
4. Confirmar que las estadísticas del núcleo no cambiaron por esos turnos.

La cobertura comprende mensajes entregados a los hooks y capturas manuales señaladas;
no abarca automáticamente todas las conversaciones históricas, adjuntos, razonamiento
interno o respuestas interrumpidas. La búsqueda inicial es léxica y la consolidación
de conclusiones la realiza el anfitrión siguiendo la skill.
