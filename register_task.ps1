# AI Art Bot — Every-2-Hours Task Scheduler Setup
# Generates 1 image every 2 hours (grok or chatgpt), posts to Instagram, then engages.

$botPath    = 'C:\Users\gageg\AIArtBot\art_bot.py'
$pythonPath = 'C:\Python314\python.exe'
$workDir    = 'C:\Users\gageg\AIArtBot'

# Remove old versions
Get-ScheduledTask -TaskName 'AIArtBot*' -ErrorAction SilentlyContinue | ForEach-Object {
    Unregister-ScheduledTask -TaskName $_.TaskName -Confirm:$false
    Write-Host "Removed: $($_.TaskName)" -ForegroundColor Yellow
}

# Action
$action = New-ScheduledTaskAction `
    -Execute          $pythonPath `
    -Argument         "`"$botPath`" run" `
    -WorkingDirectory $workDir

# Trigger: start at the next even hour, repeat every 2 hours indefinitely
$now       = Get-Date
$nextEven  = $now.Date.AddHours(([Math]::Floor($now.Hour / 2) + 1) * 2)
Write-Host "First run scheduled at: $nextEven"

$trigger = New-ScheduledTaskTrigger `
    -Once `
    -At                  $nextEven `
    -RepetitionInterval  (New-TimeSpan -Hours 2)
    # No -RepetitionDuration means it runs indefinitely

# Settings: 45-min execution limit (full run ~25 min; 45 min is a safe ceiling)
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 45)

Register-ScheduledTask `
    -TaskName   'AIArtBot_Hourly' `
    -Action     $action `
    -Trigger    $trigger `
    -Settings   $settings `
    -RunLevel   Limited `
    -Description 'Generate 1 AI art image every 2 hours (grok/chatgpt), post to Instagram, engage.' `
    -Force | Out-Null

$info = Get-ScheduledTaskInfo -TaskName 'AIArtBot_Hourly'
$task = Get-ScheduledTask -TaskName 'AIArtBot_Hourly'

Write-Host ""
Write-Host "AIArtBot_Hourly registered." -ForegroundColor Green
Write-Host "  State      : $($task.State)"
Write-Host "  Next run   : $($info.NextRunTime)"
Write-Host "  Exec limit : $($task.Settings.ExecutionTimeLimit)"
Write-Host "  Repetition : $($task.Triggers[0].Repetition.Interval)"
Write-Host ""
Write-Host "To trigger immediately:" -ForegroundColor Cyan
Write-Host "  Start-ScheduledTask -TaskName 'AIArtBot_Hourly'"
