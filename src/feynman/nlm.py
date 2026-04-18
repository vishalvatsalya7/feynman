"""Subprocess wrapper around the `nlm` CLI (notebooklm-mcp-cli)."""
from __future__ import annotations

import json
import logging
import shutil
import subprocess
from typing import Any

from feynman.config import Config

log = logging.getLogger(__name__)


def _nlm_bin(cfg: Config) -> str:
    if cfg.nlm_path:
        return cfg.nlm_path
    found = shutil.which("nlm")
    if not found:
        raise FileNotFoundError(
            "`nlm` binary not found in PATH. "
            "Install it with: pip install notebooklm-mcp-cli"
        )
    return found


def _run(args: list[str], cfg: Config) -> subprocess.CompletedProcess[str]:
    bin_ = _nlm_bin(cfg)
    cmd = [bin_] + args
    log.debug("nlm: %s", " ".join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
    if result.returncode != 0:
        raise RuntimeError(
            f"`nlm {' '.join(args)}` exited {result.returncode}:\n"
            f"stdout: {result.stdout[:500]}\n"
            f"stderr: {result.stderr[:500]}"
        )
    return result


def list_notebooks(cfg: Config) -> dict[str, str]:
    """Return {title: notebook_id} for all existing notebooks."""
    result = _run(["notebook", "list", "--json"], cfg)
    try:
        data: Any = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"Could not parse `nlm notebook list --json` output: {exc}\n"
            f"Raw output: {result.stdout[:300]}"
        ) from exc

    # notebooklm-mcp-cli returns a list of objects with at least {id, title}
    notebooks: dict[str, str] = {}
    for nb in data:
        title = nb.get("title") or nb.get("name") or ""
        nb_id = nb.get("id") or nb.get("notebookId") or ""
        if title and nb_id:
            notebooks[title] = nb_id
    return notebooks


def create_notebook(title: str, cfg: Config) -> str:
    """Create a notebook and return its ID."""
    _run(["notebook", "create", title], cfg)
    # nlm doesn't reliably return the new ID on stdout, so we re-list
    notebooks = list_notebooks(cfg)
    nb_id = notebooks.get(title)
    if not nb_id:
        raise RuntimeError(
            f"Notebook '{title}' was not found after creation. "
            "The nlm command may have failed silently."
        )
    log.info("Created NLM notebook: %r → %s", title, nb_id)
    return nb_id


def add_url_source(notebook_id: str, url: str, cfg: Config) -> None:
    """Add a generic URL source to a notebook."""
    _run(["source", "add", notebook_id, "--url", url], cfg)
    log.info("Added URL source to notebook %s: %s", notebook_id, url[:80])


def add_youtube_source(notebook_id: str, url: str, cfg: Config) -> None:
    """Add a YouTube video source to a notebook."""
    _run(["source", "add", notebook_id, "--youtube", url], cfg)
    log.info("Added YouTube source to notebook %s: %s", notebook_id, url[:80])
