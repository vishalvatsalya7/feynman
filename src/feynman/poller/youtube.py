"""Poll YouTube playlists for new videos via public RSS/Atom feeds.

No API key, no OAuth, no quota — YouTube exposes Atom feeds for all playlists:
  https://www.youtube.com/feeds/videos.xml?playlist_id=<ID>
"""
from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timezone

import requests

from feynman import db
from feynman.config import Config, PlaylistConfig

log = logging.getLogger(__name__)

_FEED_URL = "https://www.youtube.com/feeds/videos.xml?playlist_id={playlist_id}"
_NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "yt": "http://www.youtube.com/xml/schemas/2015",
    "media": "http://search.yahoo.com/mrss/",
}


@dataclass
class YouTubeItem:
    video_id: str
    url: str
    title: str
    notebook_name: str  # the NotebookLM project name for this item


def _fetch_feed(playlist_id: str) -> tuple[str, list[YouTubeItem]]:
    """
    Fetch the RSS feed for a playlist.
    Returns (playlist_title, items).
    """
    url = _FEED_URL.format(playlist_id=playlist_id)
    resp = requests.get(url, timeout=15, headers={"User-Agent": "feynman/1.0"})
    resp.raise_for_status()

    root = ET.fromstring(resp.text)

    # Playlist title is the feed's top-level <title> element
    title_el = root.find("atom:title", _NS)
    playlist_title = title_el.text.strip() if title_el is not None and title_el.text else playlist_id

    items: list[YouTubeItem] = []
    for entry in root.findall("atom:entry", _NS):
        video_id_el = entry.find("yt:videoId", _NS)
        video_title_el = entry.find("atom:title", _NS)
        link_el = entry.find("atom:link", _NS)

        if video_id_el is None:
            continue

        video_id = video_id_el.text or ""
        video_title = video_title_el.text if video_title_el is not None else ""
        video_url = (
            link_el.get("href")
            if link_el is not None
            else f"https://www.youtube.com/watch?v={video_id}"
        )
        # notebook_name is set after we know the playlist title
        items.append(YouTubeItem(
            video_id=video_id,
            url=video_url,
            title=video_title,
            notebook_name="",
        ))

    return playlist_title, items


def _poll_playlist(playlist: PlaylistConfig, cfg: Config) -> list[YouTubeItem]:
    """Poll a single playlist and return new (unseen) items."""
    poll_key = f"youtube_last_poll_ts_{playlist.id}"

    # Guard: skip if polled too recently
    last_poll = db.get_poll_state(poll_key)
    if last_poll:
        elapsed = (
            datetime.now(timezone.utc) - datetime.fromisoformat(last_poll)
        ).total_seconds()
        min_gap = max(cfg.poll_interval_seconds - 60, 60)
        if elapsed < min_gap:
            log.info(
                "[%s] poll skipped — last ran %.0fs ago (min gap %ds).",
                playlist.id, elapsed, min_gap,
            )
            return []

    try:
        playlist_title, all_items = _fetch_feed(playlist.id)
    except Exception as exc:
        log.error("[%s] RSS fetch failed: %s", playlist.id, exc)
        return []

    db.set_poll_state(poll_key, datetime.now(timezone.utc).isoformat())

    # Use config override if provided, else the RSS feed title
    notebook_name = playlist.notebook.strip() if playlist.notebook.strip() else playlist_title
    for item in all_items:
        item.notebook_name = notebook_name

    new_items = [i for i in all_items if not db.is_processed(i.video_id)]
    log.info("[%s] %d new item(s) found (notebook: '%s')", playlist.id, len(new_items), notebook_name)
    return new_items


def fetch_new_playlist_items(cfg: Config) -> list[YouTubeItem]:
    """Poll all configured playlists and return new items across all of them."""
    new_items: list[YouTubeItem] = []
    for playlist in cfg.playlists:
        if not playlist.id:
            continue
        try:
            new_items += _poll_playlist(playlist, cfg)
        except Exception as exc:
            log.error("Unexpected error polling playlist %s: %s", playlist.id, exc)
    return new_items
