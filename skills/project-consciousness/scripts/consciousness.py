#!/usr/bin/env python3
"""Run the installed project's life CLI without changing the caller's cwd."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys


PROJECT_ENV = "PROJECT_CONSCIOUSNESS_HOME"


def is_project(path: Path) -> bool:
    package = path / "project_consciousness"
    return all((package / name).is_file() for name in ("__init__.py", "__main__.py"))


def resolve_project(explicit: str | None = None) -> Path:
    """Honor an explicit locator; auto-detect only around this skill's checkout."""
    location = explicit if explicit is not None else os.environ.get(PROJECT_ENV)
    if location is not None:
        if not location.strip():
            raise ValueError("La ruta del proyecto no puede estar vacía.")
        candidate = Path(location).expanduser().resolve()
        if not is_project(candidate):
            raise ValueError(f"No se encontró el paquete project_consciousness en {candidate}.")
        return candidate
    for candidate in Path(__file__).resolve().parents:
        if is_project(candidate):
            return candidate
    raise ValueError(
        f"Indica --project PATH o {PROJECT_ENV} con la raíz del checkout de PROJECT CONSCIOUSNESS."
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Ejecuta el CLI life de PROJECT CONSCIOUSNESS con el Python actual.",
        epilog="Para ayuda de life: consciousness.py --project PATH -- --help",
    )
    parser.add_argument("--project", metavar="PATH", help=f"Raíz del checkout; precede a {PROJECT_ENV}.")
    parser.add_argument("life_args", nargs=argparse.REMAINDER, help="Comando life y sus argumentos.")
    args = parser.parse_args(argv)
    forwarded = args.life_args
    if forwarded and forwarded[0] == "--":
        forwarded = forwarded[1:]
    if not forwarded:
        parser.print_help()
        return 2
    try:
        if sys.version_info < (3, 12):
            raise ValueError("El proyecto requiere Python 3.12 o posterior.")
        project = resolve_project(args.project)
        environment = os.environ.copy()
        previous = environment.get("PYTHONPATH")
        environment["PYTHONPATH"] = str(project) + (os.pathsep + previous if previous else "")
        # -P prevents a package in the caller's cwd from shadowing --project.
        process = subprocess.run(
            [sys.executable, "-P", "-m", "project_consciousness", "life", *forwarded],
            env=environment,
            check=False,
        )
        return process.returncode
    except KeyboardInterrupt:
        return 130
    except (ValueError, OSError) as exc:
        print(json.dumps({"error": {"code": "INVALID_PROJECT", "message": str(exc)}}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
