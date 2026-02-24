$botPath    = 'C:\Users\gageg\AIArtBot\art_bot.py'
$pythonPath = 'python'
$workDir    = 'C:\Users\gageg\AIArtBot'

Get-ScheduledTask -TaskName 'AIArtBot*' -ErrorAction SilentlyContinue | ForEach-Object {
    Unregister-ScheduledTask -TaskName $_.TaskName -Confirm:$false
    Write-Host "Removed: $($_.TaskName)"
}

$action   = New-ScheduledTaskAction -Execute $pythonPath -Argument "`"$botPath`" run" -WorkingDirectory $workDir
$trigger  = New-ScheduledTaskTrigger -Daily -At '00:00AM'
$trigger.RepetitionInterval = New-TimeSpan -Hours 1
$trigger.RepetitionDuration = [System.TimeSpan]::MaxValue
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes 10)

Register-ScheduledTask -TaskName 'AIArtBot_Hourly' -Action $action -Trigger $trigger -Settings $settings -Description 'Every hour, conjure three visions of the same dream — rendered through different eyes, different centuries, different hands. A carousel of worlds where scholars translate light, whales drift through medieval skies, and mirrors shatter into deserts. Art that did not exist an hour ago.' -Force
Write-Host 'AIArtBot_Hourly task registered successfully.'
