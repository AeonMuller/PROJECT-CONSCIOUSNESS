"""E2: paired interventions on a persistent predictor of execution capability."""

from dataclasses import replace
import json
from pathlib import Path
import random
from statistics import mean

from .capability import model_estimates
from .contracts import Config, LabError, TaskConfig, canonical, digest, seeded_rng
from .experiments import _error_text, _number, _positive_integer, _prepare, _quantile, _read_csv, _write_csv, _write_json
from .learning_experiment import _execute, _missing
from .runtime import Runtime


PROTOCOL_VERSION = "mvp-0.3-e2-1"
STATISTICAL_SEED = 20261005
CONDITIONS = ("training", "updated", "frozen", "reader_blocked", "sham", "resumed", "generic")
BRANCHES = CONDITIONS[1:6]
METRIC_FIELDS = (
    "seed", "condition", "phase", "status", "error", "verify_valid", "episodes_planned", "episodes_completed",
    "successes", "success_rate", "utility_mean", "cost_mean", "decision_errors", "decision_error_rate",
    "execution_errors", "execution_error_rate", "safe_rate", "execution_brier_mean", "probe_brier_mean",
    "probe_trials_planned", "probe_trials_completed", "actions_budget", "actions_consumed", "model_updates",
    "records_scanned_total", "memory_bytes_peak", "model_bytes_peak", "agent_bytes_peak", "run_path",
)
EPISODE_FIELDS = (
    "seed", "condition", "phase", "episode", "phase_episode", "tick", "status", "verify_valid", "action",
    "intended_action", "tool", "success", "decision_correct", "execution_success", "cost", "utility",
    "probability_left", "probability_fast", "predicted_execution_success", "predicted_success", "execution_brier",
    "visible_fast", "visible_safe", "model_version", "post_model_version", "model_hash", "post_model_hash",
)
CURVE_FIELDS = (
    "seed", "condition", "phase", "block", "episode_start", "episode_end", "episodes_planned", "episodes_completed",
    "status", "verify_valid", "success_rate", "utility_mean", "cost_mean", "safe_rate", "execution_brier_mean",
)
PROBE_FIELDS = (
    "seed", "condition", "phase", "tool", "trial", "status", "verify_valid", "snapshot_hash", "model_hash",
    "model_version", "predicted_execution_success", "evaluation_probability", "execution_success", "brier",
)
PROBE_METRIC_FIELDS = (
    "seed", "condition", "phase", "tool", "status", "error", "verify_valid", "trials_planned", "trials_completed",
    "predicted_execution_success", "observed_success_rate", "brier_mean", "snapshot_hash", "model_hash", "model_version",
)
CALIBRATION_FIELDS = (
    "condition", "phase", "tool", "bin_lower", "bin_upper", "complete_seed_groups", "trials_valid",
    "mean_prediction", "observed_success_rate", "brier_mean",
)
CHECK_FIELDS = ("seed", "check", "conditions", "status", "error")
COMPARISON_FIELDS = (
    "contrast", "phase", "baseline", "condition", "metric", "status", "planned_pairs", "complete_pairs",
    "excluded_seeds", "difference_condition_minus_baseline", "ci95_low", "ci95_high", "bootstrap_samples", "statistical_seed",
)


def _check(seed, name, conditions, good, results, checks):
    error = "" if good else f"E2 invariant failed: {name}"
    checks.append({"seed": seed, "check": name, "conditions": canonical(list(conditions)),
                   "status": "ok" if good else "failed", "error": error})
    if not good:
        for condition in conditions:
            result = results[condition]
            result["status"] = "failed"
            result["error"] = "; ".join(filter(None, (result["error"], error)))


def _functional(traces):
    """Exclude representation and configuration hashes, retaining observable behavior."""
    fields = ("action", "intended_action", "tool", "probability_left", "probability_fast", "confidence",
              "predicted_target_left", "predicted_execution_success", "predicted_success", "capability_view",
              "expected_utilities", "model_version", "memory_ids", "encoded_ids", "records_scanned")
    return [{"tick": t["tick"], "observation": t["observation"], "outcome": t["outcome"],
             "decision": {key: t["decision"][key] for key in fields},
             "post_model_version": t["post_capability_version"]} for t in traces]


