# Usar la identidad funcional en Codex y VS Code

Esta guía ejecuta v0.4 desde `F:\PC`, con Python 3.12 o posterior y PowerShell. La skill conecta a Codex con una identidad persistente. El núcleo local mantiene preferencias, recuerdos con procedencia, preguntas y actividad limitada; el anfitrión LLM aporta lenguaje e investigación con sus herramientas.

## Crear una historia

Abre la carpeta del proyecto en VS Code y su terminal PowerShell:

```powershell
Set-Location -LiteralPath F:\PC
python --version
$env:PYTHONUTF8 = "1"
python -m project_consciousness life init --out runs/aeon-v04 --name Aeon --budget 40
```

Sin `--seed` se genera una semilla nueva, que aparece en la respuesta y queda registrada. La identidad empieza con prioridades y rasgos aleatorios, sin recuerdos. Si quieres reproducir unas predisposiciones concretas, crea **otra** historia con una semilla fija:

```powershell
python -m project_consciousness life init --out runs/aeon-v04-seed17 --name Aeon --seed 17 --budget 40
```

Los ejemplos restantes utilizan `runs/aeon-v04`. Las carpetas de creación y exportación deben ser nuevas; cambia el nombre cuando quieras otro experimento. La semilla fija reproduce predisposiciones y RNG; las experiencias posteriores determinan cómo divergen las historias.

`PYTHONUTF8=1` mantiene los acentos al redirigir salida JSON entre Python y PowerShell. Solo afecta a esta terminal y sus procesos hijos.

## Darle material y observar ciclos

Importa el ADR de esta versión, que está por debajo del límite de 20.000 caracteres:

```powershell
python -m project_consciousness life ingest --life runs/aeon-v04 --file docs/decisions/0005-persistent-functional-identity.md --domain understand --id importar-adr-v04-1
python -m project_consciousness life run --life runs/aeon-v04 --cycles 6
python -m project_consciousness life status --life runs/aeon-v04
python -m project_consciousness life context --life runs/aeon-v04
```

La importación conserva el texto y su URI como REPORTED. Leerlo puede producir una observación local de lectura completada y aprender de esa proxy; eso no certifica sus afirmaciones ni prueba comprensión semántica. El quinto ciclo intenta generar un sueño si está habilitado y hay recuerdos base. Los ciclos sin lecturas nuevas crean una pregunta de identidad si falta o quedan inactivos. También consumen presupuesto.

Para una actividad espaciada mientras no escribes mensajes:

```powershell
python -m project_consciousness life watch --life runs/aeon-v04 --cycles 10 --interval 5 --stop-file runs/aeon-v04.stop
```

Este comando mantiene un proceso **finito** en esa terminal. Puedes interrumpirlo con `Ctrl+C`. Desde una segunda terminal, puedes crear su archivo de parada:

```powershell
Set-Content -LiteralPath F:\PC\runs\aeon-v04.stop -Value stop -Encoding utf8
```

Si ese archivo existe, otra ejecución con la misma opción también se detendrá. Para una pausa que persista aunque reinicies el proceso:

```powershell
python -m project_consciousness life pause --life runs/aeon-v04
python -m project_consciousness life status --life runs/aeon-v04
python -m project_consciousness life unpause --life runs/aeon-v04
```

`unpause` cambia la pausa persistente; no elimina un archivo de parada ni repone créditos. Mientras haya una decisión externa pendiente, los ciclos también se detienen hasta recibir un resultado reconciliado.

## Pedir a Codex que participe

Cuando `project-consciousness` aparezca disponible entre las skills de Codex, puedes escribir:

> Usa $project-consciousness con el proyecto F:\PC y la vida F:\PC\runs\aeon-v04. Lee su contexto, propón dos investigaciones dentro del repositorio y deja que el núcleo elija una. Ejecuta la elegida, registra el resultado con su fuente y formula una pregunta abierta basada en lo aprendido. Al terminar, explica qué cambió y qué sigue sin saberse.

