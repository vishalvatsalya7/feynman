"""SQLite state management for feynman."""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Generator

DB_PATH = Path.home() / ".feynman" / "state.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS processed_items (
    id           TEXT PRIMARY KEY,
    source_type  TEXT NOT NULL,
    url          TEXT NOT NULL,
    title        TEXT,
    topic_label  TEXT,
    notebook_id  TEXT,
    created_at   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS notebook_cache (
    title       TEXT PRIMARY KEY,
    notebook_id TEXT NOT NULL,
    synced_at   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS poll_state (
    key   TEXT PRIMARY KEY,
    value TEXT
);

"""


@contextmanager
def _conn() -> Generator[sqlite3.Connection, None, None]:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    try:
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


def init_db() -> None:
    with _conn() as con:
        con.executescript(_SCHEMA)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── processed items ──────────────────────────────────────────────────────────

def is_processed(item_id: str) -> bool:
    with _conn() as con:
        row = con.execute(
            "SELECT 1 FROM processed_items WHERE id = ?", (item_id,)
        ).fetchone()
        return row is not None


def mark_processed(
    item_id: str,
    source_type: str,
    url: str,
    title: str | None,
    topic_label: str | None,
    notebook_id: str | None,
) -> None:
    with _conn() as con:
        con.execute(
            """INSERT OR IGNORE INTO processed_items
               (id, source_type, url, title, topic_label, notebook_id, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (item_id, source_type, url, title, topic_label, notebook_id, _now()),
        )


def mark_seen_without_processing(item_id: str, source_type: str, url: str) -> None:
    """Mark an item as seen on first run (to avoid bulk backfill) without topic/notebook."""
    mark_processed(item_id, source_type, url, None, None, None)


def get_recent_processed(limit: int = 10) -> list[dict]:
    with _conn() as con:
        rows = con.execute(
            "SELECT * FROM processed_items ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]


# ── notebook cache ────────────────────────────────────────────────────────────

def get_notebook_cache() -> dict[str, str]:
    with _conn() as con:
        rows = con.execute("SELECT title, notebook_id FROM notebook_cache").fetchall()
        return {r["title"]: r["notebook_id"] for r in rows}


def set_notebook_cache(title: str, notebook_id: str) -> None:
    with _conn() as con:
        con.execute(
            """INSERT OR REPLACE INTO notebook_cache (title, notebook_id, synced_at)
               VALUES (?, ?, ?)""",
            (title, notebook_id, _now()),
        )


def refresh_notebook_cache(notebooks: dict[str, str]) -> None:
    """Replace all notebook cache entries with a fresh dict."""
    with _conn() as con:
        con.execute("DELETE FROM notebook_cache")
        now = _now()
        con.executemany(
            "INSERT INTO notebook_cache (title, notebook_id, synced_at) VALUES (?, ?, ?)",
            [(title, nb_id, now) for title, nb_id in notebooks.items()],
        )


# ── poll state ────────────────────────────────────────────────────────────────

def get_poll_state(key: str) -> str | None:
    with _conn() as con:
        row = con.execute(
            "SELECT value FROM poll_state WHERE key = ?", (key,)
        ).fetchone()
        return row["value"] if row else None


def set_poll_state(key: str, value: str) -> None:
    with _conn() as con:
        con.execute(
            "INSERT OR REPLACE INTO poll_state (key, value) VALUES (?, ?)",
            (key, value),
        )


