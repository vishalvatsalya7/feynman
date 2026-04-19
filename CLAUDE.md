# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
uv sync                                      # install dependencies
uv run python -m feynman run                 # one poll cycle
uv run python -m feynman run --backfill      # ingest all existing playlist videos
uv run python -m feynman setup               # verify RSS feeds + nlm CLI
uv run python -m feynman install-service     # install macOS launchd agent
uv run python -m feynman uninstall-service   # remove launchd agent
uv run python -m feynman status              # show last 10 processed videos
uv run pytest                                # run tests
FEYNMAN_CONFIG=/path/to/config.yaml uv run python -m feynman run  # custom config
```

## Architecture

Feynman is a macOS background service that bridges YouTube playlists → NotebookLM notebooks. Each playlist maps 1-to-1 to a NotebookLM notebook (named after the playlist title, with optional override).

**Data flow per poll cycle (`pipeline.py:run_once`):**
1. Load `config.yaml` → `Config` dataclass (`config.py`)
2. Call `nlm notebook list --json` → refresh in-memory + SQLite notebook cache
3. Poll each configured playlist via YouTube's public Atom RSS feed (no API key) → filter out already-processed video IDs
4. For each new video: resolve or create the target notebook, call `nlm source add --youtube <url>`, persist to SQLite

**Key modules:**
- `pipeline.py` — orchestrator; `run_once()` is the main entry point
- `poller/youtube.py` — Atom feed fetcher; `YouTubeItem` dataclass; per-playlist poll-gap guard stored in `poll_state` table
- `nlm.py` — thin subprocess wrapper around the `nlm` CLI (notebooklm-mcp-cli); all NotebookLM operations go through here
- `db.py` — SQLite at `~/.feynman/state.db`; three tables: `processed_items`, `notebook_cache`, `poll_state`
- `service.py` — generates and loads/unloads a launchd plist at `~/Library/LaunchAgents/com.feynman.service.plist`
- `config.py` — resolves config path via `FEYNMAN_CONFIG` env var → CWD → package root

**Config resolution order:** `FEYNMAN_CONFIG` env var → `./config.yaml` → `<package_root>/config.yaml`

**Error handling convention:** failed items are NOT marked processed — they retry next cycle. Failed notebook listing falls back to stale SQLite cache.

**External dependency:** `nlm` CLI (`notebooklm-mcp-cli`) must be installed and authenticated (`nlm login`) separately; feynman wraps it via subprocess with a 90s timeout.
