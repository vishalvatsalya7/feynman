"""Generate and install the macOS launchd plist for the feynman service."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

from feynman.config import load_config

_PLIST_LABEL = "com.feynman.service"
_PLIST_PATH = Path.home() / "Library" / "LaunchAgents" / f"{_PLIST_LABEL}.plist"

_PLIST_TEMPLATE = """\
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
    "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{label}</string>

    <key>ProgramArguments</key>
    <array>
        <string>{uv_bin}</string>
        <string>run</string>
        <string>--project</string>
        <string>{project_dir}</string>
        <string>python</string>
        <string>-m</string>
        <string>feynman</string>
        <string>run</string>
    </array>

    <key>EnvironmentVariables</key>
    <dict>
        <key>HOME</key>
        <string>{home}</string>
        <key>PATH</key>
        <string>{path}</string>
    </dict>

    <key>StartInterval</key>
    <integer>{interval_seconds}</integer>

    <key>RunAtLoad</key>
    <false/>

    <key>StandardOutPath</key>
    <string>{home}/.feynman/logs/launchd.stdout.log</string>

    <key>StandardErrorPath</key>
    <string>{home}/.feynman/logs/launchd.stderr.log</string>

    <key>WorkingDirectory</key>
    <string>{project_dir}</string>
</dict>
</plist>
"""


def _project_root() -> Path:
    """Walk up from this file to the repo root (where pyproject.toml lives)."""
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "pyproject.toml").exists():
            return parent
    # Fallback: CWD
    return Path.cwd()


def install() -> None:
    cfg = load_config()

    uv_bin = shutil.which("uv")
    if not uv_bin:
        print(
            "[error] `uv` not found in PATH. Install it from https://docs.astral.sh/uv/",
            file=sys.stderr,
        )
        sys.exit(1)

    project_dir = _project_root()
    home = str(Path.home())
    path = os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin:/opt/homebrew/bin")

    # Ensure log dir exists before launchd tries to write to it
    (Path.home() / ".feynman" / "logs").mkdir(parents=True, exist_ok=True)

    plist_content = _PLIST_TEMPLATE.format(
        label=_PLIST_LABEL,
        uv_bin=uv_bin,
        project_dir=str(project_dir),
        home=home,
        path=path,
        interval_seconds=cfg.poll_interval_seconds,
    )

    _PLIST_PATH.parent.mkdir(parents=True, exist_ok=True)
    _PLIST_PATH.write_text(plist_content)
    print(f"[ok] Wrote plist to {_PLIST_PATH}")

    uid = os.getuid()
    domain = f"gui/{uid}"

    # Unload existing service if loaded (ignore errors)
    subprocess.run(
        ["launchctl", "bootout", f"{domain}/{_PLIST_LABEL}"],
        capture_output=True,
    )

    result = subprocess.run(
        ["launchctl", "bootstrap", domain, str(_PLIST_PATH)],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        print(
            f"[ok] Service installed and loaded.\n"
            f"     Runs every {cfg.poll_interval_seconds // 60} minute(s).\n"
            f"     Logs: ~/.feynman/logs/feynman.log"
        )
    else:
        print(
            f"[error] launchctl bootstrap failed:\n{result.stderr}",
            file=sys.stderr,
        )
        print(f"Try manually:\n  launchctl load {_PLIST_PATH}")


def uninstall() -> None:
    uid = os.getuid()
    domain = f"gui/{uid}"
    subprocess.run(
        ["launchctl", "bootout", f"{domain}/{_PLIST_LABEL}"],
        capture_output=True,
    )
    if _PLIST_PATH.exists():
        _PLIST_PATH.unlink()
        print(f"[ok] Removed {_PLIST_PATH}")
    print("[ok] Service uninstalled.")
