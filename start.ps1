<#
.SYNOPSIS
    Automated Resume Analysis System — Unified Startup & Cloudflare Tunnel Script (Windows PowerShell)
.DESCRIPTION
    Windows PowerShell equivalent of start.sh for Mariwasa Siam Ceramics Inc.
    1. Validates prerequisites (Docker Desktop / Engine, Docker Compose, .env, directories, cloudflared)
    2. Starts or builds all application containers (DB, Redis, Backend, Worker, Frontend)
    3. Sets up & verifies Cloudflare Tunnel (Custom Domain e.g. mariwasa.bid or Quick Tunnel)
    4. Updates .env (PUBLIC_BASE_URL & FRONTEND_URL CORS whitelist) without UTF-8 BOM
    5. Recreates backend and worker so the live tunnel URL takes effect immediately
    6. Verifies database & service health and displays the access dashboard
.EXAMPLE
    .\start.ps1
    .\start.ps1 -Quick
    .\start.ps1 --quick
    .\start.ps1 --logs backend
    .\start.ps1 --stop
#>

$ErrorActionPreference = "Stop"

# Ensure UTF-8 console output where supported
try {
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
} catch {}

# --- Project Paths & Config ---
$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectDir

$EnvFile = Join-Path $ProjectDir ".env"
$EnvExample = Join-Path $ProjectDir ".env.example"

$TunnelContainer = "resume_analysis_tunnel"
$BackendContainer = "resume_analysis_backend"
$WorkerContainer = "resume_analysis_worker"
$DbContainer = "resume_analysis_db"
$RedisContainer = "resume_analysis_redis"
$FrontendContainer = "resume_analysis_frontend"
$TempDir = if ($env:TEMP) { $env:TEMP } else { [System.IO.Path]::GetTempPath() }
$CloudflaredPidFile = Join-Path $TempDir "cloudflared_custom.pid"
$CloudflaredLogFile = Join-Path $TempDir "cloudflared_custom.log"

$script:DockerComposeCmd = @()
$script:ActiveTunnelUrl = ""

# --- Helper: Read a key from .env ---
function Get-EnvValue {
    param(
        [string]$Key,
        [string]$Default = ""
    )
    if (-not (Test-Path $EnvFile)) { return $Default }
    $lines = Get-Content -Path $EnvFile -ErrorAction SilentlyContinue
    foreach ($line in $lines) {
        if ($line -match "^\s*#") { continue }
        if ($line -match "^\s*$([regex]::Escape($Key))=(.*)$") {
            return $Matches[1].Trim().Trim('"').Trim("'")
        }
    }
    return $Default
}

# --- Helper: Upsert a key in .env (UTF-8 without BOM) ---
function Set-EnvValue {
    param(
        [string]$Key,
        [string]$Value
    )
    $lines = @()
    if (Test-Path $EnvFile) {
        $lines = [System.Collections.Generic.List[string]]@(Get-Content -Path $EnvFile)
    } else {
        $lines = [System.Collections.Generic.List[string]]@()
    }

    $pattern = "^$([regex]::Escape($Key))="
    $updated = $false
    for ($i = 0; $i -lt $lines.Count; $i++) {
        if ($lines[$i] -match $pattern) {
            $lines[$i] = "$Key=$Value"
            $updated = $true
            break
        }
    }
    if (-not $updated) {
        $lines.Add("$Key=$Value")
    }

    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllLines($EnvFile, $lines, $utf8NoBom)
}

# --- Helper: Detect Docker Compose ---
function Initialize-DockerCompose {
    $null = & docker compose version 2>$null
    if ($LASTEXITCODE -eq 0) {
        $script:DockerComposeCmd = @("docker", "compose")
        return
    }
    if (Get-Command "docker-compose" -ErrorAction SilentlyContinue) {
        $script:DockerComposeCmd = @("docker-compose")
        return
    }
    Write-Host "X Error: Neither 'docker compose' (v2 plugin) nor 'docker-compose' (v1) was found." -ForegroundColor Red
    Write-Host "Please install Docker Desktop for Windows: https://docs.docker.com/desktop/install/windows-install/" -ForegroundColor Yellow
    exit 1
}

function Invoke-Compose {
    param(
        [Parameter(ValueFromRemainingArguments = $true)]
        [string[]]$ComposeArgs
    )
    $exe = $script:DockerComposeCmd[0]
    $prefix = @()
    if ($script:DockerComposeCmd.Count -gt 1) {
        $prefix = $script:DockerComposeCmd[1..($script:DockerComposeCmd.Count - 1)]
    }
    & $exe @($prefix + $ComposeArgs)
}

