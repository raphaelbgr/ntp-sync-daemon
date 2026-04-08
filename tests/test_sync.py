"""Tests for ntp_sync.sync — focusing on locale-safe date formatting.

The historical bug: Windows branch used strftime("%m-%d-%Y") which PowerShell
parses with the system locale. On pt-BR (DD-MM-YYYY), April 7 ("04-07-2026")
was read as July 4 — a silent 88-day forward jump every sync cycle.

Fix: ISO 8601 "YYYY-MM-DDTHH:MM:SS" is parsed by .NET/PowerShell with
InvariantCulture when the year comes first, so it is always correct.
"""

import platform
import subprocess
import time
from datetime import datetime, timezone
from unittest.mock import MagicMock, call, patch

import pytest

from ntp_sync.sync import set_system_time


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_timestamp(year, month, day, hour=12, minute=0, second=0):
    """Return a UTC POSIX timestamp for the given local naive datetime."""
    dt = datetime(year, month, day, hour, minute, second)
    return dt.timestamp()


# ---------------------------------------------------------------------------
# Windows — locale ambiguity cases
# ---------------------------------------------------------------------------

class TestWindowsLocaleSafety:
    """All dates where day ≤ 12 are locale-vulnerable with MM-DD-YYYY.

    For each such date, MM-DD and DD-MM swap month and day, producing a
    completely different (and wrong) date.  ISO 8601 is immune.
    """

    # Every (month, day) pair where day <= 12 and month != day (real ambiguity)
    AMBIGUOUS_DATES = [
        (1,  2), (1,  3), (1,  4), (1,  5), (1,  6),
        (1,  7), (1,  8), (1,  9), (1, 10), (1, 11), (1, 12),
        (2,  1), (2,  3), (2,  4), (2,  5), (2,  6),
        (2,  7), (2,  8), (2,  9), (2, 10), (2, 11), (2, 12),
        (3,  1), (3,  2), (3,  4), (3,  5), (3,  6),
        (3,  7), (3,  8), (3,  9), (3, 10), (3, 11), (3, 12),
        (4,  1), (4,  2), (4,  3), (4,  5), (4,  6),
        (4,  7), (4,  8), (4,  9), (4, 10), (4, 11), (4, 12),  # Apr 7 = the bug
        (5,  1), (5,  2), (5,  3), (5,  4), (5,  6),
        (5,  7), (5,  8), (5,  9), (5, 10), (5, 11), (5, 12),
        (6,  1), (6,  2), (6,  3), (6,  4), (6,  5),
        (6,  7), (6,  8), (6,  9), (6, 10), (6, 11), (6, 12),
        (7,  1), (7,  2), (7,  3), (7,  4), (7,  5), (7,  6),
        (7,  8), (7,  9), (7, 10), (7, 11), (7, 12),
        (8,  1), (8,  2), (8,  3), (8,  4), (8,  5), (8,  6),
        (8,  7), (8,  9), (8, 10), (8, 11), (8, 12),
        (9,  1), (9,  2), (9,  3), (9,  4), (9,  5), (9,  6),
        (9,  7), (9,  8), (9, 10), (9, 11), (9, 12),
        (10, 1), (10, 2), (10, 3), (10, 4), (10, 5), (10, 6),
        (10, 7), (10, 8), (10, 9), (10, 11), (10, 12),
        (11, 1), (11, 2), (11, 3), (11, 4), (11, 5), (11, 6),
        (11, 7), (11, 8), (11, 9), (11, 10), (11, 12),
        (12, 1), (12, 2), (12, 3), (12, 4), (12, 5), (12, 6),
        (12, 7), (12, 8), (12, 9), (12, 10), (12, 11),
    ]

    @pytest.mark.parametrize("month,day", AMBIGUOUS_DATES)
    def test_iso_format_no_locale_ambiguity(self, month, day):
        """The command must use ISO 8601 (YYYY-MM-DDTHH:MM:SS) format."""
        ts = _make_timestamp(2026, month, day, 15, 30, 0)
        with patch("platform.system", return_value="Windows"), \
             patch("time.time", return_value=ts), \
             patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            set_system_time(0.0)

        cmd = mock_run.call_args[0][0]
        date_arg = cmd[-1]  # last arg: "Set-Date -Date '...'"
        # Must contain T (ISO 8601 separator) — not a slash or locale-dependent dash
        assert "T" in date_arg, (
            f"Expected ISO 8601 in Set-Date arg for {month:02d}/{day:02d}, got: {date_arg}"
        )
        # Year must come first
        assert date_arg.startswith("Set-Date -Date '2026-"), (
            f"Expected year-first ISO format for {month:02d}/{day:02d}, got: {date_arg}"
        )

    def test_the_original_bug_apr7(self):
        """Apr 7 2026 — the exact date that triggered the bug.

        Old format "04-07-2026" → pt-BR PowerShell reads July 4.
        New format "2026-04-07T..." → always April 7.
        """
        ts = _make_timestamp(2026, 4, 7, 17, 31, 34)
        with patch("platform.system", return_value="Windows"), \
             patch("time.time", return_value=ts), \
             patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            set_system_time(0.0)

        date_arg = mock_run.call_args[0][0][-1]
        assert "2026-04-07T" in date_arg, f"Expected 2026-04-07T in command, got: {date_arg}"
        # The bad old format must NOT appear
        assert "04-07-2026" not in date_arg
        assert "07-04-2026" not in date_arg

    def test_command_structure(self):
        """Windows branch must invoke powershell with Set-Date."""
        ts = _make_timestamp(2026, 6, 15, 10, 0, 0)
        with patch("platform.system", return_value="Windows"), \
             patch("time.time", return_value=ts), \
             patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            set_system_time(0.0)

        cmd = mock_run.call_args[0][0]
        assert cmd[0] == "powershell"
        assert cmd[1] == "-Command"
        assert "Set-Date -Date" in cmd[2]

    @pytest.mark.parametrize("month,day", [(1, 13), (2, 14), (3, 15), (12, 31)])
    def test_unambiguous_dates_also_use_iso(self, month, day):
        """Dates with day > 12 were never locale-ambiguous, but still use ISO."""
        ts = _make_timestamp(2026, month, day, 8, 0, 0)
        with patch("platform.system", return_value="Windows"), \
             patch("time.time", return_value=ts), \
             patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            set_system_time(0.0)

        date_arg = mock_run.call_args[0][0][-1]
        assert "T" in date_arg


