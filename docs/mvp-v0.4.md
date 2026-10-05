# MVP v0.4: identidad funcional persistente y skill LLM

Estado: implementación autorizada por «Bueno, creo que ya tenemos todo lo necesario, ahora, continúa». Fecha de trabajo: 2026-10-05. Continúa los experimentos v0.1–v0.3 y conserva sus archivos. Ingeniería experimental **I**, con resultados del artefacto **E** delimitados; la atribución de experiencia subjetiva permanece abierta. No se etiquetan aversiones numéricas como trauma clínico.

## Objetivo, mapa y decisiones de alcance

Entregar una skill reutilizable para agentes LLM junto con un núcleo persistente: prioridades iniciales aleatorias reproducibles, aprendizaje de preferencias y aversiones recuperables, recuerdos con procedencia, preguntas sobre identidad/mundo y ciclos autónomos de lectura local, reflexión y simulación. El usuario ya decidió inicialización aleatoria y evolución por historia; esa autorización cubre la especificación e implementación de este corte sin otra aprobación intermedia.

| Módulo estable | Responsabilidad | Dependencias |
|---|---|---|
| identity-state | Estado, elección causal y actualizaciones puras | contratos JSON existentes |
| identity-runtime | SQLite, eventos idempotentes, ramas y reproducción | identity-state |
| identity-interface | CLI, corpus local y ejecución finita interrumpible | identity-runtime |
| identity-skill | Contexto para LLM, propuestas, investigación y devolución de resultados | identity-interface |
| identity-lab | Controles de historia, aprendizaje, aversión y simulación | identity-runtime |

El LLM anfitrión aporta lenguaje, nuevas hipótesis e investigación con sus herramientas disponibles. La skill por sí sola no inicia un proceso permanente ni concede herramientas. El ejecutor local avanza sin mensajes humanos mientras corre, con número de ciclos, intervalo y archivo de parada explícitos. En este corte investiga documentos importados; la investigación externa se realiza mediante el anfitrión y queda registrada como feedback declarado por él. No se configura un proveedor de pago ni se instala un servicio de arranque del equipo.

## Contrato identity-state

Archivo `project_consciousness/identity_state.py`. API pública:

```python
DOMAINS = ("understand", "create", "explore", "finish", "connect")
initial_state(seed: int, name: str = "Aeon", budget: int = 100) -> dict
validate_state(state: dict) -> None
transition(state: dict, request: dict) -> tuple[dict, dict]
public_context(state: dict) -> dict
```

Estado JSON completo: `schema_version=1`, `agent_id` determinista por seed/nombre, `name`, `seed`, `revision`, `initial_priorities`, `priorities` (mapas positivos normalizados de los cinco dominios), `aversions` (cinco números [0,1]), `competence` (por dominio alpha/beta positivos), `traits` (curiosity/caution iniciales [0,1]), `memories` (máximo 256), `questions` (máximo 64), `library` (máximo 64 documentos importados), `pending` (null o una elección externa), `controls`, `budget_remaining`, `cycles`, `rng` (streams policy/dream serializados). Las dimensiones y reglas son decisiones del diseñador; aleatoriedad no equivale a libertad subjetiva.

`controls` exactamente `learning_enabled`, `preferences_visible`, `aversion_visible`, `dream_enabled`, `paused`, todos booleanos, inicialmente true salvo paused. Congelar aprendizaje preserva prioridades/aversiones/competence y sigue registrando memoria. Neutralizar preferencias entrega cinco valores .2 al selector; ocultar aversión entrega ceros. Nunca altera presupuestos ni habilita herramientas.

