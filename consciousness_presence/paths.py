"""Locations for private state, independent of working directory and skill upgrades."""

import os
from pathlib import Path


def resolve_home(explicit=None):
    value = explicit if explicit is not None else os.environ.get("PROJECT_CONSCIOUSNESS_PRESENCE_HOME")
    if value is not None and not str(value).strip():
        raise ValueError("Presence home cannot be empty")
    return Path(value).expanduser().resolve() if value is not None else Path.home() / ".project-consciousness" / "presence"
