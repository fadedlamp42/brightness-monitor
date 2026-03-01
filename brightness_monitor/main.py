"""CLI entrypoint for brightness-monitor.

parses arguments, configures logging, loads config, and hands off
to the daemon loop. this is the only module that touches argparse.
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from brightness_monitor.config import load_config
from brightness_monitor.daemon import run_daemon

log = logging.getLogger("brightness_monitor")


def main():
    parser = argparse.ArgumentParser(
        description="sync MacBook keyboard brightness to Claude API usage",
    )
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="path to config.yaml (default: config.yaml in project root)",
    )
    parser.add_argument(
        "--token",
        type=str,
        default=None,
        help="OAuth token (overrides env var and Keychain lookup)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="log what would happen without touching brightness",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="enable debug logging",
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )

    config_path = Path(args.config) if args.config else None
    config = load_config(config_path)

    kb = config.output.keyboard
    log.info(
        "config: window=%(window)s, poll=%(poll)ds, "
        "output: speech=%(speech)s keyboard=%(keyboard)s",
        {
            "window": config.window,
            "poll": config.poll_interval,
            "speech": config.output.speech,
            "keyboard": kb.enabled,
        },
    )
    if kb.enabled:
        log.info(
            "keyboard: fade=%(fade)d, pulse<%(pulse).0f%%, "
            "readout every %(every).0f%% below %(thresh).0f%%",
            {
                "fade": kb.fade_speed,
                "pulse": kb.pulse_threshold,
                "every": kb.readout.every_percent,
                "thresh": kb.readout.threshold,
            },
        )

    run_daemon(
        config=config,
        dry_run=args.dry_run,
        token_override=args.token,
    )


if __name__ == "__main__":
    main()
