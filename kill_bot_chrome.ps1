$botProfile = "AIArtBot\chrome_profile"
$killed = 0
Get-Process chrome -ErrorAction SilentlyContinue | ForEach-Object {
    $procId = $_.Id
    try {
        $cmdLine = (Get-WmiObject Win32_Process -Filter "ProcessId=$procId" -ErrorAction SilentlyContinue).CommandLine
        if ($cmdLine -and $cmdLine -like "*$botProfile*") {
            Write-Host "Killing bot Chrome PID $procId"
            $_ | Stop-Process -Force
            $killed++
        }
    } catch {}
}
Write-Host "Killed $killed bot Chrome processes"
