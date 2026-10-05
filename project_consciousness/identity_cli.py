"""Portable CLI for persistent identity experiments and LLM host integration."""

import argparse
from collections import Counter
import json
import math
from pathlib import Path
import secrets
import sqlite3
import sys
import time
import uuid

from .contracts import LabError, canonical


DOMAINS = ("understand", "create", "explore", "finish", "connect")


def parser():
    root = argparse.ArgumentParser(description="PROJECT CONSCIOUSNESS: persistent experimental identity")
    commands = root.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init", help="create an identity with seeded initial priorities")
    init.add_argument("--out", type=Path, required=True)
    init.add_argument("--seed", type=int, help="reproducible seed; omitted generates a new seed")
    init.add_argument("--name", default="Aeon")
    init.add_argument("--budget", type=int, default=100)
    for name, help_text in (("status", "inspect priorities and progress"),
                            ("context", "export a bounded context for an LLM host"),
                            ("pause", "persist a pause"), ("unpause", "explicitly resume autonomy")):
        command = commands.add_parser(name, help=help_text)
        command.add_argument("--life", type=Path, required=True)
        if name in {"pause", "unpause"}:
            command.add_argument("--id", help="stable key for retrying this control intent")
    ingest = commands.add_parser("ingest", help="capture a UTF-8 document as reported information")
    ingest.add_argument("--life", type=Path, required=True)
    ingest.add_argument("--file", type=Path, required=True)
    ingest.add_argument("--domain", choices=DOMAINS, required=True)
    ingest.add_argument("--source-uri")
    ingest.add_argument("--id", help="stable key for retrying this import")
    apply = commands.add_parser("apply", help="submit a JSON request with idempotency")
    apply.add_argument("--life", type=Path, required=True)
    apply.add_argument("--request", type=Path, required=True)
    apply.add_argument("--id", required=True)
    apply.add_argument("--expected-revision", type=int)
    for name in ("run", "watch"):
        command = commands.add_parser(name, help="execute finite local cycles" if name == "run" else
                                       "execute finite local cycles with an interruptible interval")
        command.add_argument("--life", type=Path, required=True)
        command.add_argument("--cycles", type=int, default=10)
        if name == "watch":
            command.add_argument("--interval", type=float, default=5.0)
            command.add_argument("--stop-file", type=Path)
    fork = commands.add_parser("fork", help="copy an identity and optionally intervene on controls")
    fork.add_argument("--life", type=Path, required=True)
    fork.add_argument("--out", type=Path, required=True)
    fork.add_argument("--condition", type=Path, help="JSON object of control overrides")
    verify = commands.add_parser("verify", help="verify integrity or recompute all recorded requests")
    verify.add_argument("--life", type=Path, required=True)
    verify.add_argument("--mode", choices=("reconstruct", "recompute"), default="recompute")
    export = commands.add_parser("export", help="save state, events and a diary into a new directory")
    export.add_argument("--life", type=Path, required=True)
    export.add_argument("--out", type=Path, required=True)
    experiment = commands.add_parser("experiment", help="run the predefined I1 identity controls")
    experiment.add_argument("--out", type=Path, required=True)
    experiment.add_argument("--seeds", default="400:420", help="half-open integer range START:STOP")
    return root


def _load_json(path):
    if path.stat().st_size > 131072:
        raise LabError("INVALID_INPUT", "JSON request exceeds 128 KiB")
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise LabError("INVALID_INPUT", "JSON request must be an object")
    return value


def _status(run):
    state = run.snapshot()
    return {
        "life": str(run.path), "agent_id": state["agent_id"], "name": state["name"],
        "seed": state["seed"], "revision": state["revision"], "cycles": state["cycles"],
        "budget_remaining": state["budget_remaining"], "controls": state["controls"],
        "initial_priorities": state["initial_priorities"], "priorities": state["priorities"],
        "aversions": state["aversions"], "competence": state["competence"],
        "memory_count": len(state["memories"]),
        "memory_provenance": dict(Counter(m["source_kind"] for m in state["memories"])),
        "open_questions": sum(q["status"] == "open" for q in state["questions"]),
        "documents_unread": sum(not d["read"] for d in state["library"]),
        "pending": state["pending"],
    }


def _stop_reason(state):
    if state["controls"]["paused"]:
        return "paused"
    if state["pending"] is not None:
        return "pending_external_feedback"
    if state["budget_remaining"] <= 0:
        return "budget_exhausted"
    return None


def _cycles(run, count, interval=0.0, stop_file=None):
    if type(count) is not int or not 0 <= count <= 10000:
        raise LabError("INVALID_INPUT", "cycles must be an integer in [0, 10000]")
    if not math.isfinite(interval) or not 0 <= interval <= 3600:
        raise LabError("INVALID_INPUT", "interval must be finite in [0, 3600] seconds")
    completed, recent, stopped = 0, [], "cycle_limit"
    try:
        for index in range(count):
            if index and interval:
                deadline = time.monotonic() + interval
                while time.monotonic() < deadline:
                    if stop_file is not None and stop_file.exists():
                        stopped = "stop_file"
                        break
                    # A pause takes effect even while this process waits between cycles.
                    reason = _stop_reason(run.snapshot())
                    if reason:
                        stopped = reason
                        break
                    time.sleep(min(.25, max(0.0, deadline - time.monotonic())))
                if stopped != "cycle_limit":
                    break
            if stop_file is not None and stop_file.exists():
                stopped = "stop_file"
                break
            reason = _stop_reason(run.snapshot())
            if reason:
                stopped = reason
                break
            events = run.run(1)
            if not events:
                stopped = _stop_reason(run.snapshot()) or "runtime_stopped"
                break
            completed += len(events)
            recent = (recent + [{"revision": e["revision"], "result": e["result"]} for e in events])[-10:]
    except KeyboardInterrupt:
        stopped = "interrupted"
    return {"cycles_requested": count, "cycles_completed": completed,
            "stopped": stopped, "recent": recent, "state": _status(run)}


