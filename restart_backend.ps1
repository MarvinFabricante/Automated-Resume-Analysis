$conns = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
if ($conns) {
    $pids = $conns | Select-Object -ExpandProperty OwningProcess -Unique
    foreach ($p in $pids) {
        if ($p -gt 0) {
            Write-Host "Stopping process $p on port 8000"
            Stop-Process -Id $p -Force -ErrorAction SilentlyContinue
        }
    }
}
Start-Sleep -Seconds 1

$root = $PSScriptRoot
$pythonBin = Join-Path $root "backend\.venv\Scripts\python.exe"
$backendDir = Join-Path $root "backend"

Start-Process -FilePath $pythonBin -ArgumentList "-m uvicorn main:app --host 127.0.0.1 --port 8000 --reload" -WorkingDirectory $backendDir -WindowStyle Hidden
Start-Sleep -Seconds 3

$ready = $false
for ($i = 0; $i -lt 15; $i++) {
    try {
        $res = Invoke-WebRequest -Uri "http://127.0.0.1:8000/docs" -UseBasicParsing -TimeoutSec 2
        if ($res.StatusCode -eq 200) {
            $ready = $true
            break
        }
    } catch {}
    Start-Sleep -Seconds 1
}

if ($ready) {
    Write-Host "Backend restarted successfully and listening on 127.0.0.1:8000"
} else {
    Write-Host "Backend failed to respond."
}
