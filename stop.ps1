<#
.SYNOPSIS
    Force-stops whatever is listening on the Coffee Core Router's port
    (8765) and the Coffee Counter Chat UI's port (3000).

.DESCRIPTION
    Independent of any running start.ps1 session - looks up the real
    listening process for each port right now and kills its whole process
    tree (`taskkill /PID <pid> /T /F`), so it also cleans up an orphaned
    node.exe left behind by npm.cmd if start.ps1's own Ctrl+C handling was
    ever bypassed (e.g. the window was closed directly instead).

.EXAMPLE
    .\stop.ps1
#>

[CmdletBinding()]
param()

$ports = 8765, 3000

foreach ($port in $ports) {
    $procIds = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue |
        Select-Object -ExpandProperty OwningProcess -Unique

    if (-not $procIds) {
        Write-Host "Port ${port}: nothing listening."
        continue
    }

    foreach ($procId in $procIds) {
        $procName = (Get-Process -Id $procId -ErrorAction SilentlyContinue).ProcessName
        Write-Host "Port ${port}: killing PID $procId ($procName) and its process tree..."
        & taskkill /PID $procId /T /F 2>$null | Out-Null
    }
}

Write-Host "Done."
