$ErrorActionPreference = "Continue"
$root = $PSScriptRoot

Write-Host "=== Stopping any old processes on 6379, 8000, 5173 ==="
$ports = @(6379, 8000, 5173)
foreach ($p in $ports) {
    $conns = Get-NetTCPConnection -LocalPort $p -ErrorAction SilentlyContinue
    if ($conns) {
        $pids = $conns | Select-Object -ExpandProperty OwningProcess -Unique
        foreach ($procId in $pids) {
            if ($procId -gt 0) {
                Write-Host "Killing old process $procId on port $p"
                Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
            }
        }
    }
}
Start-Sleep -Seconds 1

Write-Host "=== 1. Starting Redis Server ==="
$redisBin = Join-Path $root "backend\.redis\redis-server.exe"
$redisConf = Join-Path $root "backend\.redis\redis.windows.conf"
$redisProc = Start-Process -FilePath $redisBin -ArgumentList $redisConf -PassThru -WindowStyle Hidden
Write-Host "Redis started (PID: $($redisProc.Id))"
Start-Sleep -Seconds 2

Write-Host "=== 2. Starting FastAPI Backend ==="
$pythonBin = Join-Path $root "backend\.venv\Scripts\python.exe"
$backendDir = Join-Path $root "backend"
$backendProc = Start-Process -FilePath $pythonBin -ArgumentList "-m uvicorn main:app --host 127.0.0.1 --port 8000 --reload" -WorkingDirectory $backendDir -PassThru -WindowStyle Hidden
Write-Host "Backend started (PID: $($backendProc.Id))"

Write-Host "=== 3. Starting Next.js Frontend ==="
$frontendDir = Join-Path $root "frontend"
$frontendProc = Start-Process -FilePath "cmd.exe" -ArgumentList "/c npm run dev" -WorkingDirectory $frontendDir -PassThru -WindowStyle Hidden
Write-Host "Frontend started (PID: $($frontendProc.Id))"

Write-Host "=== 4. Waiting for Backend (http://127.0.0.1:8000/docs) ==="
$backendReady = $false
for ($i = 0; $i -lt 30; $i++) {
    Start-Sleep -Seconds 1
    try {
        $res = Invoke-WebRequest -Uri "http://127.0.0.1:8000/docs" -UseBasicParsing -TimeoutSec 2
        if ($res.StatusCode -eq 200) {
            $backendReady = $true
            break
        }
    } catch {}
}
if ($backendReady) {
    Write-Host "[OK] Backend is listening on 127.0.0.1:8000"
} else {
    Write-Host "[WARN] Backend health check timed out."
}

Write-Host "=== 5. Waiting for Frontend (http://127.0.0.1:5173) ==="
$frontendReady = $false
for ($i = 0; $i -lt 40; $i++) {
    Start-Sleep -Seconds 1
    try {
        $res = Invoke-WebRequest -Uri "http://127.0.0.1:5173" -UseBasicParsing -TimeoutSec 2
        if ($res.StatusCode -ge 200 -and $res.StatusCode -lt 400) {
            $frontendReady = $true
            break
        }
    } catch {}
}
if ($frontendReady) {
    Write-Host "[OK] Frontend is listening on 127.0.0.1:5173"
} else {
    Write-Host "[WARN] Frontend health check timed out."
}

Write-Host "=== 6. Launching Cloudflare Tunnel ==="
$cfBin = "C:\Program Files (x86)\cloudflared\cloudflared.exe"
& $cfBin tunnel --url http://127.0.0.1:5173
