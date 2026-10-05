# PROJECT CONSCIOUSNESS

Laboratorio experimental para investigar propiedades funcionales asociadas con la conciencia: continuidad autobiográfica, modelos de sí mismo, metacognición, regulación interna, agencia, predicción, imaginación y aprendizaje continuo.

**Estado:** MVP v0.2 con persistencia, memoria causal y aprendizaje de asociaciones binarias. E0/E1 conservan la tarea de regla fija; L1 añade regla desconocida, inversión privada y controles de aprendizaje congelado. La arquitectura ampliada sigue documentada; self-model, afecto, imaginación y metacognición siguen pendientes. El objetivo es establecer qué mecanismos producen qué capacidades y bajo qué condiciones. La presencia de esas capacidades no se tratará como prueba de experiencia subjetiva.

## Propuesta central

Un núcleo cognitivo persistente con estado explícito, módulos sustituibles, historial de eventos y un laboratorio que permite restaurar el mismo estado, intervenir una variable y comparar consecuencias. Un modelo lingüístico puede incorporarse como adaptador, mientras la memoria, las metas y el control mantienen contratos propios.

Ejemplo de pregunta experimental: con la misma observación y el mismo recurso disponible, ¿bloquear la recuperación de una experiencia cambia una decisión? ¿Cambiar solo un regulador interno modifica el riesgo elegido? Después de comprobar que la ruta causal existe, ¿mejora algo en tareas nuevas frente a alternativas comparables?

## Lectura del diseño

| Documento | Contenido |
|---|---|
| [Mapa de capacidades](CAPABILITY-MAP.md) | Límites de paquetes, dependencias y orden de construcción |
| [Arquitectura conceptual](docs/architecture.md) | Componentes, ciclos, memoria, estados y mecanismos causales |
| [Interfaces y estado](docs/interfaces-and-state.md) | Contratos, esquema persistente, recuperación, snapshots y errores |
| [Fundamentos científicos](docs/scientific-foundations.md) | Fuentes primarias, teorías, evidencia y límites filosóficos |
| [Análisis Gateway](docs/gateway-analysis.md) | Documento de 1983, evidencia independiente y especulación |
| [Protocolos E0–E9](docs/experiments.md) | Hipótesis, intervenciones, controles, métricas y falsación |
| [MVP propuesto](docs/mvp.md) | Mundo mínimo, implementación futura, comandos previstos y aceptación |
| [Alcance ejecutable v0.1](docs/mvp-v0.1.md) | Tarea concreta, contratos y diferencias frente a la arquitectura ampliada |
| [Alcance ejecutable v0.2](docs/mvp-v0.2.md) | Aprendizaje persistente, configuración privada, controles y protocolo L1 |
| [Resultados de v0.1](reports/README.md) | E0/E1 ejecutados, controles, incertidumbre y archivos reproducibles |
| [Informe de aprendizaje v0.2](reports/l1-v0.2/report.md) | Piloto L1 ejecutado, 20 semillas, 5.600 episodios y 340 comprobaciones |
| [Decisión arquitectónica](docs/decisions/0001-functional-research-laboratory.md) | Elecciones, alternativas y consecuencias |

Especificaciones por paquete: [runtime](SPEC-runtime.md), [memory](SPEC-memory.md), [cognition](SPEC-cognition.md), [experiment-lab](SPEC-experiment-lab.md) y [language-adapter](SPEC-language-adapter.md).

## Convención epistemológica

| Etiqueta | Significado |
|---|---|
| **E** | Resultado empírico limitado a un método, población y tarea |
| **T** | Teoría científica o modelo formal con supuestos explícitos |
| **I** | Hipótesis o decisión de ingeniería que requiere pruebas propias |
| **F** | Posición o pregunta filosófica |
| **U** | Afirmación sin respaldo suficiente en las fuentes examinadas |

