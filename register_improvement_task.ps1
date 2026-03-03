# AIArtBot Improvement Agent — Task Scheduler Setup
# Runs every 6 hours starting at 01:00, offset from art bot (even hours) and monitor (23:00).

$agentPath  = 'C:\Users\gageg\AIArtBot\improvement_agent.py'
$pythonPath = 'C:\Python314\python.exe'
$workDir    = 'C:\Users\gageg\AIArtBot'
$taskName   = 'AIArtBot_Improvement'

# Remove existing task if present
if (Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
    Write-Host "Removed existing task: $taskName" -ForegroundColor Yellow
}

# Action
$action = New-ScheduledTaskAction `
    -Execute          $pythonPath `
    -Argument         "`"$agentPath`" run" `
    -WorkingDirectory $workDir

# Trigger: start at next 01:00, repeat every 6 hours indefinitely
# (-Once + -RepetitionInterval is the correct pattern; -Daily doesn't expose RepetitionInterval)
$now      = Get-Date
$nextRun  = $now.Date.AddHours(1)   # today at 01:00
if ($nextRun -le $now) { $nextRun = $nextRun.AddDays(1) }   # already past — use tomorrow

$trigger = New-ScheduledTaskTrigger `
    -Once `
    -At                 $nextRun `
    -RepetitionInterval (New-TimeSpan -Hours 6)
    # No -RepetitionDuration means the repetition runs indefinitely

# Settings
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RunOnlyIfNetworkAvailable `
    -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit (New-TimeSpan -Hours 3)

Register-ScheduledTask `
    -TaskName    $taskName `
    -Action      $action `
    -Trigger     $trigger `
    -Settings    $settings `
    -RunLevel    Limited `
    -Description 'AIArtBot improvement agent: research + test + auto-deploy improvements every 6 hours.' `
    -Force | Out-Null

$info = Get-ScheduledTaskInfo -TaskName $taskName
$task = Get-ScheduledTask -TaskName $taskName

Write-Host ""
Write-Host "$taskName registered." -ForegroundColor Green
Write-Host "  State       : $($task.State)"
Write-Host "  Next run    : $($info.NextRunTime)"
Write-Host "  Exec limit  : $($task.Settings.ExecutionTimeLimit)"
Write-Host "  Repetition  : $($task.Triggers[0].Repetition.Interval)"
Write-Host ""
Write-Host "Schedule:"
Write-Host "  01:00 — Improvement agent"
Write-Host "  07:00 — Improvement agent"
Write-Host "  13:00 — Improvement agent"
Write-Host "  19:00 — Improvement agent"
Write-Host "  (Art bot runs 00:00, 02:00, 04:00 ... 22:00)"
Write-Host "  (Monitor runs 23:00)"
Write-Host ""
Write-Host "To trigger immediately:" -ForegroundColor Cyan
Write-Host "  Start-ScheduledTask -TaskName '$taskName'"
Write-Host ""
Write-Host "To check status:" -ForegroundColor Cyan
Write-Host "  python improvement_agent.py status"
