# PROJECT CONSCIOUSNESS

[Español](README.md) | [English](README.en.md)

**Un laboratorio experimental de código abierto para investigar propiedades funcionales asociadas con la conciencia.**

El proyecto construye sistemas con memoria persistente, modelos de capacidades propias, preferencias aprendidas, preguntas y simulación. Su pregunta central es cómo los estados internos modifican causalmente las decisiones posteriores y qué ocurre al intervenir esos estados.

El proyecto nace de una iniciativa de investigación sin fines de lucro, dedicada a la exploración científica, computacional y filosófica. Su objetivo es producir experimentos reproducibles sobre esas propiedades. Los resultados no se interpretan como demostraciones de experiencia subjetiva.

**Versión actual: MVP v0.4.** Núcleo en Python, persistencia SQLite, experimentos controlados y una skill para conectar un agente LLM como Codex. Se agradecen aportaciones de programación, metodología, ciencia cognitiva, filosofía, documentación y reproducción independiente de resultados.

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

- Recuperación y consolidación de memoria más allá del buffer actual.
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
- Especificaciones de [runtime](SPEC-runtime.md), [memoria](SPEC-memory.md), [cognición](SPEC-cognition.md), [laboratorio](SPEC-experiment-lab.md) y [adaptador lingüístico](SPEC-language-adapter.md).
- [Historial de cambios](CHANGELOG.md) y [resultados de las distintas versiones](reports/README.md).

## Criterio científico y límites

La documentación distingue resultados empíricos (**E**), teorías o modelos (**T**), decisiones de ingeniería (**I**), cuestiones filosóficas (**F**) y afirmaciones sin respaldo suficiente (**U**). Una implementación inspirada en una teoría sigue necesitando sus propias pruebas. El análisis del Gateway Process separa el contenido documental de su respaldo científico; la desclasificación no se considera un aval de sus afirmaciones.

Los recuerdos distinguen `OBSERVED`, `REPORTED`, `INFERRED` y `SIMULATED`. El aprendizaje actual modifica parámetros del núcleo, no los pesos del LLM. Las cinco dimensiones de preferencia son fijas; los sueños locales usan plantillas; las preguntas aún no tienen una operación de cierre. Los conceptos de personalidad, miedo o trauma humano no se consideran demostrados por estos estados numéricos.

No se propone una puntuación agregada que certifique conciencia. El valor del proyecto está en hacer explícitos sus mecanismos, probarlos y permitir que otras personas cuestionen y reproduzcan sus resultados.

## Licencia

PROJECT CONSCIOUSNESS se distribuye bajo la [licencia MIT](LICENSE). Permite usar, copiar, modificar, distribuir y comercializar el software, incluidas las modificaciones privadas, siempre que se conserven el aviso de copyright y el aviso de permiso en todas las copias o porciones sustanciales del software. No exige publicar las modificaciones.

El propósito de investigación sin fines de lucro de este proyecto no limita esos permisos. El texto completo de `LICENSE` establece las condiciones y la exclusión de garantías.

Si utilizas el proyecto en una investigación, producto o trabajo derivado, se agradece que menciones **PROJECT CONSCIOUSNESS, por AeonMuller**, y enlaces al [repositorio original](https://github.com/AeonMuller/PROJECT-CONSCIOUSNESS). Esta mención pública es una solicitud voluntaria, adicional a la obligación de conservar los avisos de MIT.
