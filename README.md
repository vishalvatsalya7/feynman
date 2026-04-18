```
  ███████╗███████╗██╗   ██╗███╗   ██╗███╗   ███╗ █████╗ ███╗   ██╗
  ██╔════╝██╔════╝╚██╗ ██╔╝████╗  ██║████╗ ████║██╔══██╗████╗  ██║
  █████╗  █████╗   ╚████╔╝ ██╔██╗ ██║██╔████╔██║███████║██╔██╗ ██║
  ██╔══╝  ██╔══╝    ╚██╔╝  ██║╚██╗██║██║╚██╔╝██║██╔══██║██║╚██╗██║
  ██║     ███████╗   ██║   ██║ ╚████║██║ ╚═╝ ██║██║  ██║██║ ╚████║
  ╚═╝     ╚══════╝   ╚═╝   ╚═╝  ╚═══╝╚═╝     ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝
```

A macOS background service that watches your YouTube playlists and automatically adds new videos as sources into matching [NotebookLM](https://notebooklm.google.com) notebooks — one notebook per playlist, named after the playlist.

No Google Cloud account, no API keys, no AI services needed.

---

## How it works

```
YouTube playlists (RSS feed, no API key)
        │
        ▼
  New video added to playlist?
        │
        ▼
  NotebookLM notebook exists for this playlist?
  ├── Yes → add video as source
  └── No  → create notebook (named after playlist), then add video
        │
        ▼
  Saved to state.db (won't process again)
```

Each playlist maps 1-to-1 to a NotebookLM notebook. The notebook name is taken directly from the playlist's title on YouTube (configurable override available).

The service runs as a **launchd agent** on a timer. It polls every 15 minutes (configurable) whenever your Mac is awake.

---

## Features

- **Multiple playlist support** — watch any number of YouTube playlists simultaneously, each routed to its own NotebookLM notebook.
- **Playlist name as notebook name** — the NotebookLM project is named after your YouTube playlist title automatically. No manual setup.
- **Auto-creates notebooks** — if the notebook doesn't exist yet in NotebookLM, it is created on the first new video.
- **No API quota** — uses YouTube's public RSS/Atom feed. No Google Cloud project, no OAuth, no quota limits.
- **Deduplication** — every processed video is recorded in a local SQLite database. Re-running never creates duplicates.
- **macOS launchd service** — runs silently in the background. Starts automatically on login with no terminal open.
- **Configurable** — polling interval, notebook name overrides, and `nlm` CLI path are set in a single `config.yaml`.

---

## Prerequisites

| Requirement | Install |
|---|---|
| Python 3.11+ | [python.org](https://python.org) or `brew install python` |
| [uv](https://docs.astral.sh/uv/) | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| [notebooklm-mcp-cli](https://github.com/jacob-bd/notebooklm-mcp-cli) | `pip install notebooklm-mcp-cli` |

---

## Setup

**1. Install dependencies**

```bash
cd feynman
uv sync
```

**2. Authenticate NotebookLM**

```bash
nlm login
```

Opens a browser and links your Google account to the `nlm` CLI. Only needed once.

**3. Edit `config.yaml`**

Add your YouTube playlist IDs (copy from the playlist URL — starts with `PL`):

```yaml
playlists:
  - id: "PLxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
  - id: "PLyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy"
```

Playlist titles are fetched automatically from YouTube — no need to type them.

**4. Verify setup**

```bash
uv run python -m feynman setup
```

This confirms each RSS feed is reachable and shows the NotebookLM notebook name that will be used:

```
[YouTube RSS feeds] (2 configured)
  [ok] PLxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
       Playlist title : 'AI Research'
       NotebookLM name: 'AI Research'
  [ok] PLyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy
       Playlist title : 'Quant Stuff'
       NotebookLM name: 'Quant Stuff'
```

**5. Run one cycle manually**

```bash
uv run python -m feynman run
```

Existing videos in the playlist are added to NotebookLM immediately. Any video added to the playlist going forward is picked up on the next poll.

> Note: YouTube's RSS feed can take a few minutes to reflect newly added videos. If a fresh addition isn't picked up right away, just wait and re-run.

**6. Install the background service**

```bash
uv run python -m feynman install-service
```

The service is now installed and running. It polls every 15 minutes and restarts automatically on login.

---

## Commands

| Command | Description |
|---|---|
| `uv run python -m feynman run` | Run one poll cycle right now |
| `uv run python -m feynman setup` | Verify RSS feeds and nlm CLI |
| `uv run python -m feynman install-service` | Install + start the launchd background service |
| `uv run python -m feynman uninstall-service` | Stop + remove the launchd service |
| `uv run python -m feynman status` | Show the last 10 processed videos |

---

## Configuration (`config.yaml`)

```yaml
playlists:
  - id: "PLxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"       # required: playlist ID from YouTube URL
  - id: "PLyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy"
    notebook: "My Custom Name"                   # optional: override the notebook name

polling:
  interval_seconds: 900    # how often to check (default: 15 min)

nlm:
  path: ""                 # path to nlm binary; blank = auto-detect via PATH

logging:
  level: "INFO"            # DEBUG | INFO | WARNING | ERROR
```

Changes to `config.yaml` take effect on the next poll cycle — no restart needed.

---

## Playlist requirements

- The playlist must be set to **Public** on YouTube. Private and Unlisted playlists are not accessible via RSS.
- **Watch Later** and **Liked Videos** are private system playlists and cannot be used. Create a regular named playlist instead.

**Finding your playlist ID:**

```
https://www.youtube.com/playlist?list=PLBXpeaigbfvR_BhtcnyvDzizWXJnyypqB
                                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                                       copy this as your playlist id
```

---

## Logs and state

| Path | Contents |
|---|---|
| `~/.feynman/state.db` | SQLite — processed videos, notebook cache, poll timestamps |
| `~/.feynman/logs/feynman.log` | Rotating app log (10 MB × 5 files) |
| `~/.feynman/logs/launchd.stdout.log` | stdout captured by launchd |
| `~/.feynman/logs/launchd.stderr.log` | stderr captured by launchd |

```bash
# Follow the live log
tail -f ~/.feynman/logs/feynman.log

# Check service status
launchctl list | grep feynman
```

---

## Running while the Mac is sleeping

The launchd service only runs while the Mac is **awake**. Options:

- **Prevent system sleep** — System Settings → Battery → prevent system sleep when plugged in (display can still sleep).
- **Power Nap** — System Settings → Battery → Enable Power Nap. macOS wakes briefly every ~1 hour to run background tasks including this service.
- **Cloud VM** — deploy feynman on an always-on server. Replace `install-service` (launchd) with a systemd service on Linux.

---

## Resetting state

To reprocess all videos from scratch (e.g. after deleting a notebook):

```bash
rm ~/.feynman/state.db
uv run python -m feynman run
```

---

## Uninstalling

```bash
uv run python -m feynman uninstall-service
rm -rf ~/.feynman
```
