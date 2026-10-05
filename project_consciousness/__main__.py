"""Command-line entry point. No package installation or external service required."""

import argparse
import json
from pathlib import Path
import sqlite3
import sys
import tomllib

from .contracts import Config, LabError, TaskConfig, canonical
from .runtime import Runtime


def load_toml(path):
    with Path(path).open("rb") as stream:
        return tomllib.load(stream)


def load_run_config(path):
    data = load_toml(path) if path else {}
    if "agent" in data or "task" in data:
        if set(data) - {"agent", "task"}:
            raise LabError("INVALID_INPUT", "sectioned run config only supports [agent] and [task]")
        return Config.from_dict(data.get("agent", {})), TaskConfig.from_dict(data.get("task", {}))
    return Config.from_dict(data), TaskConfig()


def parse_seeds(value):
    try:
        parts = value.split(":")
        if len(parts) != 2:
            raise ValueError
        start, stop = map(int, parts)
        if not 0 <= start < stop <= 2**63 or stop - start > 10000:
            raise ValueError
        return list(range(start, stop))
    except (ValueError, AttributeError) as error:
        raise LabError("INVALID_INPUT", "seeds must be a nonempty half-open START:STOP range, at most 10000 seeds") from error


def export_run(run):
    traces = run.traces()
    destination = run.path / "decisions.jsonl"
    destination.write_text("".join(canonical(trace) + "\n" for trace in traces), encoding="utf-8")
    terminal = [t for t in traces if t["outcome"]["terminal"]]
    result = {"run": str(run.path), "tick": run.snapshot()["tick"],
            "completed_episodes": len(terminal),
            "success_rate": sum(t["outcome"]["success"] for t in terminal) / len(terminal) if terminal else None,
            "decisions": str(destination)}
    if run.manifest["task"] == "capability-v1":
        result.update(mean_utility=sum(t["outcome"]["reward"] for t in terminal) / len(terminal) if terminal else None,
                      execution_success_rate=sum(t["outcome"]["execution_success"] for t in terminal) / len(terminal) if terminal else None,
                      decision_accuracy=sum(t["outcome"]["decision_correct"] for t in terminal) / len(terminal) if terminal else None,
                      tool_counts={tool: sum(t["decision"]["tool"] == tool for t in terminal) for tool in ("fast", "safe")})
    return result


def parser():
    root = argparse.ArgumentParser(description="PROJECT CONSCIOUSNESS v0.4: persistent cognition and identity laboratory")
    commands = root.add_subparsers(dest="command", required=True)
    commands.add_parser("life", help="persistent identity, preferences and LLM host integration; life --help for commands")
    run = commands.add_parser("run", help="create a run; output must not exist")
    run.add_argument("--config", type=Path)
    run.add_argument("--seed", type=int, default=17)
    run.add_argument("--ticks", type=int, default=100)
    run.add_argument("--out", type=Path, required=True)
    resume = commands.add_parser("resume", help="execute additional ticks")
    resume.add_argument("--run", type=Path, required=True)
    resume.add_argument("--ticks", type=int, required=True)
    replay = commands.add_parser("replay", help="verify integrity or recompute transitions")
    replay.add_argument("--run", type=Path, required=True)
    replay.add_argument("--mode", choices=("reconstruct", "recompute"), default="recompute")
    replay.add_argument("--verify", action="store_true", help="verification is always performed")
    fork = commands.add_parser("fork", help="branch a committed state without changing its parent")
    fork.add_argument("--run", type=Path, required=True)
    fork.add_argument("--tick", type=int, help="committed tick to branch; defaults to latest")
    fork.add_argument("--condition", type=Path, required=True)
    fork.add_argument("--out", type=Path, required=True)
    experiment = commands.add_parser("experiment", help="execute E0, E1, L1 or E2")
    experiment.add_argument("--protocol", type=Path, required=True)
    experiment.add_argument("--seeds", help="half-open seed range, e.g. 100:120")
    experiment.add_argument("--out", type=Path, required=True)
    report = commands.add_parser("report", help="regenerate a report from recorded experiment data")
    report.add_argument("--experiment", type=Path, required=True)
    report.add_argument("--out", type=Path)
    status = commands.add_parser("status", help="show run metadata and last committed tick")
    status.add_argument("--run", type=Path, required=True)
    return root


