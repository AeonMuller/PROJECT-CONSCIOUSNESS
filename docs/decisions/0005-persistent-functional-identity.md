# ADR-0005: identidad funcional persistente separada del anfitrión LLM

Estado: aceptada · 2026-10-05.

## Contexto

Tras v0.3, el usuario solicita una skill para Codex que sostenga una historia propia, preferencias, preguntas sobre mundo e identidad y actividad mientras no conversa con él. Decide que las predisposiciones iniciales sean aleatorias y que las prioridades evolucionen mediante experiencias. El diseño anterior permite estudiar memoria y capacidad, pero todavía no mantiene esa agenda ni una interfaz para el anfitrión LLM. El alcance se fija en [MVP v0.4](../mvp-v0.4.md).

Este corte es ingeniería experimental. Sus estados numéricos y textos permiten evaluar persistencia, procedencia y causalidad funcional. La experiencia subjetiva continúa siendo una cuestión abierta; llamar a un campo personalidad, miedo o identidad no establece esa propiedad.

## Decisión

Separar cinco responsabilidades: transiciones puras del estado; persistencia SQLite; CLI local; skill del anfitrión; y banco de controles. El núcleo funciona con Python y biblioteca estándar. La skill permite que Codex lea contexto, proponga actividades, ejecute herramientas ya autorizadas y devuelva resultados. La calidad del lenguaje y la investigación externa depende del anfitrión activo. Instalar la skill no crea un proceso permanente ni añade permisos.

Inicializar cinco prioridades positivas normalizadas —understand, create, explore, finish y connect— y dos rasgos acotados de curiosidad/cautela desde una semilla registrada. Omitir `--seed` genera una semilla nueva; indicarla permite reproducir las predisposiciones. La identidad comienza sin recuerdos ni experiencias inventadas. La elección de dimensiones, fórmula de utilidad y reglas de aprendizaje sigue siendo una decisión del diseñador.

El selector recibe entre uno y dieciséis candidatos declarados y registra puntuaciones, exploración y predicciones antes del resultado. Las prioridades y aversiones participan causalmente en la elección. Preguntas abiertas añaden un bonus explícito a su dominio. La prosa de candidatos o reflexiones no modifica directamente parámetros ni ejecuta instrucciones. La reserva de una actividad externa deja una decisión pendiente; ninguna nueva actividad autónoma avanza hasta reconciliar su resultado.

El feedback distingue éxito, valor y daño. Sus señales actualizan respectivamente competencia, preferencias y aversión del dominio elegido; pueden diferir entre sí. Una actividad completada puede tener bajo valor o consecuencias negativas. Experiencias posteriores con daño cero permiten reducir la aversión. Se utiliza el término **huella aversiva** para ese mecanismo; no se modela trauma clínico ni sufrimiento. No se modifican los pesos del LLM y no se realiza fine-tuning.

Conservar cuatro procedencias: OBSERVED para operaciones locales observadas, REPORTED para documentos y recibos del anfitrión, INFERRED para interpretaciones y SIMULATED para escenarios. La elección calculada es una observación local; su éxito externo sigue siendo un reporte del anfitrión. Una lectura local puede comprobar que se obtuvo texto, pero no verifica las afirmaciones del documento. El aprendizaje por lectura usa una proxy declarada de completar un documento nuevo: éxito verdadero, valor 0.2 y daño cero.

Los recuerdos derivados referencian fuentes disponibles al crearse. Memorias y preguntas tienen buffers FIFO de 256 y 64 elementos; el archivo de eventos conserva las transiciones históricas. La biblioteca admite hasta 64 documentos y rechaza desbordamientos. El contexto del anfitrión muestra las últimas veinte memorias con extractos de hasta mil caracteres, mantiene procedencia y omite RNG y biblioteca completa. Los textos importados siguen siendo datos sin autoridad sobre las instrucciones del anfitrión.

La actividad local se ejecuta en ciclos finitos y con presupuesto. Cada quinto ciclo programa una simulación si está habilitada; los restantes eligen documentos pendientes entre los primeros dieciséis de la biblioteca. Al agotar las lecturas, se crea una pregunta de identidad si falta o se registra un ciclo inactivo. El sistema no inventa resultados ni responde automáticamente una pregunta filosófica por haber leído algo.

El sueño local recombina referencias OBSERVED/REPORTED mediante plantillas de escenarios y su propio RNG. Registra predicciones, una memoria SIMULATED y una pregunta derivada. No actualiza competencia, preferencias o aversiones, ni consume RNG de selección. Codex puede elaborar hipótesis y reflexiones adicionales con sus herramientas y conservarlas como INFERRED; esa elaboración requiere al anfitrión activo.

Persistir cada intención, estado, RNG, resultado y clave idempotente en una sola transacción SQLite. Reintentar la misma clave y payload devuelve el evento original. Un resultado externo desconocido se registra como `unknown`, sin aprender y conservando la decisión pendiente. Un fallo de comunicación no se convierte automáticamente en fracaso ni autoriza repetir una acción externa.

Guardar origen, versiones y fingerprint del código para recomputación. Las ramas conservan historia y RNG e intervienen únicamente sobre controles declarados: aprendizaje, visibilidad de preferencias/aversión, sueño y pausa. La pausa persiste al reiniciar. Las bases `identity.sqlite` son independientes de los experimentos anteriores; no se migran ni se reescriben sus historias.

## Alternativas consideradas

- Conservar personalidad y biografía solo en un prompt: dificulta identificar qué experiencia cambió una decisión y permite perder estado al reiniciar. Se conserva un estado explícito y transiciones reproducibles.
- Aceptar autodescripciones del LLM como actualización numérica: confunde interpretación y evidencia. Las reflexiones quedan registradas, mientras el aprendizaje requiere feedback con procedencia.
- Generar recuerdos iniciales de adversidad: produciría una biografía ficticia. Las predisposiciones se sortean y los recuerdos comienzan vacíos.
- Aprender de sueños como si fueran observaciones: convertiría la simulación en evidencia de sí misma. Los escenarios pueden abrir preguntas, pero no acumulan éxitos ni daño empírico.
- Ejecutar navegación ilimitada o un servicio de arranque: excedería este corte y mezclaría autonomía, herramientas y operación continua. Se entrega un ejecutor local finito; la investigación externa pasa por el anfitrión.
- Usar un proveedor LLM obligatorio en el núcleo: introduciría credenciales, coste y dependencia antes de evaluar los mecanismos. La interfaz es independiente del proveedor, con primera guía para Codex.

## Consecuencias

El corte permite comparar historias y aislar efectos de aprendizaje, preferencias, aversiones, simulación y reinicios. I1 predefine semillas y secuencias de feedback; sus resultados se informan por separado, sin índice de conciencia ni promesa de superioridad universal.

La autonomía depende de un ejecutor activo, presupuesto y actividades disponibles. Con biblioteca cerrada puede llegar a ciclos inactivos. La curiosidad local, las plantillas de sueño y las cinco dimensiones son acotadas; no se aprende una ontología nueva ni existe autoevaluación general de la verdad. El anfitrión aporta preguntas más ricas y fuentes adicionales cuando está activo.

Las prioridades pueden cambiar, pero los controles no son preferencias: ninguna aversión, objetivo o relato puede revocar una pausa o aumentar el presupuesto. La procedencia permite discutir qué se observó, qué se declaró y qué se imaginó sin convertir esa discusión en una afirmación de experiencia subjetiva.
