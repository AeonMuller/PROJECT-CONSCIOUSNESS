"""L1: paired acquisition, reversal, frozen learning and persistence controls."""

from dataclasses import replace
import json
from pathlib import Path
import random
from statistics import mean

from .contracts import Config, LabError, TaskConfig, canonical, digest
from .experiments import (
    STATISTICAL_SEED, _error_text, _number, _positive_integer, _prepare,
    _quantile, _read_csv, _recover_traces, _write_csv, _write_json,
)
from .runtime import Runtime


PROTOCOL_VERSION = "mvp-0.2-l1-1"
CONDITIONS = ("training", "adaptive", "frozen", "sham", "resumed", "untrained_frozen")
BRANCHES = CONDITIONS[1:5]
METRIC_FIELDS = (
    "seed", "condition", "phase", "status", "error", "verify_valid",
    "episodes_planned", "episodes_completed", "successes", "success_rate", "brier_mean",
    "last10_episodes", "last10_success_rate", "last10_brier_mean", "recovery_episode",
    "recovery_censored", "actions_budget", "actions_consumed", "model_updates",
    "records_scanned_total", "memory_bytes_peak", "model_bytes_peak", "agent_bytes_peak", "run_path",
)
EPISODE_FIELDS = (
    "seed", "condition", "phase", "episode", "phase_episode", "tick", "status", "verify_valid",
    "action", "success", "probability_left", "predicted_target_left", "target_left", "brier",
    "predicted_success", "model_version", "post_model_version", "model_hash", "post_model_hash",
)
CURVE_FIELDS = ("seed", "condition", "phase", "block", "episode_start", "episode_end",
                "episodes_planned", "episodes_completed", "status", "verify_valid", "success_rate", "brier_mean")
CHECK_FIELDS = ("seed", "check", "conditions", "status", "error")
COMPARISON_FIELDS = (
    "contrast", "phase", "baseline", "condition", "metric", "status", "planned_pairs",
    "complete_pairs", "excluded_seeds", "difference_condition_minus_baseline", "ci95_low", "ci95_high",
    "bootstrap_samples", "statistical_seed",
)


def _execute(path, factory, ticks, checkpoints=(), reference=None):
    """Keep all committed data even if the execution or a real reopen fails."""
    runtime = None
    result = {"path": path, "traces": [], "initial": None, "final": None,
              "error": "", "verified": False, "status": "failed"}
    try:
        runtime = factory()
        result["initial"] = runtime.snapshot()
        if reference is not None and any(result["initial"][key] != reference[key]
                                         for key in ("tick", "agent", "environment", "rng")):
            raise LabError("BRANCH_MISMATCH", "branch state differs before intervention")
        previous = 0
        for checkpoint in sorted(set(checkpoints)):
            runtime.run(checkpoint - previous)
            runtime.close()
            runtime = None
            runtime = Runtime.open(path)
            previous = checkpoint
        runtime.run(ticks - previous)
        # Include a genuine restart in the training-to-branch and verification path.
        runtime.close()
        runtime = None
        runtime = Runtime.open(path)
        result["traces"] = runtime.traces()
        result["final"] = runtime.snapshot()
        verification = runtime.verify(mode="recompute")
        result["verified"] = verification["valid"]
        if not verification["valid"] or len(result["traces"]) != ticks:
            raise LabError("INVALID_RUN", canonical({"ticks": len(result["traces"]), "verification": verification}))
        result["status"] = "ok"
    except Exception as error:
        result["error"] = _error_text(error)
        result["traces"] = _recover_traces(path, runtime)
    finally:
        if runtime is not None:
            runtime.close()
    return result


def _missing(path, error):
    return {"path": path, "traces": [], "initial": None, "final": None,
            "error": error, "verified": False, "status": "failed"}


def _check(seed, name, conditions, good, results, checks):
    error = "" if good else f"L1 invariant failed: {name}"
    checks.append({"seed": seed, "check": name, "conditions": canonical(list(conditions)),
                   "status": "ok" if good else "failed", "error": error})
    if not good:
        for condition in conditions:
            result = results[condition]
            result["status"] = "failed"
            result["error"] = "; ".join(filter(None, (result["error"], error)))