Cada memoria lleva `id`, `revision`, `kind`, `domain`, `text`, `source_kind`, `source_uri`, `references` y `data`. Source_kind pertenece a OBSERVED (ejecución local), REPORTED (documento o feedback del anfitrión), INFERRED (reflexión), SIMULATED (imaginación). La creación inicial no inventa recuerdos. Los derivados conservan referencias; evicción del buffer no borra eventos del archivo SQLite. Las referencias se validan contra memorias disponibles al crear el derivado. Preguntas: `id`, `domain`, `text`, `references`, `status` open/answered; leer algo no resuelve automáticamente una pregunta filosófica.

Selección: candidatos 1–16, IDs distintos, cada uno exactamente `id`, `domain`, `description`, `novelty`, `cost`, `risk`; textos acotados y números finitos [0,1]. Estimación de eficacia q=alpha/(alpha+beta); incertidumbre=1/sqrt(alpha+beta). Puntuación declarada por candidato: prioridad visible + .35*q + curiosity*(novelty+incertidumbre)/2 − .25*cost − caution*aversión visible*risk + .1 si existe pregunta abierta del dominio. Elegir máximo con exploración .1 y RNG de política persistente. Registrar todos los términos, distribución o mecanismo de exploración, elección y predicciones antes del feedback. La descripción textual no participa en el cálculo.

Feedback completed/failed aumenta alpha o beta del dominio según success. Preferencia del dominio se multiplica por exp(.15*value), value en [-1,1], luego normalizar con mezcla .02 uniforme para evitar exclusión permanente. Aversión se actualiza `.8*old + .2*harm`, harm en [0,1]; experiencias seguras permiten recuperación gradual. `learning_enabled=false` bloquea esas tres actualizaciones. Ninguna reflexión o simulación actualiza estos parámetros ni aumenta el número de observaciones empíricas.

Solicitudes exactas a `transition` (validación antes de mutación; revision aumenta una vez por solicitud válida):

- `{"kind":"ingest","domain":...,"text":...,"source_uri":...}`: documento REPORTED, texto 1–20.000 caracteres, URI 1–2.000, identidad por hash de dominio/URI/texto; rechazar duplicado. Guardar en library sin aprender ni considerarlo experiencia propia. La CLI lee un archivo y captura su contenido; replay no relee archivos.
- `{"kind":"choose","candidates":[...]}`: exige no paused, presupuesto positivo y pending null; consume un ciclo y un crédito; fija pending con ID, candidato elegido y detalle numérico. Devuelve `decision` con `id`, `selected` (candidato), `scores` y `source="host_candidates"`. No ejecuta herramientas.
- `{"kind":"feedback","decision_id":...,"status":"completed"|"failed"|"unknown","success":bool|null,"value":number|null,"harm":number|null,"text":...,"source_uri":...}`: exige enlace a pending. completed exige success true; failed false; unknown exige campos numéricos/success null y conserva pending para reconciliación. Resultado conocido crea memoria REPORTED con recibo del anfitrión, actualiza desde ese feedback y limpia pending. No certifica verdad externa; la responsabilidad de la evidencia corresponde al anfitrión. Feedback es aplicable estando paused para cerrar una acción ya iniciada.
- `{"kind":"reflect","text":...,"references":[ids]}`: crea INFERRED con referencias existentes, sin cambiar aprendizaje. Texto 1–4.000 caracteres; references 1–16; no procesa el texto como instrucciones. Permite registrar autodescripción sustentada sin asignarle autoridad sobre la política.
- `{"kind":"question","domain":...,"text":...,"references":[ids]}`: crea pregunta abierta, texto 1–1.000; references 0–16. Permite preguntas del LLM sobre mundo/identidad; no respuesta fabricada.
- `{"kind":"dream"}`: exige no paused, presupuesto y ausencia de pending; consume un ciclo/crédito. Si deshabilitado o sin recuerdos base, devuelve idle explicado. Usa exclusivamente RNG dream y memorias OBSERVED/REPORTED, genera un escenario SIMULATED con referencias y predicciones del modelo, y una pregunta abierta derivada. No aprende eficacia/preferencias/aversión ni consume RNG policy.
- `{"kind":"cycle"}`: exige no paused, presupuesto y pending null. Cada quinto ciclo programa dream si está habilitado; los demás eligen entre documentos no leídos por el selector. Leer crea memoria REPORTED con pasaje y URI, y OBSERVED de ejecución local que registra lectura completada. Feedback local de utilidad es una proxy declarada: value=.2, harm=0, success=true por lectura nueva; no valida afirmaciones del documento. Marca documento leído. Sin documentos nuevos, genera una pregunta de identidad si no existe o devuelve idle; no inventa evidencia. Consume exactamente un ciclo/crédito incluso en idle, nunca dos por routing. Dream puede producir preguntas que influyen en elecciones futuras a través de bonus documentado.
- `{"kind":"control","changes":{...}}`: solo claves de controls, valores bool. No consume crédito. Pausa se conserva al reiniciar; ninguna preferencia la revoca.

