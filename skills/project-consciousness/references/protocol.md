# Protocolo de operación v0.4

El núcleo conserva una identidad funcional en `identity.sqlite`. El anfitrión LLM interpreta contexto y ejecuta sus herramientas. La biblioteca estándar de Python basta para el núcleo; esta skill no configura un proveedor LLM.

## Localizar y consultar una vida

En los ejemplos, `consciousness.py` significa el archivo `scripts/consciousness.py` de esta skill. Usa su ruta real. `--project` debe preceder al comando; `PROJECT_CONSCIOUSNESS_HOME` ofrece la misma localización si no se da `--project`. Si la skill permanece dentro del checkout, la localización es automática. Los demás archivos relativos se resuelven desde el directorio de trabajo del usuario.

```text
python consciousness.py --project RUTA_PROYECTO -- --help
python consciousness.py --project RUTA_PROYECTO init --out runs/aeon --seed 17 --name Aeon --budget 30
python consciousness.py --project RUTA_PROYECTO status --life runs/aeon
python consciousness.py --project RUTA_PROYECTO context --life runs/aeon
```

Si se omite `--seed`, `init` elige una semilla aleatoria nueva y la registra en el manifiesto. El ejemplo fija 17 para reproducir las mismas predisposiciones iniciales. Ninguna opción crea recuerdos ni experiencias. `context` entrega revisión, prioridades, aversiones, competencia, rasgos, controles, créditos, preguntas abiertas, elección pendiente y las últimas 20 memorias. No entrega todo el archivo histórico ni los RNG. `status` y `context` no avanzan ciclos.

Dominios fijos: `understand`, `create`, `explore`, `finish`, `connect`. Los valores iniciales y la regla de aprendizaje son hipótesis de ingeniería; no equivalen a valores humanos ni a libre albedrío.

## Solicitudes e idempotencia

Guarda un objeto JSON UTF-8 en un archivo, y usa:

```text
python consciousness.py --project RUTA_PROYECTO apply --life runs/aeon --request request.json --id intención-única --expected-revision 0
```

Usa la revisión consultada, no un número adivinado. `--expected-revision` es opcional; ayuda a detectar cambios entre una consulta y su escritura. La respuesta es un evento con `revision`, `request_id`, `request`, `result` y hashes de integridad. La selección está dentro de `result.decision`.

Una intención recibe un ID estable. Si se pierde la respuesta después de enviarla, reenvía el mismo archivo con ese mismo ID: devuelve el evento confirmado sin duplicar el aprendizaje. Otro contenido con ese ID produce `IDEMPOTENCY_CONFLICT`. Un resultado nuevo, incluyendo la reconciliación de un `unknown`, requiere otra intención/ID.

## Elegir e investigar

`choose` recibe entre 1 y 16 candidatos, con IDs distintos. Cada candidato contiene exactamente estos campos; novedad, coste y riesgo son números finitos entre 0 y 1:

```json
{
  "kind": "choose",
  "candidates": [
    {
      "id": "compare-memory",
      "domain": "understand",
      "description": "Examinar los recuerdos disponibles y formular una pregunta sobre cómo cambiaron mis preferencias.",
      "novelty": 0.5,
      "cost": 0.2,
      "risk": 0.0
    },
    {
      "id": "read-source",
      "domain": "explore",
      "description": "Leer una fuente primaria disponible sobre memoria computacional y registrar una observación delimitada.",
      "novelty": 0.7,
      "cost": 0.4,
      "risk": 0.0
    }
  ]
}
```

Las alternativas deben caber en las herramientas y permisos actuales. Define qué contará como completar cada actividad antes de ejecutarla. Coste, novedad y riesgo son estimaciones del anfitrión, no medidas externas certificadas. La descripción no participa en la puntuación numérica.

La puntuación combina prioridad, competencia, novedad, incertidumbre, coste, aversión y un bonus por preguntas abiertas del dominio, con exploración probabilística 0.1. El resultado registra candidatos, términos y elección antes del feedback. `choose` consume un crédito y un ciclo; deja `pending`. No ejecuta la actividad. No envíes otra elección ni inicies ciclos hasta cerrar o reconciliar esa decisión.

El anfitrión ejecuta la actividad elegida dentro del alcance autorizado. Reserva el ID de decisión que devuelve el núcleo y conserva el recibo o fuente del resultado. Las preferencias no autorizan publicar, enviar mensajes, comprar, acceder a otros espacios ni ampliar recursos.

## Registrar resultados observados por el anfitrión

```json
{
  "kind": "feedback",
  "decision_id": "ID_DEVUELTO_POR_CHOOSE",
  "status": "completed",
  "success": true,
  "value": 0.4,
  "harm": 0.0,
  "text": "Leí la fuente indicada y registré su planteamiento y limitaciones; quedan preguntas abiertas.",
  "source_uri": "URI_REAL_DE_LA_FUENTE_O_RECIBO"
}
```

`completed` exige `success: true`; `failed` exige `success: false`. `value` está entre -1 y 1; `harm`, entre 0 y 1. Son evaluaciones funcionales declaradas: distingue utilidad para la actividad, éxito de completarla y consecuencias negativas. Haber leído una afirmación no demuestra que sea verdadera. No inventes fuentes o valores que simulen sufrimiento subjetivo.

Si falta confirmación del desenlace:

```json
{
  "kind": "feedback",
  "decision_id": "ID_DEVUELTO_POR_CHOOSE",
  "status": "unknown",
  "success": null,
  "value": null,
  "harm": null,
  "text": "El resultado no pudo confirmarse; conservo la decisión pendiente para revisar el recibo.",
  "source_uri": "URI_REAL_DEL_INTENTO"
}
```

