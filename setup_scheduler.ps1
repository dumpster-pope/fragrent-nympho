# AI Art Bot — Windows Task Scheduler Setup
# Run this script as Administrator once to register the hourly task.
# After setup: 1 image per hour, 24 images per day, saved to Desktop\AI_Art\

$botPath    = "C:\Users\gageg\AIArtBot\art_bot.py"
$pythonPath = "python"   # Change to full path (e.g. C:\Python312\python.exe) if needed
$workDir    = "C:\Users\gageg\AIArtBot"

# ── Remove any old tasks from the previous DALL-E version ─────────────────────
$oldTasks = Get-ScheduledTask -TaskName "AIArtBot*" -ErrorAction SilentlyContinue
foreach ($t in $oldTasks) {
    Unregister-ScheduledTask -TaskName $t.TaskName -Confirm:$false
    Write-Host "  Removed old task: $($t.TaskName)" -ForegroundColor Yellow
}

# ── Create hourly task ────────────────────────────────────────────────────────
$action   = New-ScheduledTaskAction `
                -Execute $pythonPath `
                -Argument "`"$botPath`" run" `
                -WorkingDirectory $workDir

# Repeat every 1 hour indefinitely, starting at midnight tonight
$trigger  = New-ScheduledTaskTrigger -Daily -At "00:00AM"
$repeat   = New-TimeSpan -Hours 1
$trigger.RepetitionInterval  = $repeat
$trigger.RepetitionDuration  = [System.TimeSpan]::MaxValue

$settings = New-ScheduledTaskSettingsSet `
                -AllowStartIfOnBatteries `
                -DontStopIfGoingOnBatteries `
                -StartWhenAvailable `
                -ExecutionTimeLimit (New-TimeSpan -Minutes 10)

Register-ScheduledTask `
    -TaskName    "AIArtBot_Hourly" `
    -Action      $action `
    -Trigger     $trigger `
    -Settings    $settings `
    -Description "Generate 1 AI art image per hour via Grok, save to Desktop\AI_Art" `
    -Force

Write-Host ""
Write-Host "✅  Task 'AIArtBot_Hourly' created." -ForegroundColor Green
Write-Host "    Runs every hour starting at midnight."
Write-Host "    Images → C:\Users\gageg\Desktop\AI_Art\"
Write-Host ""
Write-Host "To run immediately (first test):" -ForegroundColor Cyan
Write-Host "    python `"$botPath`" run"
Write-Host ""
Write-Host "To view all bot tasks:" -ForegroundColor Cyan
Write-Host "    Get-ScheduledTask -TaskName 'AIArtBot*'"
Write-Host ""
Write-Host "NOTE: Make sure you are logged into grok.com in Chrome before" -ForegroundColor Yellow
Write-Host "      the bot runs, or set chrome_profile_path in config.json." -ForegroundColor Yellow