# ---------------------------------------------------------------------------
# Offset calculation
# ---------------------------------------------------------------------------

class TestOffsetApplication:
    """Verify that the NTP offset is correctly added to current time."""

    def test_positive_offset_advances_clock(self):
        base_ts = _make_timestamp(2026, 4, 7, 12, 0, 0)
        with patch("platform.system", return_value="Windows"), \
             patch("time.time", return_value=base_ts), \
             patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            set_system_time(3600.0)  # +1 hour offset

        date_arg = mock_run.call_args[0][0][-1]
        assert "T13:00:00" in date_arg, f"Expected 13:00:00 after +1h offset, got: {date_arg}"

    def test_negative_offset_rewinds_clock(self):
        base_ts = _make_timestamp(2026, 4, 7, 12, 0, 0)
        with patch("platform.system", return_value="Windows"), \
             patch("time.time", return_value=base_ts), \
             patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            set_system_time(-3600.0)  # -1 hour offset

        date_arg = mock_run.call_args[0][0][-1]
        assert "T11:00:00" in date_arg, f"Expected 11:00:00 after -1h offset, got: {date_arg}"

    def test_zero_offset_keeps_time(self):
        base_ts = _make_timestamp(2026, 4, 7, 15, 30, 45)
        with patch("platform.system", return_value="Windows"), \
             patch("time.time", return_value=base_ts), \
             patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            set_system_time(0.0)

        date_arg = mock_run.call_args[0][0][-1]
        assert "T15:30:45" in date_arg

    def test_large_negative_offset_88_days(self):
        """Simulate the actual bug scenario: clock is 88 days ahead, NTP corrects."""
        # Clock thinks it's July 4 but should be April 7 (~88 days off)
        wrong_ts = _make_timestamp(2026, 7, 4, 17, 31, 36)
        offset = -88 * 24 * 3600  # ~88 days back
        with patch("platform.system", return_value="Windows"), \
             patch("time.time", return_value=wrong_ts), \
             patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            set_system_time(float(offset))

        date_arg = mock_run.call_args[0][0][-1]
        # Should land around April 7
        assert "2026-04-" in date_arg, f"Expected ~April date after correction, got: {date_arg}"

    def test_small_millisecond_offset(self):
        """Sub-second offsets should not corrupt the time string."""
        base_ts = _make_timestamp(2026, 4, 7, 12, 0, 0)
        with patch("platform.system", return_value="Windows"), \
             patch("time.time", return_value=base_ts), \
             patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            set_system_time(0.123)

        date_arg = mock_run.call_args[0][0][-1]
        assert "Set-Date" in date_arg  # just verify no crash


# ---------------------------------------------------------------------------
# Darwin
# ---------------------------------------------------------------------------

