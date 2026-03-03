# register_monitor_task.ps1
#
# Registers AIArtBot_Monitor to run once per day at 11:00 PM.
# The monitor checks health, catches unposted images, and self-heals.
#
# Run once as Administrator:
#   powershell -ExecutionPolicy Bypass -File register_monitor_task.ps1
#
# To trigger manually (no Admin needed after registration):
#   powershell -Command "Start-ScheduledTask -TaskName 'AIArtBot_Monitor'"

$TaskName   = "AIArtBot_Monitor"
$PythonExe  = "C:\Python314\python.exe"
$ScriptPath = "C:\Users\gageg\AIArtBot\monitor_agent.py"
$WorkDir    = "C:\Users\gageg\AIArtBot"

# Remove any existing version of this task
Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue

# Action: run Python with the monitor script
$action = New-ScheduledTaskAction `
    -Execute    $PythonExe `
    -Argument   "`"$ScriptPath`"" `
    -WorkingDirectory $WorkDir

# Trigger: daily at 11:00 PM
$trigger = New-ScheduledTaskTrigger -Daily -At "11:00PM"

# Settings
$settings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit   (New-TimeSpan -Hours 2) `
    -StartWhenAvailable `
    -RunOnlyIfNetworkAvailable `
    -MultipleInstances    IgnoreNew `
    -RestartCount         2 `
    -RestartInterval      (New-TimeSpan -Minutes 5)

# Register with standard user privileges — Chrome won't run as admin
Register-ScheduledTask `
    -TaskName  $TaskName `
    -Action    $action `
    -Trigger   $trigger `
    -Settings  $settings `
    -RunLevel  Limited `
    -Force

Write-Host ""
Write-Host "AIArtBot_Monitor task registered." -ForegroundColor Green
Write-Host "  Runs daily at 11:00 PM."
Write-Host "  Logs: C:\Users\gageg\AIArtBot\logs\monitor_YYYYMMDD.log"
Write-Host "  Report: C:\Users\gageg\AIArtBot\monitor_report.json"
Write-Host ""
Write-Host "To run it now:"
Write-Host "  powershell -Command `"Start-ScheduledTask -TaskName '$TaskName'`""
Write-Host ""
Write-Host "To view the report:"
Write-Host "  python -c `"import json,pathlib; [print(r['run_at'], r['overall_healthy'], r.get('issues','')) for r in json.loads(pathlib.Path('monitor_report.json').read_text())]`""
