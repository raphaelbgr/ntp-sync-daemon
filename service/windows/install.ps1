# Install ntp-sync-daemon as a Windows scheduled task
# Run as Administrator

$action = New-ScheduledTaskAction `
    -Execute "pythonw" `
    -Argument "-m ntp_sync --verbose"

$trigger = New-ScheduledTaskTrigger -AtStartup

$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -RestartCount 999 `
    -RestartInterval (New-TimeSpan -Seconds 30) `
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