def _invariants(seed, results, checks):
    training, adaptive = results["training"], results["adaptive"]
    reference = training["final"]
    for condition in BRANCHES:
        current = results[condition]
        same = reference is not None and current["initial"] is not None and all(
            reference[key] == current["initial"][key] for key in ("tick", "agent", "environment", "rng"))
        if same:
            expected_config = {**reference["config"], "learning_enabled": condition != "frozen"}
            same = current["initial"]["config"] == expected_config
        _check(seed, f"initial_state_{condition}", (condition,), same, results, checks)
        first = next((t["decision"] for t in current["traces"] if t["outcome"]["terminal"]), None)
        baseline = next((t["decision"] for t in adaptive["traces"] if t["outcome"]["terminal"]), None)
        _check(seed, f"first_decision_{condition}", (condition,), first is not None and first == baseline,
               results, checks)
        observations = [t["observation"] for t in current["traces"]]
        expected = [t["observation"] for t in adaptive["traces"]]
        _check(seed, f"observations_{condition}", (condition,), bool(observations) and observations == expected,
               results, checks)
    for condition in ("sham", "resumed"):
        _check(seed, f"complete_traces_{condition}", ("adaptive", condition),
               bool(adaptive["traces"]) and adaptive["traces"] == results[condition]["traces"], results, checks)
    for condition in ("frozen", "untrained_frozen"):
        current = results[condition]
        before, after = current["initial"], current["final"]
        stable = (before is not None and after is not None
                  and before["agent"]["learner"] == after["agent"]["learner"]
                  and all(t["post_model_hash"] == digest(before["agent"]["learner"]) for t in current["traces"]))
        _check(seed, f"whole_learner_frozen_{condition}", (condition,), stable, results, checks)
    observed = [t["observation"] for t in results["untrained_frozen"]["traces"]]
    expected = [t["observation"] for t in training["traces"] + adaptive["traces"]]
    _check(seed, "exogenous_observation_sequence", ("training", "adaptive", "untrained_frozen"),
           bool(observed) and observed == expected, results, checks)


