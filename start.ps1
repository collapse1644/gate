#requires -Version 5.1
<#
.SYNOPSIS
    Start the GATE CS 2027 Tutor application (backend, local AI server, frontend).

.DESCRIPTION
    This script starts all three components of the GATE CS 2027 Tutor:
    1. FastAPI backend on port 8000
    2. llama.cpp local inference server on port 8080 (via backend manager)
    3. Next.js frontend on port 3000

    It performs pre-flight checks to detect stale processes on the required
    ports and refuses to start if a backend instance is already running.

.PARAMETER BackendPort
    Port for the FastAPI backend (default: 8000).

.PARAMETER LlamaPort
    Port for the llama.cpp server (default: 8080).

.PARAMETER FrontendPort
    Port for the Next.js frontend (default: 3000).

.PARAMETER SkipBackend
    Skip starting the backend (useful if already running externally).

.PARAMETER SkipLlama
    Skip starting the local AI server.

.PARAMETER SkipFrontend
    Skip starting the frontend.

.EXAMPLE
    .\start.ps1
    # Start all components on default ports.

.EXAMPLE
    .\start.ps1 -BackendPort 8001 -LlamaPort 8081 -FrontendPort 3001
    # Start all components on custom ports.

.EXAMPLE
    .\start.ps1 -SkipLlama
    # Start backend and frontend only, without local AI server.

.NOTES
    Run from the project root: G:\MINI-PROJ\gate
    Requires: Python 3.11 venv at backend/.venv, Node.js 24, llama.cpp CUDA build.
#>
[CmdletBinding()]
param(
    [int]$BackendPort = 8000,
    [int]$LlamaPort = 8080,
    [int]$FrontendPort = 3000,
    [switch]$SkipBackend,
    [switch]$SkipLlama,
    [switch]$SkipFrontend
)

$ErrorActionPreference = "Stop"
$script:ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot ".")
$script:BackendDir = Join-Path $script:ProjectRoot "backend"
$script:FrontendDir = Join-Path $script:ProjectRoot "frontend"
$script:PythonExe = Join-Path $script:BackendDir ".venv\Scripts\python.exe"
$script:LogDir = Join-Path $script:ProjectRoot "logs"

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

function Write-Header {
    param([string]$Message)
    Write-Host ""
    Write-Host ("=" * 60)
    Write-Host $Message
    Write-Host ("=" * 60)
}

function Write-Success {
    param([string]$Message)
    Write-Host ("[OK] " + $Message) -ForegroundColor Green
}

function Write-Warning {
    param([string]$Message)
    Write-Host ("[WARN] " + $Message) -ForegroundColor Yellow
}

function Write-Error {
    param([string]$Message)
    Write-Host ("[ERROR] " + $Message) -ForegroundColor Red
}

function Write-Info {
    param([string]$Message)
    Write-Host ("[INFO] " + $Message) -ForegroundColor Cyan
}

# Get the process ID(s) listening on a specific TCP port.
function Get-PortProcessId {
    param([int]$Port)

    $output = netstat -ano 2>$null | Select-String ":$Port"
    if (-not $output) {
        return $null
    }

    $pids = @()
    foreach ($line in $output) {
        # Line format: "  TCP    0.0.0.0:8000      0.0.0.0:0              LISTENING       1234"
        $parts = $line -split "\s+" | Where-Object { $_ -ne "" }
        if ($parts.Count -ge 5 -and $parts[4] -match "^\d+$") {
            $processId = [int]$parts[4]
            $pids += $processId
        }
    }
    return $pids | Select-Object -Unique
}

# Check if a process is still running.
function Test-ProcessAlive {
    param([int]$ProcessId)
    try {
        $proc = Get-Process -Id $ProcessId -ErrorAction SilentlyContinue
        return $null -ne $proc
    } catch {
        return $false
    }
}

