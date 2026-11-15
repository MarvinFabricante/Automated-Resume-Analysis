$ErrorActionPreference = "Continue"
$root = $PSScriptRoot

Write-Host "Stopping any previous instances on 6379, 8000, 5173..."
$ports = @(6379, 8000, 5173)
foreach ($p in $ports) {
    $conns = Get-NetTCPConnection -LocalPort $p -ErrorAction SilentlyContinue
    if ($conns) {
        $pids = $conns | Select-Object -ExpandProperty OwningProcess -Unique
        foreach ($procId in $pids) {
            if ($procId -gt 0) {
                Write-Host "Stopping process $procId on port $p..."
                Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
            }
        }
    }
}
Start-Sleep -Seconds 1

Write-Host "1. Starting Redis..."
$redisBin = Join-Path $root "backend\.redis\redis-server.exe"
$redisConf = Join-Path $root "backend\.redis\redis.windows.conf"
Start-Process -FilePath $redisBin -ArgumentList $redisConf -WindowStyle Hidden
Start-Sleep -Seconds 2

Write-Host "2. Starting Backend (FastAPI)..."
$pythonBin = Join-Path $root "backend\.venv\Scripts\python.exe"
$backendDir = Join-Path $root "backend"
$backendLog = Join-Path $root "backend.log"
$backendErr = Join-Path $root "backend_err.log"
Start-Process -FilePath $pythonBin -ArgumentList "-m uvicorn main:app --host 127.0.0.1 --port 8000" -WorkingDirectory $backendDir -WindowStyle Hidden -RedirectStandardOutput $backendLog -RedirectStandardError $backendErr

Write-Host "3. Starting Frontend (Next.js)..."
$frontendDir = Join-Path $root "frontend"
$frontendLog = Join-Path $root "frontend.log"
$frontendErr = Join-Path $root "frontend_err.log"
Start-Process -FilePath "cmd.exe" -ArgumentList "/c npm run dev" -WorkingDirectory $frontendDir -WindowStyle Hidden -RedirectStandardOutput $frontendLog -RedirectStandardError $frontendErr

Write-Host "4. Waiting for Backend to be healthy on port 8000..."
$backendReady = $false
for ($i = 0; $i -lt 20; $i++) {
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
    Write-Host "Backend is READY on http://127.0.0.1:8000"
} else {
    Write-Host "Backend did not respond in time. Checking logs:"
    if (Test-Path $backendErr) { Get-Content $backendErr -Tail 15 }
}

Write-Host "5. Waiting for Frontend to be healthy on port 5173..."
$frontendReady = $false
for ($i = 0; $i -lt 30; $i++) {
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
    Write-Host "Frontend is READY on http://127.0.0.1:5173"
} else {
    Write-Host "Frontend did not respond in time. Checking logs:"
    if (Test-Path $frontendErr) { Get-Content $frontendErr -Tail 15 }
}

Write-Host "Service startup complete."