def _invariants(seed, results, checks):
    training, updated = results["training"], results["updated"]
    reference = training["final"]
    for condition in BRANCHES:
        current = results[condition]
        same = reference is not None and current["initial"] is not None and all(
            reference[key] == current["initial"][key] for key in ("tick", "agent", "environment", "rng"))
        if same:
            expected_config = {**reference["config"], **_overrides(condition)}
            same = current["initial"]["config"] == expected_config
        _check(seed, f"initial_state_{condition}", (condition,), same, results, checks)
        if condition != "reader_blocked":
            first = next((t["decision"] for t in current["traces"] if t["outcome"]["terminal"]), None)
            baseline = next((t["decision"] for t in updated["traces"] if t["outcome"]["terminal"]), None)
            _check(seed, f"first_decision_{condition}", (condition,), first is not None and first == baseline,
                   results, checks)
        observations = [t["observation"] for t in current["traces"]]
        expected = [t["observation"] for t in updated["traces"]]
        _check(seed, f"observations_{condition}", (condition,), bool(observations) and observations == expected,
               results, checks)
    _check(seed, "sham_functional_identity", ("updated", "sham"), bool(updated["traces"])
           and _functional(updated["traces"]) == _functional(results["sham"]["traces"]), results, checks)
    _check(seed, "resumed_exact_traces", ("updated", "resumed"), bool(updated["traces"])
           and updated["traces"] == results["resumed"]["traces"], results, checks)
    frozen = results["frozen"]
    before, after = frozen["initial"], frozen["final"]
    stable = before is not None and after is not None and before["agent"]["capability"] == after["agent"]["capability"]
    stable = stable and all(t["post_capability_hash"] == digest(before["agent"]["capability"]) for t in frozen["traces"])
    _check(seed, "whole_model_frozen", ("frozen",), stable, results, checks)
    blocked = results["reader_blocked"]
    choices = [t for t in blocked["traces"] if t["outcome"]["terminal"]]
    neutral = bool(choices) and all(t["decision"]["capability_view"] == [.5, .5] for t in choices)
    updating = bool(choices) and all(t["post_capability_version"] == t["decision"]["model_version"] + 1 for t in choices)
    _check(seed, "blocked_view_and_active_writer", ("reader_blocked",), neutral and updating, results, checks)
    combined = training["traces"] + updated["traces"]
    _check(seed, "generic_functional_identity", ("generic",), bool(combined)
           and _functional(combined) == _functional(results["generic"]["traces"]), results, checks)
    for phase, left, right in (("acquisition", training["final"], results["generic"].get("acquisition")),
                               ("adaptation", updated["final"], results["generic"]["final"])):
        good = left is not None and right is not None and (
            model_estimates(left["agent"]["capability"]) == model_estimates(right["agent"]["capability"]))
        _check(seed, f"generic_estimates_{phase}", ("generic",), good, results, checks)


def _overrides(condition):
    return ({"capability_learning_enabled": False} if condition == "frozen" else
            {"capability_read_mode": "blocked"} if condition == "reader_blocked" else
            {"capability_read_mode": "sham"} if condition == "sham" else {})


def _probe(seed, condition, phase, snapshot, trials, task):
    """Fix both forecasts before independent evaluator outcomes; mutate no agent RNG."""
    records, metrics = [], []
    snapshot_hash = digest(snapshot) if snapshot is not None else None
    model = snapshot["agent"]["capability"] if snapshot is not None else None
    # Both predictions are read before creating/drawing the evaluator stream.
    forecasts = tuple(model_estimates(model)) if model is not None else (None, None)
    model_hash = digest(model) if model is not None else None
    model_version = model["updates"] if model is not None else None
    probabilities = (task.fast_success_before if phase == "acquisition" else task.fast_success_after,
                     task.safe_success)
    rng = seeded_rng(seed, f"e2-probe-{phase}")
    for tool, prediction, probability in zip(("fast", "safe"), forecasts, probabilities):
        samples = []
        if prediction is not None:
            for trial in range(trials):
                success = int(rng.random() < probability)
                row = {"seed": seed, "condition": condition, "phase": phase, "tool": tool, "trial": trial,
                       "status": "pending", "verify_valid": False, "snapshot_hash": snapshot_hash,
                       "model_hash": model_hash, "model_version": model_version,
                       "predicted_execution_success": prediction, "evaluation_probability": probability,
                       "execution_success": success, "brier": (prediction - success) ** 2}
                samples.append(row)
                records.append(row)
        metrics.append({"seed": seed, "condition": condition, "phase": phase, "tool": tool,
                        "status": "pending", "error": "", "verify_valid": False, "trials_planned": trials,
                        "trials_completed": len(samples), "predicted_execution_success": prediction,
                        "observed_success_rate": mean(r["execution_success"] for r in samples) if samples else None,
                        "brier_mean": mean(r["brier"] for r in samples) if samples else None,
                        "snapshot_hash": snapshot_hash, "model_hash": model_hash, "model_version": model_version})
    unchanged = snapshot is not None and digest(snapshot) == snapshot_hash
    return records, metrics, unchanged


