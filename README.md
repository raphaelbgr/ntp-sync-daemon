# ntp-sync-daemon

Cross-platform NTP time synchronization daemon with round-robin server redundancy.

Syncs your system clock against trusted NTP servers on a configurable interval, retrying indefinitely on failure with automatic server rotation.

## Use Case: Dead CMOS Battery

If your machine has a dead or dying CMOS battery (the CR2032 coin cell on the motherboard), the hardware clock resets to a wrong date every time the computer loses power. The OS's built-in time service (w32time, systemd-timesyncd, timed) typically only nudges the clock by small amounts and may refuse to jump large deltas — leaving you stuck with a date months in the past or future until you manually intervene.

`ntp-sync-daemon` is designed to handle exactly this situation:

- **Corrects large jumps** — no minimum offset cap; will correct a clock that is days, months, or years wrong
- **Runs at startup** — scheduled task / launchd / systemd service fires before you open a browser or run any code
- **Retries aggressively** — if the first NTP query fails (no network yet), it retries every 30 seconds until it succeeds
- **Works without replacing the battery** — until you can get to a hardware store, the daemon keeps your clock accurate every session

Typical symptom the daemon fixes automatically:

```
Clock shows: 2025-07-04 (wrong — CMOS reset)
NTP corrects to: 2026-04-07 (correct)
Delta corrected: 88 days, silently, on every boot
```

## Features

- **Round-robin redundancy** across 10 trusted NTP servers (NIST, Google, Cloudflare, Apple, Microsoft, NTP Pool)
- **Automatic retry** with configurable delay — never gives up
- **Cross-platform** — macOS, Linux, Windows
- **Locale-safe date formatting** — Windows `Set-Date` receives ISO 8601 (`YYYY-MM-DDTHH:MM:SS`), which .NET parses with InvariantCulture regardless of system locale. No MM-DD vs DD-MM ambiguity on non-English Windows installs (pt-BR, ja-JP, fr-FR, etc.)
- **Full global timezone support** — correctly sets local time on any UTC offset, including half-hour (India UTC+5:30, Iran UTC+3:30, Newfoundland UTC-3:30) and quarter-hour zones (Nepal UTC+5:45, Chatham Islands UTC+13:45). DST transitions handled by the OS timezone database
- **Minimal offset threshold** — skips adjustment if clock drift < 10ms
- **Graceful shutdown** on SIGTERM/SIGINT
- **Dry-run mode** for testing without changing the clock

## NTP Servers

| Server | Provider |
|--------|----------|
| `time.nist.gov` | NIST (US) |
| `time.google.com` | Google |
| `time.cloudflare.com` | Cloudflare |
| `time.apple.com` | Apple |
| `time.windows.com` | Microsoft |
| `0-3.pool.ntp.org` | NTP Pool Project |

## Installation

```bash
pip install .
```

Or install directly from GitHub:

```bash
pip install git+https://github.com/raphaelbgr/ntp-sync-daemon.git
```

## Usage

```bash
# Default: sync every 1 hour, retry every 30s on failure
sudo ntp-sync-daemon

# Custom interval (every 30 minutes)
sudo ntp-sync-daemon --interval 1800

# Test mode (don't change clock)
ntp-sync-daemon --dry-run --verbose

# Run as a Python module
sudo python -m ntp_sync
```

### Options

| Flag | Default | Description |
|------|---------|-------------|
| `--interval` | `3600` | Sync interval in seconds |
| `--retry-delay` | `30` | Retry delay on failure in seconds |
| `--dry-run` | off | Query servers without adjusting clock |
| `-v, --verbose` | off | Debug logging |
| `--version` | — | Show version |

## Install as System Service

### macOS (launchd)

```bash
sudo cp service/launchd/com.rbgnr.ntp-sync-daemon.plist /Library/LaunchDaemons/
sudo launchctl load /Library/LaunchDaemons/com.rbgnr.ntp-sync-daemon.plist
```

To uninstall:

```bash
sudo launchctl unload /Library/LaunchDaemons/com.rbgnr.ntp-sync-daemon.plist
sudo rm /Library/LaunchDaemons/com.rbgnr.ntp-sync-daemon.plist
```

### Linux (systemd)

```bash
sudo cp service/systemd/ntp-sync-daemon.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now ntp-sync-daemon
```

To check status:

```bash
sudo systemctl status ntp-sync-daemon
journalctl -u ntp-sync-daemon -f
```

### Windows (Scheduled Task)

Run PowerShell as Administrator:

```powershell
.\service\windows\install.ps1
```

To uninstall:

```powershell
.\service\windows\uninstall.ps1
```

The task runs as SYSTEM at startup with automatic restart every minute on failure — so even if the network is not ready at boot, it will keep retrying until the clock is corrected.

## Permissions

Setting the system clock requires elevated privileges:

- **macOS/Linux**: Run with `sudo`, or configure passwordless sudo for the date/timedatectl commands
- **Windows**: Run as Administrator, or use the scheduled task installer (runs as SYSTEM)

## Timezone Support

The daemon uses Python's `datetime.fromtimestamp()` to convert the corrected UTC timestamp to local time before passing it to the OS command. This delegates timezone resolution entirely to the OS timezone database, which covers:

| Region | UTC Offset |
|--------|-----------|
| Line Islands, Kiribati | UTC+14:00 |
| Chatham Islands, New Zealand | UTC+13:45 |
| Australia Central | UTC+9:30 |
| China, Singapore | UTC+8:00 |
| India | UTC+5:30 |
| Nepal | UTC+5:45 |
| Iran | UTC+3:30 |
| UTC / GMT | UTC+0:00 |
| US Eastern | UTC-5:00 |
| Newfoundland, Canada | UTC-3:30 |
| Baker Island | UTC-12:00 |

DST transitions (spring-forward / fall-back) are handled transparently by the OS.

On Windows, the time string is formatted as ISO 8601 (`YYYY-MM-DDTHH:MM:SS`) without a timezone suffix, which PowerShell's `Set-Date` interprets as local time regardless of the machine's display locale.

## Testing

```bash
pip install pytest
pytest tests/
```

The test suite covers:

- **184 tests** across locale safety, offset math, platform dispatch, timezone coverage, and edge cases
- All 132 locale-ambiguous month/day combinations for Windows (any day ≤ 12 where MM-DD and DD-MM diverge)
- 12 UTC offsets spanning the full range of timezones on the planet, including half-hour and quarter-hour zones
- DST spring-forward and fall-back boundary cases
- macOS, Linux (timedatectl + date fallback), Windows, and unsupported platform error path
- Edge cases: leap day (Feb 29), New Year's Eve/Day, midnight, 88-day large-delta correction

## License

MIT