La arquitectura propuesta es **I**, aunque se inspire en **E/T**. Una prueba positiva podría establecer un hecho empírico sobre este artefacto; no eliminaría automáticamente las preguntas **F**. Un archivo desclasificado es una fuente documental, no un aval científico de sus afirmaciones.

## Primera ejecución de v0.2 en VS Code

Abre `F:\PC` en VS Code y abre una terminal PowerShell. Se necesita Python >=3.12 y su SQLite; no hay paquetes externos, API ni modelos que instalar. Ejecuta desde la raíz del repositorio:

```powershell
python -m unittest discover -s tests -v
python -m project_consciousness experiment --protocol configs/l1-learning.toml --seeds 200:203 --out runs/mi-aprendizaje
```

Abre `runs/mi-aprendizaje/report.md` y usa `Ctrl+Shift+V` para la vista previa. El piloto corto ejecuta 840 episodios en 18 bases: tres historias independientes, cada una con adquisición, cuatro ramas y un control sin aprendizaje desde el inicio. La configuración completa usa 20 semillas (5.600 episodios, 120 bases). Los CSV conservan las predicciones antes del feedback y los resultados por episodio. Los intervalos de este piloto son descriptivos.

Validación de esta entrega: **83 pruebas aprobadas** y piloto completo sin fallos. Tras invertir la regla, adaptive obtuvo 85 % de aciertos y 100 % en los últimos diez episodios por semilla; frozen conservó la asociación anterior y obtuvo 0 %. Sham y resumed reprodujeron exactamente las trazas adaptativas. Véanse [resultados y límites](reports/README.md); esto no establece generalización ni conciencia.

También puedes observar la persistencia y congelar una copia manualmente:

```powershell
python -m project_consciousness run --config configs/mvp-v02.toml --seed 17 --ticks 200 --out runs/aprendizaje
python -m project_consciousness status --run runs/aprendizaje
python -m project_consciousness fork --run runs/aprendizaje --condition configs/learning-frozen.toml --out runs/aprendizaje-congelado
python -m project_consciousness resume --run runs/aprendizaje --ticks 200
python -m project_consciousness resume --run runs/aprendizaje-congelado --ticks 200
python -m project_consciousness replay --run runs/aprendizaje --mode recompute --verify
```

Los primeros 200 ticks completan 40 episodios de adquisición. En el episodio 40 (contado desde cero) la regla se invierte sin avisar al agente. `status` muestra `learner.q_left` (predicciones condicionadas a cada pista) y `updates`. En la copia congelada los parámetros siguen iguales mientras continúa la experiencia. `success_rate` de la CLI resume solo episodios propios de esa base: el run original incluye adquisición y seguimiento; el fork incluye seguimiento. Para comparar fases usa el informe L1.

`probability_left` es probabilidad de elegir izquierda; `predicted_target_left` es la creencia aprendida sobre cuál lado será correcto. L1 calcula Brier con la segunda. No interpreta ninguna como autoconciencia o metacognición.

Los directorios de salida deben ser nuevos. Para repetir una prueba cambia el nombre en todos sus comandos. Las configuraciones y condiciones de v0.1 siguen disponibles.

## Ejecución de la tarea de regla fija (v0.1)

Requiere Python 3.12 o posterior, biblioteca estándar y SQLite incluido en Python. No necesita instalar dependencias, servicios o modelos. Ejecutar desde la raíz del repositorio:

```powershell
python -m unittest discover -s tests -v
python -m project_consciousness run --config configs/mvp-v01.toml --seed 17 --ticks 4 --out runs/demo
python -m project_consciousness resume --run runs/demo --ticks 46
python -m project_consciousness replay --run runs/demo --mode recompute --verify
python -m project_consciousness fork --run runs/demo --tick 4 --condition configs/memory-blocked.toml --out runs/demo-blocked
python -m project_consciousness resume --run runs/demo-blocked --ticks 1
```