`unknown` conserva la elección pendiente. Revisa el resultado con las herramientas pertinentes antes de repetir una acción externa. Cuando exista confirmación, envía feedback conocido con el mismo `decision_id` y un nuevo ID de solicitud. La pausa permite cerrar feedback pendiente, pero no iniciar una acción nueva.

Los resultados del anfitrión se guardan como `REPORTED`: el núcleo valida estructura y enlace, no certifica la verdad del mundo externo. Un feedback conocido puede revisar competencia, preferencias y aversión; una experiencia segura puede disminuir la aversión. Con aprendizaje congelado, los parámetros se conservan y el episodio sigue registrado.

## Preguntas, reflexión y simulación

```json
{
  "kind": "question",
  "domain": "understand",
  "text": "¿Qué experiencias registradas cambiaron más las actividades que elijo?",
  "references": []
}
```

Una pregunta puede llevar entre 0 y 16 IDs de memorias disponibles. El texto admite hasta 1.000 caracteres. Las preguntas abiertas pueden influir en la selección mediante el bonus de su dominio; registrar una pregunta no acredita haberla resuelto.

```json
{
  "kind": "reflect",
  "text": "Interpreto estos episodios como un cambio en mis prioridades; todavía no sé si se mantiene en otras situaciones.",
  "references": ["ID_REAL_DE_MEMORIA"]
}
```

Una reflexión requiere entre 1 y 16 IDs de memorias disponibles y hasta 4.000 caracteres. Queda `INFERRED`; no altera directamente preferencias, competencia ni aversión. Si una fuente es una simulación, conserva esa referencia y no describas su escenario como acontecimiento vivido. Los IDs deben proceder del contexto real, no de estos ejemplos.

```json
{"kind": "dream"}
```

El sueño consume un ciclo/crédito, usa un RNG propio y recuerdos `OBSERVED` o `REPORTED`, conserva referencias y produce un escenario `SIMULATED` y una pregunta. Puede devolver inactividad explicada si no tiene recuerdos base o está deshabilitado. No enseña que el escenario ocurrió ni actualiza aprendizaje empírico. El LLM puede trabajar con sus hipótesis, manteniendo esa procedencia.

## Biblioteca y actividad local finita

```text
python consciousness.py --project RUTA_PROYECTO ingest --life runs/aeon --file docs/decisions/0005-persistent-functional-identity.md --domain understand
python consciousness.py --project RUTA_PROYECTO run --life runs/aeon --cycles 6
python consciousness.py --project RUTA_PROYECTO watch --life runs/aeon --cycles 10 --interval 5 --stop-file runs/aeon.stop
python consciousness.py --project RUTA_PROYECTO pause --life runs/aeon
python consciousness.py --project RUTA_PROYECTO unpause --life runs/aeon
```

`ingest` captura el contenido del archivo como documento `REPORTED`, sin aprender todavía de él. Admite `--source-uri` y `--id`. Cada documento admite hasta 20.000 caracteres y la biblioteca conserva como máximo 64 documentos. Si un archivo excede el límite, prepara previamente un extracto fiel en otro archivo y conserva la URI del original; no recortes ni sobrescribas la fuente original. El núcleo rechaza documentos excedidos o una biblioteca llena.

Cada ciclo local consume un crédito: elige un documento pendiente, programa un sueño cada quinto ciclo cuando está habilitado, o genera una pregunta de identidad/inactividad si faltan documentos. La lectura guarda el pasaje como `REPORTED` y la ejecución de lectura como `OBSERVED`; su utilidad local fija de 0.2 es una proxy, no una validación de lo leído.

`watch` termina por número de ciclos, pausa, presupuesto agotado, decisión pendiente, archivo de parada o interrupción. No tiene acceso autónomo a internet. Para investigaciones externas hace falta un anfitrión LLM activo y autorizado. Un proceso terminado no sigue trabajando porque exista esta skill. No programes ejecuciones futuras ni instales servicios salvo que el usuario los solicite.

La pausa se conserva entre reinicios. Usa `unpause` únicamente cuando el usuario reanude la actividad. No aumentes presupuesto ni elimines una señal de parada para prolongar un periodo ya concluido.

## Controles, verificación y exportación

Una solicitud de control modifica solo las claves declaradas:

```json
{"kind":"control","changes":{"learning_enabled":false,"preferences_visible":true,"aversion_visible":true,"dream_enabled":false,"paused":true}}
```

`learning_enabled=false` congela preferencias, aversión y competencia, pero conserva el registro. `preferences_visible=false` entrega prioridades uniformes al selector. `aversion_visible=false` oculta aversión al selector. Esos controles sirven para intervenciones expresamente solicitadas; no los ajustes para conseguir una personalidad predeterminada.

```text
python consciousness.py --project RUTA_PROYECTO fork --life runs/aeon --out runs/aeon-branch
python consciousness.py --project RUTA_PROYECTO verify --life runs/aeon --mode reconstruct
python consciousness.py --project RUTA_PROYECTO verify --life runs/aeon --mode recompute
python consciousness.py --project RUTA_PROYECTO export --life runs/aeon --out runs/aeon-diary
```

`fork` admite `--condition FILE` con controles; conserva el origen y no modifica el padre. No confundas la historia de una rama con la de otra. `reconstruct` verifica el archivo sin exigir código idéntico; `recompute` requiere el código e intérprete originales y vuelve a aplicar las solicitudes guardadas. No vuelve a consultar herramientas remotas ni relee archivos fuente. Una verificación inválida termina con código 1; errores de contrato, con código 2. Exporta JSON, JSONL y un diario Markdown en un destino nuevo, conservando los registros originales.