# --- Banner ---
function Show-Banner {
    Write-Host ""
    Write-Host "  ===============================================================" -ForegroundColor Cyan
    Write-Host "               Automated Resume Analysis System                  " -ForegroundColor Cyan
    Write-Host "          Mariwasa Siam Ceramics Inc. - Service Runner           " -ForegroundColor Cyan
    Write-Host "  ===============================================================" -ForegroundColor Cyan
    Write-Host ""
}

# --- Help ---
function Show-Help {
    Show-Banner
    Write-Host "Usage: .\start.ps1 [OPTION]" -ForegroundColor White
    Write-Host ""
    Write-Host "Options:" -ForegroundColor White
    Write-Host "  (no flags)          Default: Check, build & start all services, auto-seed missing data, setup Cloudflare tunnel" -ForegroundColor Green
    Write-Host "  -q, --quick, -Quick Fast start: Start existing containers without rebuilding images" -ForegroundColor Green
    Write-Host "  -b, --rebuild       Force clean rebuild of all container images (--no-cache)" -ForegroundColor Green
    Write-Host "  -r, --restart       Restart all containers and re-verify Cloudflare tunnel" -ForegroundColor Green
    Write-Host "  -s, --stop          Gracefully stop and take down all containers" -ForegroundColor Green
    Write-Host "  --status            Show current health of all containers, domain, and tunnel" -ForegroundColor Green
    Write-Host "  --logs [svc]        View logs (e.g. .\start.ps1 --logs backend or .\start.ps1 --logs frontend)" -ForegroundColor Green
    Write-Host "  --seed              Run idempotent database & ML seeds (jobs, HR/Admin accounts, templates, configs)" -ForegroundColor Green
    Write-Host "  --no-seed           Skip automatic database seeding during startup" -ForegroundColor Green
    Write-Host "  --no-tunnel         Start local services without Cloudflare tunnel" -ForegroundColor Green
    Write-Host "  -h, --help          Show this help menu" -ForegroundColor Green
    Write-Host ""
}

# --- Pre-flight Checks ---
function Invoke-PreflightChecks {
    Write-Host "[1/6] Running system pre-flight checks..." -ForegroundColor Blue

    if (-not (Get-Command "docker" -ErrorAction SilentlyContinue)) {
        Write-Host "  X Docker is not installed or not in PATH." -ForegroundColor Red
        Write-Host "  Please install Docker Desktop for Windows: https://docs.docker.com/desktop/install/windows-install/" -ForegroundColor Yellow
        exit 1
    }

    $prevEAP = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    $null = & docker info 2>$null
    $dockerOk = ($LASTEXITCODE -eq 0)
    $ErrorActionPreference = $prevEAP

    if (-not $dockerOk) {
        Write-Host "  X Docker daemon is not running." -ForegroundColor Red
        Write-Host "  Please start Docker Desktop and wait until it shows 'Running'." -ForegroundColor Yellow
        exit 1
    }

    Initialize-DockerCompose

    if (-not (Test-Path $EnvFile)) {
        if (Test-Path $EnvExample) {
            Write-Host "  ! .env file not found. Initializing from .env.example..." -ForegroundColor Yellow
            Copy-Item -Path $EnvExample -Destination $EnvFile
            Write-Host "  OK Created .env file" -ForegroundColor Green
        } else {
            Write-Host "  X Missing .env and .env.example! Cannot start services." -ForegroundColor Red
            exit 1
        }
    }

    $resumesDir = Join-Path $ProjectDir "uploads\resumes"
    $resumeImagesDir = Join-Path $ProjectDir "uploads\resume_images"
    $physicalResumesDir = Join-Path $ProjectDir "uploads\physical_resumes"
    $exportsDir = Join-Path $ProjectDir "exports"
    $dataDir = Join-Path $ProjectDir "backend\data"
    New-Item -ItemType Directory -Force -Path $resumesDir | Out-Null
    New-Item -ItemType Directory -Force -Path $resumeImagesDir | Out-Null
    New-Item -ItemType Directory -Force -Path $physicalResumesDir | Out-Null
    New-Item -ItemType Directory -Force -Path $exportsDir | Out-Null
    New-Item -ItemType Directory -Force -Path $dataDir | Out-Null

    $customDomain = Get-EnvValue -Key "CUSTOM_DOMAIN"
    if (-not [string]::IsNullOrWhiteSpace($customDomain)) {
        if (Get-Command "cloudflared" -ErrorAction SilentlyContinue) {
            Write-Host "  OK Cloudflare connector CLI (cloudflared) detected" -ForegroundColor Green
        } else {
            Write-Host "  ! Note: 'cloudflared' binary not found in PATH." -ForegroundColor Yellow
        }
    }

    Write-Host "  OK Pre-flight checks passed" -ForegroundColor Green
    Write-Host ""
}

