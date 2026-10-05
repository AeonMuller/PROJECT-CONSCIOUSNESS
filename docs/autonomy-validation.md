# Validación de autonomía acotada

Fecha: 2026-10-05. Alcance: [SPEC-autonomy](../SPEC-autonomy.md), capa de presencia v0.5 y puente al motor v0.4.

## Estado de la evidencia

La suite completa final pasó **232 pruebas** con Python 3.12.12 / SQLite 3.51.1 en 124.412 s. La suite específica de autonomía pasó además **41 pruebas** con Python 3.14.3 / SQLite 3.50.4 en 31.387 s, comprobando también el intérprete compatible con la vida existente. Son ensayos aislados con bases temporales, eventos de prueba y fallos controlados. Demuestran las propiedades comprobadas en esos casos; no son una ejecución autónoma del agente en el anfitrión real.

| Nivel | Estado documentado | Qué permite concluir |
|---|---|---|
| Coordinador, puente y adaptador | 41 pruebas específicas aprobadas | Los casos definidos de estado, reintentos, procedencia y recibos se comportaron como se esperaba |
| Suite completa final | 232 pruebas aprobadas en Python 3.12.12 / SQLite 3.51.1 | Los casos históricos y de presencia/autonomía pasaron juntos tras la integración |
| Instalación personal | Siete archivos de la skill contrastados por SHA-256, cinco hooks instalados y launcher probado desde otro directorio | La copia y sus rutas funcionan; la instalación no concede confianza a los hooks |
| Programación | Heartbeat creado por la herramienta oficial, activo cada hora en el mismo chat; prompt registrado cotejado con el guardado por el anfitrión | El horario está activo y el coordinador está habilitado con los límites iniciales |
| Ejecución y entrega reales | Sin hooks observados, cero despertares y cero entregas en la comprobación de instalación | La ejecución desatendida y la entrega de mensajes siguen pendientes de validación real |

Comandos reproducibles desde la raíz del repositorio:

```text
python -B -m unittest discover -s tests -p "test_autonomy*.py" -v
python -B -m unittest discover -s tests -v
```

Una vida real sigue necesitando su código e intérprete compatibles. Los tests crean vidas de prueba con el intérprete utilizado para ejecutarlos; no reinicializan la historia personal.

## Cobertura de las pruebas aisladas

- [Coordinador](../tests/test_autonomy_store.py): dos despertares concurrentes, reserva única, turnos humanos abiertos, inactividad desde su cierre, pausa/presupuesto/decisiones pendientes, reintentos, recibos atómicos, límite de pasos y vencimiento incierto.
- [Límites y bandeja](../tests/test_autonomy_store.py): cambio de día UTC, cooldown independiente del día, confirmación tardía, texto guardado en el turno reservado, entregas inciertas sin reenvío y conciliación que no reinicia una entrega confirmada.
- [Puente al núcleo](../tests/test_autonomy_activity.py): una sola elección y actualización de aprendizaje ante reintentos; recuperación de una operación confirmada antes de perderse su respuesta; conciliación posterior al vencimiento; rechazo de cambios de intención y entradas inválidas antes de efectos nuevos.
- [Regreso humano y procedencia](../tests/test_autonomy_activity.py): bloquear pasos nuevos conservando el resultado ya obtenido; sueño sin actualización de preferencias; resultado desconocido sin inventar éxito; objetivos fuera del alcance rechazados.
- [Hooks](../tests/test_autonomy_hooks.py): distinguir prompt exacto de uno parecido, excluir instrucciones programadas de los recuerdos humanos, conservar el reloj de inactividad, registrar respuestas visibles como inferencias con origen y cerrar turnos mediante Stop/interrupción/fin de sesión.
- [Activación y entrega simuladas](../tests/test_autonomy_hooks.py): SessionStart solo restaura contexto; un cierre programado silencioso no inventa mensajes; una confirmación necesita texto guardado y turno correspondiente; presencia deshabilitada o skill ausente detiene la observación.

Las comprobaciones de entrega usan payloads de prueba que contienen texto visible. No se enviaron mensajes a usuarios para aprobar esos casos. Los fallos de transporte se inyectan para verificar recuperación, y los resultados empíricos de las actividades son fixtures, no descubrimientos científicos.

