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

    Requires elevated privileges (root/admin).
    """
    now = time.time() + offset
    dt = datetime.fromtimestamp(now, tz=timezone.utc)
    system = platform.system()

    if system == "Darwin":
        # macOS: use sntp or systemsetup
        date_str = dt.strftime("%m%d%H%M%Y.%S")
        subprocess.run(
            ["sudo", "-n", "date", date_str],
            check=True,
            capture_output=True,
        )

    elif system == "Linux":
        date_str = dt.strftime("%Y-%m-%d %H:%M:%S")
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
        # Windows: use w32tm or PowerShell
        date_str = dt.strftime("%m-%d-%Y")
        time_str = dt.strftime("%H:%M:%S")
        subprocess.run(
            ["powershell", "-Command",
             f"Set-Date -Date '{date_str} {time_str}'"],
            check=True,
            capture_output=True,
        )

    else:
        raise OSError(f"Unsupported platform: {system}")

    logger.info(
        "System clock adjusted by %.6fs -> %s (UTC)",
        offset,
        dt.strftime("%Y-%m-%d %H:%M:%S.%f"),
    )
