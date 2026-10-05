# Protocolos experimentales de PROJECT CONSCIOUSNESS

Estado: programa experimental general. E0 y una versión acotada de E1 ya tienen una implementación en [MVP v0.1](mvp-v0.1.md). [MVP v0.2](mvp-v0.2.md) implementa L1, un experimento acotado de aprendizaje/reversión relacionado con E5/E8, sin completar esos protocolos. E2–E9 y las variantes amplias de E1 siguen propuestas. Los informes de cada ejecución se generan aparte y distinguen qué ensayos se realizaron. El objeto de estudio son propiedades funcionales y sus mecanismos causales; ningún resultado aquí definido constituye una prueba de experiencia subjetiva o conciencia.

## Alcance y etiquetas

- **E — evidencia empírica:** resultado publicado, con la población, tarea y medida de la fuente. Su existencia no valida automáticamente esta arquitectura.
- **T — teoría o modelo:** formalismo para explicar o medir fenómenos, con supuestos explícitos. No equivale a consenso sobre conciencia.
- **I — ingeniería e hipótesis:** mecanismo, tarea, intervención o umbral propuesto para este proyecto. Todos los protocolos E0–E9 son **I**, aunque algunas medidas y analogías procedan de E/T.

Hipótesis general de ingeniería: una arquitectura persistente puede producir dependencia de la historia, autoestimación de capacidades, control de incertidumbre, adaptación y planificación mediante estados internos que influyen en decisiones posteriores. Cablear esas dependencias y observar un efecto solo demuestra que el software utiliza ese estado. La utilidad, generalización y especificidad del mecanismo requieren pruebas adicionales.

La conciencia fenomenal, el estatus moral y la identidad personal son cuestiones filosóficas que estas pruebas no resuelven. No se construirá una puntuación total de conciencia sumando métricas heterogéneas.

## Banco experimental común

El primer banco será un POMDP discreto cerrado: observación parcial, acciones limitadas, recompensas, recursos y transiciones estocásticas. Habrá señales recordables, oportunidades de verificación costosa, rutas de distinto riesgo, cambios en eficacia de acciones y secuencias de tareas. El mundo verdadero, las probabilidades generadoras, las claves de evaluación y las etiquetas de intervención pertenecen al evaluador. El agente recibe exclusivamente su interfaz de observación y resultados de acciones.

La implementación futura será un proceso local Python con SQLite, modelo del mundo tabular aprendido, memoria episódica y semántica, modelo de capacidades propias, variables de control afectivo, metacontrol `verify/act/budget` y planificación mediante rollouts. Los parámetros aprendidos también son estado persistente: guardar hechos sin modificar un predictor o una política no bastará para afirmar aprendizaje continuo del componente evaluado.

Una configuración inicial de piloto, pendiente de validar coste y dificultad, será:

| Campo | Propuesta I |
|---|---|
| Horizonte | 100 pasos por episodio de tarea; terminar antes si el mundo alcanza un estado terminal; tick global continuo entre episodios |
| Acciones externas | Catálogo discreto común para todos los agentes; cada verificación consume una acción y un coste |
| Planificación | Máximo 4 candidatos, profundidad 4 y 32 trayectorias totales por tick (128 transiciones imaginadas); contabilizar consumo real |
| Memoria accesible | Hasta 256 registros episódicos de 4 KiB, más 1 MiB de parámetros/estado aprendido; índices y cachés presupuestados; log de auditoría separado |
| Aleatoriedad | Streams independientes para mundo, política, recuperación, imaginación y aprendizaje |
| Desarrollo | 20 semillas distintas; ajustar generadores y comprobar que las tareas son resolubles |
| Piloto de evaluación | Otras 20 semillas, emparejadas entre condiciones; describir variabilidad sin afirmar potencia suficiente |
| Confirmación | Semillas y familias retenidas nuevas; tamaño determinado después del piloto y congelado antes de observar resultados |
| Lenguaje | Sin LLM necesario; reportero opcional que lee trazas, sin escribir estado ni seleccionar acciones |

Los números anteriores sirven para comenzar el piloto. No son umbrales científicos ni una estimación de potencia. El presupuesto de memoria debe fijarse y registrarse antes de cada comparación; no crecerá silenciosamente con el número de tareas.

## Condiciones y controles