# --- Health Waiters ---
function Wait-ForDb {
    Write-Host "  ... waiting for PostgreSQL to be ready"
    $dbUser = Get-EnvValue -Key "DB_USER" -Default "postgres"
    $dbName = Get-EnvValue -Key "DB_NAME" -Default "automated_resume_db"
    $prevEAP = $ErrorActionPreference
    $ErrorActionPreference = "Continue"

    for ($i = 0; $i -lt 30; $i++) {
        $null = Invoke-Compose exec -T db pg_isready -U $dbUser -d $dbName 2>$null
        if ($LASTEXITCODE -eq 0) {
            $ErrorActionPreference = $prevEAP
            return $true
        }
        Start-Sleep -Seconds 1
    }

    $ErrorActionPreference = $prevEAP
    return $false
}

function Wait-ForRedis {
    Write-Host "  ... waiting for Redis to be ready"
    $prevEAP = $ErrorActionPreference
    $ErrorActionPreference = "Continue"

    for ($i = 0; $i -lt 20; $i++) {
        $null = Invoke-Compose exec -T redis redis-cli ping 2>$null
        if ($LASTEXITCODE -eq 0) {
            $ErrorActionPreference = $prevEAP
            return $true
        }
        Start-Sleep -Seconds 1
    }

    $ErrorActionPreference = $prevEAP
    return $false
}

function Wait-ForHttpEndpoint {
    param(
        [string]$Url,
        [int]$MaxRetries = 30
    )
    for ($i = 0; $i -lt $MaxRetries; $i++) {
        try {
            $resp = Invoke-WebRequest -Uri $Url -Method Get -TimeoutSec 3 -UseBasicParsing -ErrorAction Stop
            if ($resp.StatusCode -ge 200 -and $resp.StatusCode -lt 400) {
                return $true
            }
        } catch {}
        Start-Sleep -Seconds 1
    }
    return $false
}

# --- Start Application Containers ---
function Start-AppContainers {
    param([string]$Mode = "build")

    Write-Host "[2/6] Starting application services..." -ForegroundColor Blue
    $customDomain = Get-EnvValue -Key "CUSTOM_DOMAIN"

    if ($Mode -eq "rebuild") {
        Write-Host "  * Rebuilding all container images (clean)..."
        Invoke-Compose build --no-cache
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
        Invoke-Compose up -d
    } elseif ($Mode -eq "quick") {
        Write-Host "  * Quick start (using existing images)..."
        Invoke-Compose up -d
    } else {
        Write-Host "  * Building and starting containers..."
        Invoke-Compose up -d --build
    }
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    if (-not [string]::IsNullOrWhiteSpace($customDomain)) {
        $prevEAP = $ErrorActionPreference
        $ErrorActionPreference = "Continue"
        $null = Invoke-Compose stop tunnel 2>$null
        $ErrorActionPreference = $prevEAP
    }

    if (-not (Wait-ForDb)) {
        Write-Host "  X PostgreSQL failed to become healthy within timeout." -ForegroundColor Red
        Write-Host "  Check logs: docker compose logs db" -ForegroundColor Yellow
        exit 1
    }
    Write-Host "  OK PostgreSQL is healthy" -ForegroundColor Green

    if (-not (Wait-ForRedis)) {
        Write-Host "  X Redis failed to become healthy within timeout." -ForegroundColor Red
        Write-Host "  Check logs: docker compose logs redis" -ForegroundColor Yellow
        exit 1
    }
    Write-Host "  OK Redis is healthy" -ForegroundColor Green

    Write-Host "  ... waiting for FastAPI backend to respond"
    if (-not (Wait-ForHttpEndpoint -Url "http://localhost:8000/" -MaxRetries 35)) {
        Write-Host "  X Backend failed to start within timeout." -ForegroundColor Red
        Write-Host "  Check logs: docker compose logs backend" -ForegroundColor Yellow
        exit 1
    }
    Write-Host "  OK Backend is healthy (port 8000)" -ForegroundColor Green

    $httpPort = Get-EnvValue -Key "HTTP_PORT" -Default "8080"
    Write-Host "  ... waiting for Frontend (Nginx) to respond"
    if (-not (Wait-ForHttpEndpoint -Url "http://localhost:$httpPort/" -MaxRetries 20)) {
        Write-Host "  X Frontend failed to start within timeout." -ForegroundColor Red
        Write-Host "  Check logs: docker compose logs frontend" -ForegroundColor Yellow
        exit 1
    }
    Write-Host "  OK Frontend is healthy (port $httpPort)" -ForegroundColor Green
    Write-Host ""
}

