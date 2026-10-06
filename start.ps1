<#
.SYNOPSIS
    Starts the Coffee Core Router and Coffee Counter Chat UI together.

.DESCRIPTION
    Launches both services, each in its own console window:
      - router:   python -m uvicorn router.app.main:app --host 0.0.0.0 --port 8765
      - frontend: npm run dev -- -H 0.0.0.0   (from web/)

    Requires OPENROUTER_API_KEY to already be set in this shell's environment
    - never pass it as an argument or put it in a file. The script stops
    immediately with a clear error if it isn't set.

    CORS_ALLOWED_ORIGINS always covers localhost and 127.0.0.1, plus one
    origin per address in -LanIp (array, or a single comma-separated string -
    both work). When -LanIp/$env:COFFEE_LAN_IP is not given at all, the
    script falls back to $DefaultLanIps below, so plain `.\start.ps1` covers
    localhost, 127.0.0.1, your LAN IP, and your Tailscale IP with zero
    arguments - see router/README.md's "LAN access" section for why
    localhost/127.0.0.1/a real IP can't be mixed in a browser's Origin
    header, which is why every one of them has to be listed explicitly.

    NEXT_PUBLIC_ROUTER_URL, unlike CORS, can only ever be ONE address - the
    frontend makes its API calls against a single router URL, it doesn't
    pick per-request. When multiple -LanIp addresses are configured, the
    Tailscale IP wins if present (see the address-selection comment below
    for why); otherwise the first configured address is used.

    NOTE: web/next.config.ts's `allowedDevOrigins` is a SEPARATE list (an
    array literal, not read from this script or any environment variable)
    that Next.js's dev server checks independently of CORS_ALLOWED_ORIGINS.
    If you add/change an address in $DefaultLanIps below, update
    web/next.config.ts's `allowedDevOrigins` array to match by hand - there
    is currently no single source of truth for both.

    Press Ctrl+C to stop both services. Each was started via Start-Process,
    and `npm run dev` on Windows resolves to npm.cmd, which spawns node.exe
    as a *child* process - the thing actually listening on port 3000. Killing
    only the launched PID would leave that child running as an orphan, so
    cleanup uses `taskkill /PID <pid> /T /F` (kills the whole process tree),
    not Stop-Process.

.PARAMETER LanIp
    Optional LAN/Tailscale/etc. IP address(es) of this machine, to allow
    another device on the network to reach the app - pass an array
    (-LanIp 192.168.1.50,100.64.0.10) or a single comma-separated string
    (-LanIp "192.168.1.50,100.64.0.10"), both are accepted. Falls back to
    $env:COFFEE_LAN_IP (also comma-separated) if not given, and to
    $DefaultLanIps below if neither is set - so omitting this entirely does
    NOT mean localhost-only anymore, it means "use the configured defaults".
    Passing -LanIp explicitly always overrides the default list completely,
    it does not merge with it.

.EXAMPLE
    .\start.ps1

.EXAMPLE
    .\start.ps1 -LanIp 192.168.1.50

.EXAMPLE
    .\start.ps1 -LanIp 192.168.1.50,100.64.0.10
#>

[CmdletBinding()]
param(
    [string[]]$LanIp
)

# Default LAN/Tailscale addresses for this machine - edit here if either
# ever changes. Used only when -LanIp and $env:COFFEE_LAN_IP are both
# absent, so plain `.\start.ps1` needs no arguments day to day. Keep this
# in sync with web/next.config.ts's `allowedDevOrigins` array by hand (see
# the header comment above) - that list cannot be driven from here.
# Empty by default, so plain `.\start.ps1` is localhost-only. To make your
# own addresses the default without editing this file, set
# $env:COFFEE_LAN_IP (comma-separated) in your PowerShell profile.
$DefaultLanIps = @()

# Which of $DefaultLanIps is the Tailscale address - used below to pick
# NEXT_PUBLIC_ROUTER_URL sensibly when several addresses are configured.
# Set $env:COFFEE_TAILSCALE_IP in your profile if you use Tailscale.
$TailscaleIp = $env:COFFEE_TAILSCALE_IP

$ErrorActionPreference = "Stop"
$repoRoot = $PSScriptRoot
$webDir = Join-Path $repoRoot "web"

