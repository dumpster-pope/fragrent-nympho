# Registers a Windows Task Scheduler job that runs instagram_bot.py post
# every 30 minutes, starting from the next half-hour mark.
# Run this script as Administrator once to register the task.

$botPath    = 'C:\Users\gageg\AIArtBot\instagram_bot.py'
$pythonPath = 'python'
$workDir    = 'C:\Users\gageg\AIArtBot'
$taskName   = 'AIArtBot_Instagram'

# Remove any previous version
schtasks /Delete /TN $taskName /F 2>$null

# Register: every 30 minutes, runs indefinitely, start immediately
schtasks /Create `
    /TN  $taskName `
    /TR  "`"$pythonPath`" `"$botPath`" post" `
    /SC  MINUTE `
    /MO  30 `
    /ST  "00:00" `
    /SD  (Get-Date -Format "MM/dd/yyyy") `
    /RI  30 `
    /DU  9999:59 `
    /RU  "SYSTEM" `
    /RL  HIGHEST `
    /F

Write-Host ""
Write-Host "Task '$taskName' registered — runs every 30 minutes."
Write-Host "The bot will post at peak engagement windows only (3 posts/day max)."
Write-Host ""
Write-Host "Before the first post, run the login setup:"
Write-Host "  python instagram_bot.py login"
Write-Host ""
Write-Host "To check status:"
Write-Host "  python instagram_bot.py status"
Write-Host "  python instagram_bot.py preview"