# --- Setup & Verify Cloudflare Tunnel ---
function Setup-CloudflareTunnel {
    Write-Host "[3/6] Setting up & verifying Cloudflare Tunnel..." -ForegroundColor Blue

    $customDomain = Get-EnvValue -Key "CUSTOM_DOMAIN"
    $tunnelToken = Get-EnvValue -Key "CLOUDFLARE_TUNNEL_TOKEN"

    if (-not [string]::IsNullOrWhiteSpace($customDomain)) {
        Write-Host "  Custom Domain: https://$customDomain" -ForegroundColor Cyan

        $prevEAP = $ErrorActionPreference
        $ErrorActionPreference = "Continue"
        $null = Invoke-Compose stop tunnel 2>$null
        $ErrorActionPreference = $prevEAP

        $cloudflaredExe = Get-Command "cloudflared" -ErrorAction SilentlyContinue
        if ($cloudflaredExe) {
            $svc = Get-Service -Name "cloudflared" -ErrorAction SilentlyContinue
            if ($svc -and $svc.Status -eq "Running") {
                Write-Host "  OK Cloudflare Windows service (cloudflared) is active and running" -ForegroundColor Green
            } else {
                if ($svc) {
                    Write-Host "  * Cloudflare Windows service is stopped. Attempting to start..." -ForegroundColor Yellow
                    try {
                        Start-Service -Name "cloudflared" -ErrorAction Stop
                        Start-Sleep -Seconds 2
                    } catch {}
                    $svc = Get-Service -Name "cloudflared" -ErrorAction SilentlyContinue
                }

                if (-not ($svc -and $svc.Status -eq "Running")) {
                    if (-not [string]::IsNullOrWhiteSpace($tunnelToken)) {
                        Write-Host "  * Starting cloudflared tunnel connector in background..."
                        $proc = Start-Process -FilePath $cloudflaredExe.Source `
                            -ArgumentList @("tunnel", "--no-autoupdate", "run", "--token", $tunnelToken) `
                            -RedirectStandardOutput $CloudflaredLogFile `
                            -RedirectStandardError "$CloudflaredLogFile.err" `
                            -WindowStyle Hidden `
                            -PassThru
                        $proc.Id | Out-File -FilePath $CloudflaredPidFile -Encoding ascii
                        Start-Sleep -Seconds 3
                        Write-Host "  OK Cloudflare connector running (PID $($proc.Id))" -ForegroundColor Green
                    } else {
                        Write-Host "  ! Notice: Please start the cloudflared service or provide CLOUDFLARE_TUNNEL_TOKEN in .env" -ForegroundColor Yellow
                    }
                }
            }
        }

        $script:ActiveTunnelUrl = "https://$customDomain"
        Write-Host "  ... verifying public reachability at $($script:ActiveTunnelUrl)"
        $reachable = $false
        $statusCode = "000"
        for ($i = 0; $i -lt 8; $i++) {
            try {
                $resp = Invoke-WebRequest -Uri $script:ActiveTunnelUrl -Method Head -TimeoutSec 6 -UseBasicParsing -ErrorAction Stop
                $statusCode = [string]$resp.StatusCode
                if ($resp.StatusCode -ge 200 -and $resp.StatusCode -lt 400) {
                    $reachable = $true
                    break
                }
            } catch {
                if ($_.Exception.Response) {
                    $statusCode = [string][int]$_.Exception.Response.StatusCode
                }
            }
            Start-Sleep -Seconds 2
        }

        if ($reachable) {
            Write-Host "  OK Custom domain is LIVE and reachable! (HTTP $statusCode)" -ForegroundColor Green
        } elseif ($statusCode -eq "530" -or $statusCode -eq "1016") {
            Write-Host "  ! DNS/Tunnel route propagating at Cloudflare edge (HTTP $statusCode). Will be live shortly." -ForegroundColor Yellow
        } else {
            Write-Host "  ! Domain status: HTTP $statusCode. Tunnel is active and routing." -ForegroundColor Yellow
        }
    } else {
        Write-Host "  * Initializing clean Cloudflare quick tunnel connection..."
        $prevEAP = $ErrorActionPreference
        $ErrorActionPreference = "Continue"
        $null = Invoke-Compose stop tunnel 2>$null
        $null = Invoke-Compose rm -f tunnel 2>$null
        $null = Invoke-Compose up -d tunnel 2>$null
        $ErrorActionPreference = $prevEAP

        $script:ActiveTunnelUrl = ""
        $maxWait = 45
        $waited = 0

        while ([string]::IsNullOrWhiteSpace($script:ActiveTunnelUrl) -and $waited -lt $maxWait) {
            Start-Sleep -Seconds 2
            $waited += 2
            $logs = & docker logs $TunnelContainer 2>&1 | Out-String
            $urlMatches = [regex]::Matches($logs, 'https://[a-zA-Z0-9-]+\.trycloudflare\.com')
            if ($urlMatches.Count -gt 0) {
                $script:ActiveTunnelUrl = $urlMatches[$urlMatches.Count - 1].Value
            } else {
                Write-Host "  ... waiting for Cloudflare edge assignment ($waited/${maxWait}s)"
            }
        }

        if ([string]::IsNullOrWhiteSpace($script:ActiveTunnelUrl)) {
            Write-Host "  X Error: Could not detect Cloudflare Tunnel URL after ${maxWait}s" -ForegroundColor Red
            Write-Host "  Check tunnel logs: docker logs $TunnelContainer" -ForegroundColor Yellow
            exit 1
        }

        Write-Host "  OK Tunnel created: $($script:ActiveTunnelUrl)" -ForegroundColor Green

        $reachable = $false
        for ($i = 0; $i -lt 8; $i++) {
            try {
                $resp = Invoke-WebRequest -Uri $script:ActiveTunnelUrl -Method Head -TimeoutSec 8 -UseBasicParsing -ErrorAction Stop
                if ($resp.StatusCode -ge 200 -and $resp.StatusCode -lt 400) {
                    $reachable = $true
                    break
                }
            } catch {}
            Start-Sleep -Seconds 2
        }
        if ($reachable) {
            Write-Host "  OK Quick tunnel is active and reachable over the internet!" -ForegroundColor Green
        }
    }

    Write-Host ""
}

# --- Synchronize .env with Tunnel URL ---
function Sync-EnvFile {
    param([string]$TunnelUrl)
    Write-Host "[4/6] Synchronizing .env configuration..." -ForegroundColor Blue

    Set-EnvValue -Key "PUBLIC_BASE_URL" -Value $TunnelUrl
    Write-Host "  OK PUBLIC_BASE_URL set to $TunnelUrl" -ForegroundColor Green

    $httpPort = Get-EnvValue -Key "HTTP_PORT" -Default "8080"
    $defaultOrigins = "http://localhost:5173,http://localhost:3000,http://localhost,http://localhost:80,http://localhost:$httpPort"
    $customDomain = Get-EnvValue -Key "CUSTOM_DOMAIN"

    $targetOrigins = $defaultOrigins
    if (-not [string]::IsNullOrWhiteSpace($customDomain)) {
        $targetOrigins = "$targetOrigins,https://$customDomain,https://www.$customDomain"
    }
    if (-not [string]::IsNullOrWhiteSpace($TunnelUrl) -and ($TunnelUrl -notlike "*//$customDomain*")) {
        $targetOrigins = "$targetOrigins,$TunnelUrl"
    }

    Set-EnvValue -Key "FRONTEND_URL" -Value $targetOrigins
    Write-Host "  OK FRONTEND_URL CORS origins updated with active domain" -ForegroundColor Green
    Write-Host ""
}

# --- Recreate Backend & Worker ---
function Apply-EnvironmentChanges {
    Write-Host "[5/6] Applying environment configuration to Backend & AI Worker..." -ForegroundColor Blue
    $prevEAP = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    $null = Invoke-Compose up -d --force-recreate backend celery_worker 2>$null
    $ErrorActionPreference = $prevEAP

    if (-not (Wait-ForHttpEndpoint -Url "http://localhost:8000/" -MaxRetries 35)) {
        Write-Host "  X Backend failed to recover after environment update." -ForegroundColor Red
        Write-Host "  Check logs: docker compose logs backend" -ForegroundColor Yellow
        exit 1
    }

    Write-Host "  OK Backend & AI Worker restarted with new domain configuration" -ForegroundColor Green
    Write-Host ""
}

# --- Verify Database & Auto-Seed ---
function Verify-Database {
    param([bool]$AutoSeed = $true)
    Write-Host "[6/6] Verifying database integrity & seed data..." -ForegroundColor Blue
    $pyCode = @"
import asyncio, os
from app.utils.database import AsyncSessionLocal
from sqlalchemy import text
async def check_counts():
    try:
        async with AsyncSessionLocal() as session:
            jobs = (await session.execute(text('SELECT count(*) FROM job_descriptions'))).scalar() or 0
            staff = (await session.execute(text("SELECT count(*) FROM users WHERE role IN ('HR', 'ADMIN')"))).scalar() or 0
            tpls = (await session.execute(text('SELECT count(*) FROM form_templates'))).scalar() or 0
            cfgs = (await session.execute(text('SELECT count(*) FROM system_configs'))).scalar() or 0
            has_ml = 1 if os.path.exists('data/production_model.pkl') else 0
            return f'{jobs}|{staff}|{tpls}|{cfgs}|{has_ml}'
    except Exception:
        return '0|0|0|0|0'
print(asyncio.run(check_counts()))
"@
    $prevEAP = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    $rawCounts = Invoke-Compose exec -T backend python -c $pyCode 2>$null
    $ErrorActionPreference = $prevEAP

    $parts = (($rawCounts | Out-String).Trim()) -split '\|'
    $jobCount = 0; $staffCount = 0; $tplCount = 0; $cfgCount = 0; $hasMl = 0
    if ($parts.Length -ge 5) {
        [void][int]::TryParse($parts[0], [ref]$jobCount)
        [void][int]::TryParse($parts[1], [ref]$staffCount)
        [void][int]::TryParse($parts[2], [ref]$tplCount)
        [void][int]::TryParse($parts[3], [ref]$cfgCount)
        [void][int]::TryParse($parts[4], [ref]$hasMl)
    }

    if ($jobCount -eq 0 -or $staffCount -eq 0 -or $tplCount -eq 0 -or $cfgCount -eq 0 -or $hasMl -eq 0) {
        if ($AutoSeed) {
            Write-Host "  ! Missing initial seed data (jobs=$jobCount, staff=$staffCount, templates=$tplCount, configs=$cfgCount, ml=$hasMl)." -ForegroundColor Yellow
            Write-Host "  Automatically seeding jobs, HR/Admin accounts, templates, configs & ML model..." -ForegroundColor Cyan
            Invoke-Compose exec -T backend python scripts/seed_defaults.py
            if ($LASTEXITCODE -ne 0) {
                Write-Host "  ! Warning: Seeding returned exit code $LASTEXITCODE" -ForegroundColor Yellow
            }
        } else {
            Write-Host "  ! Initial seed data incomplete (jobs=$jobCount, staff=$staffCount). Skipped due to --no-seed." -ForegroundColor Yellow
            Write-Host "  Tip: Run .\start.ps1 --seed anytime to populate jobs, accounts, and configs." -ForegroundColor Cyan
        }
    } else {
        Write-Host "  OK Database verified ($jobCount jobs, $staffCount HR/Admin accounts, $tplCount form templates, $cfgCount configs, ML model ready)" -ForegroundColor Green
    }
    Write-Host ""
}

# --- Run Seeds ---
function Invoke-Seeds {
    Show-Banner
    Invoke-PreflightChecks
    Write-Host "Running Unified Database & ML Seeds (Jobs, HR/Admin Accounts, Templates, Configs)..." -ForegroundColor Blue
    Write-Host ""

    Invoke-Compose up -d db redis backend | Out-Null
    if (-not (Wait-ForDb)) {
        Write-Host "  X PostgreSQL failed to become ready." -ForegroundColor Red
        exit 1
    }
    if (-not (Wait-ForHttpEndpoint -Url "http://localhost:8000/" -MaxRetries 35)) {
        Write-Host "  X Backend failed to become ready." -ForegroundColor Red
        exit 1
    }

    Invoke-Compose exec -T backend python scripts/seed_defaults.py
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    Write-Host ""
    Write-Host "OK Seeding complete!" -ForegroundColor Green
}

# --- Show Status ---
function Show-AppStatus {
    Show-Banner
    Invoke-PreflightChecks
    Write-Host "Container Status:" -ForegroundColor White
    Invoke-Compose ps
    Write-Host ""

    $customDomain = Get-EnvValue -Key "CUSTOM_DOMAIN"
    $envTunnelUrl = Get-EnvValue -Key "PUBLIC_BASE_URL"

    Write-Host "Tunnel & Domain Status:" -ForegroundColor White
    if (-not [string]::IsNullOrWhiteSpace($customDomain)) {
        Write-Host "  Mode:                  Purchased Custom Domain ($customDomain)" -ForegroundColor Green
        Write-Host "  Configured in .env:    $envTunnelUrl" -ForegroundColor Cyan
        $svc = Get-Service -Name "cloudflared" -ErrorAction SilentlyContinue
        if ($svc -and $svc.Status -eq "Running") {
            Write-Host "  Connector Service:     cloudflared Windows service is ACTIVE" -ForegroundColor Green
        } elseif (Test-Path $CloudflaredPidFile) {
            $pidVal = Get-Content $CloudflaredPidFile -ErrorAction SilentlyContinue
            Write-Host "  Connector Process:     Running in background (PID $pidVal)" -ForegroundColor Green
        } else {
            Write-Host "  Connector Service:     INACTIVE" -ForegroundColor Yellow
        }

        $statusCode = "000"
        try {
            $resp = Invoke-WebRequest -Uri "https://$customDomain" -Method Head -TimeoutSec 5 -UseBasicParsing -ErrorAction Stop
            $statusCode = [string]$resp.StatusCode
        } catch {
            if ($_.Exception.Response) {
                $statusCode = [string][int]$_.Exception.Response.StatusCode
            }
        }
        if ($statusCode -eq "200" -or $statusCode -eq "301" -or $statusCode -eq "302") {
            Write-Host "  Public Reachability:   Online & Responding (HTTP $statusCode)" -ForegroundColor Green
        } else {
            Write-Host "  Public Reachability:   HTTP $statusCode (connecting or propagating)" -ForegroundColor Yellow
        }
    } else {
        $logs = & docker logs $TunnelContainer 2>&1 | Out-String
        $urlMatches = [regex]::Matches($logs, 'https://[a-zA-Z0-9-]+\.trycloudflare\.com')
        if ($urlMatches.Count -gt 0) {
            $tunnelUrl = $urlMatches[$urlMatches.Count - 1].Value
            Write-Host "  Mode:                  Quick Tunnel (trycloudflare.com)" -ForegroundColor Yellow
            Write-Host "  Active URL:            $tunnelUrl" -ForegroundColor Green
            Write-Host "  Configured in .env:    $envTunnelUrl" -ForegroundColor Cyan
            if (Wait-ForHttpEndpoint -Url $tunnelUrl -MaxRetries 1) {
                Write-Host "  Reachability:          Online & Responding (200 OK)" -ForegroundColor Green
            } else {
                Write-Host "  Reachability:          Connecting / Not responding yet" -ForegroundColor Yellow
            }
        } else {
            Write-Host "  No active tunnel found. Run .\start.ps1 to start it." -ForegroundColor Red
        }
    }
    Write-Host ""
}

# --- Stop Services ---
function Stop-AppServices {
    Show-Banner
    Initialize-DockerCompose
    Write-Host "Stopping all Automated Resume Analysis services..." -ForegroundColor Yellow
    Invoke-Compose down
    if (Test-Path $CloudflaredPidFile) {
        $pidVal = (Get-Content $CloudflaredPidFile -ErrorAction SilentlyContinue | Out-String).Trim()
        if ($pidVal -match "^\d+$") {
            Stop-Process -Id ([int]$pidVal) -Force -ErrorAction SilentlyContinue
        }
        Remove-Item -Path $CloudflaredPidFile -Force -ErrorAction SilentlyContinue
    }
    Write-Host "OK All services stopped." -ForegroundColor Green
}

# --- View Logs ---
function Show-AppLogs {
    param([string]$Service = "")
    Initialize-DockerCompose
    if (-not [string]::IsNullOrWhiteSpace($Service)) {
        Write-Host "Streaming logs for service: $Service (Ctrl+C to exit)..." -ForegroundColor Cyan
        Invoke-Compose logs -f $Service
    } else {
        Write-Host "Streaming logs for all services (Ctrl+C to exit)..." -ForegroundColor Cyan
        Invoke-Compose logs -f
    }
}

# --- Display Final Dashboard ---
function Show-Dashboard {
    param([string]$TunnelUrl)
    $customDomain = Get-EnvValue -Key "CUSTOM_DOMAIN"
    $httpPort = Get-EnvValue -Key "HTTP_PORT" -Default "8080"

    Write-Host "=================================================================" -ForegroundColor Green
    Write-Host "              APPLICATION READY & RUNNING!                       " -ForegroundColor Green
    Write-Host "=================================================================" -ForegroundColor Green
    Write-Host ""
    if (-not [string]::IsNullOrWhiteSpace($customDomain)) {
        Write-Host "  PUBLIC DOMAIN:            https://$customDomain" -ForegroundColor Cyan
        Write-Host "  WWW DOMAIN:               https://www.$customDomain" -ForegroundColor Cyan
    } elseif (-not [string]::IsNullOrWhiteSpace($TunnelUrl)) {
        Write-Host "  PUBLIC URL (Cloudflare):  $TunnelUrl" -ForegroundColor Cyan
    } else {
        Write-Host "  PUBLIC TUNNEL:            Disabled (--no-tunnel)" -ForegroundColor Yellow
    }
    Write-Host "  LOCAL FRONTEND:           http://localhost:$httpPort" -ForegroundColor White
    Write-Host "  FASTAPI DOCS (Swagger):   http://localhost:8000/docs" -ForegroundColor White
    Write-Host "  POSTGRESQL PORT:          localhost:5434" -ForegroundColor White
    Write-Host "  REDIS CACHE PORT:         localhost:6380" -ForegroundColor White
    Write-Host ""
    if (-not [string]::IsNullOrWhiteSpace($TunnelUrl)) {
        Write-Host "  GOOGLE OAUTH CONFIGURATION:" -ForegroundColor Yellow
        Write-Host "     If using Google Login, add this authorized redirect URI in"
        Write-Host "     Google Cloud Console (Credentials > Authorized redirect URIs):"
        Write-Host "     $TunnelUrl/api/auth/google/callback" -ForegroundColor White
        Write-Host ""
    }
    Write-Host "  HELPFUL COMMANDS:" -ForegroundColor White
    Write-Host "     View status:   .\start.ps1 --status" -ForegroundColor Green
    Write-Host "     Run seeds:     .\start.ps1 --seed" -ForegroundColor Green
    Write-Host "     Stream logs:   .\start.ps1 --logs (or .\start.ps1 --logs backend)" -ForegroundColor Green
    Write-Host "     Stop app:      .\start.ps1 --stop" -ForegroundColor Green
    Write-Host "     Restart app:   .\start.ps1 --restart" -ForegroundColor Green
    Write-Host "=================================================================" -ForegroundColor Green
    Write-Host ""
}

# ==============================================================================
# Main Argument Dispatcher
# ==============================================================================
$mode = "build"
$autoSeed = $true
$useTunnel = $true
$i = 0
while ($i -lt $args.Count) {
    $arg = [string]$args[$i]
    switch -Regex ($arg.ToLowerInvariant()) {
        "^(-h|--help|-help|help|\?)$" {
            Show-Help
            exit 0
        }
        "^(-s|--stop|-stop|stop|down)$" {
            Stop-AppServices
            exit 0
        }
        "^(--status|-status|status)$" {
            Show-AppStatus
            exit 0
        }
        "^(--seed|-seed|seed)$" {
            Invoke-Seeds
            exit 0
        }
        "^(--no-seed|-noseed)$" {
            $autoSeed = $false
        }
        "^(--no-tunnel|-notunnel)$" {
            $useTunnel = $false
        }
        "^(-l|--logs|-logs|logs)$" {
            $svc = ""
            if (($i + 1) -lt $args.Count) {
                $svc = [string]$args[$i + 1]
            }
            Show-AppLogs -Service $svc
            exit 0
        }
        "^(-q|--quick|-quick|quick)$" {
            $mode = "quick"
        }
        "^(-b|--rebuild|-rebuild|rebuild)$" {
            $mode = "rebuild"
        }
        "^(-r|--restart|-restart|restart)$" {
            $mode = "restart"
        }
        "^(start|up)$" {
            # default build/up
        }
        default {
            Write-Host "Unknown option: $arg" -ForegroundColor Red
            Show-Help
            exit 1
        }
    }
    $i++
}

Show-Banner
Invoke-PreflightChecks

if ($mode -eq "restart") {
    Write-Host "Restarting all services..." -ForegroundColor Yellow
    Invoke-Compose down
    $mode = "quick"
}

Start-AppContainers -Mode $mode
$httpPort = Get-EnvValue -Key "HTTP_PORT" -Default "8080"
if ($useTunnel) {
    Setup-CloudflareTunnel
    Sync-EnvFile -TunnelUrl $script:ActiveTunnelUrl
    Apply-EnvironmentChanges
} else {
    Write-Host "[3/6] Cloudflare Tunnel skipped (--no-tunnel)." -ForegroundColor Blue
    Sync-EnvFile -TunnelUrl "http://localhost:$httpPort"
    Apply-EnvironmentChanges
    $script:ActiveTunnelUrl = ""
}
Verify-Database -AutoSeed $autoSeed
Show-Dashboard -TunnelUrl $script:ActiveTunnelUrl