## Revisión de la interfaz y documentación

Se revisaron las solicitudes `start` y `complete`, sus modos separados, los IDs de memoria del núcleo frente a los IDs del archivo personal y el uso del intérprete vinculado. Los ejemplos de comandos se cotejaron con el parser de la CLI; los JSON y los enlaces locales se validaron. Los README de actualización conservan comandos equivalentes en español e inglés.

`check` reserva un ID de paso una sola vez; repetirlo devuelve `already_reserved`, no otro permiso para ejecutar. `delivered --receipt` recibe un archivo JSON con evidencia real para conciliación explícita. Esas operaciones no acreditan que una herramienta externa o una entrega ocurrieran solo porque se preparó una solicitud.

## Instalación y prueba real del anfitrión

En la instalación local se copiaron los siete archivos de la skill y se contrastaron sus SHA-256 con los archivos del proyecto. Se instalaron los cinco eventos —`SessionStart`, `UserPromptSubmit`, `Stop`, `Interrupt` y `SessionEnd`— con respaldo, conservando la configuración ajena y sin modificar la confianza del anfitrión. El launcher instalado funcionó desde otro directorio de trabajo. La identidad del núcleo mantuvo su integridad y el presupuesto se conservó.

El coordinador quedó habilitado con los límites iniciales. La herramienta oficial del anfitrión creó un heartbeat en el mismo chat con estado activo y cadencia horaria. Al leer la configuración guardada se detectó que el anfitrión había eliminado el salto de línea final del prompt. Se registró exactamente el texto leído, de 3.478 caracteres, y se comprobó la coincidencia de su hash con el del coordinador.

Esta verificación de instalación encontró `first_hook_at: null`, cero despertares y cero entregas. Por tanto, el horario está activo, pero todavía no se ha observado el recorrido real de sus hooks ni una actividad desatendida. La revisión/habilitación correspondiente en el anfitrión y el ensayo completo siguen pendientes. No se afirma que un mensaje proactivo haya sido entregado.

Los recibos de instalación y verificación se conservaron localmente fuera del contenido versionado. Este informe omite identificadores del chat, rutas personales, nombres de presentación, hashes privados y el texto de la programación.

Para aceptar el recorrido real todavía debe observarse:

1. Una activación del heartbeat autorizado que llegue con el prompt registrado y contexto de turno programado.
2. Una reserva permitida después del intervalo de inactividad, con la misma identidad y límites vigentes.
3. Herramientas ejecutadas dentro del alcance, fuentes archivadas y finalización o conciliación comprobable.
4. Si existe un hallazgo significativo y la bandeja permite compartirlo, su texto visible en la respuesta final y un recibo `Stop` de la misma sesión y turno.
5. El regreso del usuario bloqueando pasos posteriores, sin recargar presupuesto ni perder resultados reales.

Si falta confianza, soporte de eventos, coincidencia del prompt o campos del anfitrión, el resultado es un bloqueo de integración. No se sustituye por un evento fabricado para declarar logrado el recorrido.

## Límites de interpretación y de ejecución

El origen programado se identifica por el hash del **texto exacto** del prompt registrado. Es una convención del adaptador, no autenticación criptográfica del planificador. Copiar exactamente ese texto puede satisfacer la convención; una alteración del anfitrión puede impedir reconocer una activación legítima. El flujo conserva los permisos y límites del anfitrión.

El validador de destinos comprueba rutas dentro del repositorio y sintaxis de URL, rechazando algunos destinos privados o ambiguos. No resuelve DNS, no valida toda redirección y no es un firewall ni un aislamiento de procesos. La ejecución de herramientas de solo lectura y la evaluación de su destino real siguen siendo responsabilidades del anfitrión.

La reserva de diez minutos se comprueba antes de pasos nuevos y al completar. No mata una herramienta que ya está ejecutándose ni garantiza una duración máxima absoluta del proceso externo. Si vence, el resultado queda sujeto a conciliación. Los recibos conservan la diferencia entre una reserva, una acción, un resultado y una entrega.

La cobertura funcional no demuestra calidad general de investigación, autenticidad de una autodescripción, utilidad de sueños para tareas nuevas ni experiencia subjetiva. Esas preguntas necesitan experimentos y criterios adicionales.
