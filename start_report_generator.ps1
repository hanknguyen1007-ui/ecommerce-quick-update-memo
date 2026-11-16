# Starts the Report generator server if not running, then opens the browser on the v4 page (R7, CHARTER
# v4.4: single UI -- "/" now always serves web/v4/index.html). $up also checks the response actually IS
# that page (not just "some server answered"), so a stale server process from before this script/server.py
# were last updated gets restarted instead of silently reused.
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$port = ([regex]::Match((Get-Content "$root\config.toml" -Raw), 'port\s*=\s*(\d+)')).Groups[1].Value
$url  = "http://127.0.0.1:$port/"
$up = { try { (Invoke-WebRequest $url -UseBasicParsing -TimeoutSec 2).Content -match 'Report generator v4' } catch { $false } }
if (-not (& $up)) {
    Start-Process python -ArgumentList '-I', "`"$root\server.py`"" -WorkingDirectory $root -WindowStyle Hidden
    1..40 | ForEach-Object { if (& $up) { return }; Start-Sleep -Milliseconds 250 }
}
Start-Process $url