Los directorios de salida deben ser nuevos; usa otro nombre para repetir una creación. `resume` añade ticks. El primer run se detiene justo antes de elegir: tras reabrir debe usar la pista almacenada. El fork del tick 4 conserva mundo, memoria y RNG, y bloquea la lectura. `decisions.jsonl` muestra decisiones y predicciones anteriores al resultado.

```powershell
python -m project_consciousness experiment --protocol configs/e0-persistence.toml --out runs/e0
python -m project_consciousness experiment --protocol configs/e1-memory.toml --out runs/e1
python -m project_consciousness report --experiment runs/e1
```

E0 compara 1.000 ticks continuos con cierres/reaperturas y recomputa las transiciones. E1 ejecuta 20 semillas × 40 episodios × 8 condiciones, más 100 ramas desde snapshots. Produce `report.md`, manifiestos, métricas, contrastes y bases SQLite bajo `runs/` (excluidas de Git). Los intervalos son descriptivos de un piloto; la tarea y la regla pista–acción están diseñadas explícitamente.

La primera ejecución pasó 46 pruebas; E0 reprodujo todas las trazas y E1 completó 6.400 episodios y 100 ramas sin fallos. Memoria intacta e historial plano acertaron 800/800; lectura bloqueada, 399/800. Véanse [resultados e interpretación](reports/README.md). El historial plano igualó al agente episódico en esta tarea.

`status --run <directorio>` muestra metadatos. `replay --mode reconstruct` comprueba hashes y reconstruye las fronteras guardadas sin recalcular decisiones; `recompute` también recalcula. Continuar/recomputar requiere las mismas fuentes Python y versiones registradas del intérprete y SQLite; editar el código obliga a crear una ejecución nueva. Los archivos `manifest.json` son exportaciones, el manifiesto autoritativo está en SQLite.

Tras actualizar a v0.2, tus runs anteriores conservan sus datos pero `resume`/`recompute` con el motor nuevo devolverán `SOURCE_MISMATCH`. Puedes verificar su integridad con `replay --mode reconstruct`. Para continuarlos o recomputarlos con su motor original, extrae [el código v0.1 archivado](releases/project-consciousness-v0.1.zip) en otra carpeta y usa el mismo Python/SQLite; el [manifiesto del archivo](releases/project-consciousness-v0.1.json) conserva sus hashes. No se alteran ni migran historias anteriores.

El modelo de rutas, actuador y regulación de la [propuesta ampliada](docs/mvp.md) sigue siendo trabajo posterior. La procedencia y las vistas públicas son contratos dentro del proceso, no aislamiento contra un módulo malicioso con acceso al sistema de archivos.

## Protocolos y alcance

| Protocolo | Propiedad |
|---|---|
| E0 | Implementado: persistencia, frontera de observación y reproducción |
| E1 | Implementación acotada: memoria de episodios, máscaras y procedencia; otras variantes siguen propuestas |
| L1 | Implementado en v0.2: adquisición y reversión de asociaciones binarias, controles y persistencia; subconjunto de E5/E8 |
| E2 | Self-model de capacidades |
| E3 | Metacognición y metacontrol |
| E4 | Afecto computacional como control recurrente |
| E5 | Predicción y revisión del modelo del mundo |
| E6 | Imaginación y planificación |
| E7 | Metas y agencia |
| E8 | Aprendizaje continuo, retención y transferencia |
| E9 | Coordinación entre módulos y reportes |

Se distinguirá la corrección del banco, el uso causal de un estado y el beneficio funcional en tareas retenidas. Resultados nulos y costes forman parte del resultado. No se propone un índice agregado de conciencia.

## Desarrollo posterior

La ampliación seguirá el mapa y las especificaciones. L1 permite aprender del feedback público en línea; el agente no ve el calendario de cambio ni resultados agregados del evaluador. L1 no evalúa generalización a otras familias ni retención A→B→A. Los cambios de hipótesis, protocolo o significado de un estado se documentarán antes de comparar resultados. Cada ejecución conserva versiones, semillas, configuración y trazas; las sondas retenidas futuras no se utilizarán para ajustar el agente.