# Wait for an HTTP endpoint to become healthy.
function Wait-ForHealth {
    param(
        [string]$Url,
        [int]$TimeoutSeconds = 60,
        [string]$ComponentName = "service"
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    Write-Info "Waiting for $ComponentName at $Url (timeout: ${TimeoutSeconds}s)..."

    while ((Get-Date) -lt $deadline) {
        try {
            $response = Invoke-RestMethod -Uri $Url -Method Get -TimeoutSec 3 -ErrorAction Stop
            if ($response) {
                Write-Success "$ComponentName is healthy at $Url"
                return $true
            }
        } catch {
            # Service not ready yet; keep waiting
        }
        Start-Sleep -Seconds 2
    }

    Write-Error "$ComponentName did not become healthy at $Url within ${TimeoutSeconds}s"
    return $false
}

# Ensure a directory exists.
function Ensure-Dir {
    param([string]$Path)
    if (-not (Test-Path $Path)) {
        New-Item -ItemType Directory -Path $Path -Force | Out-Null
    }
}

# ---------------------------------------------------------------------------
# Pre-flight checks
# ---------------------------------------------------------------------------

Write-Header "GATE CS 2027 Tutor - Startup Pre-flight Checks"

Ensure-Dir $script:LogDir

# Check Python venv
if (-not (Test-Path $script:PythonExe)) {
    Write-Error "Python venv not found at $script:PythonExe"
    Write-Info "Create it with: cd backend && python -m venv .venv && .venv\Scripts\pip install -r requirements.txt"
    exit 1
}
Write-Success "Python venv found"

# Check Node.js
try {
    $nodeVersion = (node --version 2>$null)
    if (-not $nodeVersion) {
        throw "node not found"
    }
    Write-Success "Node.js found: $nodeVersion"
} catch {
    Write-Error "Node.js not found. Install from https://nodejs.org/"
    exit 1
}

# Check npm
try {
    $npmVersion = (npm --version 2>$null)
    if (-not $npmVersion) {
        throw "npm not found"
    }
    Write-Success "npm found: $npmVersion"
} catch {
    Write-Error "npm not found."
    exit 1
}

# Detect stale processes on required ports
Write-Info "Checking ports: backend=$BackendPort, llama=$LlamaPort, frontend=$FrontendPort"

$backendPids = Get-PortProcessId -Port $BackendPort
if ($backendPids) {
    Write-Error "Port $BackendPort is already in use by PID(s): $($backendPids -join ', ')"
    Write-Info "Run .\stop.ps1 to stop existing application processes, or use a different port."
    exit 1
}
Write-Success "Port $BackendPort is available"

$llamaPids = Get-PortProcessId -Port $LlamaPort
if ($llamaPids) {
    Write-Warning "Port $LlamaPort is already in use by PID(s): $($llamaPids -join ', ')"
    Write-Info "A local AI server may already be running. This is acceptable if it is your llama-server."
} else {
    Write-Success "Port $LlamaPort is available"
}

$frontendPids = Get-PortProcessId -Port $FrontendPort
if ($frontendPids) {
    Write-Error "Port $FrontendPort is already in use by PID(s): $($frontendPids -join ', ')"
    Write-Info "Run .\stop.ps1 to stop existing application processes, or use a different port."
    exit 1
}
Write-Success "Port $FrontendPort is available"

# ---------------------------------------------------------------------------
# Start backend
# ---------------------------------------------------------------------------

if (-not $SkipBackend) {
    Write-Header "Starting FastAPI Backend (port $BackendPort)"

    $backendStdoutLog = Join-Path $script:LogDir "backend.stdout.log"
    $backendStderrLog = Join-Path $script:LogDir "backend.stderr.log"
    $backendArgs = @(
        "-m", "uvicorn", "app.main:app",
        "--reload",
        "--port", $BackendPort.ToString()
    )

    try {
        $proc = Start-Process -FilePath $script:PythonExe `
            -ArgumentList $backendArgs `
            -WorkingDirectory $script:BackendDir `
            -RedirectStandardOutput $backendStdoutLog `
            -RedirectStandardError $backendStderrLog `
            -PassThru
        Write-Success "Backend started (PID: $($proc.Id))"
    } catch {
        Write-Error "Failed to start backend: $_"
        exit 1
    }

    $healthUrl = "http://127.0.0.1:$BackendPort/api/health"
    if (-not (Wait-ForHealth -Url $healthUrl -ComponentName "Backend")) {
        Write-Error "Backend health check failed. Check $backendStdoutLog and $backendStderrLog for details."
        exit 1
    }
} else {
    Write-Info "Skipping backend start (-SkipBackend)"
}

# ---------------------------------------------------------------------------
# Start local AI server (llama.cpp)
# ---------------------------------------------------------------------------

if (-not $SkipLlama) {
    Write-Header "Starting Local AI Server (llama.cpp on port $LlamaPort)"

    # Check if llama-server is already managed by the backend
    $statusUrl = "http://127.0.0.1:$BackendPort/api/ai/status"
    try {
        $aiStatus = Invoke-RestMethod -Uri $statusUrl -Method Get -TimeoutSec 5 -ErrorAction Stop
        if ($aiStatus.local.ready -eq $true) {
            Write-Success "Local AI server is already ready (managed by backend)"
        } elseif ($aiStatus.local.server.managed_process -eq $true) {
            Write-Info "Local AI server process is managed but not ready. Waiting..."
            Wait-ForHealth -Url "http://127.0.0.1:$LlamaPort/health" -ComponentName "Local AI Server" -TimeoutSeconds 120
        } else {
            Write-Info "Local AI server not running. Starting via backend manager..."
            $startUrl = "http://127.0.0.1:$BackendPort/api/ai/local/start"
            try {
                $startResp = Invoke-RestMethod -Uri $startUrl -Method Post -TimeoutSec 120 -ErrorAction Stop
                if ($startResp.endpoint_healthy -eq $true) {
                    Write-Success "Local AI server started (PID: $($startResp.pid))"
                } else {
                    Write-Warning "Local AI server start reported: $($startResp.detail)"
                }
            } catch {
                Write-Error "Failed to start local AI server via backend: $_"
                Write-Info "Ensure local_server_path and local_model_path are configured in Settings."
            }
        }
    } catch {
        Write-Warning "Could not query AI status: $_. Local AI server may need manual start via Settings."
    }
} else {
    Write-Info "Skipping local AI server start (-SkipLlama)"
}

# ---------------------------------------------------------------------------
# Start frontend
# ---------------------------------------------------------------------------

if (-not $SkipFrontend) {
    Write-Header "Starting Next.js Frontend (port $FrontendPort)"

    $frontendStdoutLog = Join-Path $script:LogDir "frontend.stdout.log"
    $frontendStderrLog = Join-Path $script:LogDir "frontend.stderr.log"

    # Set the API URL environment variable for the frontend (inherited by cmd.exe)
    $env:NEXT_PUBLIC_API_URL = "http://127.0.0.1:$BackendPort/api"

    try {
        $proc = Start-Process -FilePath "cmd.exe" `
            -ArgumentList "/c", "npm", "run", "dev" `
            -WorkingDirectory $script:FrontendDir `
            -RedirectStandardOutput $frontendStdoutLog `
            -RedirectStandardError $frontendStderrLog `
            -PassThru
        Write-Success "Frontend started (PID: $($proc.Id))"
    } catch {
        Write-Error "Failed to start frontend: $_"
        exit 1
    }

    $frontendUrl = "http://127.0.0.1:$FrontendPort"
    if (-not (Wait-ForHealth -Url $frontendUrl -ComponentName "Frontend" -TimeoutSeconds 90)) {
        Write-Error "Frontend health check failed. Check $frontendStdoutLog and $frontendStderrLog for details."
        exit 1
    }
} else {
    Write-Info "Skipping frontend start (-SkipFrontend)"
}

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

Write-Header "GATE CS 2027 Tutor - Startup Complete"
Write-Success "Backend:    http://127.0.0.1:$BackendPort/api/health"
Write-Success "Frontend:   http://127.0.0.1:$FrontendPort"
if (-not $SkipLlama) {
    Write-Success "Local AI:   http://127.0.0.1:$LlamaPort/health (managed via backend)"
}
Write-Host ""
Write-Host "Logs are in: $script:LogDir" -ForegroundColor Cyan
Write-Host "To stop all components: .\stop.ps1" -ForegroundColor Cyan
Write-Host ""