def _phase_rows(seed, condition, result, acquisition, adaptation, config, out):
    phases = [("acquisition", 0, acquisition)] if condition == "training" else [("adaptation", acquisition, adaptation)]
    if condition == "untrained_frozen":
        phases = [("acquisition", 0, acquisition), ("adaptation", acquisition, adaptation)]
    metrics, episodes, curves = [], [], []
    for phase, start, planned in phases:
        traces = [t for t in result["traces"] if start <= t["observation"]["episode"] < start + planned]
        completed = [t for t in traces if t["outcome"]["terminal"]]
        phase_episodes = []
        for trace in completed:
            decision, outcome = trace["decision"], trace["outcome"]
            target_left = int((decision["action"] == "left") == outcome["success"])
            phase_episodes.append({
                "seed": seed, "condition": condition, "phase": phase,
                "episode": trace["observation"]["episode"],
                "phase_episode": trace["observation"]["episode"] - start + 1,
                "tick": trace["tick"], "status": result["status"], "verify_valid": result["verified"],
                "action": decision["action"], "success": int(outcome["success"]),
                "probability_left": decision["probability_left"],
                "predicted_target_left": decision["predicted_target_left"], "target_left": target_left,
                "brier": (decision["predicted_target_left"] - target_left) ** 2,
                "predicted_success": decision["predicted_success"], "model_version": decision["model_version"],
                "post_model_version": trace["post_model_version"], "model_hash": decision["model_hash"],
                "post_model_hash": trace["post_model_hash"],
            })
        episodes.extend(phase_episodes)
        successes = sum(e["success"] for e in phase_episodes)
        # "Last ten" always means the planned horizon; incomplete early tails do not qualify.
        tail = [e for e in phase_episodes if e["phase_episode"] > max(0, planned - 10)]
        recovery = next((phase_episodes[i]["phase_episode"] for i in range(9, len(phase_episodes))
                         if sum(e["success"] for e in phase_episodes[i - 9:i + 1]) >= 8), None)
        metrics.append({
            "seed": seed, "condition": condition, "phase": phase,
            "status": result["status"], "error": result["error"], "verify_valid": result["verified"],
            "episodes_planned": planned, "episodes_completed": len(completed), "successes": successes,
            "success_rate": successes / len(completed) if completed else None,
            "brier_mean": mean(e["brier"] for e in phase_episodes) if phase_episodes else None,
            "last10_episodes": len(tail), "last10_success_rate": mean(e["success"] for e in tail) if tail else None,
            "last10_brier_mean": mean(e["brier"] for e in tail) if tail else None,
            "recovery_episode": recovery if phase == "adaptation" else None,
            "recovery_censored": recovery is None if phase == "adaptation" else None,
            "actions_budget": planned * (config.delay + 2), "actions_consumed": len(traces),
            "model_updates": sum(t["post_model_version"] - t["decision"]["model_version"] for t in traces),
            "records_scanned_total": sum(t["decision"]["records_scanned"] for t in traces),
            "memory_bytes_peak": max((max(t["post_memory_bytes"], t["decision"]["memory_bytes"]) for t in traces), default=0),
            "model_bytes_peak": max((t["post_model_bytes"] for t in traces), default=0),
            "agent_bytes_peak": max((t["post_agent_bytes"] for t in traces), default=0),
            "run_path": str(result["path"].relative_to(out)),
        })
        for block_start in range(1, planned + 1, 10):
            block_end = min(block_start + 9, planned)
            block = [e for e in phase_episodes if block_start <= e["phase_episode"] <= block_end]
            curves.append({
                "seed": seed, "condition": condition, "phase": phase, "block": (block_start - 1) // 10 + 1,
                "episode_start": block_start, "episode_end": block_end, "episodes_planned": block_end - block_start + 1,
                "episodes_completed": len(block), "status": result["status"], "verify_valid": result["verified"],
                "success_rate": mean(e["success"] for e in block) if block else None,
                "brier_mean": mean(e["brier"] for e in block) if block else None,
            })
    return metrics, episodes, curves


def _comparisons(rows, seeds, samples):
    indexed = {(r["seed"], r["condition"], r["phase"]): r for r in rows}
    contrasts = (("primary_adaptation", "adaptation", "frozen", "adaptive"),
                 ("acquisition_learning", "acquisition", "untrained_frozen", "training"),
                 ("sham_control", "adaptation", "adaptive", "sham"),
                 ("restart_control", "adaptation", "adaptive", "resumed"))
    output = []
    for name, phase, baseline, condition in contrasts:
        for metric in ("success_rate", "brier_mean", "last10_success_rate", "last10_brier_mean", "model_updates", "agent_bytes_peak", "actions_consumed"):
            differences, excluded = [], []
            for seed in seeds:
                left, right = indexed[(seed, baseline, phase)], indexed[(seed, condition, phase)]
                valid = all(r["status"] == "ok" and r["verify_valid"] is True
                            and r["episodes_completed"] == r["episodes_planned"] and r[metric] is not None
                            for r in (left, right))
                if valid:
                    differences.append(right[metric] - left[metric])
                else:
                    excluded.append(seed)
            rng = random.Random(int(digest({"statistical_seed": STATISTICAL_SEED, "contrast": name, "metric": metric}), 16))
            bootstrap = sorted(mean(rng.choices(differences, k=len(differences))) for _ in range(samples)) if len(differences) >= 2 else []
            output.append({
                "contrast": name, "phase": phase, "baseline": baseline, "condition": condition, "metric": metric,
                "status": "incomplete" if excluded else ("descriptive_single_seed" if len(differences) < 2 else "ok"),
                "planned_pairs": len(seeds), "complete_pairs": len(differences), "excluded_seeds": canonical(excluded),
                "difference_condition_minus_baseline": mean(differences) if differences else None,
                "ci95_low": _quantile(bootstrap, .025) if bootstrap else None,
                "ci95_high": _quantile(bootstrap, .975) if bootstrap else None,
                "bootstrap_samples": samples if bootstrap else 0, "statistical_seed": STATISTICAL_SEED,
            })
    return output


