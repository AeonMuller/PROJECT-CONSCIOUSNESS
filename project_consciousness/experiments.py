"""Frozen pilot protocols and reports derived from persisted experimental data."""

from dataclasses import replace
from datetime import datetime, timezone
import csv
import hashlib
import json
from pathlib import Path
import platform
import random
import sqlite3
from statistics import mean

from . import __version__
from .contracts import Config, LabError, canonical, digest
from .runtime import Runtime


PROTOCOL_VERSION = "mvp-0.1-e0-e1-1"
STATISTICAL_SEED = 20261003
CONDITIONS = ("intact", "sham", "block_read", "block_write", "mask_relevant",
              "mask_irrelevant", "history", "reactive")
READER_CONDITIONS = ("intact", "sham", "block_read", "mask_relevant", "mask_irrelevant")
METRIC_FIELDS = (
    "seed", "condition", "status", "error", "episodes_planned", "episodes_completed",
    "successes", "success_rate", "success_rate_completed", "brier_mean",
    "actions_budget", "actions_consumed", "records_capacity", "records_scanned_total",
    "memory_bytes_peak", "memory_bytes_mean", "verify_valid", "restart_tick", "run_path",
)
COMPARISON_FIELDS = (
    "baseline", "condition", "metric", "status", "planned_pairs", "complete_pairs",
    "excluded_seeds", "difference_condition_minus_baseline", "ci95_low", "ci95_high",
    "bootstrap_samples", "statistical_seed",
)
CAUSAL_FIELDS = (
    "seed", "condition", "status", "error", "parent_tick", "same_pre_state",
    "same_observation", "baseline_probability_left", "probability_left",
    "total_variation", "baseline_action", "action", "action_changed", "verify_valid",
    "run_path",
)


def _write_json(path: Path, data: dict) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def _write_csv(path: Path, rows: list[dict], fields: tuple[str, ...]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def _read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _positive_integer(value: int, name: str, minimum: int = 1) -> None:
    if type(value) is not int or value < minimum:
        raise LabError("INVALID_INPUT", f"{name} must be an integer >= {minimum}")


def _prepare(out: Path, experiment: str, config: Config, **parameters) -> tuple[Path, dict]:
    out = Path(out).resolve()
    if out.exists():
        raise LabError("PATH_EXISTS", f"Experiment directory already exists: {out}")
    out.mkdir(parents=True, exist_ok=False)
    sources = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
               for p in sorted(Path(__file__).parent.glob("*.py"))}
    manifest = {
        "experiment": experiment, "protocol_version": PROTOCOL_VERSION,
        "package_version": __version__, "created_utc": datetime.now(timezone.utc).isoformat(),
        "python": platform.python_version(), "sqlite": sqlite3.sqlite_version,
        "source_files": sources, "source_fingerprint": digest(sources),
        "config": config.to_dict(), "parameters": parameters, "status": "running",
        "interpretation": "Hipótesis de ingeniería; tarea y asociación pista-respuesta diseñadas. No mide conciencia.",
    }
    _write_json(out / "manifest.json", manifest)
    return out, manifest


def _error_text(error: Exception) -> str:
    return f"{getattr(error, 'code', type(error).__name__)}: {error}"


def _recover_traces(path: Path, runtime: Runtime | None) -> list:
    """Keep confirmed work in the denominator even when a reopen fails."""
    try:
        if runtime is not None:
            return runtime.traces()
        with Runtime.open(path) as reopened:
            return reopened.traces()
    except Exception:
        return []  # The calling row remains explicitly failed, never successful.


