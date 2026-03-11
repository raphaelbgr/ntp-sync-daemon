# Install ntp-sync-daemon as a Windows scheduled task
# Run as Administrator

# First, ensure package is installed system-wide (not user site-packages)
Write-Host "Installing ntp-sync-daemon system-wide..."
$python = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $python) {
    Write-Error "Python not found in PATH. Please install Python first."
    exit 1
}
& $python -m pip install --force-reinstall "$PSScriptRoot\..\.." 2>&1 | Out-Null

# Find the installed script
$scriptPath = Join-Path (Split-Path $python) "Scripts\ntp-sync-daemon.exe"
if (-not (Test-Path $scriptPath)) {
    # Fallback: run as python module
    $pythonw = (Get-Command pythonw -ErrorAction SilentlyContinue).Source
    if (-not $pythonw) { $pythonw = $python }
    $exe = $pythonw
    $args = "-m ntp_sync --verbose"
    Write-Host "Using Python module mode: $exe $args"
} else {
    $exe = $scriptPath
    $args = "--verbose"
    Write-Host "Using installed script: $exe"
}

# Remove existing task if present
Unregister-ScheduledTask -TaskName "NTPSyncDaemon" -Confirm:$false -ErrorAction SilentlyContinue

$action = New-ScheduledTaskAction `
    -Execute $exe `
    -Argument $args

$trigger = New-ScheduledTaskTrigger -AtStartup

$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -RestartCount 999 `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -ExecutionTimeLimit (New-TimeSpan -Days 9999)

$principal = New-ScheduledTaskPrincipal `
    -UserId "SYSTEM" `
    -RunLevel Highest

Register-ScheduledTask `
    -TaskName "NTPSyncDaemon" `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Principal $principal `
    -Description "Cross-platform NTP time sync daemon with round-robin redundancy"

Write-Host ""
Write-Host "ntp-sync-daemon installed as scheduled task 'NTPSyncDaemon'"
Write-Host "Starting task now..."
Start-ScheduledTask -TaskName "NTPSyncDaemon"

Start-Sleep -Seconds 2
$state = (Get-ScheduledTask -TaskName "NTPSyncDaemon").State
Write-Host "Task state: $state"
Write-Host "Check status: Get-ScheduledTask -TaskName 'NTPSyncDaemon'"
