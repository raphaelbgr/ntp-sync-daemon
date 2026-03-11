# ntp-sync-daemon

Cross-platform NTP time synchronization daemon with round-robin server redundancy.

Syncs your system clock against trusted NTP servers on a configurable interval, retrying indefinitely on failure with automatic server rotation.

## Features

- **Round-robin redundancy** across 10 trusted NTP servers (NIST, Google, Cloudflare, Apple, Microsoft, NTP Pool)
- **Automatic retry** with configurable delay — never gives up
- **Cross-platform** — macOS, Linux, Windows
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

## Permissions

Setting the system clock requires elevated privileges:

- **macOS/Linux**: Run with `sudo`, or configure passwordless sudo for the date/timedatectl commands
- **Windows**: Run as Administrator, or use the scheduled task installer (runs as SYSTEM)

## License

MIT