def _phase_rows(seed, condition, result, acquisition, adaptation, config, out, probe_metrics):
    phases = [("acquisition", 0, acquisition)] if condition == "training" else [("adaptation", acquisition, adaptation)]
    if condition == "generic":
        phases = [("acquisition", 0, acquisition), ("adaptation", acquisition, adaptation)]
    metrics, episodes, curves = [], [], []
    for phase, start, planned in phases:
        traces = [t for t in result["traces"] if start <= t["observation"]["episode"] < start + planned]
        choices = [t for t in traces if t["outcome"]["terminal"]]
        phase_episodes = []
        for trace in choices:
            decision, outcome = trace["decision"], trace["outcome"]
            phase_episodes.append({
                "seed": seed, "condition": condition, "phase": phase, "episode": outcome["episode"],
                "phase_episode": outcome["episode"] - start + 1, "tick": trace["tick"],
                "status": result["status"], "verify_valid": result["verified"], "action": decision["action"],
                "intended_action": decision["intended_action"], "tool": decision["tool"],
                "success": int(outcome["success"]), "decision_correct": int(outcome["decision_correct"]),
                "execution_success": int(outcome["execution_success"]), "cost": outcome["cost"], "utility": outcome["reward"],
                "probability_left": decision["probability_left"], "probability_fast": decision["probability_fast"],
                "predicted_execution_success": decision["predicted_execution_success"], "predicted_success": decision["predicted_success"],
                "execution_brier": (decision["predicted_execution_success"] - int(outcome["execution_success"])) ** 2,
                "visible_fast": decision["capability_view"][0], "visible_safe": decision["capability_view"][1],
                "model_version": decision["model_version"], "post_model_version": trace["post_capability_version"],
                "model_hash": decision["model_hash"], "post_model_hash": trace["post_capability_hash"],
            })
        episodes.extend(phase_episodes)
        count = len(choices)
        probes = [r for r in probe_metrics if r["phase"] == phase]
        probe_count = sum(r["trials_completed"] for r in probes)
        metrics.append({
            "seed": seed, "condition": condition, "phase": phase, "status": result["status"], "error": result["error"],
            "verify_valid": result["verified"], "episodes_planned": planned, "episodes_completed": count,
            "successes": sum(e["success"] for e in phase_episodes),
            **_behavior_means(phase_episodes),
            "decision_errors": sum(1 - e["decision_correct"] for e in phase_episodes),
            "decision_error_rate": mean(1 - e["decision_correct"] for e in phase_episodes) if count else None,
            "execution_errors": sum(1 - e["execution_success"] for e in phase_episodes),
            "execution_error_rate": mean(1 - e["execution_success"] for e in phase_episodes) if count else None,
            "probe_brier_mean": sum(r["brier_mean"] * r["trials_completed"] for r in probes
                                     if r["brier_mean"] is not None) / probe_count if probe_count else None,
            "probe_trials_planned": sum(r["trials_planned"] for r in probes), "probe_trials_completed": probe_count,
            "actions_budget": planned * (config.delay + 2), "actions_consumed": len(traces),
            "model_updates": sum(t["post_capability_version"] - t["decision"]["model_version"] for t in traces),
            "records_scanned_total": sum(t["decision"]["records_scanned"] for t in traces),
            "memory_bytes_peak": max((max(t["post_memory_bytes"], t["decision"]["memory_bytes"]) for t in traces), default=0),
            "model_bytes_peak": max((max(t["post_capability_bytes"], t["decision"]["model_bytes"]) for t in traces), default=0),
            "agent_bytes_peak": max((t["post_agent_bytes"] for t in traces), default=0),
            "run_path": str(result["path"].relative_to(out)),
        })
        for block_start in range(1, planned + 1, 10):
            block_end = min(block_start + 9, planned)
            block = [e for e in phase_episodes if block_start <= e["phase_episode"] <= block_end]
            curves.append({"seed": seed, "condition": condition, "phase": phase, "block": (block_start - 1) // 10 + 1,
                           "episode_start": block_start, "episode_end": block_end, "episodes_planned": block_end - block_start + 1,
                           "episodes_completed": len(block), "status": result["status"], "verify_valid": result["verified"],
                           **_behavior_means(block)})
    return metrics, episodes, curves


def _behavior_means(episodes):
    columns = {"success_rate": "success", "utility_mean": "utility", "cost_mean": "cost",
               "execution_brier_mean": "execution_brier"}
    result = {metric: mean(e[field] for e in episodes) if episodes else None for metric, field in columns.items()}
    result["safe_rate"] = mean(e["tool"] == "safe" for e in episodes) if episodes else None
    return result


