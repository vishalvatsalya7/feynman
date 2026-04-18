"""One-time setup: verify RSS feeds and nlm CLI."""
from __future__ import annotations

from feynman import db
from feynman.config import load_config


def run_setup() -> None:
    cfg = load_config()
    db.init_db()

    print("=== Feynman Setup ===\n")
    _ensure_feynman_dir()
    _check_playlists(cfg)
    _check_nlm(cfg)

    print(
        "\nSetup complete.\n"
        "Next steps:\n"
        "  1. uv run python -m feynman run      # test one cycle\n"
        "  2. uv run python -m feynman install-service\n"
    )


def _ensure_feynman_dir() -> None:
    from pathlib import Path
    feynman_dir = Path.home() / ".feynman"
    (feynman_dir / "logs").mkdir(parents=True, exist_ok=True)
    print(f"[ok] ~/.feynman directory ready at {feynman_dir}")


def _check_playlists(cfg) -> None:
    import requests
    print(f"\n[YouTube RSS feeds] ({len(cfg.playlists)} configured)")
    if not cfg.playlists:
        print("  [warning] No playlists configured in config.yaml")
        return
    for pl in cfg.playlists:
        url = f"https://www.youtube.com/feeds/videos.xml?playlist_id={pl.id}"
        try:
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                # Parse the playlist title from the feed
                import xml.etree.ElementTree as ET
                root = ET.fromstring(resp.text)
                title_el = root.find("{http://www.w3.org/2005/Atom}title")
                feed_title = title_el.text.strip() if title_el is not None and title_el.text else "(unknown)"
                notebook = pl.notebook.strip() if pl.notebook.strip() else feed_title
                print(f"  [ok] {pl.id}")
                print(f"       Playlist title : {feed_title!r}")
                print(f"       NotebookLM name: {notebook!r}")
            else:
                print(f"  [warning] {pl.id} → HTTP {resp.status_code} (check playlist ID)")
        except Exception as exc:
            print(f"  [error] {pl.id} → {exc}")


def _check_nlm(cfg) -> None:
    import shutil
    print("\n[nlm CLI]")
    nlm_bin = cfg.nlm_path or shutil.which("nlm")
    if nlm_bin:
        print(f"  [ok] nlm found at {nlm_bin}")
    else:
        print(
            "  [warning] `nlm` binary not found.\n"
            "  Install it: pip install notebooklm-mcp-cli\n"
            "  Then authenticate: nlm login"
        )