if (-not $env:OPENROUTER_API_KEY) {
    Write-Error @"
OPENROUTER_API_KEY is not set in this shell's environment.

The router will fail on its first real request without it. Set it before
running this script, e.g.:

  `$env:OPENROUTER_API_KEY = "sk-or-..."
  .\start.ps1

Never put the key in a file or pass it as a script argument.
"@
    exit 1
}

# Resolve the effective LAN/Tailscale address list: explicit -LanIp first,
# then $env:COFFEE_LAN_IP, then $DefaultLanIps - each one fully overrides
# the next, never merges with it, matching -LanIp's documented behavior.
# Every source is normalized the same way (split on comma, trim, drop
# empties) so an array argument, a quoted comma-separated string argument,
# and a comma-separated env var all behave identically.
if (-not $LanIp -and $env:COFFEE_LAN_IP) {
    $LanIp = @($env:COFFEE_LAN_IP)
}
if (-not $LanIp) {
    $LanIp = $DefaultLanIps
}
$LanIp = @($LanIp | ForEach-Object { $_ -split "," } | ForEach-Object { $_.Trim() } | Where-Object { $_ })

# CORS_ALLOWED_ORIGINS: always localhost + 127.0.0.1, plus one origin per
# resolved LAN/Tailscale address - CORS has no concept of "pick one," every
# origin that should be allowed to call the router has to be listed.
$origins = @("http://localhost:3000", "http://127.0.0.1:3000")
foreach ($ip in $LanIp) {
    $origins += "http://${ip}:3000"
}
$env:CORS_ALLOWED_ORIGINS = $origins -join ","

# NEXT_PUBLIC_ROUTER_URL: unlike CORS, the frontend calls exactly one
# router URL, so with multiple addresses configured we have to pick one.
# The Tailscale IP wins when present - it's the only address in
# $DefaultLanIps that resolves from both this PC and a phone off the home
# LAN, so a browser tab open on either device gets a working router URL
# without needing to know which network it's currently on. The LAN IP only
# works from other devices on the same home network. Falls back to
# whichever address was actually given, in order, if Tailscale isn't among
# them (e.g. a one-off -LanIp override with just a LAN IP).
$routerIp = $null
if ($TailscaleIp) {
    $routerIp = $LanIp | Where-Object { $_ -eq $TailscaleIp } | Select-Object -First 1
}
if (-not $routerIp) {
    $routerIp = $LanIp | Select-Object -First 1
}
if (-not $routerIp) {
    # No LAN addresses configured: localhost-only.
    $routerIp = "localhost"
}

# web/next.config.ts reads this to build allowedDevOrigins, so both lists
# now come from the same place.
$env:COFFEE_LAN_IP = $LanIp -join ","
$env:NEXT_PUBLIC_ROUTER_URL = "http://${routerIp}:8765"

Write-Host "LAN/Tailscale addresses = $($LanIp -join ', ')"
Write-Host "CORS_ALLOWED_ORIGINS = $($env:CORS_ALLOWED_ORIGINS)"
Write-Host "NEXT_PUBLIC_ROUTER_URL = $($env:NEXT_PUBLIC_ROUTER_URL)"
Write-Host ""

Write-Host "Starting router (port 8765)..."
$routerProc = Start-Process -FilePath "python" `
    -ArgumentList "-m", "uvicorn", "router.app.main:app", "--host", "0.0.0.0", "--port", "8765" `
    -WorkingDirectory $repoRoot `
    -WindowStyle Normal `
    -PassThru

Write-Host "Starting frontend (port 3000)..."
$frontendProc = Start-Process -FilePath "npm.cmd" `
    -ArgumentList "run", "dev", "--", "-H", "0.0.0.0" `
    -WorkingDirectory $webDir `
    -WindowStyle Normal `
    -PassThru

Write-Host ""
Write-Host "Router:   http://localhost:8765  (PID $($routerProc.Id))"
Write-Host "Frontend: http://localhost:3000  (PID $($frontendProc.Id))"
foreach ($ip in $LanIp) {
    Write-Host "LAN:      http://${ip}:3000"
}
Write-Host ""
Write-Host "Press Ctrl+C to stop both services."

function Stop-Tree {
    param([System.Diagnostics.Process]$Process, [string]$Name)

    if ($null -eq $Process) { return }
    if ($Process.HasExited) { return }

    Write-Host "Stopping $Name (PID $($Process.Id))..."
    # /T kills the whole process tree, not just the launched PID - required
    # for the frontend, since npm.cmd's real listener (node.exe) is a child
    # process that Stop-Process/taskkill without /T would leave orphaned.
    & taskkill /PID $Process.Id /T /F 2>$null | Out-Null
}

try {
    while ($true) {
        Start-Sleep -Seconds 1
        if ($routerProc.HasExited) {
            Write-Warning "Router process exited unexpectedly (exit code $($routerProc.ExitCode)). Stopping frontend too."
            break
        }
        if ($frontendProc.HasExited) {
            Write-Warning "Frontend process exited unexpectedly (exit code $($frontendProc.ExitCode)). Stopping router too."
            break
        }
    }
}
finally {
    Write-Host ""
    Write-Host "Stopping router and frontend..."
    Stop-Tree -Process $routerProc -Name "router"
    Stop-Tree -Process $frontendProc -Name "frontend"
    Write-Host "Stopped."
}
