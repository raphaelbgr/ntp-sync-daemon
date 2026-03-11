# Uninstall ntp-sync-daemon Windows scheduled task
# Run as Administrator

Stop-ScheduledTask -TaskName "NTPSyncDaemon" -ErrorAction SilentlyContinue
Unregister-ScheduledTask -TaskName "NTPSyncDaemon" -Confirm:$false
Write-Host "ntp-sync-daemon scheduled task removed."
