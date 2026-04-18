"""Entry point: python -m feynman <command>"""
from __future__ import annotations

import sys


def main() -> None:
    from feynman import log as _log
    from feynman.config import load_config

    cfg = load_config()
    _log.init(cfg.log_level)

    cmd = sys.argv[1] if len(sys.argv) > 1 else "run"

    if cmd == "run":
        backfill = "--backfill" in sys.argv
        from feynman.pipeline import run_once
        run_once(backfill=backfill)

    elif cmd == "setup":
        from feynman.setup import run_setup
        run_setup()

    elif cmd == "install-service":
        from feynman.service import install
        install()

    elif cmd == "uninstall-service":
        from feynman.service import uninstall
        uninstall()

    elif cmd == "status":
        from feynman.pipeline import print_status
        print_status()

    else:
        print(
            "Usage: python -m feynman <command>\n\n"
            "Commands:\n"
            "  run [--backfill]   Run one poll cycle (backfill ingests existing items)\n"
            "  setup              One-time setup: cookies, YouTube OAuth, Ollama check\n"
            "  install-service    Install and load the macOS launchd service\n"
            "  uninstall-service  Stop and remove the launchd service\n"
            "  status             Show recently processed items\n",
            file=sys.stderr,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