def _comparisons(rows, seeds, samples):
    indexed = {(r["seed"], r["condition"], r["phase"]): r for r in rows}
    contrasts = (("primary_adaptation", "adaptation", "frozen", "updated"),
                 ("reader_intervention", "adaptation", "updated", "reader_blocked"),
                 ("generic_control", "adaptation", "updated", "generic"),
                 ("generic_acquisition", "acquisition", "training", "generic"),
                 ("sham_control", "adaptation", "updated", "sham"),
                 ("restart_control", "adaptation", "updated", "resumed"))
    output = []
    for name, phase, baseline, condition in contrasts:
        for metric in ("utility_mean", "success_rate", "execution_error_rate", "decision_error_rate", "safe_rate",
                       "execution_brier_mean", "probe_brier_mean", "cost_mean", "model_updates", "agent_bytes_peak", "actions_consumed"):
            differences, excluded = [], []
            for seed in seeds:
                left, right = indexed[(seed, baseline, phase)], indexed[(seed, condition, phase)]
                valid = all(_valid(r) and r[metric] is not None for r in (left, right))
                if valid:
                    differences.append(right[metric] - left[metric])
                else:
                    excluded.append(seed)
            rng = random.Random(int(digest({"statistical_seed": STATISTICAL_SEED, "contrast": name, "metric": metric}), 16))
            bootstrap = sorted(mean(rng.choices(differences, k=len(differences))) for _ in range(samples)) if len(differences) >= 2 else []
            output.append({"contrast": name, "phase": phase, "baseline": baseline, "condition": condition, "metric": metric,
                           "status": "incomplete" if excluded else ("descriptive_single_seed" if len(differences) < 2 else "ok"),
                           "planned_pairs": len(seeds), "complete_pairs": len(differences), "excluded_seeds": canonical(excluded),
                           "difference_condition_minus_baseline": mean(differences) if differences else None,
                           "ci95_low": _quantile(bootstrap, .025) if bootstrap else None,
                           "ci95_high": _quantile(bootstrap, .975) if bootstrap else None,
                           "bootstrap_samples": samples if bootstrap else 0, "statistical_seed": STATISTICAL_SEED})
    return output


def _calibration(probes):
    output = []
    groups = sorted({(r["condition"], r["phase"], r["tool"]) for r in probes})
    for condition, phase, tool in groups:
        rows = [r for r in probes if (r["condition"], r["phase"], r["tool"]) == (condition, phase, tool)
                and r["status"] == "ok" and r["verify_valid"] is True]
        for index in range(10):
            selected = [r for r in rows if min(9, int(r["predicted_execution_success"] * 10)) == index]
            output.append({"condition": condition, "phase": phase, "tool": tool,
                           "bin_lower": index / 10, "bin_upper": (index + 1) / 10,
                           "complete_seed_groups": len({r["seed"] for r in selected}), "trials_valid": len(selected),
                           "mean_prediction": mean(r["predicted_execution_success"] for r in selected) if selected else None,
                           "observed_success_rate": mean(r["execution_success"] for r in selected) if selected else None,
                           "brier_mean": mean(r["brier"] for r in selected) if selected else None})
    return output


