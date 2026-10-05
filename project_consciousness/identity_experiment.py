"""I1: predefined paired controls of an engineered persistent identity.

All feedback is a synthetic fixture. This protocol tests causal paths and
reproducibility, not intelligence, wellbeing or subjective consciousness.
"""

from collections import Counter
import csv
import json
from pathlib import Path

from .contracts import LabError, digest
from .identity_runtime import LifeRuntime
from .identity_state import DOMAINS


CONDITIONS = {
    "updated": {}, "frozen": {"learning_enabled": False},
    "neutral": {"preferences_visible": False},
    "no-aversion": {"aversion_visible": False},
    "no-dream": {"dream_enabled": False}, "restarted": {},
}
OUTCOMES = {
    "understand": (True, .8, 0.0), "create": (True, .4, .2),
    "explore": (False, -.8, 1.0), "finish": (True, .2, 0.0),
    "connect": (False, -.4, .6),
}
PROTOCOL = {
    "id": "I1", "version": 1, "default_seeds": "400:420", "budget": 100,
    "training_local_cycles": 12, "training_exposures": list(DOMAINS),
    "training_feedback": {"success": True, "value": .4, "harm": .8},
    "followup_choices": 10, "followup_local_cycles": 5,
    "candidate_fields": {"novelty": .5, "cost": .2, "risk": 1.0},
    "conditions": CONDITIONS, "outcomes_by_domain": OUTCOMES,
    "restart_after_choices": [4, 8], "restart_after_local_cycles": [2],
    "scope": "Synthetic causal engineering controls; no consciousness score or performance superiority hypothesis.",
}


def _seeds(value):
    try:
        start, stop = (int(part) for part in value.split(":"))
    except (AttributeError, TypeError, ValueError) as error:
        raise LabError("INVALID_INPUT", "seeds must be START:STOP") from error
    if not 0 <= start < stop <= 2**63 or stop - start > 100:
        raise LabError("INVALID_INPUT", "seeds must contain 1 to 100 values in [0, 2**63)")
    return range(start, stop)


def _candidates(domains=DOMAINS):
    return [{"id": domain, "domain": domain, "description": f"Synthetic I1 activity: {domain}",
             **PROTOCOL["candidate_fields"]} for domain in domains]


def _feedback(decision, success, value, harm, source):
    return {"kind": "feedback", "decision_id": decision["id"],
            "status": "completed" if success else "failed", "success": success,
            "value": value, "harm": harm,
            "text": "Synthetic I1 fixture outcome, not an observation about a person or the external world.",
            "source_uri": source}


def _functional_events(events):
    # Each fork has a distinct manifest/chain anchor. Compare functional payloads,
    # including state hashes and request IDs, rather than lineage-specific hashes.
    return [{key: event[key] for key in ("revision", "request_id", "request", "result",
                                        "before_hash", "after_hash")} for event in events]


