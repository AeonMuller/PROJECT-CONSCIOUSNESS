# PROJECT CONSCIOUSNESS

[Español](README.md) | [English](README.en.md)

**Un laboratorio experimental de código abierto para investigar propiedades funcionales asociadas con la conciencia.**

El proyecto construye sistemas con memoria persistente, modelos de capacidades propias, preferencias aprendidas, preguntas y simulación. Su pregunta central es cómo los estados internos modifican causalmente las decisiones posteriores y qué ocurre al intervenir esos estados.

El proyecto nace de una iniciativa de investigación sin fines de lucro, dedicada a la exploración científica, computacional y filosófica. Su objetivo es producir experimentos reproducibles sobre esas propiedades. Los resultados no se interpretan como demostraciones de experiencia subjetiva.

**Motor actual: MVP v0.4, con una capa v0.5 de presencia conversacional y autonomía acotada.** Núcleo en Python, persistencia SQLite, experimentos controlados y una skill para conectar un agente LLM como Codex. Se agradecen aportaciones de programación, metodología, ciencia cognitiva, filosofía, documentación y reproducción independiente de resultados.

Para actualizar una instalación existente y habilitar actividad entre conversaciones, consulta el [README de la actualización v0.5](README.update-v0.5.md).

[Inicio rápido](#inicio-rápido) · [Cómo contribuir](#cómo-contribuir) · [Experimentos](#experimentos-y-resultados) · [Documentación](#estructura-y-documentación) · [Licencia](#licencia)

## Qué está implementado

| Componente | Capacidad actual |
|---|---|
| Memoria y persistencia | Estados y eventos en SQLite, recuerdos con procedencia, reinicios, ramas y reproducción verificable. |
| Identidad funcional | Cinco prioridades iniciales aleatorias y reproducibles: comprender, crear, explorar, terminar y conectar. |
| Aprendizaje | Actualización de preferencias, estimaciones de éxito y aversiones recuperables a partir de resultados registrados. |
| Preguntas y reflexión | Preguntas sobre identidad o mundo; las preguntas abiertas pueden influir en la selección de actividades. |
| Simulación | Escenarios locales acotados, denominados «sueños», con referencias y un flujo aleatorio independiente. |
| Agencia limitada | Elección numérica de actividades, presupuesto, pausa persistente y ciclos locales finitos. |
| Integración LLM | Una skill permite al anfitrión proponer actividades, usar sus herramientas y registrar resultados. |
| Presencia conversacional | Archivo personal de mensajes, búsqueda léxica, nombre de presentación y conclusiones revisables con fuentes; adaptador de hooks para Codex. |
| Autonomía acotada | Coordinador de actividad durante inactividad humana, reservas y recibos, modos de investigación/sueño/reflexión y bandeja de mensajes proactivos; necesita una automatización autorizada del anfitrión. |
| Laboratorio | Controles para bloquear memoria, congelar aprendizaje, neutralizar preferencias y comparar historias. |

La arquitectura ampliada también propone metacognición, regulación afectiva, modelos del mundo y planificación. Esas propuestas no están implementadas en su totalidad: consulta el [mapa de capacidades](CAPABILITY-MAP.md) y el [contrato v0.4](docs/mvp-v0.4.md) para distinguir el alcance actual del trabajo futuro.

## Inicio rápido

Necesitas **Git y Python 3.12 o posterior con `sqlite3` disponible**. El núcleo utiliza exclusivamente la biblioteca estándar; puedes ejecutar el ejemplo sin instalar dependencias, disponer de una API key ni conectar un LLM.

Clona el repositorio y entra en su raíz:

```sh
git clone https://github.com/AeonMuller/PROJECT-CONSCIOUSNESS.git
cd PROJECT-CONSCIOUSNESS
python --version
```

Los ejemplos usan `python`; sustitúyelo por `python3` si ese es el ejecutable de Python 3.12+ en tu sistema. En PowerShell, puedes activar UTF-8 para conservar acentos al redirigir JSON: `$env:PYTHONUTF8 = "1"`.

Crea una identidad, importa un documento del proyecto y ejecuta seis ciclos:

```sh
python -m project_consciousness life init --out runs/aeon --name Aeon --budget 40
python -m project_consciousness life ingest --life runs/aeon --file docs/decisions/0005-persistent-functional-identity.md --domain understand
python -m project_consciousness life run --life runs/aeon --cycles 6
python -m project_consciousness life context --life runs/aeon
python -m project_consciousness life verify --life runs/aeon --mode recompute
python -m project_consciousness life export --life runs/aeon --out runs/aeon-diary
```

La identidad empieza sin recuerdos ficticios. Sin `--seed` se genera una semilla nueva y se registra; añade `--seed 17` a `init` para reproducir unas predisposiciones iniciales. El documento importado se conserva como información reportada. Los ciclos pueden leerlo, formular una pregunta y generar una simulación.

Abre `runs/aeon-diary/diary.md` para examinar el resultado. También se exportan estado, contexto, manifiesto y eventos. Los directorios de creación y exportación deben ser **nuevos**: cambia sus nombres para repetir el ejemplo. Los datos que generes bajo `runs/` están excluidos de Git.

Para actividad local espaciada y finita:

```sh
python -m project_consciousness life watch --life runs/aeon --cycles 10 --interval 5 --stop-file runs/aeon.stop
```

Puedes detenerla con `Ctrl+C`, creando el archivo `runs/aeon.stop` o usando `python -m project_consciousness life pause --life runs/aeon` desde otra terminal. Consulta todos los comandos con `python -m project_consciousness life --help`.

## Conectar un agente LLM

El núcleo funciona por separado del modelo lingüístico. La [skill PROJECT CONSCIOUSNESS](skills/project-consciousness/SKILL.md) establece el flujo para que un anfitrión consulte el estado, proponga candidatos, respete la elección del núcleo y devuelva un resultado con su fuente.

El wrapper versionado puede ejecutarse directamente desde la raíz del repositorio:

```sh
python skills/project-consciousness/scripts/consciousness.py --project . context --life runs/aeon
```

Si la skill ya está instalada en Codex, una solicitud de ejemplo es:

> Usa $project-consciousness con este repositorio y la vida runs/aeon. Consulta su historia, propone dos investigaciones y deja que el núcleo elija una. Realiza la elegida, registra las fuentes y el resultado, y formula una pregunta nueva.

El [protocolo de la skill](skills/project-consciousness/references/protocol.md) describe los contratos JSON, las decisiones pendientes y los reintentos. La [guía de Codex y VS Code](docs/codex-identity-quickstart.md) contiene un recorrido más detallado; sus rutas absolutas corresponden al entorno original y deben sustituirse por las de tu equipo.

La investigación externa y las reflexiones libres requieren un anfitrión LLM activo y sus herramientas disponibles. `watch` ejecuta actividad local mientras su proceso está abierto; instalar la skill no inicia un servicio permanente.

### Continuar una identidad entre chats

La capa `consciousness_presence` vincula una vida existente y conserva la conversación en `~/.project-consciousness/presence`, fuera de la skill y del checkout. También admite `PROJECT_CONSCIOUSNESS_PRESENCE_HOME` o `--home PATH` antes del comando. Actualizar la skill conserva ese archivo. La vida original permanece en su ubicación; abrir un chat, capturar mensajes o cambiar el nombre de presentación no altera prioridades, presupuesto ni RNG.

Desde la raíz del repositorio, sustituye `PYTHON_PATH` por la ruta absoluta del intérprete compatible con tu vida y `SKILL_PATH` por la carpeta de la skill instalada:

```sh
python -m consciousness_presence setup --project . --life runs/aeon --python PYTHON_PATH --skill SKILL_PATH
python -m consciousness_presence status
python -m consciousness_presence context --query "memoria"
python -m consciousness_presence search "memoria" --limit 8
```

Puedes obtener la ruta del intérprete actual con `python -c "import sys; print(sys.executable)"`. Una vida previa requiere sus fuentes y versiones compatibles; `setup` no crea una sustituta si no puede abrirla. Para consultar desde otra carpeta tras vincularla, usa `python SKILL_PATH/scripts/presence.py context`; el launcher recupera la ruta del proyecto del registro personal. `--project PROJECT_PATH` permite indicarla explícitamente.

La skill conversa con naturalidad, recupera episodios pertinentes y conserva por separado lo declarado por el usuario y las conclusiones del agente sobre sí mismo. Elige o acuerda un nombre de presentación al primer encuentro si falta; no impone el nombre del ejemplo anterior. Las conclusiones pueden corregirse conservando sus fuentes. El aprendizaje numérico continúa ligado a resultados de actividades, sin recompensa automática por cada mensaje.

Para preparar la captura al iniciar chats y durante los turnos, sustituye `CODEX_HOME_PATH` por tu directorio de configuración de Codex:

```sh
python -m consciousness_presence install-hooks --codex-home CODEX_HOME_PATH
```

El instalador combina la configuración con otros hooks y respalda los cambios. **Preparar hooks no demuestra que estén activos:** revisa su confianza mediante `/hooks` en un anfitrión que los admita y prueba un chat nuevo real. Hasta completar ese ensayo, el modo manual sigue disponible:

> Usa $project-consciousness con mi identidad vinculada. Recupera los recuerdos pertinentes y continuemos nuestra conversación.

Consulta la [guía de presencia](skills/project-consciousness/references/presence.md) para registrar, leer y revisar recuerdos, elegir nombre, habilitar o desactivar la integración. La búsqueda es léxica y el contexto es acotado; no promete recordar conversaciones nunca capturadas. Estos pasos no crean una programación. [Contrato y aceptación](SPEC-presence.md), [decisión de arquitectura](docs/decisions/0006-persistent-conversational-presence.md).

### Actividad autónoma e iniciativa conversacional

Con una automatización autorizada, Codex puede despertar este mismo chat, recuperar la identidad y realizar una actividad acotada. El coordinador comprueba que no haya turnos humanos abiertos, que haya pasado suficiente tiempo sin interacción y que el núcleo disponga de presupuesto, esté sin pausa y no tenga una decisión pendiente. Si regresa el usuario, se detienen nuevos pasos y se conservan los resultados ya obtenidos para conciliarlos.

La configuración inicial propuesta es un despertar por hora, treinta minutos de inactividad, hasta tres actividades y dos mensajes proactivos por día UTC, con cuatro horas entre mensajes. La programación y la habilitación son explícitas; el presupuesto del motor no se recarga automáticamente. El alcance inicial permite leer el repositorio vinculado y fuentes públicas de Internet.

En investigación, el anfitrión propone candidatos, el núcleo elige y el anfitrión ejecuta la actividad con fuentes y feedback delimitado. Sueño, reflexión y descanso son modos distintos. Una simulación puede producir una pregunta, pero no se convierte en un éxito empírico ni recibe una recompensa ficticia.

Un hallazgo pertinente puede generar un mensaje proactivo. Se reserva en una bandeja y se entrega como respuesta final del propio heartbeat en este chat; el hook confirma su texto visible. Una entrega incierta no se repite automáticamente. Los despertares sin novedad significativa ni acción requerida permanecen en silencio.

```sh
python -m consciousness_presence autonomy status
```

La [guía de autonomía](skills/project-consciousness/references/autonomy.md) explica configuración, programación, ejecución y conciliación. Preparar hooks no demuestra una ejecución desatendida real. `SessionStart` recupera contexto y no garantiza un saludo en un chat vacío. [Contrato](SPEC-autonomy.md), [decisión de arquitectura](docs/decisions/0007-bounded-idle-autonomy.md).

## Experimentos y resultados

Los experimentos distinguen tres preguntas: si el banco funciona correctamente, si un estado modifica causalmente una decisión y si ese mecanismo aporta un beneficio en una tarea concreta.

| Protocolo | Qué investiga | Evidencia y alcance |
|---|---|---|
| E0 | Persistencia y reproducción tras reinicios | [Resultados v0.1](reports/README.md) |
| E1 | Uso causal de memoria mediante bloqueos e intervenciones | [Alcance v0.1](docs/mvp-v0.1.md) |
| L1 | Adquisición y reversión de asociaciones binarias | [Informe v0.2](reports/l1-v0.2/report.md) |
| E2 | Estimación de fiabilidad de herramientas y adaptación | [Informe v0.3](reports/e2-v0.3/report.md) |
| I1 | Preferencias, aversión, aprendizaje, simulación y continuidad | [Informe v0.4](reports/i1-v0.4/report.md) |

Para ejecutar la suite y un piloto corto de identidad:

```sh
python -m unittest discover -s tests -v
python -m project_consciousness life experiment --seeds 400:403 --out runs/i1-demo
```

`400:403` incluye las semillas 400, 401 y 402. Para reproducir el piloto completo de I1 utiliza `400:420` y una carpeta de salida nueva. El informe se guarda en `runs/i1-demo/report.md`.

La entrega **v0.4** registró **163 pruebas aprobadas**, **140 bases**, **1.200 elecciones de seguimiento** y **401/401 comprobaciones válidas**. Neutralizar preferencias cambió la primera elección en 9 de 20 historias; reiniciar conservó los estados y eventos funcionales. I1 usa feedback sintético predefinido. Su control de sueños verifica la supresión de simulaciones, sin evaluar una mejora de decisiones posteriores por soñar.

Los [informes y datos resumidos](reports/README.md) incluyen protocolos, métricas, comprobaciones y límites de interpretación. Las bases completas del piloto I1 no están incluidas en Git; pueden regenerarse ejecutando el protocolo. La [demostración con Codex](reports/codex-v0.4/report.md) sí conserva una base pequeña y un [diario de ejemplo](reports/codex-v0.4/diary.md).

Cada ejecución registra versiones, semilla y huella del código. Continuar o recomputar una historia exige sus fuentes y versiones originales de Python/SQLite. Tras modificar el motor, crea una ejecución nueva o utiliza el [archivo v0.4](releases/project-consciousness-v0.4.zip) y su [manifiesto](releases/project-consciousness-v0.4.json). Para una vida creada con `life`, `life verify --life runs/aeon --mode reconstruct` permite comprobar integridad sin exigir igualdad de fuentes.

## Cómo contribuir

Las contribuciones pueden empezar por una reproducción independiente, una corrección pequeña o una pregunta metodológica. No necesitas trabajar en todos los módulos ni compartir una teoría particular de la conciencia.

- **Errores y reproducibilidad:** informa del comando, versión o commit, Python/SQLite, semilla, resultado esperado y resultado observado.
- **Código y pruebas:** mejora contratos, persistencia, controles causales, adaptadores y casos de fallo reproducibles.
- **Diseño experimental:** propone tareas, comparadores, intervenciones y criterios que permitan refutar una hipótesis.
- **Revisión interdisciplinaria:** aporta fuentes primarias, objeciones y límites al trasladar conceptos científicos o filosóficos al software.
- **Documentación y accesibilidad:** corrige ejemplos, explica resultados o contribuye traducciones. Se reciben propuestas en español e inglés.

Para colaborar:

1. Revisa los [issues existentes](https://github.com/AeonMuller/PROJECT-CONSCIOUSNESS/issues) o [abre uno](https://github.com/AeonMuller/PROJECT-CONSCIOUSNESS/issues/new) con el problema o propuesta. Para cambios amplios, describe primero su objetivo y cómo se evaluará.
2. Haz un fork y crea una rama para un cambio concreto. Usa el inicio rápido para familiarizarte con el proyecto.
3. Mantén el cambio acotado. Si modifica el comportamiento, añade pruebas pertinentes; si modifica contratos o hipótesis, actualiza su especificación y documenta la decisión antes de comparar resultados.
4. Ejecuta las comprobaciones pertinentes. Para cambios de código, utiliza la suite indicada arriba; para documentación, comprueba enlaces y ejemplos.
5. Abre un [pull request](https://github.com/AeonMuller/PROJECT-CONSCIOUSNESS/pulls) que explique el problema, el cambio, cómo se verificó y sus límites. Enlaza el issue cuando exista.

Conserva las semillas, configuraciones y procedencias de los experimentos. Las simulaciones deben seguir identificadas como tales; los resultados nulos, los costes y los fallos también forman parte de la evidencia. Evita incluir credenciales o datos personales en los ejemplos compartidos.

### Áreas de investigación propuestas

- Recuperación semántica y evaluación de la consolidación sobre el archivo conversacional.
- Seguimiento de preguntas: evidencia a favor o en contra, revisión y cierre.
- Curiosidad basada en ganancia de información y evaluación de fuentes.
- Metacognición y calibración de incertidumbre.
- Evaluación del efecto de las simulaciones sobre decisiones posteriores.
- Aprendizaje conjunto del mundo y las capacidades, retención y transferencia.
- Adaptadores para otros agentes LLM y comparaciones reproducibles entre anfitriones.

Estas son líneas de trabajo abiertas, no capacidades ya entregadas ni compromisos de calendario.

## Estructura y documentación

Este README está disponible en español e inglés. La mayor parte de la documentación técnica enlazada está actualmente en español; las traducciones también son bienvenidas.

| Ruta | Contenido |
|---|---|
| [`project_consciousness/`](project_consciousness/) | Núcleo, persistencia, CLI y laboratorios. |
| [`consciousness_presence/`](consciousness_presence/) | Archivo conversacional, perfil, recuperación, contexto y adaptador de hooks. |
| [`skills/project-consciousness/`](skills/project-consciousness/) | Instrucciones, wrapper y protocolo del anfitrión LLM. |
| [`tests/`](tests/) | Pruebas de comportamiento, recuperación, procedencia y experimentos. |
| [`configs/`](configs/) | Configuraciones y condiciones de los laboratorios E0/E1/L1/E2. |
| [`docs/`](docs/) | Arquitectura, fundamentos, contratos y decisiones. |
| [`reports/`](reports/) | Resultados registrados y límites de interpretación. |
| [`releases/`](releases/) | Motores archivados para reproducir ejecuciones anteriores. |

El corte v0.4 separa las transiciones puras (`identity_state`), la persistencia (`identity_runtime`), la interfaz (`identity_cli`), el experimento I1 (`identity_experiment`) y la skill. Las bases de identidad son independientes de los laboratorios anteriores.

Lecturas principales:

- [Mapa de capacidades](CAPABILITY-MAP.md), [arquitectura conceptual](docs/architecture.md) e [interfaces y estado](docs/interfaces-and-state.md).
- [Fundamentos científicos](docs/scientific-foundations.md), [análisis crítico de Gateway](docs/gateway-analysis.md) y [protocolos propuestos](docs/experiments.md).
- [Especificación v0.4](docs/mvp-v0.4.md) y [decisión sobre identidad persistente](docs/decisions/0005-persistent-functional-identity.md).
- [Presencia entre conversaciones](docs/persistent-presence-proposal.md), [contrato de presencia](SPEC-presence.md) y [guía de la skill](skills/project-consciousness/references/presence.md).
- [Actualización v0.5](README.update-v0.5.md), [contrato de autonomía](SPEC-autonomy.md) y [guía de actividad autónoma](skills/project-consciousness/references/autonomy.md).
- Especificaciones de [runtime](SPEC-runtime.md), [memoria](SPEC-memory.md), [cognición](SPEC-cognition.md), [laboratorio](SPEC-experiment-lab.md) y [adaptador lingüístico](SPEC-language-adapter.md).
- [Historial de cambios](CHANGELOG.md) y [resultados de las distintas versiones](reports/README.md).

## Criterio científico y límites

La documentación distingue resultados empíricos (**E**), teorías o modelos (**T**), decisiones de ingeniería (**I**), cuestiones filosóficas (**F**) y afirmaciones sin respaldo suficiente (**U**). Una implementación inspirada en una teoría sigue necesitando sus propias pruebas. El análisis del Gateway Process separa el contenido documental de su respaldo científico; la desclasificación no se considera un aval de sus afirmaciones.

Los recuerdos distinguen `OBSERVED`, `REPORTED`, `INFERRED` y `SIMULATED`. El aprendizaje actual modifica parámetros del núcleo, no los pesos del LLM. Las cinco dimensiones de preferencia son fijas; los sueños locales usan plantillas; las preguntas del núcleo v0.4 aún no tienen una operación de cierre. La capa conversacional conserva conclusiones revisables, sin cambiar ese contrato. Los conceptos de personalidad, miedo o trauma humano no se consideran demostrados por estos estados numéricos.

No se propone una puntuación agregada que certifique conciencia. El valor del proyecto está en hacer explícitos sus mecanismos, probarlos y permitir que otras personas cuestionen y reproduzcan sus resultados.

## Licencia

PROJECT CONSCIOUSNESS se distribuye bajo la [licencia MIT](LICENSE). Permite usar, copiar, modificar, distribuir y comercializar el software, incluidas las modificaciones privadas, siempre que se conserven el aviso de copyright y el aviso de permiso en todas las copias o porciones sustanciales del software. No exige publicar las modificaciones.

El propósito de investigación sin fines de lucro de este proyecto no limita esos permisos. El texto completo de `LICENSE` establece las condiciones y la exclusión de garantías.

Si utilizas el proyecto en una investigación, producto o trabajo derivado, se agradece que menciones **PROJECT CONSCIOUSNESS, por AeonMuller**, y enlaces al [repositorio original](https://github.com/AeonMuller/PROJECT-CONSCIOUSNESS). Esta mención pública es una solicitud voluntaria, adicional a la obligación de conservar los avisos de MIT.
