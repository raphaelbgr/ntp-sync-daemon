# Install ntp-sync-daemon as a Windows scheduled task
# Run as Administrator

# Find pythonw.exe automatically
$pythonw = (Get-Command pythonw -ErrorAction SilentlyContinue).Source
if (-not $pythonw) {
    $pythonw = (Get-Command python -ErrorAction SilentlyContinue).Source
    if (-not $pythonw) {
        Write-Error "Python not found in PATH. Please install Python first."
        exit 1
    }
}
Write-Host "Using Python: $pythonw"

# Remove existing task if present
Unregister-ScheduledTask -TaskName "NTPSyncDaemon" -Confirm:$false -ErrorAction SilentlyContinue

$action = New-ScheduledTaskAction `
    -Execute $pythonw `
    -Argument "-m ntp_sync --verbose"

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

Write-Host "ntp-sync-daemon installed as scheduled task 'NTPSyncDaemon'"
Write-Host "Starting task..."
Start-ScheduledTask -TaskName "NTPSyncDaemon"
Write-Host "Done. Check status with: Get-ScheduledTask -TaskName 'NTPSyncDaemon'"