def _write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def run_experiment(out, seeds="400:420"):
    seeds = list(_seeds(seeds))
    out = Path(out).resolve()
    if out.exists():
        raise LabError("OUTPUT_EXISTS", f"refusing to overwrite {out}")
    out.mkdir(parents=True, exist_ok=False)
    _write_json(out / "protocol.json", PROTOCOL)
    checks, rows, scores, manifests = [], [], [], []
    total_events = 0

    def check(seed, name, passed, detail=None):
        checks.append({"seed": seed, "check": name, "passed": bool(passed), "detail": detail})

    for seed in seeds:
        seed_path = out / "identities" / str(seed)
        with LifeRuntime.create(seed_path / "base", seed=seed, budget=PROTOCOL["budget"]) as base:
            for domain in DOMAINS:
                base.apply({"kind": "ingest", "domain": domain,
                            "text": f"Synthetic I1 corpus fixture for {domain}. It defines no facts about consciousness.",
                            "source_uri": f"fixture://i1/corpus/{domain}"}, f"import-{domain}")
            for step in range(PROTOCOL["training_local_cycles"]):
                base.apply({"kind": "cycle"}, f"training-cycle-{step}")
            for domain in PROTOCOL["training_exposures"]:
                decision = base.apply({"kind": "choose", "candidates": _candidates((domain,))},
                                      f"exposure-{domain}")["result"]["decision"]
                feedback = PROTOCOL["training_feedback"]
                base.apply(_feedback(decision, feedback["success"], feedback["value"], feedback["harm"],
                                     f"fixture://i1/exposure/{domain}"),
                           f"exposure-feedback-{domain}")
            origin = base.snapshot()
            base_events = base.events()
            total_events += len(base_events)
            manifests.append(base.manifest)
            check(seed, "base_recompute", base.verify("recompute")["valid"])
            for condition, overrides in CONDITIONS.items():
                with base.fork(seed_path / condition, overrides) as child:
                    manifests.append(child.manifest)
            check(seed, "parent_unchanged", origin == base.snapshot() and base_events == base.events())

        states, histories, decisions = {}, {}, {}
        for condition in CONDITIONS:
            path = seed_path / condition
            run = LifeRuntime.open(path)
            try:
                for step in range(PROTOCOL["followup_choices"]):
                    decision = run.apply({"kind": "choose", "candidates": _candidates()},
                                         f"followup-choice-{step}")["result"]["decision"]
                    domain = decision["selected"]["domain"]
                    run.apply(_feedback(decision, *OUTCOMES[domain], f"fixture://i1/followup/{step}/{domain}"),
                              f"followup-feedback-{step}")
                    if condition == "restarted" and step + 1 in PROTOCOL["restart_after_choices"]:
                        run.close()
                        run = LifeRuntime.open(path)
                for step in range(PROTOCOL["followup_local_cycles"]):
                    run.apply({"kind": "cycle"}, f"followup-cycle-{step}")
                    if condition == "restarted" and step + 1 in PROTOCOL["restart_after_local_cycles"]:
                        run.close()
                        run = LifeRuntime.open(path)
                states[condition], histories[condition] = run.snapshot(), run.events()
                check(seed, f"{condition}_recompute", run.verify("recompute")["valid"])
            finally:
                run.close()
            state, events = states[condition], histories[condition]
            total_events += len(events)
            selected = [e["result"]["decision"] for e in events if e["request"]["kind"] == "choose"]
            decisions[condition] = selected
            new_memories = [m for m in state["memories"] if m["revision"] > origin["revision"]]
            provenance = Counter(m["source_kind"] for m in new_memories)
            row = {"seed": seed, "condition": condition, "choices": len(selected),
                   "budget_consumed": origin["budget_remaining"] - state["budget_remaining"],
                   "priority_l1_change": sum(abs(state["priorities"][d] - origin["priorities"][d]) for d in DOMAINS),
                   "aversion_l1_change": sum(abs(state["aversions"][d] - origin["aversions"][d]) for d in DOMAINS),
                   "new_memories": len(new_memories),
                   **{kind: provenance[kind] for kind in ("OBSERVED", "REPORTED", "INFERRED", "SIMULATED")},
                   **{f"selected_{d}": sum(item["selected"]["domain"] == d for item in selected) for d in DOMAINS}}
            rows.append(row)
            check(seed, f"{condition}_budget_and_no_pending", row["budget_consumed"] == 15 and state["pending"] is None)
            for step, decision in enumerate(selected):
                scores.extend({"seed": seed, "condition": condition, "step": step,
                               "selected": decision["selected"]["id"], **score} for score in decision["scores"])

        check(seed, "restarted_exact_state", states["updated"] == states["restarted"])
        check(seed, "restarted_functional_events", _functional_events(histories["updated"]) ==
              _functional_events(histories["restarted"]))
        check(seed, "frozen_maps_and_new_memories", all(states["frozen"][key] == origin[key] for key in
              ("priorities", "aversions", "competence")) and len(states["frozen"]["memories"]) > len(origin["memories"]))
        check(seed, "neutral_initial_score", all(s["priority"] == .2 for s in decisions["neutral"][0]["scores"]))
        first_updated, first_blocked = decisions["updated"][0]["scores"], decisions["no-aversion"][0]["scores"]
        other_terms = ("candidate_id", "domain", "priority", "efficacy", "uncertainty", "novelty_term",
                       "efficacy_term", "cost_penalty", "question_bonus")
        check(seed, "aversion_initial_score_intervention", all(
            b["aversion_penalty"] == 0 and a["aversion_penalty"] > 0 and
            all(a[key] == b[key] for key in other_terms) and
            abs((b["score"] - a["score"]) - a["aversion_penalty"]) < 1e-12
            for a, b in zip(first_updated, first_blocked)))
        check(seed, "no_dream_no_new_simulations", not any(m["source_kind"] == "SIMULATED" and
              m["revision"] > origin["revision"] for m in states["no-dream"]["memories"]))
        for condition in CONDITIONS:
            row = next(row for row in rows if row["seed"] == seed and row["condition"] == condition)
            row["choices_different_from_updated"] = sum(a["selected"]["id"] != b["selected"]["id"] for a, b in
                                                        zip(decisions["updated"], decisions[condition]))
            row["first_choice_different_from_updated"] = int(decisions["updated"][0]["selected"]["id"] !=
                                                             decisions[condition][0]["selected"]["id"])

    check(None, "single_source_fingerprint", len({m["source_hash"] for m in manifests}) == 1)
    summary = {"protocol": "I1", "protocol_hash": digest(PROTOCOL), "seeds": seeds,
               "identities": len(manifests), "events": total_events,
               "followup_choices": sum(row["choices"] for row in rows), "score_rows": len(scores),
               "checks": len(checks), "failed_checks": sum(not c["passed"] for c in checks),
               "source_hashes": sorted({m["source_hash"] for m in manifests}), "conditions": {}}
    for condition in CONDITIONS:
        group = [row for row in rows if row["condition"] == condition]
        summary["conditions"][condition] = {
            "choices_different_from_updated": sum(row["choices_different_from_updated"] for row in group),
            "first_choices_different_from_updated": sum(row["first_choice_different_from_updated"] for row in group),
            "mean_priority_l1_change": sum(row["priority_l1_change"] for row in group) / len(group),
            "new_simulations": sum(row["SIMULATED"] for row in group),
        }
    _write_json(out / "summary.json", summary)
    _write_json(out / "checks.json", checks)
    _write_json(out / "manifests.json", manifests)
    for filename, records in (("conditions.csv", rows), ("scores.csv", scores)):
        with (out / filename).open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(records[0]))
            writer.writeheader()
            writer.writerows(records)
    lines = ["# I1: identidad persistente y controles causales", "",
             f"{len(seeds)} semillas; {len(manifests)} bases; {total_events} eventos; "
             f"{summary['followup_choices']} elecciones de seguimiento; {len(scores)} filas de puntuación.", "",
             f"Comprobaciones: {summary['checks'] - summary['failed_checks']}/{summary['checks']} válidas.", "",
             "| Condición | Elecciones distintas de updated | Primera elección distinta | Cambio medio L1 de prioridades | Sueños nuevos |",
             "|---|---:|---:|---:|---:|"]
    for condition, values in summary["conditions"].items():
        lines.append(f"| {condition} | {values['choices_different_from_updated']} | "
                     f"{values['first_choices_different_from_updated']} | {values['mean_priority_l1_change']:.6f} | "
                     f"{values['new_simulations']} |")
    lines += ["", "El denominador de elecciones es diez por semilla y condición; el de primeras elecciones es el número de semillas.", "",
              "Los resultados describen un mecanismo diseñado con feedback sintético. La primera elección compara el mismo estado; "
              "las siguientes incluyen historias que pueden divergir. Un cambio de puntuación puede no cambiar el máximo. "
              "No se mide conciencia, bienestar, personalidad humana ni superioridad general.", "",
              "Frozen conserva prioridades, aversiones y competencia; los recuerdos siguen creciendo. No-dream bloquea nuevas "
              "simulaciones. Restarted debe reproducir estados y eventos funcionales, excluyendo hashes de cadena que identifican cada rama.", "",
              "Todas las fuentes del corpus y feedback están etiquetadas fixture://. REPORTED no certifica verdad externa; "
              "los sueños permanecen SIMULATED. El corpus cerrado agota sus lecturas; los ciclos posteriores pueden quedar idle.", "",
              "Reproducir con el código archivado de esta versión y el mismo Python/SQLite:", "",
              "```powershell", f"python -m project_consciousness life experiment --seeds {seeds[0]}:{seeds[-1] + 1} --out runs/i1-new", "```", "",
              f"Source fingerprint: `{summary['source_hashes']}`.",
              f"Protocolo: `{summary['protocol_hash']}`. Archivos: protocol.json, checks.json, conditions.csv, scores.csv y bases identities/."]
    (out / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"valid": summary["failed_checks"] == 0, "out": str(out), "report": str(out / "report.md"), **summary}