1. **Arquitectura completa:** todos los módulos habilitados y mismo aprendizaje autorizado.
2. **Agente reactivo sin persistencia:** observación actual, mismas acciones y presupuesto externo. Control de dependencia histórica, no competidor con información equivalente.
3. **Agente recurrente genérico:** mismo historial observable, capacidad de almacenamiento y parámetros aprendibles comparables; estado recurrente o historial plano sin la organización modular propuesta. Es el control principal de que una organización específica añade algo al mero acceso a historia.
4. **Chatbot con historial, opcional:** mismo modelo fijo, observaciones, herramientas y límites de tokens que la condición lingüística completa. No comparar un sistema sin LLM con otro de mayor capacidad y atribuir diferencias a la arquitectura.
5. **Sham:** pasar por la infraestructura de intervención y reserialización dejando el valor funcional intacto. Controla efectos del mecanismo experimental.
6. **Control de presupuesto:** mismo límite de pasos, consultas, almacenamiento y cómputo interno. Para un módulo eliminado, añadir una condición que reasigne su presupuesto a un mecanismo alternativo útil y especificado antes de medir. Ejecutar operaciones vacías solo sirve para estudiar latencia, no para demostrar igualdad de capacidad.

Registrar límites y consumo real: transiciones externas e imaginadas, actualizaciones, consultas de memoria, bytes, tiempo, tokens y llamadas cuando existan. Comparar a varios presupuestos y reportar la frontera rendimiento–coste. La evaluación de agentes requiere atención al coste, a los conjuntos retenidos y a la reproducibilidad; una mejora con más recursos tiene una interpretación diferente de una mejora a presupuesto comparable. [Kapoor et al., 2024](https://arxiv.org/abs/2407.01502)

Las ablaciones se aplican por separado a **escritores** y **lectores**. Un escritor deshabilitado deja de actualizar su almacenamiento funcional, mientras el evaluador conserva el log de auditoría. Un lector deshabilitado no puede recuperar ese estado por otra vía. El log de auditoría nunca es una memoria oculta del agente. Toda ruta alternativa de información se registra y se mantiene constante o se declara como otra condición.

## Diseño causal, snapshots y replay

Cada snapshot contiene el estado funcional completo del agente, memoria y sus índices, parámetros aprendidos, buffers, metas, contadores, streams RNG, versión de esquema/configuración y estado completo del entorno. El agente no obtiene acceso al estado del entorno por estar incluido en el paquete del evaluador.

Para una intervención, clonar un snapshot, asignar aleatoriamente condiciones a ramas, modificar solo el mecanismo especificado y conservar la intervención como evento de evaluación. Los eventos originales permanecen inmutables; las máscaras de recuperación o estados sustituidos pertenecen a una rama identificada. No sobrescribir retrospectivamente la autobiografía original.

Se distinguen dos estimandos:

- **Efecto inmediato bajo entrada idéntica:** presentar la misma observación, fijar los demás estados y medir la distribución de la próxima acción o elección de metacontrol. Es apropiado para detectar un lector causal.
- **Efecto total en trayectoria:** dejar evolucionar cada rama en un mundo clonado y comparar resultados. Las acciones distintas producirán observaciones distintas; esto es parte del efecto total y no demuestra por sí solo una mediación específica.

Para una variable interna `m`, resultado `Y` y `n` snapshots independientes:

\[
\widehat{\Delta}_m = \frac{1}{n}\sum_{i=1}^{n}
\left[Y_i\bigl(do(m=m_1)\bigr)-Y_i\bigl(do(m=m_0)\bigr)\right].
\]

En decisiones estocásticas, el cambio inmediato puede medirse por distancia de variación total entre políticas:

\[
D_m = \tfrac12\sum_a|\pi(a\mid do(m=m_1))-\pi(a\mid do(m=m_0))|.
\]

Una diferencia de salida no demuestra beneficio ni conciencia. Para afirmar mediación, cortar además la conexión propuesta entre módulo y consumidor: si cambia la memoria pero el planner recibe una salida controlada idéntica, se espera que desaparezca el efecto atribuido a esa conexión. Esta prueba exige evitar rutas alternativas y no se deduce de una correlación en el log.

Los streams independientes evitan que consumir números aleatorios en imaginación cambie accidentalmente el siguiente resultado del mundo. En ramas divergentes, el ruido exógeno del entorno se indexará por episodio, tick y proceso causal; usar un único generador con distinto número de llamadas no garantiza mundos contrafácticos comparables.

**Replay pasivo** reproduce eventos y verifica estados; **replay de decisión** vuelve a ejecutar módulos contra entradas registradas. El segundo no representa una trayectoria físicamente válida si impone observaciones incompatibles con acciones nuevas. Se usará para estudiar decisiones locales, nunca como resultado de recompensa de un mundo cerrado.

## Protocolos E0–E9

### E0 — Persistencia, aislamiento y reproducción

**Propósito I:** establecer que el banco mide el sistema especificado.

Comparar una ejecución continua con la misma ejecución interrumpida, guardada, cerrada y restaurada en varios ticks. Repetir en condiciones normales y con una intervención sham. Reconstruir las vistas persistentes desde eventos y contrastarlas con el snapshot. Forzar interrupciones antes y después de commits para detectar actualizaciones dobles o parciales.

**Métricas:** igualdad de acciones y hashes canónicos de estados, divergencia por tick, eventos duplicados, inconsistencias entre memoria e índices, consumo de RNG por stream y accesos no permitidos.

**Aceptación de software:** reproducción exacta en el perfil tabular determinista y versiones fijadas; recuperación sin doble actualización; cero acceso del agente a claves o estado oculto. Cualquier diferencia invalida el experimento afectado hasta resolver su causa. Si posteriormente se introduce una API LLM no determinista, se podrá reproducir el response cache, pero eso no equivale a repetir independientemente la inferencia remota.

### E1 — Memoria autobiográfica y procedencia

**Hipótesis I:** episodios propios relevantes, con orden y fuente, permiten resolver decisiones dependientes de historia y distinguir experiencia de imaginación.

Presentar una señal contingente de episodio que determina dónde recuperar un recurso tras distractores y un reinicio. Diseñar pares de historias con la misma observación presente y respuestas correctas diferentes. Comparar memoria intacta, escritor episódico deshabilitado, lector deshabilitado, máscara selectiva del episodio crítico y memoria sustituida por la de otro agente. Separar almacenamiento episódico de agregados semánticos en un factorial reducido para localizar rutas redundantes.

Como control negativo, enmascarar eventos irrelevantes con igual tamaño y edad. Como prueba de procedencia, introducir un rollout que predice un recurso inexistente y comprobar que no se convierte en un hecho observado. No dar al agente etiquetas de condición experimental.

**Métricas:** éxito tras distractores/reinicio, recuperación correcta del episodio y fuente, confusiones `observado/imaginado/ajeno`, proporción de decisiones con evidencia recuperada válida y efecto de la máscara relevante frente a la irrelevante.

**Aceptación de software:** aislamiento writer/reader y conservación de procedencia. **Resultado funcional:** efecto específico del episodio pertinente en acciones y desempeño; igualdad o superioridad frente al historial plano es una pregunta separada. **Falsación:** ningún cambio tras intervenir episodios relevantes, cambios equivalentes con episodios irrelevantes o aparente ventaja explicada por una ruta oculta. Si otro módulo contiene la información, el resultado indica redundancia y no ausencia de memoria en todo el sistema.

### E2 — Self-model de capacidades

**Hipótesis I:** una estimación propia de `P(action succeeds | context)` predice fallos y modifica selección de acciones o solicitud de ayuda.

Cambiar silenciosamente la eficacia de una herramienta o habilidad propia manteniendo las otras transiciones del mundo. Observar su actualización a partir de consecuencias. Desde snapshots con idéntica observación, comparar self-model actualizado, congelado, sobreestimado, subestimado y correspondiente a otro agente. Intervenir sobre estimaciones dentro de rangos plausibles; los extremos fuera de distribución serán pruebas de estrés separadas.

**Métricas:** Brier/NLL de probabilidades de éxito emitidas antes del resultado, regret respecto de un oráculo con la misma observación y capacidades verdaderas, intentos fallidos, tiempo de adaptación y elección de alternativa. Separar capacidad propia de incertidumbre sobre el entorno.

**Aceptación de software:** el registro identifica qué estimación leyó el decisor. **Resultado funcional:** calibración útil y adaptación en contextos retenidos. **Falsación:** las estimaciones no anticipan eficacia propia, solo cambian el reporte textual o la política responde a etiquetas explícitas de éxito futuro.

### E3 — Metacognición y metacontrol

**Hipótesis I:** estimaciones de incertidumbre específicas de cada caso mejoran la decisión de verificar, actuar o asignar cómputo, descontando su coste.

Usar discriminaciones binarias con dificultad controlada y una acción `verify` de coste conocido. Guardar decisión y confianza antes de recibir feedback. Comparar control completo, lector de confianza cortado, confianza constante, confianza permutada dentro de estratos de dificultad y verificación a tasa fija equivalente. Igualar desempeño de primer orden o modelarlo explícitamente al comparar sensibilidad metacognitiva.

**Métricas:** Brier, NLL, curvas de calibración, AUROC para discriminar aciertos de errores, riesgo frente a cobertura y utilidad neta de verificaciones. Medir también asignación de cómputo según incertidumbre y mejora obtenida por esa asignación. ECE será descriptivo: sus bins y tamaño de muestra afectan la medida. La calibración de probabilidades es distinta de la habilidad de distinguir aciertos de errores. [Guo et al., 2017](https://proceedings.mlr.press/v70/guo17a.html)

Para la tarea binaria, estimar `d'`, `meta-d'` y, si el denominador lo permite, `M-ratio = meta-d'/d'`. `Meta-d'` es una medida bajo teoría de detección de señales, no una medida de conciencia. Evitar interpretar el cociente cuando `d'` se aproxima a cero, controlar confianza sesgada, comprobar supuestos distribucionales y reportar incertidumbre del ajuste. [Maniscalco y Lau, 2012/2014](https://www.columbia.edu/~bsm2105/type2sdt/), [Fleming y Lau, 2014](https://www.frontiersin.org/journals/human-neuroscience/articles/10.3389/fnhum.2014.00443/full)

**Aceptación de software:** confianza anterior al feedback, cortes de lectura efectivos y costes completos. **Resultado funcional:** mejor utilidad o curva riesgo–cobertura que controles comparables en casos nuevos. **Falsación:** confianza sin discriminación, ventaja eliminada al contabilizar verificaciones o efecto reducido a fluidez verbal.

### E4 — Afecto computacional como control recurrente

**Hipótesis I:** variables recurrentes de valencia, activación y presión de recursos pueden modular saliencia de memoria y aversión al riesgo de manera específica y útil. Estos nombres designan variables de ingeniería; no implican emociones sentidas. Controlabilidad estimada será una extensión separada.

Comparar dinámica completa, lectores afectivos cortados, estado fijo de referencia neutral y estado fijo en la media obtenida exclusivamente de entrenamiento. Permutar trayectorias afectivas entre episodios emparejados para conservar distribución marginal y romper su correspondencia temporal con eventos. Usar tareas con rutas de igual valor esperado y riesgo diferente, más tareas donde el riesgo no es relevante. Mantener observación y recursos físicos iguales al intervenir afecto.

Intervenir por separado sobre `afecto → saliencia`, `afecto → riesgo` y `afecto → presupuesto`. Medir el próximo paso con entrada idéntica y después el efecto total. Restaurar el estado original para comprobar reversibilidad; el reinicio físico debe preservar el estado afectivo salvo intervención explícita.

**Métricas:** proporción de rutas riesgosas, distribución de episodios retenidos, latencia de decaimiento, consumo de cómputo, utilidad y violaciones de límites del mundo. Comparar dinámica con control fijo en la media para distinguir efecto temporal de un sesgo promedio.

**Aceptación de software:** cada variable tiene rango, dinámica y lectores documentados; los cortes eliminan los efectos de su ruta. **Resultado funcional:** efecto específico y, si se reclama beneficio, ventaja a coste comparable. **Falsación:** cambiar nombres emocionales solo altera lenguaje, los efectos sobreviven con lectores cortados o la dinámica no añade utilidad frente a controles fijos/permutados. Un efecto cableado constituye causalidad implementada; la analogía psicológica seguirá siendo I.

### E5 — Predicción y revisión del modelo del mundo

**Hipótesis I:** un modelo tabular aprendido produce predicciones probabilísticas que mejoran con experiencia y detectan cambios de contingencia.

Registrar `P(o_next, reward | belief, action)` antes de ejecutar la acción. Comparar modelo actualizado, lector congelado, modelo permutado y predictor de frecuencias de base. Introducir cambios de transición y recompensa sin proporcionar la respuesta correcta. Evaluar primero sobre transiciones retenidas con entradas comparables y luego en trayectorias interactivas. Un conjunto diagnóstico de sondas común evita confundir mejora predictiva con visitar estados más fáciles.

**Métricas:** NLL/Brier, error de recompensa, calidad a varios horizontes, sorpresa anterior a actualización y pasos hasta recuperar desempeño. El planificador no obtiene una copia del generador verdadero.

**Aceptación de software:** forecast anterior a observación y actualización solo a partir de datos permitidos. **Resultado funcional:** mejora en datos retenidos frente a predictor congelado/base. **Falsación:** solo mejora en datos ya vistos, ventaja por acceso a probabilidades del evaluador o incapacidad de revisar predicciones tras un cambio.

### E6 — Imaginación, planificación y monitorización de realidad

**Hipótesis I:** rollouts del modelo aprendido permiten decidir mejor cuando cambian transiciones o se devalúa un resultado, sin confundir posibilidades con observaciones.

Usar una tarea multietapa y cambios que favorecen replantear rutas. Comparar planner completo, imaginación deshabilitada, horizonte corto, rollouts barajados y control que usa el mismo presupuesto en búsqueda o actualización alternativa. Añadir un oráculo de modelo conocido únicamente como techo, no como competidor equiparable.

El diseño de tareas multietapa tiene antecedentes empíricos en control basado en modelos; sus resultados humanos no atribuyen conciencia a un planner. [Daw et al., 2011](https://www.princeton.edu/~ndaw/dgsdd11.pdf) Entrenar decisiones mediante trayectorias imaginadas también es una técnica demostrada de aprendizaje por refuerzo, no evidencia de experiencia imaginativa. [Hafner et al., 2025](https://www.nature.com/articles/s41586-025-08744-2)

**Métricas:** regret, éxito tras devaluación/cambio, transiciones reales necesarias para adaptación, coste de planificación, error de rollouts y hechos imaginados indebidamente consolidados. No interpretar un simple patrón de repetición de acciones como diagnóstico suficiente de control basado en modelos.

**Aceptación de software:** linaje y etiqueta `imagined` en todo rollout; cero escritura directa como experiencia observada. **Resultado funcional:** ventaja bajo cambios nuevos a presupuesto comparable. **Falsación:** ventaja desaparece con el coste, exige modelo verdadero o el planner añade simulaciones sin modificar elecciones pertinentes.

### E7 — Agencia y persistencia/revisión de metas

**Hipótesis I:** metas explícitas mantienen una política de acción durante interrupciones y se revisan ante evidencia de inviabilidad o conflicto.

Asignar dos metas incompatibles con prioridades definidas y recursos limitados. Interrumpir el proceso y reanudar. Introducir una ruta bloqueada, una oportunidad distractora y una condición legítima de cancelación. Comparar metas persistentes, lector cortado, prioridades permutadas y política puramente reactiva. La meta inicial procede del diseño experimental: este protocolo no demuestra motivación intrínseca ni libre albedrío.

**Métricas:** cumplimiento, pasos de desvío, coste irrecuperable acumulado, tiempo hasta revisar/cancelar la meta y regret bajo restricciones. La persistencia rígida que ignora inviabilidad cuenta como fallo.

**Aceptación de software:** meta activa y revisión sobreviven a reinicio con trazabilidad. **Resultado funcional:** continuidad y revisión oportunas en situaciones retenidas. **Falsación:** mismo comportamiento con metas diferentes, desvíos explicados por un último prompt o persistencia sin capacidad de revisión.

### E8 — Aprendizaje continuo, retención y transferencia

**Hipótesis I:** parámetros actualizados por experiencia incorporan contingencias nuevas sin olvidar indiscriminadamente las anteriores.

Secuencia inicial `A → B → C → A`, con contextos observables que permiten distinguir reglas incompatibles. Comparar aprendizaje online, learner congelado, actualización sin consolidación/replay y consolidación/replay con memoria limitada. La variante sin señal de contexto será un experimento posterior distinto: no atribuir a retención un fallo causado por ambigüedad irresoluble de tarea.

Después de cada bloque y tras asimilar su último feedback, clonar el agente y evaluar todas las tareas en conjuntos retenidos. Congelar parámetros aprendidos `Θ` y acumulación persistente entre sondas; permitir inferencia dinámica de creencias, recursos, metas y memoria temporal dentro de cada episodio evaluado. Descartar después el clon y restaurar el snapshot inicial de la sonda siguiente, para que evaluar no entrene. Repetir a igual presupuesto de datos, almacenamiento y actualizaciones; etiquetar separadamente parámetros, memoria de hechos y caches.

Con tablas ilimitadas totalmente separadas por contexto, puede no existir interferencia y el beneficio del replay sería trivialmente nulo. La comparación de retención usa capacidad limitada o una regla de descuento declarada en el manifiesto, junto a un control tabular sin interferencia. Repetir episodios en un estimador de conteos no suma nuevas observaciones independientes: registrar pesos y procedencia de toda reponderación.

Definir `R[i,j]` como desempeño en tarea `j` después de aprender bloque `i`. Las medidas de transferencia y desempeño se adaptan del marco de GEM; aquí el desempeño puede ser éxito normalizado y debe usar la misma escala en todas las tareas. [Lopez-Paz y Ranzato, 2017](https://proceedings.neurips.cc/paper/2017/file/f87522788a2be2d171666752f97ddebb-Paper.pdf)

\[
ACC = \tfrac1T\sum_{j=1}^{T}R_{T,j},\qquad
BWT = \tfrac1{T-1}\sum_{j=1}^{T-1}(R_{T,j}-R_{j,j}).
\]

Reportar además pérdida respecto al mejor desempeño previo por tarea, curva de aprendizaje y pasos para reaprender A. `BWT < 0` indica deterioro promedio respecto al desempeño al terminar cada tarea; no todo cambio posterior es olvido catastrófico. `FWT` requiere una referencia explícita sin aprendizaje previo y tareas evaluadas antes de entrenarlas; no afirmar transferencia porque el agente memoriza identificadores.

EWC es un antecedente para redes con pesos entrenables, pero no es requisito ni una descripción correcta del learner tabular del MVP. Su resultado original protege pesos relevantes de tareas anteriores; extrapolarlo a una arquitectura cognitiva completa sería I. [Kirkpatrick et al., 2017](https://doi.org/10.1073/pnas.1611835114)

**Aceptación de software:** actualizar parámetros persistentes con eventos autorizados y excluir datos de test. **Resultado funcional:** aprendizaje nuevo y retención medidos en situaciones nuevas; revelar cualquier intercambio retención–plasticidad. **Falsación:** mejora explicada solo por almacenamiento literal, evaluación que entrena inadvertidamente o retención conseguida impidiendo todo aprendizaje nuevo.

### E9 — Coordinación entre módulos y reportes verbales

**Hipótesis I:** la disponibilidad compartida de información relevante coordina memoria, predicción, metacontrol y acción cuando compiten por recursos limitados.

Introducir dos candidatos competidores por acceso a la memoria de trabajo/pizarra del ciclo. Comparar acceso normal, broadcast congelado, sustitución de contenido por un candidato irrelevante del mismo tamaño y corte selectivo de un consumidor. Conservar entradas locales cuando el objetivo sea probar coordinación por broadcast. Usar tareas donde la señal debe llegar a dos consumidores y controles donde solo uno la necesita. Las etiquetas de módulo no se incluirán como instrucciones al reportero.

Además, ejecutar con reportero encendido, apagado y texto de reportero permutado. Si el reportero es de solo lectura, apagarlo debe dejar idéntica la trayectoria funcional con el mismo snapshot. Si un reporte tiene permiso de retroalimentar decisiones, constituye otro canal causal que debe declararse e intervenirse por separado.

**Métricas:** efectos por consumidor, desempeño en tareas que exigen coordinación, coste, incompatibilidades entre decisiones y evidencia, concordancia de reportes con eventos verificables y errores de procedencia. Una traza es evidencia de lo calculado, no acceso privilegiado a una mente; no se requiere registrar cadenas de pensamiento en lenguaje libre.

**Aceptación de software:** restricciones de capacidad reales y reportero efectivamente de solo lectura. **Resultado funcional:** efectos específicos de las rutas cortadas y coordinación que generaliza. **Falsación:** resultados explicados por una ruta local o cache no intervenida, un broadcast irrelevante produce la misma ventaja o solo cambia la narración. Este protocolo no calcula integración fenomenal ni una medida de IIT.

## Métricas probabilísticas comunes

Para predicciones binarias `p_i` emitidas antes del resultado `y_i ∈ {0,1}`:

\[
Brier = \tfrac1N\sum_i(p_i-y_i)^2,
\]

\[
NLL = -\tfrac1N\sum_i\left[y_i\log p_i+(1-y_i)\log(1-p_i)\right].
\]

Fijar un tratamiento numérico de probabilidades 0/1, reportar su uso y comparar con frecuencias de base. Brier y NLL combinan varios aspectos de la predicción; acompañarlos de diagramas de calibración y discriminación. Probabilidades emitidas después de observar el resultado no son forecasts. El self-model, el predictor del mundo y la confianza de decisión tendrán columnas distintas, aunque compartan medidas.

El regret se define como diferencia de utilidad entre la política evaluada y una referencia explícita en la misma tarea. Un oráculo con estado oculto es un techo de información superior; no se usa para atribuir al agente fallos que cualquier política con observación parcial tendría.

## Prerregistro, incertidumbre y aceptación

Separar tres resultados: **banco válido**, **dependencia causal implementada** e **hipótesis funcional respaldada en las tareas especificadas**. El primero puede exigir invariantes exactos; los dos últimos requieren estimandos y controles. Un experimento científicamente útil puede rechazar la hipótesis funcional y aun así aprobar el banco de software.

Antes de la confirmación, congelar generadores, familias de tareas, semillas retenidas, versiones, baselines, presupuesto, medida primaria, contrastes, reglas de exclusión y diferencia mínima relevante `δ`. El valor de `δ` se justificará por coste o utilidad de la tarea y no por qué cifra produce significación en el piloto. Los ajustes hechos tras ver resultados se etiquetarán exploratorios y necesitarán un nuevo conjunto retenido.

La unidad independiente será la semilla con su historia completa, no cada tick ni cada clon de un mismo snapshot. Los snapshots procedentes de una historia son medidas dependientes. Reportar diferencias emparejadas y un IC del 95 % con remuestreo por semilla; si hay suficiente estructura, anidar las familias de tareas dentro de un esquema previamente especificado. Con pocas semillas, reconocer intervalos imprecisos en lugar de declarar ausencia de efecto.

- **Hipótesis de mejora:** intervalo de la diferencia primaria por encima de `δ`, con coste y controles satisfechos.
- **Equivalencia práctica de un control negativo:** intervalo de la diferencia contenido en `[-δ, δ]`; un valor p no significativo no basta.
- **Refutación de una mejora mínima:** intervalo que excluye efectos de tamaño al menos `δ` en la dirección prevista. Un intervalo amplio que cruza ambos rangos deja el resultado inconcluso.
- **Muchas comparaciones:** declarar una familia confirmatoria limitada y corregirla, por ejemplo con Holm; el resto será exploratorio. Los diez protocolos no se convierten en diez afirmaciones confirmadas por defecto.

No asumir potencia con 20 semillas. El piloto estimará variación, dificultad, frecuencia de fallos y coste; después se hará un cálculo o simulación de potencia para el contraste primario, con supuestos publicados. No detener una corrida confirmatoria al observar un resultado favorable salvo regla secuencial prerregistrada.

Un informe por protocolo incluirá configuración y hashes, intervención, datos retenidos, consumo de recursos, tamaño de efecto e intervalo, resultado de controles, fallos, conclusión limitada y alternativas explicativas. AgentBench muestra el valor de evaluar agentes en interacciones multietapa, pero resolver sus tareas tampoco evalúa conciencia. [Liu et al., ICLR 2024; revisión posterior del preprint](https://arxiv.org/abs/2308.03688)

## Confusores y límites que deben registrarse

| Confusor | Control obligatorio |
|---|---|
| Más historia o más cómputo en el sistema completo | Recurrente genérico, capacidades de memoria comparables, límites y consumo real, curvas a varios presupuestos |
| El módulo deshabilitado deja una cache o ruta alternativa | Inventario de lectores/escritores, cortes por interfaz y pruebas locales desde snapshot |
| Leakage desde evaluador, test o reporte | Interfaz de observación exclusiva, almacenamiento separado y auditoría de accesos |
| Tareas diseñadas para que gane el mecanismo programado | Familias retenidas, negativos, adversariales y baselines competentes; reconocer que demostrar cableado es distinto de generalizar |
| Efectos por cambios de número de llamadas RNG | Streams independientes y ruido exógeno definido para ramas |
| Confianza textual, personalidad o vocabulario emocional | Medidas numéricas anteriores al feedback, acción observable, reportero apagado y permutado |
| Intervenciones fuera de distribución | Rangos plausibles de entrenamiento y pruebas de estrés etiquetadas aparte |
| Orden o deriva temporal | Orden de condiciones aleatorio, semillas emparejadas y versiones fijadas |
| Evaluación que aprende | Clones con escrituras congeladas y restablecimiento entre sondas |
| Pseudorreplicación | Unidad semilla/historia, agrupación de clones y ticks |
| Ganancia de reward a costa de restricciones | Utilidad, costes y violaciones reportados por separado |
| Mejor predicción por visitar estados fáciles | Conjunto diagnóstico común más evaluación interactiva |

Se podrán extender estos protocolos a tareas sociales, otros agentes y arquitecturas distribuidas una vez válido el banco individual. La coordinación colectiva, los resultados animales y los modelos neurocientíficos requieren sus propios diseños y no justificarán retrospectivamente llamar consciente al MVP.

## Fuentes primarias y métodos verificados

1. [Maniscalco y Lau (2012), *A signal detection theoretic approach for estimating metacognitive sensitivity from confidence ratings*; recursos de autores y extensión 2014](https://www.columbia.edu/~bsm2105/type2sdt/). **T/método:** meta-d', dependencia del desempeño de primer orden y precauciones sobre variancias.
2. [Fleming y Lau (2014), *How to measure metacognition*](https://www.frontiersin.org/journals/human-neuroscience/articles/10.3389/fnhum.2014.00443/full). **T/método:** distingue sesgo, sensibilidad y eficiencia; advierte problemas de cocientes con `d'` pequeño. Es una exposición metodológica, no una prueba nueva de conciencia artificial.
3. [Guo et al. (2017), *On Calibration of Modern Neural Networks*, ICML](https://proceedings.mlr.press/v70/guo17a.html). **E/método:** calibración de probabilidades en redes clasificadoras; extrapolarla a control cognitivo exige evaluación propia.
4. [Daw et al. (2011), *Model-Based Influences on Humans' Choices and Striatal Prediction Errors*](https://www.princeton.edu/~ndaw/dgsdd11.pdf). **E/T:** elecciones humanas en una tarea multietapa y modelos de control; no test de conciencia.
5. [Hafner et al. (2025), *Mastering diverse control tasks through world models*, Nature](https://www.nature.com/articles/s41586-025-08744-2). **E/ingeniería publicada:** aprendizaje por modelos del mundo y trayectorias imaginadas; el MVP utiliza un predictor tabular más pequeño.
6. [Lopez-Paz y Ranzato (2017), *Gradient Episodic Memory for Continual Learning*, NeurIPS](https://proceedings.neurips.cc/paper/2017/file/f87522788a2be2d171666752f97ddebb-Paper.pdf). **E/método:** métricas ACC/BWT/FWT y memoria limitada en aprendizaje secuencial.
7. [Kirkpatrick et al. (2017), *Overcoming catastrophic forgetting in neural networks*, PNAS](https://doi.org/10.1073/pnas.1611835114). **E/T:** EWC y protección de pesos en tareas secuenciales, con alcance distinto del MVP tabular.
8. [Liu et al., *AgentBench: Evaluating LLMs as Agents*, ICLR 2024](https://arxiv.org/abs/2308.03688). **E/ingeniería publicada:** evaluación multientorno de agentes; fijar una revisión del benchmark si se incorpora posteriormente.
9. [Kapoor et al. (2024), *AI Agents That Matter*](https://arxiv.org/abs/2407.01502). **E/método:** problemas de coste, holdouts y reproducibilidad en evaluación de agentes.

Fuentes consultadas el 3 de octubre de 2026. Las conclusiones propuestas para PROJECT CONSCIOUSNESS permanecen I hasta ejecutar y evaluar los protocolos; incluso resultados positivos no convierten las preguntas filosóficas en hechos empíricos.