def run_e0(out: Path, seed: int = 17, ticks: int = 1000, config: Config = Config()) -> dict:
    """Compare continuous execution with actual close/reopen interruptions."""
    _positive_integer(ticks, "ticks", 2)
    if config.policy_mode != "fixed":
        raise LabError("INVALID_INPUT", "E0 retains the fixed policy; use L1 for learned persistence")
    if type(seed) is not int or not 0 <= seed < 2**63:
        raise LabError("INVALID_INPUT", "seed must be an integer in [0, 2**63)")
    checkpoints = sorted({tick for tick in (1, ticks // 3, ticks // 2, ticks - 1) if 0 < tick < ticks})
    out, manifest = _prepare(out, "E0", config, seed=seed, ticks=ticks, checkpoints=checkpoints)
    traces: dict[str, list] = {}
    rows = []
    for condition in ("continuous", "resumed"):
        path = out / "runs" / condition
        runtime = None
        verification = {"valid": False, "errors": []}
        error = ""
        current_traces = []
        try:
            runtime = Runtime.create(path, seed, config)
            if condition == "continuous":
                runtime.run(ticks)
            else:
                previous = 0
                for checkpoint in checkpoints:
                    runtime.run(checkpoint - previous)
                    runtime.close()
                    runtime = None
                    runtime = Runtime.open(path)
                    previous = checkpoint
                runtime.run(ticks - previous)
            current_traces = runtime.traces()
            verification = runtime.verify(mode="recompute")
            if not verification["valid"]:
                error = "Verification failed: " + canonical(verification["errors"])
        except Exception as exc:
            error = _error_text(exc)
            current_traces = _recover_traces(path, runtime)
        finally:
            if runtime is not None:
                runtime.close()
        traces[condition] = current_traces
        rows.append({"condition": condition, "status": "failed" if error else "ok",
                     "error": error, "ticks_planned": ticks, "ticks_completed": len(current_traces),
                     "verify_valid": verification["valid"], "run_path": str(path.relative_to(out))})
    left, right = traces["continuous"], traces["resumed"]
    mismatches = [i for i in range(max(len(left), len(right)))
                  if i >= len(left) or i >= len(right) or left[i] != right[i]]
    valid = (all(row["status"] == "ok" and row["ticks_completed"] == ticks for row in rows)
             and not mismatches)
    summary = {
        "experiment": "E0", "status": "passed" if valid else "failed", "valid": valid,
        "ticks_planned": ticks, "checkpoints": checkpoints, "mismatch_ticks": mismatches,
        "runs_planned": 2, "runs_completed": sum(row["status"] == "ok" for row in rows),
        "scope": "Continuidad con cierres reales y recomputación. Fallos de commit e idempotencia se cubren en tests del runtime.",
        "experiment_dir": str(out), "report_path": str(out / "report.md"),
    }
    _write_csv(out / "metrics.csv", rows, ("condition", "status", "error", "ticks_planned", "ticks_completed", "verify_valid", "run_path"))
    _write_csv(out / "comparisons.csv", [{"traces_equal": not mismatches,
                                        "mismatch_ticks": canonical(mismatches)}], ("traces_equal", "mismatch_ticks"))
    _write_json(out / "summary.json", summary)
    manifest["status"] = summary["status"]
    _write_json(out / "manifest.json", manifest)
    write_report(out)
    return summary


def _condition_config(config: Config, condition: str) -> Config:
    changes = {
        "intact": {}, "sham": {"read_mode": "sham"},
        "block_read": {"read_mode": "block_all"}, "block_write": {"write_enabled": False},
        "mask_relevant": {"read_mode": "mask_relevant"},
        "mask_irrelevant": {"read_mode": "mask_irrelevant"},
        "history": {"agent_mode": "history"}, "reactive": {"agent_mode": "reactive"},
    }
    return replace(config, **changes[condition])


def _measure(seed: int, condition: str, traces: list, episodes: int, config: Config,
             error: str, verified: bool, path: str) -> dict:
    completed = [trace for trace in traces if trace["outcome"]["terminal"]]
    successes = sum(bool(trace["outcome"]["success"]) for trace in completed)
    briers = []
    for trace in completed:
        decision, outcome = trace["decision"], trace["outcome"]
        # The evaluator infers the binary label from the observed action and its outcome.
        true_left = (decision["action"] == "left") == bool(outcome["success"])
        briers.append((decision["probability_left"] - int(true_left)) ** 2)
    memory_bytes = [max(trace["decision"]["memory_bytes"], trace.get("post_memory_bytes", 0)) for trace in traces]
    return {
        "seed": seed, "condition": condition, "status": "failed" if error else "ok", "error": error,
        "episodes_planned": episodes, "episodes_completed": len(completed), "successes": successes,
        "success_rate": successes / episodes,
        "success_rate_completed": successes / len(completed) if completed else None,
        "brier_mean": mean(briers) if briers else None,
        "actions_budget": episodes * (config.delay + 2), "actions_consumed": len(traces),
        "records_capacity": config.capacity, "records_scanned_total": sum(t["decision"]["records_scanned"] for t in traces),
        "memory_bytes_peak": max(memory_bytes, default=0), "memory_bytes_mean": mean(memory_bytes) if memory_bytes else 0,
        "verify_valid": verified, "restart_tick": config.delay + 1, "run_path": path,
    }


def _quantile(sorted_values: list[float], probability: float) -> float:
    index = (len(sorted_values) - 1) * probability
    lower = int(index)
    upper = min(lower + 1, len(sorted_values) - 1)
    return sorted_values[lower] + (sorted_values[upper] - sorted_values[lower]) * (index - lower)


def _paired_comparisons(rows: list[dict], seeds: list[int], samples: int) -> list[dict]:
    indexed = {(row["seed"], row["condition"]): row for row in rows}
    comparisons = []
    for condition in CONDITIONS[1:]:
        for metric in ("success_rate", "brier_mean", "records_scanned_total", "memory_bytes_peak", "actions_consumed"):
            differences, excluded = [], []
            for seed in seeds:
                baseline, treatment = indexed[(seed, "intact")], indexed[(seed, condition)]
                if (baseline["status"] != "ok" or treatment["status"] != "ok"
                        or baseline["verify_valid"] is not True or treatment["verify_valid"] is not True
                        or baseline[metric] is None or treatment[metric] is None):
                    excluded.append(seed)
                else:
                    differences.append(treatment[metric] - baseline[metric])
            # This stream does not access or advance either world or policy RNG.
            rng = random.Random(int(digest({"statistical_seed": STATISTICAL_SEED, "condition": condition, "metric": metric}), 16))
            bootstrap = sorted(mean(rng.choices(differences, k=len(differences))) for _ in range(samples)) if len(differences) >= 2 else []
            comparisons.append({
                "baseline": "intact", "condition": condition, "metric": metric,
                "status": "incomplete" if excluded else ("descriptive_single_seed" if len(differences) < 2 else "ok"),
                "planned_pairs": len(seeds), "complete_pairs": len(differences), "excluded_seeds": canonical(excluded),
                "difference_condition_minus_baseline": mean(differences) if differences else None,
                "ci95_low": _quantile(bootstrap, 0.025) if bootstrap else None,
                "ci95_high": _quantile(bootstrap, 0.975) if bootstrap else None,
                "bootstrap_samples": samples if bootstrap else 0, "statistical_seed": STATISTICAL_SEED,
            })
    return comparisons


def _causal_branches(out: Path, seeds: list[int], config: Config, rows: list[dict]) -> list[dict]:
    results = []
    successful = {row["seed"] for row in rows if row["condition"] == "intact" and row["status"] == "ok"}
    parent_tick = config.delay + 1
    for seed in seeds:
        parent = None
        parent_error = ""
        try:
            if seed not in successful:
                raise LabError("PARENT_FAILED", "The intact trajectory did not complete and verify")
            parent = Runtime.open(out / "runs" / "intact" / f"seed-{seed}")
            reference = parent.snapshot(parent_tick)
            baseline_trace = next(trace for trace in parent.traces() if trace["tick"] == parent_tick)
        except Exception as exc:
            parent_error = _error_text(exc)
        try:
            for condition in READER_CONDITIONS:
                path = out / "branches" / f"seed-{seed}" / condition
                result = {field: None for field in CAUSAL_FIELDS}
                result.update(seed=seed, condition=condition, status="failed", error=parent_error,
                              parent_tick=parent_tick, run_path=str(path.relative_to(out)))
                branch = None
                try:
                    if parent_error:
                        results.append(result)
                        continue
                    branch_config = _condition_config(config, condition)
                    branch = parent.fork(path, parent_tick, {"read_mode": branch_config.read_mode})
                    before = branch.snapshot()
                    same_pre_state = all(before[key] == reference[key] for key in ("tick", "agent", "environment", "rng"))
                    trace = branch.step()
                    verified = branch.verify(mode="recompute")["valid"]
                    same_observation = trace["observation"] == baseline_trace["observation"]
                    baseline_decision, decision = baseline_trace["decision"], trace["decision"]
                    valid = same_pre_state and same_observation and verified
                    result.update(
                        status="ok" if valid else "failed", error="" if valid else "Causal branch invariants failed",
                        same_pre_state=same_pre_state, same_observation=same_observation,
                        baseline_probability_left=baseline_decision["probability_left"], probability_left=decision["probability_left"],
                        total_variation=abs(decision["probability_left"] - baseline_decision["probability_left"]),
                        baseline_action=baseline_decision["action"], action=decision["action"],
                        action_changed=decision["action"] != baseline_decision["action"], verify_valid=verified,
                    )
                except Exception as exc:
                    result["error"] = _error_text(exc)
                finally:
                    if branch is not None:
                        branch.close()
                results.append(result)
        finally:
            if parent is not None:
                parent.close()
    return results


def run_e1(out: Path, seeds: list[int] | None = None, episodes: int = 40,
           config: Config = Config(), bootstrap_samples: int = 2000) -> dict:
    """Run paired full trajectories plus local, same-snapshot reader interventions."""
    if config.policy_mode != "fixed":
        raise LabError("INVALID_INPUT", "E1 retains the fixed policy; use L1 for association learning")
    seeds = list(range(100, 120)) if seeds is None else list(seeds)
    if not seeds or any(type(seed) is not int or not 0 <= seed < 2**63 for seed in seeds) or len(set(seeds)) != len(seeds):
        raise LabError("INVALID_INPUT", "seeds must be nonempty, distinct integers in [0, 2**63)")
    _positive_integer(episodes, "episodes")
    _positive_integer(bootstrap_samples, "bootstrap_samples")
    if (config.agent_mode, config.read_mode, config.write_enabled) != ("episodic", "intact", True):
        raise LabError("INVALID_INPUT", "E1 fixes agent/read/write conditions; customize only delay and capacity")
    out, manifest = _prepare(
        out, "E1", config, seeds=seeds, episodes=episodes, conditions=list(CONDITIONS),
        bootstrap_samples=bootstrap_samples, statistical_seed=STATISTICAL_SEED,
        estimand="Differences condition minus intact, paired by seed; descriptive 95% percentile bootstrap",
        success_denominator="episodes_planned; completed-only rate also exported",
        brier_definition="mean squared error of probability_left against the binary true-left outcome; one component",
        budget="Same action limit, delay, record capacity; reactive intentionally has no historical information",
        branch_design="One first-choice snapshot per seed; identical world, RNG and agent before read intervention",
        inferential_limit="Engineered delayed-cue task, programmed association, no training or held-out generalization",
    )
    rows = []
    for condition in CONDITIONS:
        condition_config = _condition_config(config, condition)
        for seed in seeds:
            path = out / "runs" / condition / f"seed-{seed}"
            runtime, traces, error, verified = None, [], "", False
            try:
                runtime = Runtime.create(path, seed, condition_config)
                runtime.run(config.delay + 1)
                runtime.close()
                runtime = None
                runtime = Runtime.open(path)
                runtime.run(episodes * (config.delay + 2) - config.delay - 1)
                traces = runtime.traces()
                verification = runtime.verify(mode="recompute")
                verified = verification["valid"]
                completed = sum(bool(trace["outcome"]["terminal"]) for trace in traces)
                if not verified or completed != episodes:
                    error = "Incomplete or invalid run: " + canonical({"episodes_completed": completed, "verification": verification})
            except Exception as exc:
                error = _error_text(exc)
                traces = _recover_traces(path, runtime)
            finally:
                if runtime is not None:
                    runtime.close()
            rows.append(_measure(seed, condition, traces, episodes, condition_config, error, verified, str(path.relative_to(out))))
            _write_csv(out / "metrics.csv", rows, METRIC_FIELDS)
    comparisons = _paired_comparisons(rows, seeds, bootstrap_samples)
    causal = _causal_branches(out, seeds, config, rows)
    failures = [row for row in rows if row["status"] != "ok"]
    causal_failures = [row for row in causal if row["status"] != "ok"]
    summary = {
        "experiment": "E1", "status": "completed" if not failures and not causal_failures else "incomplete",
        "runs_planned": len(seeds) * len(CONDITIONS), "runs_completed": len(rows) - len(failures),
        "failed_runs": [{key: row[key] for key in ("seed", "condition", "error")} for row in failures],
        "branches_planned": len(seeds) * len(READER_CONDITIONS), "branches_completed": len(causal) - len(causal_failures),
        "failed_branches": [{key: row[key] for key in ("seed", "condition", "error")} for row in causal_failures],
        "episodes_planned": len(rows) * episodes, "episodes_completed": sum(row["episodes_completed"] for row in rows),
        "experiment_dir": str(out), "report_path": str(out / "report.md"),
        "comparisons_path": str(out / "comparisons.csv"), "causal_path": str(out / "causal_contrasts.csv"),
    }
    _write_csv(out / "comparisons.csv", comparisons, COMPARISON_FIELDS)
    _write_csv(out / "causal_contrasts.csv", causal, CAUSAL_FIELDS)
    _write_json(out / "summary.json", summary)
    manifest["status"] = summary["status"]
    _write_json(out / "manifest.json", manifest)
    write_report(out)
    return summary


def _number(value, digits: int = 4) -> str:
    return "—" if value is None or value == "" else f"{float(value):.{digits}f}"


def write_report(experiment_dir: Path, out_file: Path | None = None) -> Path:
    """Regenerate a report using exported data; never rerun or modify the agent."""
    experiment_dir = Path(experiment_dir).resolve()
    default_path = (experiment_dir / "report.md").resolve()
    path = Path(out_file).resolve() if out_file is not None else default_path
    if path.suffix.lower() != ".md":
        raise LabError("INVALID_INPUT", "Report output must have a .md extension")
    if path.exists() and path != default_path:
        raise LabError("OUTPUT_EXISTS", f"Refusing to overwrite an existing custom report path: {path}")
    manifest = json.loads((experiment_dir / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("experiment") == "L1":
        from .learning_experiment import write_learning_report
        return write_learning_report(experiment_dir, out_file)
    summary = json.loads((experiment_dir / "summary.json").read_text(encoding="utf-8"))
    rows = _read_csv(experiment_dir / "metrics.csv")
    comparisons = _read_csv(experiment_dir / "comparisons.csv")
    lines = [f"# PROJECT CONSCIOUSNESS — {manifest['experiment']}", "",
             f"Protocolo `{manifest['protocol_version']}` · Estado: **{summary['status']}**.", "",
             "Este informe evalúa propiedades funcionales en una tarea diseñada por ingeniería. "
             "La asociación entre pista y acción está programada; no demuestra aprendizaje de esa asociación ni conciencia.", "",
             f"Código: `{manifest['source_fingerprint']}`. Python {manifest['python']}; SQLite {manifest['sqlite']}.", ""]
    if manifest["experiment"] == "E0":
        lines += [f"Se planificaron {summary['ticks_planned']} acciones por ejecución; "
                  f"cierres y reaperturas en ticks {', '.join(map(str, summary['checkpoints']))}.", "",
                  "| Ejecución | Acciones confirmadas / previstas | Verificación | Estado |",
                  "|---|---:|---|---|"]
        for row in rows:
            lines.append(f"| {row['condition']} | {row['ticks_completed']} / {row['ticks_planned']} | {row['verify_valid']} | {row['status']} |")
        lines += ["", f"Trazas completas iguales: **{comparisons[0]['traces_equal']}**. "
                  f"Ticks divergentes: `{comparisons[0]['mismatch_ticks']}`.", "", summary["scope"], ""]
    elif manifest["experiment"] == "E1":
        parameters = manifest["parameters"]
        causal = _read_csv(experiment_dir / "causal_contrasts.csv")
        lines += [f"Semillas: {', '.join(map(str, parameters['seeds']))}. "
                  f"Episodios por semilla y condición: {parameters['episodes']}. "
                  f"Demora: {manifest['config']['delay']}; capacidad: {manifest['config']['capacity']} registros.", "",
                  "Todas las trayectorias cierran y reabren el almacenamiento antes de la primera elección. "
                  "Comparten presupuesto de acciones y límite de registros. El control reactivo carece deliberadamente de historia; "
                  "los costes reales pueden diferir. El límite se expresa en registros, no en bytes; se mide el consumo en bytes.", "",
                  f"Trayectorias completas: **{summary['runs_completed']} / {summary['runs_planned']}**; "
                  f"episodios completados: **{summary['episodes_completed']} / {summary['episodes_planned']}**.", "",
                  "| Condición | Corridas válidas / previstas | Éxitos verificados / episodios previstos | Brier de episodios verificados | Registros examinados, corridas válidas | Memoria pico válida (bytes) |",
                  "|---|---:|---:|---:|---:|---:|"]
        for condition in CONDITIONS:
            selected = [row for row in rows if row["condition"] == condition]
            valid_rows = [row for row in selected if row["status"] == "ok" and row["verify_valid"] == "True"]
            successes = sum(int(row["successes"]) for row in valid_rows)
            planned = sum(int(row["episodes_planned"]) for row in selected)
            observed = sum(int(row["episodes_completed"]) for row in valid_rows)
            weighted_brier = sum(float(row["brier_mean"]) * int(row["episodes_completed"]) for row in valid_rows if row["brier_mean"] != "")
            brier = weighted_brier / observed if observed else None
            scanned = sum(int(row["records_scanned_total"]) for row in valid_rows)
            peak = max((int(row["memory_bytes_peak"]) for row in valid_rows), default=0)
            valid = len(valid_rows)
            lines.append(f"| {condition} | {valid} / {len(selected)} | {successes} / {planned} | {_number(brier)} | {scanned} | {peak} |")
        lines += ["", "Brier binario usa un componente: media de `(probability_left − etiqueta_left)²`, registrada antes del resultado. "
                  "La tabla agrega éxitos, Brier y costes exclusivamente de corridas con estado ok y verificación válida. "
                  "Los éxitos conservan el denominador planificado de todas las corridas; este cociente es un recuento conservador, "
                  "no una estimación de rendimiento cuando hay fallos. Los episodios ausentes no se imputan para Brier. "
                  "Las corridas fallidas o no verificadas no constituyen evidencia funcional: sus datos brutos parciales se conservan en metrics.csv.", "",
                  "## Diferencias pareadas en éxito", "",
                  "Diferencia = condición − intacta. Bootstrap percentil por semilla; IC descriptivo del 95%. "
                  "Las semillas son unidades de remuestreo, no los episodios. El RNG estadístico es independiente y fijo. "
                  "Con una sola semilla no se calcula intervalo. Los pares incompletos se identifican explícitamente y su exclusión limita la interpretación.", "",
                  "| Condición | Pares completos / previstos | Diferencia | IC 95% | Estado |",
                  "|---|---:|---:|---|---|"]
        for row in comparisons:
            if row["metric"] == "success_rate":
                lines.append(f"| {row['condition']} | {row['complete_pairs']} / {row['planned_pairs']} | "
                             f"{_number(row['difference_condition_minus_baseline'])} | [{_number(row['ci95_low'])}, {_number(row['ci95_high'])}] | {row['status']} |")
        lines += ["", "## Intervenciones desde el mismo snapshot", "",
                  "Cada semilla aporta una situación anterior a su primera elección. Las ramas mantienen mundo, memoria y RNG; "
                  "solo cambia el acceso de lectura. Se comprueba igualdad de estado previo y observación. "
                  "La variación total entre políticas binarias es `abs(p_left_rama − p_left_intacta)`.", "",
                  "| Lectura | Ramas válidas / previstas | TV media | Acciones distintas / ramas válidas |",
                  "|---|---:|---:|---:|"]
        for condition in READER_CONDITIONS:
            selected = [row for row in causal if row["condition"] == condition]
            valid = [row for row in selected if row["status"] == "ok" and row["verify_valid"] == "True"]
            distance = mean(float(row["total_variation"]) for row in valid) if valid else None
            changed = sum(row["action_changed"] == "True" for row in valid)
            lines.append(f"| {condition} | {len(valid)} / {len(selected)} | {_number(distance)} | {changed} / {len(valid)} |")
        lines += ["", "El escritor bloqueado se evalúa desde el comienzo de trayectorias completas. "
                  "Desactivarlo después de codificar la pista no borraría un recuerdo existente.", "",
                  "Se espera paridad entre memoria episódica e historial plano en esta tarea. Una igualdad de rendimiento "
                  "no establece equivalencia general; diferencias de coste deben revisarse por separado. "
                  "Un efecto de las máscaras demuestra una dependencia implementada del lector, no memoria autobiográfica humana, "
                  "utilidad general ni experiencia subjetiva. Esta tarea no evalúa aprendizaje continuo, self-model ni afecto.", "",
                  "Los intervalos son descriptivos de este piloto, sin cálculo de potencia ni corrección por múltiples comparaciones. "
                  "Un resultado nulo sigue siendo un resultado válido; se requieren otras familias de tareas y reglas aprendidas para estudiar generalización.", ""]
        failures = [row for row in causal if row["status"] != "ok" or row["verify_valid"] != "True"]
        if failures:
            lines += ["### Ramas fallidas", ""]
            lines.extend(f"- Semilla {row['seed']}, {row['condition']}: {row['error']}" for row in failures)
            lines.append("")
    else:
        raise LabError("INVALID_INPUT", "Unsupported experiment report")
    failures = [row for row in rows if row["status"] != "ok" or row["verify_valid"] != "True"]
    if failures:
        lines += ["## Ejecuciones fallidas", ""]
        lines.extend(f"- {row.get('seed', '')} {row['condition']}: {row['error']}" for row in failures)
        lines.append("")
    lines += ["## Datos auditables", "",
              "`manifest.json` conserva protocolo, configuración y versiones. `metrics.csv` conserva denominadores, costes y fallos. "
              "`comparisons.csv` conserva contrastes. `summary.json` conserva estado y recuentos. "
              "Las bases SQLite de `runs/` conservan las trazas completas y snapshots. "
              "En E1, `causal_contrasts.csv` y `branches/` conservan las intervenciones locales. "
              "Este informe puede regenerarse a partir de las exportaciones sin ejecutar el agente.", ""]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
    return path