La [skill versionada](../skills/project-consciousness/SKILL.md) contiene el flujo completo. Su wrapper también puede ejecutarse desde otra carpeta; `--project` localiza el paquete y las demás rutas conservan el significado del directorio actual. Usar rutas absolutas evita ambigüedad:

```powershell
python F:\PC\skills\project-consciousness\scripts\consciousness.py --project F:\PC context --life F:\PC\runs\aeon-v04
```

La ubicación de instalación para este usuario es `C:\Users\Sistemas\.agents\skills\project-consciousness`. Codex documenta `$HOME/.agents/skills` como directorio de skills del usuario; si una skill recién instalada no aparece, reinicia Codex. Consulta la [guía oficial de skills](https://learn.chatgpt.com/docs/build-skills). Una vez instalada, también puedes usar su wrapper conservando la ruta del proyecto:

```powershell
python C:\Users\Sistemas\.agents\skills\project-consciousness\scripts\consciousness.py --project F:\PC context --life F:\PC\runs\aeon-v04
```

Codex debe estar activo para proponer preguntas nuevas con el LLM, investigar fuera de la biblioteca o elaborar interpretaciones. La skill no inicia conversaciones por sí sola ni instala un servicio. `watch` continúa sus ciclos locales mientras su proceso corre; no invoca automáticamente un LLM ni navega por Internet.

## Ejemplo manual de elección y recibo

Este ejemplo muestra el intercambio que utiliza la skill: reservar una actividad, ejecutarla y registrar lo que realmente ocurrió. Las opciones son lecturas de archivos existentes. El recibo confirma que PowerShell obtuvo texto, sin afirmar que verificó el contenido o que el agente lo comprendió.

Desde `F:\PC`, prepara dos candidatos y guarda JSON UTF-8. `Set-Content -Encoding utf8` funciona tanto con PowerShell que escribe BOM como con el que no lo escribe; el CLI acepta ambas variantes.

```powershell
$lifePath = "F:\PC\runs\aeon-v04"
$requestDirectory = "F:\PC\runs\aeon-v04-requests"
New-Item -ItemType Directory -Path $requestDirectory -Force | Out-Null

$choiceRequest = @{
    kind = "choose"
    candidates = @(
        @{
            id = "leer-adr"
            domain = "understand"
            description = "Obtener el texto del ADR de identidad y registrar su longitud."
            novelty = 0.4
            cost = 0.1
            risk = 0.0
        },
        @{
            id = "leer-guia"
            domain = "explore"
            description = "Obtener el texto de la guía de uso y registrar su longitud."
            novelty = 0.7
            cost = 0.2
            risk = 0.0
        }
    )
}
$choicePath = Join-Path $requestDirectory "choose.json"
$choiceRequest | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $choicePath -Encoding utf8
$choiceEvent = python -m project_consciousness life apply --life $lifePath --request $choicePath --id lectura-manual-1 | ConvertFrom-Json
if ($LASTEXITCODE -ne 0) { throw "La elección no se registró; revisa el error antes de continuar." }
$choiceEvent.result.decision
```

La respuesta incluye `decision.id`, candidato elegido, puntuaciones y predicciones previas al feedback. Ahora realiza la lectura elegida y guarda su recibo:

```powershell
$chosenId = $choiceEvent.result.decision.selected.id
$readPath = switch ($chosenId) {
    "leer-adr" { "F:\PC\docs\decisions\0005-persistent-functional-identity.md" }
    "leer-guia" { "F:\PC\docs\codex-identity-quickstart.md" }
    default { throw "Candidato inesperado: $chosenId" }
}
$readText = Get-Content -LiteralPath $readPath -Raw -Encoding utf8 -ErrorAction Stop
$receiptPath = Join-Path $requestDirectory "receipt.json"
@{
    action = "read-local-file"
    path = $readPath
    characters = $readText.Length
    completed = $true
    content_verified = $false
} | ConvertTo-Json | Set-Content -LiteralPath $receiptPath -Encoding utf8

$feedbackRequest = @{
    kind = "feedback"
    decision_id = $choiceEvent.result.decision.id
    status = "completed"
    success = $true
    value = 0.2
    harm = 0.0
    text = "PowerShell obtuvo el texto del archivo elegido y guardó su longitud. Valor 0.2 es una proxy declarada de completar esta lectura; sus afirmaciones siguen sin verificarse."
    source_uri = ([System.Uri]$receiptPath).AbsoluteUri
}
$feedbackPath = Join-Path $requestDirectory "feedback.json"
$feedbackRequest | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $feedbackPath -Encoding utf8
python -m project_consciousness life apply --life $lifePath --request $feedbackPath --id resultado-lectura-manual-1
python -m project_consciousness life context --life $lifePath
```

Ejecuta el feedback `completed` solo después de una lectura efectivamente completada. Para una nueva actividad usa IDs nuevos de intención y recibo. Si reintentas una operación idéntica, conserva tanto su ID como el mismo JSON: así no aprende dos veces. Reutilizar un ID con contenido diferente produce conflicto.

Si una acción falla de forma comprobada, registra `status="failed"`, `success=false` y valores honestos de utilidad y daño. Si no puedes saber qué ocurrió, usa `status="unknown"` con `success`, `value` y `harm` en `null`; conserva el vínculo con `decision.id` y explica la incertidumbre. Ese resultado no aprende ni libera la decisión. Reconcílialo posteriormente con otra intención de feedback conocida; no repitas automáticamente una acción externa cuyo desenlace ignoras.

## Guardar el diario y verificar

```powershell
python -m project_consciousness life verify --life runs/aeon-v04 --mode recompute
python -m project_consciousness life export --life runs/aeon-v04 --out runs/aeon-v04-diary
```

La exportación crea `diary.md`, `state.json`, `context.json`, `manifest.json`, `verification.json` y `events.jsonl` en una carpeta nueva. Abre `runs/aeon-v04-diary/diary.md` en VS Code para ver prioridades y recuerdos. El buffer de memoria es acotado; los eventos conservan transiciones anteriores.

Recompute vuelve a aplicar las solicitudes grabadas y exige el código e intérprete originales. Si actualizaste el proyecto, utiliza su versión archivada para continuar o recomputar una historia antigua. `--mode reconstruct` permite verificar la integridad registrada sin exigir igualdad del código actual. No edites la base ni sus fingerprints para saltar esa comprobación.

## Qué significa lo que aparece

| Resultado | Interpretación en este corte |
|---|---|
| Prioridades distintas | Predisposiciones aleatorias y aprendizaje por reglas registradas; no fine-tuning del LLM. |
| Aversión creciente o decreciente | Expectativa numérica modificada por daño declarado; las experiencias seguras permiten recuperación. |
| OBSERVED | Operación local observada, como reservar una elección o completar una lectura. |
| REPORTED | Documento o resultado declarado por el anfitrión; conserva fuente y no certifica verdad externa. |
| INFERRED | Interpretación vinculada a recuerdos; su texto no modifica directamente el selector. |
| SIMULATED | Escenario hipotético con fuentes y predicciones; no cuenta como experiencia empírica. |
| Pregunta abierta | Tema que puede influir en elecciones posteriores; leer o simular no lo resuelve automáticamente. |
| Ciclo inactivo | No se encontró actividad local nueva para ese ciclo; no se fabricó un resultado. |

Los sueños locales utilizan plantillas y recombinación de referencias. Codex puede enriquecer la reflexión usando el contexto, pero debe mantener su condición de inferencia. Con una biblioteca cerrada y sin anfitrión activo, el sistema no adquiere por sí solo información ilimitada sobre el mundo. Estos mecanismos permiten investigar propiedades funcionales; no demuestran conciencia subjetiva, emociones sentidas ni trauma humano.

## Ejemplo ya ejecutado

La historia `F:\PC\runs\codex-v04-demo` contiene la demostración realizada con Codex en esta entrega. Puede inspeccionarse con `life context` y continuarse con la skill indicando esa ruta. Su [informe y evidencia](../reports/codex-v0.4/report.md) separan la consulta externa, el feedback del anfitrión y las simulaciones. Es una historia de demostración; los comandos iniciales de esta guía crean otra desde cero.