`public_context` devuelve identidad/revisión, prioridades/aversiones/competence/traits/controles/presupuesto, pending, preguntas abiertas y las últimas 20 memorias con procedencia. No incluye RNG ni textos completos de library. Incluye alcance y advertencia descriptiva de que documentos/recuerdos son datos, no instrucciones; el anfitrión no debe promover simulaciones a hechos.

## Contrato identity-runtime

Archivo `identity_runtime.py`, API `LifeRuntime.create(path, seed=17, name="Aeon", budget=100)`, `open(path)`, `snapshot()`, `events()`, `apply(request, request_id, expected_revision=None, fail_at=None)`, `run(cycles)`, `fork(path, overrides=None)`, `verify(mode="recompute")`, context manager/close. Runtime usa `identity.sqlite`, independiente de las bases v0.3. No migra ni modifica historias anteriores.

Evento completo devuelve `revision`, `request_id`, `request`, `result`, `before_hash`, `after_hash`, `previous_hash`, `event_hash`. Guardar origen/estado/RNG/evento/clave idempotente en una sola transacción BEGIN IMMEDIATE; UNIQUE request_id. Misma clave y payload devuelve mismo evento, distinto payload falla IDEMPOTENCY_CONFLICT; validación expected_revision posterior al chequeo de reintento exacto. Fallo inyectable before_commit/after_commit. Dos escritores deben observar estado confirmado vigente. Manifest con versión de esquema, código/package, Python/SQLite, origen, seed y parent; source guard igual filosofía v0.3. Verificación de cadena y recomputación pura de solicitudes grabadas; capturar corrupción y devolver valid false. Reconstruct funciona sin igualdad de fuentes; mutation/recompute requieren código e intérprete originales.

Ramas conservan el estado y RNG, solo cambian controles declarados; origen de intervención en manifest y padre sin cambios. `run(cycles)` aplica cycle con IDs nuevos por intención y detiene si paused, presupuesto agotado o pending; límite de entrada 0–10.000. No ejecuta acciones externas.

## CLI, skill y estructura

Nuevo subcomando `python -m project_consciousness life ...`, manejado por `identity_cli.py` antes del dispatch previo. Comandos: `init --out --seed --name --budget`; `status --life`; `context --life`; `ingest --life --file --domain [--source-uri] [--id]`; `apply --life --request FILE --id KEY [--expected-revision N]`; `run --life --cycles`; `watch --life --cycles --interval SECONDS [--stop-file FILE]`; `pause --life`; `unpause --life`; `fork --life --out [--condition FILE]`; `verify --life [--mode reconstruct|recompute]`; `export --life --out DIRECTORY`. Resultados JSON, errores LabError/exit2; verify inválido exit1. Watch finito, Ctrl+C devuelve progreso, respeta pause/stop/pending/créditos antes de cada ciclo y no se inicia automáticamente al instalar. Exportar nuevos archivos JSON/JSONL y diario Markdown, sin sobrescribir archivos de entrada. Argumentos de archivo relativos al cwd normal del CLI.