def dispatch(args):
    if args.command == "run":
        if args.ticks < 0:
            raise LabError("INVALID_INPUT", "ticks must be nonnegative")
        config, task = load_run_config(args.config)
        with Runtime.create(args.out, args.seed, config, task) as run:
            run.run(args.ticks)
            return export_run(run)
    if args.command == "resume":
        with Runtime.open(args.run) as run:
            run.run(args.ticks)
            return export_run(run)
    if args.command == "replay":
        with Runtime.open(args.run) as run:
            return run.verify(args.mode)
    if args.command == "fork":
        with Runtime.open(args.run) as parent:
            with parent.fork(args.out, args.tick, load_toml(args.condition)) as child:
                return export_run(child)
    if args.command == "status":
        with Runtime.open(args.run) as run:
            state = run.snapshot()
            result = {"manifest": run.manifest, "tick": state["tick"]}
            if "learner" in state["agent"]:
                result["learner"] = state["agent"]["learner"]
            if "capability" in state["agent"]:
                result["capability"] = state["agent"]["capability"]
            return result
    # Importing the laboratory here keeps its privileges outside the agent API.
    from .experiments import run_e0, run_e1, write_report
    if args.command == "report":
        return {"report": str(write_report(args.experiment, args.out))}
    data = load_toml(args.protocol)
    if set(data) - {"experiment", "agent", "task"}:
        raise LabError("INVALID_INPUT", "protocol only supports [experiment], [agent] and [task]")
    options = data.get("experiment", {})
    if not isinstance(options, dict):
        raise LabError("INVALID_INPUT", "[experiment] must be a table")
    config = Config.from_dict(data.get("agent", {}))
    protocol = options.get("protocol")
    if protocol in {"E0", "E1"} and "task" in data:
        raise LabError("INVALID_INPUT", "[task] is only supported by L1/E2; E0/E1 retain their original task")
    if protocol == "E0":
        if set(options) - {"protocol", "seed", "ticks"} or args.seeds:
            raise LabError("INVALID_INPUT", "E0 accepts protocol, seed and ticks; no --seeds")
        return run_e0(args.out, seed=options.get("seed", 17), ticks=options.get("ticks", 1000), config=config)
    if protocol == "E1":
        if set(options) - {"protocol", "seeds", "episodes", "bootstrap_samples"}:
            raise LabError("INVALID_INPUT", "unknown E1 protocol setting")
        return run_e1(args.out, seeds=parse_seeds(args.seeds or options.get("seeds", "100:120")),
                      episodes=options.get("episodes", 40), config=config,
                      bootstrap_samples=options.get("bootstrap_samples", 2000))
    if protocol == "L1":
        if set(options) - {"protocol", "seeds", "acquisition_episodes", "adaptation_episodes", "bootstrap_samples"}:
            raise LabError("INVALID_INPUT", "unknown L1 protocol setting")
        from .learning_experiment import run_l1
        task = TaskConfig.from_dict(data["task"]) if "task" in data else None
        return run_l1(args.out, seeds=parse_seeds(args.seeds or options.get("seeds", "200:220")),
                      acquisition_episodes=options.get("acquisition_episodes", 40),
                      adaptation_episodes=options.get("adaptation_episodes", 40),
                      bootstrap_samples=options.get("bootstrap_samples", 2000),
                      config=config if "agent" in data else None, task=task)
    if protocol == "E2":
        if set(options) - {"protocol", "seeds", "acquisition_episodes", "adaptation_episodes", "bootstrap_samples", "probe_trials"}:
            raise LabError("INVALID_INPUT", "unknown E2 protocol setting")
        from .capability_experiment import run_e2
        task = TaskConfig.from_dict(data["task"]) if "task" in data else None
        return run_e2(args.out, seeds=parse_seeds(args.seeds or options.get("seeds", "300:320")),
                      acquisition_episodes=options.get("acquisition_episodes", 40),
                      adaptation_episodes=options.get("adaptation_episodes", 40),
                      bootstrap_samples=options.get("bootstrap_samples", 2000),
                      probe_trials=options.get("probe_trials", 100),
                      config=config if "agent" in data else None, task=task)
    raise LabError("INVALID_INPUT", "protocol must be E0, E1, L1 or E2")


def main(argv=None):
    arguments = sys.argv[1:] if argv is None else list(argv)
    if arguments and arguments[0] == "life":
        from .identity_cli import main as identity_main
        return identity_main(arguments[1:])
    args = parser().parse_args(arguments)
    try:
        result = dispatch(args)
        print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
        failed = isinstance(result, dict) and (result.get("valid") is False or result.get("status") in {"failed", "incomplete"})
        return 1 if failed else 0
    except (LabError, OSError, sqlite3.Error, ValueError, TypeError) as error:
        print(json.dumps({"error": {"code": getattr(error, "code", "IO_OR_INPUT_ERROR"), "message": str(error)}}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