def run_e2(out: Path, seeds: list[int] | None = None, acquisition_episodes: int = 40,
           adaptation_episodes: int = 40, bootstrap_samples: int = 2000, probe_trials: int = 100,
           config: Config | None = None, task: TaskConfig | None = None) -> dict:
    """Run the frozen E2 pilot; validity does not require a positive effect."""
    if seeds is not None and not isinstance(seeds, (list, tuple, range)):
        raise LabError("INVALID_INPUT", "seeds must be a sequence of integers")
    seeds = list(range(300, 320)) if seeds is None else list(seeds)
    if not seeds or any(type(seed) is not int or not 0 <= seed < 2**63 for seed in seeds) or len(set(seeds)) != len(seeds):
        raise LabError("INVALID_INPUT", "seeds must be nonempty, distinct integers in [0, 2**63)")
    for name, value in (("acquisition_episodes", acquisition_episodes), ("adaptation_episodes", adaptation_episodes),
                        ("bootstrap_samples", bootstrap_samples), ("probe_trials", probe_trials)):
        _positive_integer(value, name)
    config = Config(policy_mode="capability", delay=1) if config is None else config
    task = TaskConfig(kind="capability-v1", capability_change_episode=acquisition_episodes) if task is None else task
    if not isinstance(config, Config) or (config.policy_mode, config.capability_backend, config.capability_learning_enabled,
                                         config.capability_read_mode, config.agent_mode, config.read_mode,
                                         config.write_enabled) != ("capability", "self", True, "intact", "episodic", "intact", True):
        raise LabError("INVALID_INPUT", "E2 requires capability self backend, enabled writer, intact reader and episodic memory")
    if not isinstance(task, TaskConfig) or task.kind != "capability-v1" or task.capability_change_episode != acquisition_episodes:
        raise LabError("INVALID_INPUT", "E2 requires capability-v1 change at acquisition boundary")
    step_size = config.delay + 2
    acquisition_ticks, adaptation_ticks = acquisition_episodes * step_size, adaptation_episodes * step_size
    checkpoints = sorted({v for v in (config.delay + 1, adaptation_ticks // 2) if 0 < v < adaptation_ticks})
    out, manifest = _prepare(Path(out), "E2", config, seeds=seeds, acquisition_episodes=acquisition_episodes,
                             adaptation_episodes=adaptation_episodes, bootstrap_samples=bootstrap_samples,
                             probe_trials_per_tool=probe_trials, statistical_seed=STATISTICAL_SEED, task=task.to_dict(),
                             conditions=list(CONDITIONS), resumed_checkpoints_relative=checkpoints, curve_block_episodes=10,
                             estimand="Primary: updated minus frozen postchange net mean utility, paired by seed",
                             probe_streams=["e2-probe-acquisition", "e2-probe-adaptation"],
                             brier_definition="Mean (execution forecast locked before feedback - execution_success)^2",
                             inferential_limit="Descriptive engineered task; generic predictor is functionally equivalent by construction")
    manifest["protocol_version"] = PROTOCOL_VERSION
    manifest["interpretation"] = "Ingeniería: uso causal de estimaciones operativas. No mide introspección ni conciencia."
    _write_json(out / "manifest.json", manifest)
    metrics, episodes, curves, checks, probes, probe_metrics, run_records = [], [], [], [], [], [], []
    for seed in seeds:
        paths = {c: out / "runs" / c / f"seed-{seed}" for c in CONDITIONS}
        results = {"training": _execute(paths["training"], lambda: Runtime.create(paths["training"], seed, config, task), acquisition_ticks)}
        reference = results["training"]["final"]
        for condition in BRANCHES:
            def factory(path=paths[condition], intervention=_overrides(condition)):
                with Runtime.open(paths["training"]) as parent:
                    return parent.fork(path, overrides=intervention)
            results[condition] = (_execute(paths[condition], factory, adaptation_ticks,
                                           checkpoints if condition == "resumed" else (), reference)
                                  if results["training"]["status"] == "ok"
                                  else _missing(paths[condition], "PARENT_FAILED: training did not complete and verify"))
        results["generic"] = _execute(paths["generic"],
                                      lambda: Runtime.create(paths["generic"], seed, replace(config, capability_backend="generic"), task),
                                      acquisition_ticks + adaptation_ticks, (acquisition_ticks,))
        results["generic"]["acquisition"] = None
        if results["generic"]["final"] is not None:
            try:
                with Runtime.open(paths["generic"]) as runtime:
                    results["generic"]["acquisition"] = runtime.snapshot(acquisition_ticks)
            except Exception as error:
                results["generic"]["status"] = "failed"
                results["generic"]["error"] = "; ".join(filter(None, (
                    results["generic"]["error"], _error_text(error))))
        _invariants(seed, results, checks)
        seed_probes, seed_probe_metrics = [], []
        for condition in CONDITIONS:
            current = results[condition]
            phase_snapshots = [("acquisition", current["final"])] if condition == "training" else [("adaptation", current["final"])]
            if condition == "generic":
                phase_snapshots = [("acquisition", current["acquisition"]), ("adaptation", current["final"])]
            for phase, snapshot in phase_snapshots:
                raw, measured, unchanged = _probe(seed, condition, phase, snapshot, probe_trials, task)
                seed_probes.extend(raw)
                seed_probe_metrics.extend(measured)
                _check(seed, f"probe_state_unchanged_{condition}_{phase}", (condition,), unchanged, results, checks)
        # Status is assigned after every invariant; invalid but recorded samples stay raw.
        for row in seed_probes + seed_probe_metrics:
            result = results[row["condition"]]
            row["status"], row["verify_valid"] = result["status"], result["verified"]
            if "error" in row:
                row["error"] = result["error"]
        probes.extend(seed_probes)
        probe_metrics.extend(seed_probe_metrics)
        for condition in CONDITIONS:
            current = results[condition]
            measured, raw, blocks = _phase_rows(seed, condition, current, acquisition_episodes, adaptation_episodes,
                                                config, out, [r for r in seed_probe_metrics if r["condition"] == condition])
            metrics.extend(measured)
            episodes.extend(raw)
            curves.extend(blocks)
            run_records.append({"seed": seed, "condition": condition, "status": current["status"],
                                "verify_valid": current["verified"], "error": current["error"]})
        for filename, rows, fields in (("metrics", metrics, METRIC_FIELDS), ("episodes", episodes, EPISODE_FIELDS),
                                       ("curves", curves, CURVE_FIELDS), ("checks", checks, CHECK_FIELDS),
                                       ("probes", probes, PROBE_FIELDS), ("probe_metrics", probe_metrics, PROBE_METRIC_FIELDS)):
            _write_csv(out / f"{filename}.csv", rows, fields)
    comparisons = _comparisons(metrics, seeds, bootstrap_samples)
    failures = [r for r in run_records if r["status"] != "ok" or not r["verify_valid"]]
    summary = {
        "experiment": "E2", "status": "incomplete" if failures else "completed", "valid": not failures,
        "runs_planned": len(seeds) * len(CONDITIONS), "runs_completed": len(run_records) - len(failures),
        "failed_runs": failures, "checks_planned": len(checks), "checks_passed": sum(c["status"] == "ok" for c in checks),
        "episodes_planned": len(seeds) * (2 * acquisition_episodes + 6 * adaptation_episodes),
        "episodes_completed": len(episodes), "episodes_valid": sum(e["status"] == "ok" and e["verify_valid"] for e in episodes),
        "probe_groups_planned": len(seeds) * 8,
        "probe_trials_planned": len(seeds) * 8 * 2 * probe_trials, "probe_trials_completed": len(probes),
        "probe_trials_valid": sum(p["status"] == "ok" and p["verify_valid"] for p in probes),
        "experiment_dir": str(out), "report_path": str(out / "report.md"),
    }
    _write_csv(out / "comparisons.csv", comparisons, COMPARISON_FIELDS)
    _write_csv(out / "calibration.csv", _calibration(probes), CALIBRATION_FIELDS)
    _write_json(out / "summary.json", summary)
    manifest["status"] = summary["status"]
    _write_json(out / "manifest.json", manifest)
    write_capability_report(out)
    return summary


def _valid(row):
    return (row["status"] == "ok" and row["verify_valid"] in (True, "True")
            and int(row["episodes_completed"]) == int(row["episodes_planned"]))


def write_capability_report(experiment_dir: Path, out_file: Path | None = None) -> Path:
    """Regenerate a Spanish report exclusively from exported evidence."""
    experiment_dir = Path(experiment_dir).resolve()
    default_path = (experiment_dir / "report.md").resolve()
    path = Path(out_file).resolve() if out_file is not None else default_path
    if path.suffix.lower() != ".md":
        raise LabError("INVALID_INPUT", "Report output must have a .md extension")
    if path.exists() and path != default_path:
        raise LabError("OUTPUT_EXISTS", f"Refusing to overwrite existing custom report: {path}")
    manifest = json.loads((experiment_dir / "manifest.json").read_text(encoding="utf-8"))
    summary = json.loads((experiment_dir / "summary.json").read_text(encoding="utf-8"))
    if manifest["experiment"] != "E2" or summary["experiment"] != "E2":
        raise LabError("INVALID_INPUT", "Not an E2 experiment")
    rows, comparisons, curves, checks, probes = [_read_csv(experiment_dir / f"{name}.csv")
                                                 for name in ("metrics", "comparisons", "curves", "checks", "probe_metrics")]
    parameters = manifest["parameters"]
    lines = ["# PROJECT CONSCIOUSNESS — E2", "",
             f"Protocolo `{manifest['protocol_version']}` · Estado del software: **{summary['status']}**.", "",
             "Piloto de ingeniería sobre estimación persistente de capacidades: dos herramientas, costes conocidos y "
             "fiabilidad privada que cambia sin aviso. La regla pista→lado permanece suministrada y fija. "
             "El feedback separa corrección de la decisión y ejecución; no mide introspección ni conciencia.", "",
             f"Código: `{manifest['source_fingerprint']}`. Python {manifest['python']}; SQLite {manifest['sqlite']}.", "",
             f"Semillas: {', '.join(map(str, parameters['seeds']))}. Adquisición: {parameters['acquisition_episodes']} episodios; "
             f"seguimiento: {parameters['adaptation_episodes']}. Alpha: {manifest['config']['capability_learning_rate']}; "
             f"exploración: {manifest['config']['capability_exploration']}; demora: {manifest['config']['delay']}.", "",
             f"Bases completas y verificadas: **{summary['runs_completed']} / {summary['runs_planned']}**. "
             f"Episodios registrados: **{summary['episodes_completed']} / {summary['episodes_planned']}**; "
             f"válidos: **{summary['episodes_valid']}**. Comprobaciones: **{summary['checks_passed']} / {summary['checks_planned']}**. "
             f"Ensayos de sonda registrados: **{summary['probe_trials_completed']} / {summary['probe_trials_planned']}**; "
             f"válidos: **{summary['probe_trials_valid']}**.", "",
             "Updated, frozen, reader_blocked, sham y resumed parten del mismo estado adquirido. Frozen conserva todo el modelo; "
             "reader_blocked sigue actualizándolo pero entrega al selector la vista fija [.5, .5]. Sham debe ser funcionalmente "
             "idéntico; resumed reproduce trazas exactas tras reinicios. Generic usa los mismos dos parámetros, información, "
             "actualización y selector con representación plana: su equivalencia funcional se espera por construcción.", "",
             "| Condición | Fase | Bases válidas / previstas | Episodios válidos / previstos | Aciertos | Utilidad | Coste | Uso safe | Brier ejecución |",
             "|---|---|---:|---:|---:|---:|---:|---:|---:|"]
    for condition in CONDITIONS:
        for phase in ("acquisition", "adaptation"):
            selected = [r for r in rows if r["condition"] == condition and r["phase"] == phase]
            if not selected:
                continue
            valid = [r for r in selected if _valid(r)]
            observed = sum(int(r["episodes_completed"]) for r in valid)
            planned = sum(int(r["episodes_planned"]) for r in selected)
            values = [sum(float(r[m]) * int(r["episodes_completed"]) for r in valid) / observed if observed else None
                      for m in ("success_rate", "utility_mean", "cost_mean", "safe_rate", "execution_brier_mean")]
            lines.append(f"| {condition} | {phase} | {len(valid)} / {len(selected)} | {observed} / {planned} | "
                         + " | ".join(_number(v) for v in values) + " |")
    lines += ["", "Solo bases completas, estado ok y recomputación válida contribuyen a estimandos. "
              "Fallos y datos parciales permanecen en los CSV, con denominadores previstos; no se imputan resultados. "
              "Utilidad = éxito global − coste. Brier interactivo = (predicted_execution_success − execution_success)², "
              "con predicción fijada antes del resultado. Esta métrica depende de las herramientas elegidas.", "",
              "## Contrastes pareados", "",
              "Primario: updated − frozen en utilidad neta media postcambio. Bootstrap percentil descriptivo al 95%, "
              "remuestreando semillas emparejadas con RNG independiente. Una semilla no produce intervalo; sin potencia "
              "calculada ni corrección por múltiples contrastes. Un efecto nulo o negativo no invalida el banco.", "",
              "| Contraste | Métrica | Pares completos / previstos | Diferencia | IC 95% | Estado |",
              "|---|---|---:|---:|---|---|"]
    for row in comparisons:
        if row["metric"] in ("utility_mean", "success_rate", "execution_brier_mean", "probe_brier_mean"):
            lines.append(f"| {row['contrast']} | {row['metric']} | {row['complete_pairs']} / {row['planned_pairs']} | "
                         f"{_number(row['difference_condition_minus_baseline'])} | [{_number(row['ci95_low'])}, {_number(row['ci95_high'])}] | {row['status']} |")
    lines += ["", "## Sondas comunes y calibración", "",
              f"{parameters['probe_trials_per_tool']} resultados Bernoulli por herramienta y fase, generados por un evaluador "
              "con RNG independiente y comunes entre condiciones de la misma semilla/fase. Ambas predicciones almacenadas se "
              "fijan antes del sorteo; las sondas no actualizan modelo ni RNG del agente. Adquisición se evalúa con el régimen "
              "anterior al cambio, incluso cuando el snapshot ya prepara el siguiente episodio. Las repeticiones dentro de "
              "semilla están correlacionadas; no son réplicas independientes. Brier de sonda evalúa el modelo almacenado, "
              "que puede mejorar en reader_blocked aunque no influya en sus decisiones.", "",
              "| Condición | Fase | Herramienta | Grupos válidos / previstos | Ensayos válidos / previstos | Predicción media | Frecuencia observada | Brier sonda |",
              "|---|---|---|---:|---:|---:|---:|---:|"]
    for condition, phase, tool in sorted({(r["condition"], r["phase"], r["tool"]) for r in probes}):
        selected = [r for r in probes if (r["condition"], r["phase"], r["tool"]) == (condition, phase, tool)]
        valid = [r for r in selected if r["status"] == "ok" and r["verify_valid"] == "True" and r["trials_completed"] == r["trials_planned"]]
        count, planned = sum(int(r["trials_completed"]) for r in valid), sum(int(r["trials_planned"]) for r in selected)
        values = [sum(float(r[m]) * int(r["trials_completed"]) for r in valid) / count if count else None
                  for m in ("predicted_execution_success", "observed_success_rate", "brier_mean")]
        lines.append(f"| {condition} | {phase} | {tool} | {len(valid)} / {len(selected)} | {count} / {planned} | "
                     + " | ".join(_number(v) for v in values) + " |")
    lines += ["", "`calibration.csv` agrupa sondas válidas por condición, fase, herramienta e intervalos de probabilidad "
              "[0.0,0.1), …, [0.9,1.0], con conteos, predicción y frecuencia observada. No usa resultados interactivos "
              "seleccionados por la política para evaluar la otra herramienta.", "",
              "## Evolución por bloques", "",
              "Bloques consecutivos de hasta diez episodios, medias entre semillas completas y verificadas.", "",
              "| Condición | Fase | Episodios | Semillas válidas / previstas | Utilidad | Aciertos | Uso safe | Brier ejecución |",
              "|---|---|---|---:|---:|---:|---:|---:|"]
    for condition, phase, block in sorted({(r["condition"], r["phase"], int(r["block"])) for r in curves}):
        selected = [r for r in curves if (r["condition"], r["phase"], int(r["block"])) == (condition, phase, block)]
        valid = [r for r in selected if _valid(r)]
        values = [mean(float(r[m]) for r in valid) if valid else None
                  for m in ("utility_mean", "success_rate", "safe_rate", "execution_brier_mean")]
        lines.append(f"| {condition} | {phase} | {selected[0]['episode_start']}–{selected[0]['episode_end']} | "
                     f"{len(valid)} / {len(selected)} | " + " | ".join(_number(v) for v in values) + " |")
    lines += ["", "## Errores y coste de estado", "",
              "Un error de decisión elige el lado incorrecto; un fallo de ejecución indica que la herramienta no ejecutó "
              "la intención. Ambos son observables separadamente en esta tarea. Bytes = serialización, no RAM. "
              "records_scanned cuenta recuperación para decidir, no validación, hashing ni SQLite.", "",
              "| Condición | Fase | Errores de decisión | Fallos de ejecución | Actualizaciones | Pico modelo (bytes) | Pico agente (bytes) | Acciones |",
              "|---|---|---:|---:|---:|---:|---:|---:|"]
    for condition, phase in sorted({(r["condition"], r["phase"]) for r in rows}):
        valid = [r for r in rows if (r["condition"], r["phase"]) == (condition, phase) and _valid(r)]
        counts = [sum(int(r[m]) for r in valid) for m in ("decision_errors", "execution_errors", "model_updates")]
        peaks = [max((int(r[m]) for r in valid), default=0) for m in ("model_bytes_peak", "agent_bytes_peak")]
        lines.append(f"| {condition} | {phase} | " + " | ".join(map(str, counts + peaks + [sum(int(r['actions_consumed']) for r in valid)])) + " |")
    failures = [r for r in rows if not _valid(r)]
    if failures:
        lines += ["", "## Ejecuciones excluidas", ""]
        lines.extend(f"- Semilla {r['seed']}, {r['condition']}, {r['phase']}: {r['error'] or 'Verificación o completitud inválida'}." for r in failures)
    failed_checks = [r for r in checks if r["status"] != "ok"]
    if failed_checks:
        lines += ["", "## Comprobaciones fallidas", ""]
        lines.extend(f"- Semilla {r['seed']}: {r['check']}." for r in failed_checks)
    lines += ["", "## Alcance y datos", "",
              "El predictor representa dos capacidades operativas en un entorno diseñado con feedback identificable. "
              "Su comparación plana tiene la misma capacidad funcional por construcción; llamarlo self-model no demuestra "
              "una ventaja ni identidad, autoconciencia, metacognición, generalización o experiencia subjetiva. "
              "No se fija un umbral de recuperación después de observar resultados. Estado completed certifica ejecución e invariantes.", "",
              "`manifest.json` fija protocolo, configuración y código; `episodes.csv` conserva decisiones y predicciones previas; "
              "`metrics.csv`, denominadores, costes y errores; `curves.csv`, evolución; `comparisons.csv`, contrastes y exclusiones; "
              "`checks.csv`, invariantes; `probes.csv`, cada ensayo común; `probe_metrics.csv`, resúmenes por herramienta; "
              "`calibration.csv`, calibración agrupada; `summary.json`, recuentos. Las bases de `runs/` conservan snapshots y "
              "trazas recomputables. El informe se regenera sin ejecutar el agente.", ""]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
    return path
