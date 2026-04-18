"""Load and validate config.yaml into a Config dataclass."""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

import yaml


def _find_config_path() -> Path:
    env = os.environ.get("FEYNMAN_CONFIG")
    if env:
        p = Path(env)
        if p.exists():
            return p
        print(f"ERROR: FEYNMAN_CONFIG={env} does not exist.", file=sys.stderr)
        sys.exit(1)

    cwd_cfg = Path.cwd() / "config.yaml"
    if cwd_cfg.exists():
        return cwd_cfg

    pkg_root = Path(__file__).parents[2]
    pkg_cfg = pkg_root / "config.yaml"
    if pkg_cfg.exists():
        return pkg_cfg

    print(
        "ERROR: config.yaml not found.\n"
        "  - Set FEYNMAN_CONFIG=/path/to/config.yaml, or\n"
        "  - Run feynman from the project directory.",
        file=sys.stderr,
    )
    sys.exit(1)


@dataclass
class PlaylistConfig:
    id: str
    notebook: str = ""  # optional override; if blank, uses the playlist title from RSS


@dataclass
class Config:
    playlists: list[PlaylistConfig] = field(default_factory=list)
    poll_interval_seconds: int = 900
    nlm_path: str = ""
    log_level: str = "INFO"


def load_config(path: Path | None = None) -> Config:
    cfg_path = path or _find_config_path()
    with open(cfg_path) as f:
        raw = yaml.safe_load(f) or {}

    cfg = Config()

    raw_playlists = raw.get("playlists", [])
    for entry in raw_playlists:
        if isinstance(entry, str):
            cfg.playlists.append(PlaylistConfig(id=entry))
        elif isinstance(entry, dict):
            cfg.playlists.append(PlaylistConfig(
                id=entry.get("id", ""),
                notebook=entry.get("notebook", ""),
            ))

    poll = raw.get("polling", {})
    cfg.poll_interval_seconds = int(poll.get("interval_seconds", cfg.poll_interval_seconds))

    nlm = raw.get("nlm", {})
    cfg.nlm_path = nlm.get("path", cfg.nlm_path) or ""

    log = raw.get("logging", {})
    cfg.log_level = log.get("level", cfg.log_level).upper()

    if not cfg.playlists:
        print(
            "WARNING: no playlists configured in config.yaml. Nothing to watch.",
            file=sys.stderr,
        )

    return cfg
