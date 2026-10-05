# Demostración con Codex v0.4

Fecha: 2026-10-05. Se utilizó la skill instalada en `C:\Users\Sistemas\.agents\skills\project-consciousness`, su wrapper y el proyecto `F:\PC`. La historia de trabajo está en `runs/codex-v04-demo`; esta carpeta conserva una copia verificable y su diario.

Se creó una identidad con semilla nueva **3014558496432903127**, presupuesto 16 y cero recuerdos iniciales. Se importó el ADR de esta versión como información REPORTED. Codex propuso dos investigaciones: leer sobre indicadores de conciencia (understand) o sobre commit atómico de SQLite (explore). Ambas tenían novelty=.6, cost=.3, risk=0, y criterio explícito de completar lectura y síntesis.

El selector eligió `consciousness-indicators` por su puntuación 0.9640168929 frente a 0.9327321824. La elección quedó registrada antes de consultar la fuente. Codex leyó el resumen primario de [Butlin et al. (2023), arXiv v3](https://arxiv.org/abs/2308.08708v3). El trabajo propone indicadores computacionales derivados de teorías de conciencia; esta demostración no evalúa su cumplimiento en Aeon ni traslada conclusiones del artículo a este sistema.

El anfitrión registró lectura y síntesis completadas con feedback REPORTED, success=true, value=.4 y harm=0. Value es una valoración declarada de la actividad; harm informa ausencia de perjuicio operativo observado en la consulta. Ninguno mide bienestar subjetivo. La prioridad understand cambió de **0.2720269525 a 0.2823883681**, y su estimación de éxito de 1/2 a 2/3. Es una actualización por el recibo, no una evaluación de comprensión.

Se guardó una pregunta abierta sobre qué evidencia falta para relacionar memoria y preferencias con indicadores de conciencia y qué refutaría esa relación. Una reflexión vinculada a los eventos quedó INFERRED. Un sueño explícito y cuatro ciclos locales produjeron lectura del ADR, otra pregunta y una simulación programada; ambos sueños siguen SIMULATED. La lectura local añadió su propia proxy de aprendizaje, separada del feedback externo anterior.

Resultado final: **10 eventos, 6 ciclos, 10 créditos restantes, 8 memorias y 4 preguntas**. Verificación por recomputación: válida, cero errores. `events.jsonl`, `state.json`, `context.json`, `manifest.json`, `verification.json`, `identity.sqlite` y `diary.md` permiten examinar el recorrido. La verificación exportada es reconstruct; también se ejecutó recompute al cerrar la demostración.

El código de producción no inició un LLM ni navegó por sí mismo: Codex, activo en esta conversación, realizó la consulta. La instalación se comprobó por igualdad SHA256 de los cuatro archivos y por ejecución del wrapper. La aparición en el selector de skills de una conversación futura no se comprobó visualmente. El proceso local terminó; no quedó un servicio o bucle permanente ejecutándose.

Para continuar la historia de trabajo, con el código v0.4 compatible:

```powershell
python -m project_consciousness life context --life runs/codex-v04-demo
python -m project_consciousness life verify --life runs/codex-v04-demo --mode recompute
```

Para preservar este archivo de evidencia, crea una rama antes de experimentar desde la copia `reports/codex-v0.4`.