class TestDarwin:
    def test_darwin_uses_date_command(self):
        ts = _make_timestamp(2026, 4, 7, 12, 0, 0)
        with patch("platform.system", return_value="Darwin"), \
             patch("time.time", return_value=ts), \
             patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            set_system_time(0.0)

        cmd = mock_run.call_args[0][0]
        assert cmd[:3] == ["sudo", "-n", "date"]

    def test_darwin_format_MMDDhhmm(self):
        """macOS date expects MMDDhhmm[[CC]YY][.ss]."""
        ts = _make_timestamp(2026, 4, 7, 15, 30, 45)
        with patch("platform.system", return_value="Darwin"), \
             patch("time.time", return_value=ts), \
             patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            set_system_time(0.0)

        date_str = mock_run.call_args[0][0][3]
        # Format: MMDDhhmm YYYY .ss -> "04071530 2026.45"
        assert date_str.startswith("0407"), f"Expected MMDDhhmm starting with 0407, got: {date_str}"
        assert "2026" in date_str


# ---------------------------------------------------------------------------
# Linux
# ---------------------------------------------------------------------------

class TestLinux:
    def test_linux_timedatectl_primary(self):
        ts = _make_timestamp(2026, 4, 7, 12, 0, 0)
        with patch("platform.system", return_value="Linux"), \
             patch("time.time", return_value=ts), \
             patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            set_system_time(0.0)

        calls = [c[0][0] for c in mock_run.call_args_list]
        assert any("timedatectl" in str(c) for c in calls)

    def test_linux_falls_back_to_date_command(self):
        ts = _make_timestamp(2026, 4, 7, 12, 0, 0)
        with patch("platform.system", return_value="Linux"), \
             patch("time.time", return_value=ts), \
             patch("subprocess.run") as mock_run:
            # set-ntp false fails -> except block -> date -s succeeds (2 calls total)
            mock_run.side_effect = [
                subprocess.CalledProcessError(1, "timedatectl"),
                MagicMock(returncode=0),  # date -s succeeds
            ]
            set_system_time(0.0)

        calls = [c[0][0] for c in mock_run.call_args_list]
        assert any("date" in str(c) for c in calls)

    def test_linux_iso_date_format(self):
        """Linux timedatectl set-time uses YYYY-MM-DD HH:MM:SS."""
        ts = _make_timestamp(2026, 4, 7, 15, 30, 45)
        with patch("platform.system", return_value="Linux"), \
             patch("time.time", return_value=ts), \
             patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            set_system_time(0.0)

        calls = mock_run.call_args_list
        set_time_call = next(
            c for c in calls if "set-time" in str(c[0][0])
        )
        date_arg = set_time_call[0][0][-1]
        assert date_arg == "2026-04-07 15:30:45", f"Got: {date_arg}"


# ---------------------------------------------------------------------------
# Unsupported platform
# ---------------------------------------------------------------------------

class TestUnsupportedPlatform:
    def test_raises_os_error(self):
        ts = _make_timestamp(2026, 4, 7, 12, 0, 0)
        with patch("platform.system", return_value="FreeBSD"), \
             patch("time.time", return_value=ts):
            with pytest.raises(OSError, match="Unsupported platform"):
                set_system_time(0.0)


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_new_years_eve(self):
        ts = _make_timestamp(2026, 12, 31, 23, 59, 59)
        with patch("platform.system", return_value="Windows"), \
             patch("time.time", return_value=ts), \
             patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            set_system_time(0.0)
        date_arg = mock_run.call_args[0][0][-1]
        assert "2026-12-31T23:59:59" in date_arg

    def test_new_years_day(self):
        ts = _make_timestamp(2026, 1, 1, 0, 0, 0)
        with patch("platform.system", return_value="Windows"), \
             patch("time.time", return_value=ts), \
             patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            set_system_time(0.0)
        date_arg = mock_run.call_args[0][0][-1]
        assert "2026-01-01T00:00:00" in date_arg

    def test_leap_day(self):
        ts = _make_timestamp(2028, 2, 29, 12, 0, 0)
        with patch("platform.system", return_value="Windows"), \
             patch("time.time", return_value=ts), \
             patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            set_system_time(0.0)
        date_arg = mock_run.call_args[0][0][-1]
        assert "2028-02-29T" in date_arg

    def test_midnight(self):
        ts = _make_timestamp(2026, 6, 15, 0, 0, 0)
        with patch("platform.system", return_value="Windows"), \
             patch("time.time", return_value=ts), \
             patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            set_system_time(0.0)
        date_arg = mock_run.call_args[0][0][-1]
        assert "T00:00:00" in date_arg
