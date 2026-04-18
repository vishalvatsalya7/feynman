"""
Main pipeline: poll → dispatch to NotebookLM.
"""
from __future__ import annotations

import logging

from feynman import db, nlm
from feynman.config import load_config
from feynman.poller.youtube import YouTubeItem, fetch_new_playlist_items

log = logging.getLogger(__name__)


def run_once(backfill: bool = False) -> None:
    """Run one full poll cycle."""
    cfg = load_config()
    db.init_db()

    # Refresh the notebook cache once per cycle
    try:
        notebooks: dict[str, str] = nlm.list_notebooks(cfg)
        db.refresh_notebook_cache(notebooks)
        log.debug("Notebook cache refreshed: %d entries", len(notebooks))
    except Exception as exc:
        log.error("Failed to list NLM notebooks: %s", exc)
        notebooks = db.get_notebook_cache()
        log.warning("Using stale notebook cache (%d entries)", len(notebooks))

    # Collect new items across all playlists
    new_items: list[YouTubeItem] = []
    try:
        new_items += fetch_new_playlist_items(cfg)
    except Exception as exc:
        log.error("YouTube poll failed: %s", exc)

    if not new_items:
        log.info("No new items this cycle.")
        return

    log.info("Processing %d new item(s)...", len(new_items))

    for item in new_items:
        try:
            _process_item(item, notebooks, cfg)
        except Exception as exc:
            log.error("Failed to process %s: %s", item.url, exc)
            # Do NOT mark as processed — will retry next cycle


def _process_item(item: YouTubeItem, notebooks: dict[str, str], cfg) -> None:
    notebook_name = item.notebook_name

    # Resolve or create notebook
    notebook_id = notebooks.get(notebook_name)
    if not notebook_id:
        notebook_id = nlm.create_notebook(notebook_name, cfg)
        notebooks[notebook_name] = notebook_id
        db.set_notebook_cache(notebook_name, notebook_id)

    # Add source to NotebookLM
    nlm.add_youtube_source(notebook_id, item.url, cfg)

    # Persist
    db.mark_processed(item.video_id, "youtube", item.url, item.title, notebook_name, notebook_id)
    log.info(
        "Processed [youtube] %s → notebook '%s'",
        item.video_id,
        notebook_name,
    )


def print_status() -> None:
    """Print recent processed items."""
    db.init_db()
    items = db.get_recent_processed(limit=10)
    if not items:
        print("No items processed yet.")
        return
    print(f"{'Video ID':<25} {'Notebook':<30} {'Processed At'}")
    print("-" * 75)
    for it in items:
        print(
            f"{it['id'][:24]:<25} "
            f"{(it['topic_label'] or '—')[:29]:<30} "
            f"{it['created_at'][:19]}"
        )