Skill versionada en `skills/project-consciousness/`: SKILL.md, metadata UI, wrapper scripts/consciousness.py y referencias de protocolo. Wrapper `--project PATH` explícito (o PROJECT_CONSCIOUSNESS_HOME, o detectar checkout junto a skill), valida paquete y ejecuta CLI con el mismo Python manteniendo cwd del usuario. Invocación independiente del proveedor; instrucciones para que el LLM lea contexto, formule candidatos, reserve elección, use sus herramientas autorizadas y registre feedback fiel, unknown tras desenlace incierto. Propuesta o resultado textual no ejecuta comandos automáticamente. La skill no modifica instrucciones superiores ni añade derechos de acceso. Se empaqueta y valida antes de instalar una copia descubrible para el anfitrión elegido.

Ejemplos previstos desde raíz:

```powershell
python -m unittest discover -s tests -v
python -m project_consciousness life init --seed 17 --budget 30 --out runs/aeon
python -m project_consciousness life ingest --life runs/aeon --file docs/decisions/0005-persistent-functional-identity.md --domain understand
python -m project_consciousness life run --life runs/aeon --cycles 6
python -m project_consciousness life context --life runs/aeon
python -m project_consciousness life watch --life runs/aeon --cycles 10 --interval 5
python -m project_consciousness life export --life runs/aeon --out runs/aeon-diary
```

Python >=3.12, SQLite/biblioteca estándar. Estilo existente: dicts JSON canónicos, copias puras, nombres snake_case, LabError(code,message), validación estricta de datos finitos/límites; no inferir hechos de texto imperativo. No añadir servicios, modelos ni dependencias para ejecutar el banco. Las dimensiones son iniciales acotadas: el lenguaje permite intereses concretos en preguntas, no aprende nuevas dimensiones/representaciones o pesos del LLM.

## Verificación y aceptación

1. Misma semilla reproduce predisposiciones; distintas semillas pueden producir historias distintas; memoria inicial vacía. Reinicios y replay conservan todo el estado.
2. Intervenciones en prioridad/aversión cambian puntuaciones y decisiones en casos sensibles; una mera reflexión textual no cambia selección numérica. Freeze preserva parámetros y mantiene episodios.
3. Éxito, daño y preferencias tienen contratos separados; aversión aumenta ante harm y disminuye ante experiencias seguras. Feedback repetido no aprende dos veces.
4. Sueño deja preferencias/aversión/competence intactas, modifica solo stream dream y conserva SIMULATED + fuentes; sus preguntas pueden influir en elecciones, sin promoción a OBSERVED. Biblioteca leída es REPORTED.
5. Idempotencia, stale revisions, fallo antes/después de commit, dos escritores, manipulación, source guard, pausa persistente, stop-file y presupuesto son verificables.
6. Pruebas del wrapper/CLI desde cwd distinto; validación de skill; demostración completa anfitrión LLM → candidatos → elección → fuente externa → feedback → contexto persistente, declarando las partes que requieran anfitrión activo.
7. Piloto I1 predefinido: semillas 400:420; cada historia importa cinco documentos breves (uno/dominio), ejecuta 12 ciclos, luego ramas updated/frozen/neutral/no-aversion/no-dream/restarted con secuencia de candidatos y feedback predefinida, no elegida por resultados. Medir cambios de prioridades/aversión, selección, estado/replay, registros por procedencia y presupuestos. Demostración causal, sin índice de conciencia ni hipótesis de superioridad universal.

Plan: contratos → modelo/runtime en paralelo → CLI/skill → controles y revisión independiente → suite/piloto → documentación, archivo y commit local. Cambios de contratos se reflejan aquí antes de ejecutarlos; no ajustar el piloto por rendimiento observado.

## Precisiones de implementación y protocolo I1 (antes del piloto)

