"""Logging setup: rotating file at ~/.feynman/logs/ + stdout."""
from __future__ import annotations

import logging
import logging.handlers
from pathlib import Path


def init(level: str = "INFO") -> None:
    log_dir = Path.home() / ".feynman" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    fmt = logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")

    # Rotating file handler: 10 MB × 5 backups
    fh = logging.handlers.RotatingFileHandler(
        log_dir / "feynman.log",
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    fh.setFormatter(fmt)
    root.addHandler(fh)

    # Stdout handler (launchd captures this to its own log)
    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    root.addHandler(sh)
