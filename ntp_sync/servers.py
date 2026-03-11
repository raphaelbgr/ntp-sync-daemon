"""Trusted NTP server pool with round-robin rotation."""

from itertools import cycle
from typing import Iterator

# Ordered by trust/reliability. Round-robin distributes load evenly.
NTP_SERVERS = [
    "time.nist.gov",         # NIST (US)
    "time.google.com",       # Google
    "time.cloudflare.com",   # Cloudflare
    "time.apple.com",        # Apple
    "time.windows.com",      # Microsoft
    "time.nist.gov",         # NIST (repeated for weight)
    "0.pool.ntp.org",        # NTP Pool
    "1.pool.ntp.org",
    "2.pool.ntp.org",
    "3.pool.ntp.org",
]


def server_pool() -> Iterator[str]:
    """Infinite round-robin iterator over NTP servers."""
    return cycle(NTP_SERVERS)
