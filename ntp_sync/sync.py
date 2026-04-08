"""NTP time query and system clock adjustment."""

import logging
import ntplib
import platform
import subprocess
import time
from datetime import datetime, timezone

logger = logging.getLogger("ntp-sync")


def query_ntp(server: str, timeout: float = 5.0) -> float:
    """Query an NTP server and return the offset in seconds.

    Raises ntplib.NTPException or socket errors on failure.
    """
    client = ntplib.NTPClient()
    response = client.request(server, version=3, timeout=timeout)
    logger.debug(
        "Server %s | offset=%.6fs stratum=%d delay=%.6fs",
        server,
        response.offset,
        response.stratum,
        response.delay,
    )
    return response.offset


def set_system_time(offset: float) -> None:
    """Adjust the system clock by the given offset (seconds).

    NTP offset is relative to UTC (time.time()). Each platform's date command
    expects local time, so we convert to the system's local timezone before
    applying.

    Requires elevated privileges (root/admin).
    """
    now = time.time() + offset
    # Local time — what the OS date commands expect
    dt_local = datetime.fromtimestamp(now)
    # UTC — for logging
    dt_utc = datetime.fromtimestamp(now, tz=timezone.utc)
    system = platform.system()

    if system == "Darwin":
        # macOS date expects: MMDDhhmm[[CC]YY][.ss] in local time
        date_str = dt_local.strftime("%m%d%H%M%Y.%S")
        subprocess.run(
            ["sudo", "-n", "date", date_str],
            check=True,
            capture_output=True,
        )

    elif system == "Linux":
        date_str = dt_local.strftime("%Y-%m-%d %H:%M:%S")
        try:
            # Try timedatectl first (systemd)
            subprocess.run(
                ["sudo", "-n", "timedatectl", "set-ntp", "false"],
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["sudo", "-n", "timedatectl", "set-time", date_str],
                check=True,
                capture_output=True,
            )
        except (subprocess.CalledProcessError, FileNotFoundError):
            # Fallback to date command
            subprocess.run(
                ["sudo", "-n", "date", "-s", date_str],
                check=True,
                capture_output=True,
            )

    elif system == "Windows":
        # Use ISO 8601 format - unambiguous regardless of Windows locale
        # Avoids MM-DD vs DD-MM misparse on non-English locales (e.g. pt-BR)
        iso_str = dt_local.strftime("%Y-%m-%dT%H:%M:%S")
        subprocess.run(
            ["powershell", "-Command",
             f"Set-Date -Date '{iso_str}'"],
            check=True,
            capture_output=True,
        )

    else:
        raise OSError(f"Unsupported platform: {system}")

    logger.info(
        "System clock adjusted by %.6fs -> %s (local) / %s (UTC)",
        offset,
        dt_local.strftime("%Y-%m-%d %H:%M:%S"),
        dt_utc.strftime("%Y-%m-%d %H:%M:%S"),
    )
