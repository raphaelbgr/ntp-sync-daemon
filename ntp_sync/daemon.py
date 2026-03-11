"""Main daemon loop with round-robin retry logic."""

import argparse
import logging
import signal
import sys
import time

from . import __version__
from .servers import NTP_SERVERS, server_pool
from .sync import query_ntp, set_system_time

logger = logging.getLogger("ntp-sync")

# Minimum offset threshold (ms) to bother adjusting the clock
MIN_OFFSET_MS = 10.0


def setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    )
    root = logging.getLogger("ntp-sync")
    root.setLevel(level)
    root.addHandler(handler)


def sync_once(
    pool_iter,
    retry_delay: float,
    dry_run: bool,
) -> bool:
    """Try each server in round-robin until one succeeds.

    Tries up to len(NTP_SERVERS) servers before giving up for this cycle.
    Returns True if sync succeeded.
    """
    attempts = len(NTP_SERVERS)
    for _ in range(attempts):
        server = next(pool_iter)
        try:
            offset = query_ntp(server)
            offset_ms = abs(offset) * 1000

            if offset_ms < MIN_OFFSET_MS:
                logger.info(
                    "Clock is accurate (offset=%.2fms from %s), no adjustment needed",
                    offset_ms,
                    server,
                )
                return True

            if dry_run:
                logger.info(
                    "[DRY RUN] Would adjust by %.6fs (%.2fms) from %s",
                    offset,
                    offset_ms,
                    server,
                )
            else:
                set_system_time(offset)
                logger.info(
                    "Synced from %s (offset was %.2fms)", server, offset_ms
                )
            return True

        except Exception as e:
            logger.warning("Failed to sync from %s: %s", server, e)
            time.sleep(retry_delay)

    return False


def run_daemon(
    interval: float,
    retry_delay: float,
    dry_run: bool,
) -> None:
    """Main daemon loop. Syncs on start, then every `interval` seconds."""
    pool_iter = server_pool()
    running = True

    def handle_signal(signum, frame):
        nonlocal running
        logger.info("Received signal %d, shutting down...", signum)
        running = False

    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    logger.info(
        "ntp-sync-daemon v%s started | interval=%ds retry=%ds dry_run=%s",
        __version__,
        interval,
        retry_delay,
        dry_run,
    )

    while running:
        success = sync_once(pool_iter, retry_delay, dry_run)

        if not success:
            logger.error(
                "All %d servers failed. Retrying in %ds...",
                len(NTP_SERVERS),
                retry_delay,
            )
            time.sleep(retry_delay)
            continue

        # Sleep in small chunks so we can respond to signals
        elapsed = 0.0
        while running and elapsed < interval:
            chunk = min(5.0, interval - elapsed)
            time.sleep(chunk)
            elapsed += chunk


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="ntp-sync-daemon",
        description="Cross-platform NTP time sync daemon with round-robin redundancy",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=3600,
        help="Sync interval in seconds (default: 3600 = 1 hour)",
    )
    parser.add_argument(
        "--retry-delay",
        type=int,
        default=30,
        help="Delay between retries on failure in seconds (default: 30)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Query servers but don't adjust system clock",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable debug logging",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    setup_logging(args.verbose)
    run_daemon(
        interval=args.interval,
        retry_delay=args.retry_delay,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