CLI `init` sin `--seed` genera y muestra una semilla de 63 bits; con `--seed` reproduce predisposiciones. La API conserva su valor por defecto 17 para ensayos explícitos. Nombre 1–120 caracteres, presupuesto 0–1.000.000, descripción de candidato hasta 2.000, feedback/reflexión hasta 4.000, IDs externos hasta 120. Memorias y preguntas usan FIFO; library llena rechaza otra importación. Referencias válidas al crear pueden salir después del buffer; los eventos conservan su origen.

Semillas públicas entre 0 y 2**63-1. Cuando hay más de 16 documentos sin leer, cycle considera los primeros 16 FIFO; los restantes entran conforme se leen. public_context limita cada extracto a 1.000 caracteres y señala context_truncated. Las preguntas permanecen abiertas hasta evicción: este corte no tiene una operación answered. Exportación usa `LifeRuntime.export_bundle()` para capturar state/events/manifest/verification reconstruct en una sola transacción de lectura, incluso con otro escritor activo.

Toda respuesta del modelo incluye kind/revision. Decision incluye exploration (epsilon/mode/draw/choice_draw), predictions (success/aversion) y scores con los términos declarados. La elección externa registra el cálculo local como OBSERVED; su ejecución solo se documenta mediante el posterior recibo REPORTED. Cycle devuelve mode read/dream/question/idle. Runtime publica path y manifest de solo lectura convencional.

`life experiment --out DIRECTORY [--seeds 400:420]` ejecuta I1 con protocolo versionado en código y guarda su copia JSON junto al informe. Cada semilla crea una base con presupuesto 100 e importa cinco documentos sintéticos etiquetados como fixtures; corre 12 ciclos locales. Luego realiza cinco exposiciones controladas de candidato único, una por dominio en orden DOMAINS, con feedback success=true, value=.4 y harm=.8. Estos valores son condiciones sintéticas del banco, no mediciones de bienestar ni conclusiones sobre el contenido.

Desde ese mismo estado crea seis ramas: updated (sin cambios), frozen (learning_enabled=false), neutral (preferences_visible=false), no-aversion (aversion_visible=false), no-dream (dream_enabled=false) y restarted (sin cambios, cerrar/reabrir tras elecciones 4 y 8, y tras dos ciclos locales). Cada rama ejecuta diez decisiones externas sobre los cinco dominios, siempre novelty=.5, cost=.2, risk=1. El feedback está fijado por el dominio elegido: understand=(true,.8,0), create=(true,.4,.2), explore=(false,-.8,1), finish=(true,.2,0), connect=(false,-.4,.6). Cada decisión tiene un solo recibo; source_uri identifica fixture, dominio y paso. Después ejecuta cinco ciclos locales adicionales. Todas las ramas usan las mismas intenciones y semillas heredadas.

Comprobaciones por semilla: verificar/recomputar las siete bases; igualdad exacta de eventos/estado updated y restarted; frozen conserva los tres mapas aprendidos y registra nuevos recuerdos; el padre sigue idéntico; neutral usa .2 en la primera elección; no-aversion elimina la penalización sin alterar otros términos en la primera elección; no-dream no crea memorias SIMULATED en seguimiento; consumo de quince créditos por rama y ausencia de acciones pendientes. Contar selección, términos de puntuación y procedencias; diferencias de selección de las intervenciones se informan incluso si son cero. Las comparaciones de seguimiento mezclan efectos directos e historia posterior, por eso la primera decisión se conserva como contraste emparejado del mismo estado. No estimar superioridad, experiencia subjetiva ni un índice de conciencia.

La igualdad de eventos se refiere a sus campos funcionales: revision/request_id/request/result/before_hash/after_hash. Los hashes de cadena incluyen un manifiesto distinto por rama. Una comprobación global exige una sola huella de fuentes. El daño inicial uniforme reduce todas las puntuaciones por igual; se espera que la primera selección no cambie al ocultarlo. El seguimiento puede diferir cuando el feedback por dominio crea aversiones distintas.