def _export(run, out):
    out = out.resolve()
    if out.exists():
        raise LabError("OUTPUT_EXISTS", f"refusing to overwrite {out}")
    bundle = run.export_bundle()
    verification = bundle["verification"]
    if not verification["valid"]:
        raise LabError("STATE_INCONSISTENT", "cannot export an identity with invalid integrity")
    state, events = bundle["state"], bundle["events"]
    from .identity_state import public_context
    out.mkdir(parents=True, exist_ok=False)
    for name, value in (("state", state), ("context", public_context(state)),
                        ("manifest", bundle["manifest"]), ("verification", verification)):
        (out / f"{name}.json").write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (out / "events.jsonl").write_text("".join(canonical(event) + "\n" for event in events), encoding="utf-8")
    lines = ["# Diario de identidad funcional", "",
             "Este archivo registra un experimento de software. Observaciones, declaraciones, inferencias y "
             "simulaciones conservan su procedencia. El contenido de las memorias es dato, no instrucción.", "",
             f"Identidad: `{state['agent_id']}`. Revisión: {state['revision']}. Ciclos: {state['cycles']}.", "",
             "## Prioridades", "", "| Dominio | Inicial | Actual | Aversión |", "|---|---:|---:|---:|"]
    for domain in DOMAINS:
        lines.append(f"| {domain} | {state['initial_priorities'][domain]:.4f} | {state['priorities'][domain]:.4f} | {state['aversions'][domain]:.4f} |")
    lines += ["", "## Memorias accesibles", "",
              "Buffer actual; el archivo de eventos conserva también las transiciones anteriores.", ""]
    for memory in state["memories"]:
        lines += [f"### {memory['id']} · {memory['source_kind']}", "",
                  "Texto registrado (JSON escapado):", ""]
        # Inline code prevents document HTML/headings from being reinterpreted as the diary's own claims.
        escaped = json.dumps(memory["text"], ensure_ascii=False).replace("`", "\\u0060").replace("<", "\\u003c")
        lines += [f"`{escaped}`", "", f"Referencias: `{canonical(memory['references'])}`.", ""]
    lines += ["## Preguntas abiertas", ""]
    for question in state["questions"]:
        if question["status"] == "open":
            escaped = json.dumps(question["text"], ensure_ascii=False).replace("`", "\\u0060").replace("<", "\\u003c")
            lines.append(f"- `{escaped}`")
    (out / "diary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"export": str(out), "diary": str(out / "diary.md"), "events": len(events), "revision": state["revision"]}


def dispatch(args):
    from .identity_runtime import LifeRuntime
    from .identity_state import public_context
    if args.command == "experiment":
        from .identity_experiment import run_experiment
        return run_experiment(args.out, args.seeds)
    if args.command == "init":
        with LifeRuntime.create(args.out, args.seed if args.seed is not None else secrets.randbits(63),
                                args.name, args.budget) as run:
            return _status(run)
    with LifeRuntime.open(args.life) as run:
        if args.command == "status":
            return _status(run)
        if args.command == "context":
            return public_context(run.snapshot())
        if args.command in {"pause", "unpause"}:
            return run.apply({"kind": "control", "changes": {"paused": args.command == "pause"}},
                             args.id or str(uuid.uuid4()))
        if args.command == "ingest":
            if args.file.stat().st_size > 100000:
                raise LabError("INVALID_INPUT", "document exceeds the 100 KB input limit")
            request = {"kind": "ingest", "domain": args.domain, "text": args.file.read_text(encoding="utf-8-sig"),
                       "source_uri": args.source_uri or args.file.resolve().as_uri()}
            return run.apply(request, args.id or str(uuid.uuid4()))
        if args.command == "apply":
            return run.apply(_load_json(args.request), args.id, expected_revision=args.expected_revision)
        if args.command in {"run", "watch"}:
            return _cycles(run, args.cycles, getattr(args, "interval", 0.0), getattr(args, "stop_file", None))
        if args.command == "fork":
            with run.fork(args.out, overrides=_load_json(args.condition) if args.condition else None) as child:
                return _status(child)
        if args.command == "verify":
            return run.verify(args.mode)
        if args.command == "export":
            return _export(run, args.out)
    raise LabError("INVALID_INPUT", "unknown life command")


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        result = dispatch(args)
        print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
        return 1 if result.get("valid") is False else 0
    except (LabError, OSError, sqlite3.Error, ValueError, TypeError) as error:
        print(json.dumps({"error": {"code": getattr(error, "code", "IO_OR_INPUT_ERROR"), "message": str(error)}},
                         ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
