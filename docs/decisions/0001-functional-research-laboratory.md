# ADR-0001: laboratorio funcional persistente e intervenible

Fecha: 2026-10-03. Estado: **propuesto para revisión**, sin implementación ni aprobación experimental implícita.

## Contexto

El proyecto solicita investigar funciones relacionadas con conciencia mediante memoria, autorrepresentación y control causal. Debe evitar que una narración persuasiva sustituya la medición de mecanismos. También requiere separar ciencia, ingeniería especulativa y filosofía, e incluir una revisión crítica del informe Gateway.

## Decisión propuesta

1. **Núcleo explícito y monolito modular.** Un coordinador conecta componentes con contratos de datos, actualizaciones por fases y presupuesto. Las dependencias de construcción están en el [mapa](../../CAPABILITY-MAP.md).
2. **Persistencia con eventos y snapshots.** SQLite conserva estado y trazas de un simulador local; la memoria cognitiva tiene acceso y presupuesto distintos del log técnico.
3. **MVP tabular y situado.** Un entorno parcialmente observable permite conocer la verdad experimental sin revelársela al agente. Las tablas y reglas de control facilitan identificar rutas causales; un modelo lingüístico se incorpora después como condición separada.
4. **Teorías como fuentes de hipótesis.** Módulos inspirados en workspace, recurrencia, metacognición y regulación se pueden sustituir y retirar. No se presenta su combinación como una teoría unificada de conciencia.
5. **Evaluación con intervenciones.** Clones de snapshots, sham, máscaras de lectores/escritores, controles de capacidad, evaluación retenida e informes con incertidumbre. Gateway aporta material documental e hipótesis etiquetadas, sin asumir sus extrapolaciones no locales.

## Alternativas consideradas

| Alternativa | Ventaja | Motivo para posponerla o descartarla como base |
|---|---|---|
| Chatbot con personalidad y conversación persistente | Prototipo conversacional rápido | Dificulta aislar estado, fuente de memoria y causalidad del relato |
| Conjunto de agentes LLM con vector store | Especialización lingüística flexible | Coste, no determinismo y rutas implícitas de información complican el primer experimento |
| Red end-to-end entrenada desde cero | Representaciones emergentes y aprendizaje de control | Necesita datos/cómputo y hace más difícil la primera atribución causal; extensión comparativa posterior |
| Simulación neuronal biológicamente detallada | Permite estudiar mecanismos concretos del sustrato modelado | No basta como criterio de experiencia; exige otra escala y validación biológica específica |
| Microservicios y mensajería distribuida | Escala y aislamiento operativo | Añade concurrencia y fallos antes de validar el ciclo funcional |
| Adoptar una teoría de conciencia como criterio de éxito | Hipótesis más estrecha | El encargo requiere pluralidad y pruebas funcionales; se permiten variantes específicas sin convertirlas en verdad de referencia |

## Consecuencias

La primera versión será pequeña y auditable, pero sus mecanismos estarán diseñados manualmente y no demostrarán emergencia de funciones equivalentes a las humanas. Un sistema tabular puede ser suficiente para algunas tareas, por lo que los baselines competentes son necesarios. La complejidad adicional solo se justificará mediante nuevos objetivos o evidencia comparativa.

La reproducibilidad exacta se limita inicialmente al entorno y runtime fijados. Extensiones con proveedores externos, robots o concurrencia necesitan contratos de efectos inciertos y otra política de reproducción. La ampliación del alcance requerirá actualizar esta decisión y las especificaciones afectadas.

## Verificación de la decisión

El primer informe deberá permitir rastrear cada resultado a datos, configuración y una intervención. Si el agente no puede continuar sin su narrador, una variable solo cambia lenguaje o las simulaciones contaminan hechos, la implementación no habrá satisfecho esta decisión. Un resultado funcional nulo con banco válido sigue siendo un resultado de investigación útil.
