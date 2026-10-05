# I1: identidad persistente y controles causales

Esta es la copia versionada del informe. Las bases completas están en `runs/i1-v04-20261005/identities`, fuera de Git. `archive-validation.json` conserva tamaños y SHA256 de todos los archivos del piloto; los CSV y comprobaciones están junto a este informe. El motor compatible está en `releases/project-consciousness-v0.4.zip`.

20 semillas; 140 bases; 3540 eventos; 1200 elecciones de seguimiento; 6000 filas de puntuación.

Comprobaciones: 401/401 válidas.

| Condición | Elecciones distintas de updated | Primera elección distinta | Cambio medio L1 de prioridades | Sueños nuevos |
|---|---:|---:|---:|---:|
| updated | 0 | 0 | 0.289373 | 20 |
| frozen | 60 | 0 | 0.000000 | 20 |
| neutral | 52 | 9 | 0.317054 | 20 |
| no-aversion | 4 | 0 | 0.287896 | 20 |
| no-dream | 0 | 0 | 0.289373 | 0 |
| restarted | 0 | 0 | 0.289373 | 20 |

El denominador de elecciones es diez por semilla y condición; el de primeras elecciones es el número de semillas.

Los resultados describen un mecanismo diseñado con feedback sintético. La primera elección compara el mismo estado; las siguientes incluyen historias que pueden divergir. Un cambio de puntuación puede no cambiar el máximo. No se mide conciencia, bienestar, personalidad humana ni superioridad general.

Las diez elecciones de seguimiento preceden a los cinco ciclos locales. El contraste no-dream confirma que se suprimen nuevas simulaciones; no evalúa una mejora de decisiones posteriores por soñar. La exposición inicial uniforme genera penalizaciones iguales: por diseño no altera el primer máximo al ocultarlas, aunque las experiencias posteriores puedan diferenciarlas.

Frozen conserva prioridades, aversiones y competencia; los recuerdos siguen creciendo. No-dream bloquea nuevas simulaciones. Restarted debe reproducir estados y eventos funcionales, excluyendo hashes de cadena que identifican cada rama.

Todas las fuentes del corpus y feedback están etiquetadas fixture://. REPORTED no certifica verdad externa; los sueños permanecen SIMULATED. El corpus cerrado agota sus lecturas; los ciclos posteriores pueden quedar idle.

Reproducir con el código archivado de esta versión y el mismo Python/SQLite:

```powershell
python -m project_consciousness life experiment --seeds 400:420 --out runs/i1-new
```

Source fingerprint: `['47d3cd19c8a023498536f478396db1cda079964af02bebf2c24211aa39b9ecf8']`.
Protocolo: `fb81332af6baa0bff3e6ee50b3750208bfcf7695a120d0ef419be1def7ac856f`. Archivos: protocol.json, checks.json, conditions.csv, scores.csv y bases identities/.