def run_l1(out: Path, seeds: list[int] | None = None, acquisition_episodes: int = 40,
           adaptation_episodes: int = 40, bootstrap_samples: int = 2000,
           config: Config | None = None, task: TaskConfig | None = None) -> dict:
    """Execute the preregistered L1 engineering pilot without performance selection."""
    if seeds is not None and not isinstance(seeds, (list, tuple, range)):
        raise LabError("INVALID_INPUT", "seeds must be a sequence of integers")
    seeds = list(range(200, 220)) if seeds is None else list(seeds)
    if not seeds or any(type(seed) is not int or not 0 <= seed < 2**63 for seed in seeds) or len(set(seeds)) != len(seeds):
        raise LabError("INVALID_INPUT", "seeds must be nonempty, distinct integers in [0, 2**63)")
    _positive_integer(acquisition_episodes, "acquisition_episodes")
    _positive_integer(adaptation_episodes, "adaptation_episodes")
    _positive_integer(bootstrap_samples, "bootstrap_samples")
    config = Config(policy_mode="learned") if config is None else config
    task = TaskConfig(kind="reversal-v1", reversal_episode=acquisition_episodes) if task is None else task
    if not isinstance(config, Config) or (config.policy_mode, config.learning_enabled, config.agent_mode,
                                         config.read_mode, config.write_enabled) != ("learned", True, "episodic", "intact", True):
        raise LabError("INVALID_INPUT", "L1 requires learned, enabled, episodic, intact read/write policy")
    if not isinstance(task, TaskConfig) or task.kind != "reversal-v1" or task.reversal_episode != acquisition_episodes:
        raise LabError("INVALID_INPUT", "L1 requires reversal-v1 at the acquisition boundary")
    step_size = config.delay + 2
    adaptation_ticks = adaptation_episodes * step_size
    checkpoints = sorted({v for v in (config.delay + 1, adaptation_ticks // 2) if 0 < v < adaptation_ticks})
    out, manifest = _prepare(
        Path(out), "L1", config, seeds=seeds, acquisition_episodes=acquisition_episodes,
        adaptation_episodes=adaptation_episodes, task=task.to_dict(), conditions=list(CONDITIONS),
        bootstrap_samples=bootstrap_samples, statistical_seed=STATISTICAL_SEED,
        resumed_checkpoints_relative=checkpoints, curve_block_episodes=10,
        recovery="First ending episode of a moving ten-episode postchange window with at least eight successes; otherwise censored",
        estimand="Primary: adaptive minus trained frozen postchange success rate, paired by seed",
        brier_definition="One-component mean (predicted_target_left - observed target-left label)^2, prediction locked before feedback",
        inferential_limit="Descriptive pilot; learned association within a programmed binary task and learning rule, no generalization or consciousness inference",
    )
    manifest["protocol_version"] = PROTOCOL_VERSION
    manifest["interpretation"] = "Hipótesis de ingeniería; asociación aprendida dentro de una tarea y algoritmo programados. No mide conciencia."
    _write_json(out / "manifest.json", manifest)
    metrics, episodes, curves, checks, run_records = [], [], [], [], []
    for seed in seeds:
        paths = {c: out / "runs" / c / f"seed-{seed}" for c in CONDITIONS}
        results = {"training": _execute(paths["training"], lambda: Runtime.create(paths["training"], seed, config, task), acquisition_episodes * step_size)}
        reference = results["training"]["final"]
        for condition in BRANCHES:
            overrides = {"learning_enabled": False} if condition == "frozen" else ({"learning_enabled": True} if condition == "sham" else {})

            def factory(path=paths[condition], intervention=overrides):
                with Runtime.open(paths["training"]) as parent:
                    return parent.fork(path, overrides=intervention)

            results[condition] = (_execute(paths[condition], factory, adaptation_ticks,
                                           checkpoints if condition == "resumed" else (), reference)
                                  if results["training"]["status"] == "ok"
                                  else _missing(paths[condition], "PARENT_FAILED: training did not complete and verify"))
        results["untrained_frozen"] = _execute(
            paths["untrained_frozen"],
            lambda: Runtime.create(paths["untrained_frozen"], seed, replace(config, learning_enabled=False), task),
            (acquisition_episodes + adaptation_episodes) * step_size,
        )
        _invariants(seed, results, checks)
        for condition in CONDITIONS:
            current = results[condition]
            phase_metrics, raw_episodes, phase_curves = _phase_rows(
                seed, condition, current, acquisition_episodes, adaptation_episodes, config, out)
            metrics.extend(phase_metrics)
            episodes.extend(raw_episodes)
            curves.extend(phase_curves)
            run_records.append({"seed": seed, "condition": condition, "status": current["status"],
                                "verify_valid": current["verified"], "error": current["error"]})
        _write_csv(out / "metrics.csv", metrics, METRIC_FIELDS)
        _write_csv(out / "episodes.csv", episodes, EPISODE_FIELDS)
        _write_csv(out / "curves.csv", curves, CURVE_FIELDS)
        _write_csv(out / "checks.csv", checks, CHECK_FIELDS)
    comparisons = _comparisons(metrics, seeds, bootstrap_samples)
    failures = [r for r in run_records if r["status"] != "ok" or not r["verify_valid"]]
    summary = {
        "experiment": "L1", "status": "incomplete" if failures else "completed", "valid": not failures,
        "runs_planned": len(seeds) * len(CONDITIONS), "runs_completed": len(run_records) - len(failures),
        "failed_runs": failures, "checks_planned": len(checks), "checks_passed": sum(c["status"] == "ok" for c in checks),
        "episodes_planned": len(seeds) * (2 * acquisition_episodes + 5 * adaptation_episodes),
        "episodes_completed": len(episodes), "episodes_valid": sum(e["status"] == "ok" and e["verify_valid"] for e in episodes),
        "experiment_dir": str(out), "report_path": str(out / "report.md"),
    }
    _write_csv(out / "comparisons.csv", comparisons, COMPARISON_FIELDS)
    _write_json(out / "summary.json", summary)
    manifest["status"] = summary["status"]
    _write_json(out / "manifest.json", manifest)
    write_learning_report(out)
    return summary


def _valid(row):
    return (row["status"] == "ok" and row["verify_valid"] == "True"
            and row["episodes_completed"] == row["episodes_planned"])


def write_learning_report(experiment_dir: Path, out_file: Path | None = None) -> Path:
    """Regenerate from exported data without executing a policy or modifying evidence."""
    experiment_dir = Path(experiment_dir).resolve()
    default_path = (experiment_dir / "report.md").resolve()
    path = Path(out_file).resolve() if out_file is not None else default_path
    if path.suffix.lower() != ".md":
        raise LabError("INVALID_INPUT", "Report output must have a .md extension")
    if path.exists() and path != default_path:
        raise LabError("OUTPUT_EXISTS", f"Refusing to overwrite existing custom report: {path}")
    manifest = json.loads((experiment_dir / "manifest.json").read_text(encoding="utf-8"))
    summary = json.loads((experiment_dir / "summary.json").read_text(encoding="utf-8"))
    if manifest["experiment"] != "L1" or summary["experiment"] != "L1":
        raise LabError("INVALID_INPUT", "Not an L1 experiment")
    rows = _read_csv(experiment_dir / "metrics.csv")
    comparisons = _read_csv(experiment_dir / "comparisons.csv")
    curves = _read_csv(experiment_dir / "curves.csv")
    checks = _read_csv(experiment_dir / "checks.csv")
    parameters = manifest["parameters"]
    lines = ["# PROJECT CONSCIOUSNESS — L1", "",
             f"Protocolo `{manifest['protocol_version']}` · Estado del software: **{summary['status']}**.", "",
             "Este piloto evalúa aprendizaje de una asociación y adaptación después de una inversión privada. "
             "La tarea binaria, la regla de actualización y la política de elección están programadas. No mide conciencia.", "",
             f"Código: `{manifest['source_fingerprint']}`. Python {manifest['python']}; SQLite {manifest['sqlite']}.", "",
             f"Semillas: {', '.join(map(str, parameters['seeds']))}. Adquisición: {parameters['acquisition_episodes']} episodios; "
             f"seguimiento: {parameters['adaptation_episodes']}. Alpha: {manifest['config']['learning_rate']}; demora: {manifest['config']['delay']}.", "",
             f"Bases completas y verificadas: **{summary['runs_completed']} / {summary['runs_planned']}**. "
             f"Episodios registrados: **{summary['episodes_completed']} / {summary['episodes_planned']}**; "
             f"episodios de bases válidas: **{summary['episodes_valid']}**. "
             f"Comprobaciones: **{summary['checks_passed']} / {summary['checks_planned']}**.", "",
             "Training aprende desde un prior neutral. Adaptive, frozen, sham y resumed parten del mismo snapshot entrenado; "
             "frozen desactiva solo la actualización. Untrained_frozen conserva el prior neutral desde el inicio. "
             "Resumed cierra y reabre antes de su primera elección y a mitad del seguimiento. "
             "Sham y resumed deben reproducir todas las trazas de adaptive.", "",
             "| Condición | Fase | Bases válidas / previstas | Episodios válidos / previstos | Aciertos válidos | Brier del modelo | Últimos 10, aciertos | Actualizaciones válidas |",
             "|---|---|---:|---:|---:|---:|---:|---:|"]
    for condition in CONDITIONS:
        for phase in ("acquisition", "adaptation"):
            selected = [r for r in rows if r["condition"] == condition and r["phase"] == phase]
            if not selected:
                continue
            valid = [r for r in selected if _valid(r)]
            observed = sum(int(r["episodes_completed"]) for r in valid)
            planned = sum(int(r["episodes_planned"]) for r in selected)
            success = sum(int(r["successes"]) for r in valid) / observed if observed else None
            brier = sum(float(r["brier_mean"]) * int(r["episodes_completed"]) for r in valid) / observed if observed else None
            tail = mean(float(r["last10_success_rate"]) for r in valid) if valid else None
            updates = sum(int(r["model_updates"]) for r in valid)
            lines.append(f"| {condition} | {phase} | {len(valid)} / {len(selected)} | {observed} / {planned} | {_number(success)} | {_number(brier)} | {_number(tail)} | {updates} |")
    lines += ["", "Los estimandos usan únicamente bases completas, con estado ok y recomputación válida. "
              "Fallos y datos parciales permanecen en los CSV, pero no constituyen evidencia funcional. "
              "Los denominadores previstos permanecen visibles; no se imputan episodios ausentes. "
              "Brier usa `(predicted_target_left − etiqueta_left)²`, registrado antes del feedback; "
              "probability_left describe selección de acciones y no se usa como predicción del modelo.", "",
              "## Contrastes pareados", "",
              "El primario es adaptive − frozen en aciertos postcambio. Bootstrap percentil descriptivo al 95%, "
              "remuestreando semillas emparejadas; RNG estadístico independiente. Una sola semilla no produce intervalo. "
              "Sin cálculo de potencia ni corrección por múltiples contrastes.", "",
              "| Contraste | Métrica | Pares completos / previstos | Diferencia | IC 95% | Estado |",
              "|---|---|---:|---:|---|---|"]
    for row in comparisons:
        if row["metric"] in ("success_rate", "brier_mean"):
            lines.append(f"| {row['contrast']} | {row['metric']} | {row['complete_pairs']} / {row['planned_pairs']} | "
                         f"{_number(row['difference_condition_minus_baseline'])} | [{_number(row['ci95_low'])}, {_number(row['ci95_high'])}] | {row['status']} |")
    lines += ["", "## Evolución por bloques", "",
              "Bloques consecutivos de hasta diez episodios dentro de cada fase; media entre semillas válidas.", "",
              "| Condición | Fase | Episodios de fase | Semillas válidas / previstas | Aciertos | Brier |",
              "|---|---|---|---:|---:|---:|"]
    for condition in ("training", "adaptive", "frozen", "untrained_frozen"):
        for phase in ("acquisition", "adaptation"):
            keys = sorted({int(r["block"]) for r in curves if r["condition"] == condition and r["phase"] == phase})
            for block in keys:
                selected = [r for r in curves if (r["condition"], r["phase"], int(r["block"])) == (condition, phase, block)]
                valid = [r for r in selected if _valid(r)]
                success = mean(float(r["success_rate"]) for r in valid) if valid else None
                brier = mean(float(r["brier_mean"]) for r in valid) if valid else None
                lines.append(f"| {condition} | {phase} | {selected[0]['episode_start']}–{selected[0]['episode_end']} | "
                             f"{len(valid)} / {len(selected)} | {_number(success)} | {_number(brier)} |")
    lines += ["", "## Recuperación y coste", "",
              "Recuperación = primer final de una ventana móvil de diez episodios postcambio con al menos ocho aciertos. "
              "No alcanzar esa ventana queda censurado al horizonte y no implica estabilidad posterior. "
              "No se detiene anticipadamente ninguna ejecución.", "",
              "| Condición | Recuperadas / válidas | Episodios de recuperación, solo recuperadas | Censuradas | Pico agente (bytes) | Acciones válidas |",
              "|---|---:|---|---:|---:|---:|"]
    for condition in CONDITIONS[1:]:
        valid = [r for r in rows if r["condition"] == condition and r["phase"] == "adaptation" and _valid(r)]
        recoveries = [int(r["recovery_episode"]) for r in valid if r["recovery_episode"] != ""]
        lines.append(f"| {condition} | {len(recoveries)} / {len(valid)} | {', '.join(map(str, recoveries)) or '—'} | "
                     f"{len(valid) - len(recoveries)} | {max((int(r['agent_bytes_peak']) for r in valid), default=0)} | "
                     f"{sum(int(r['actions_consumed']) for r in valid)} |")
    failures = [r for r in rows if not _valid(r)]
    if failures:
        lines += ["", "## Ejecuciones excluidas", ""]
        lines.extend(f"- Semilla {r['seed']}, {r['condition']}, {r['phase']}: {r['error'] or 'Verificación o completitud inválida'}." for r in failures)
    failed_checks = [r for r in checks if r["status"] != "ok"]
    if failed_checks:
        lines += ["", "## Comprobaciones fallidas", ""]
        lines.extend(f"- Semilla {r['seed']}: {r['check']}." for r in failed_checks)
    lines += ["", "## Alcance y datos", "",
              "Una diferencia favorable demuestra adaptación implementada a esta inversión; no establece transferencia entre tareas, "
              "retención de reglas antiguas, aprendizaje abierto, metacognición, self-model ni experiencia subjetiva. "
              "La misma estructura y semillas compartidas hacen que los controles no sean réplicas independientes. "
              "El estado completed certifica ejecución e invariantes, no exige un resultado científico positivo.", "",
              "`manifest.json` fija configuración, protocolo, semillas y código. `episodes.csv` conserva resultados y predicciones previas "
              "al feedback; `metrics.csv`, costes, denominadores y errores; `curves.csv`, bloques; `comparisons.csv`, contrastes y exclusiones; "
              "`checks.csv`, invariantes; `summary.json`, recuentos. Las bases de `runs/` conservan snapshots y trazas recomputables. "
              "El informe se regenera a partir de estas exportaciones sin ejecutar el agente.", ""]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
    return path
