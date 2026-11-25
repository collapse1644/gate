#requires -Version 5.1
<#
.SYNOPSIS
    Stop the GATE CS 2027 Tutor application components.

.DESCRIPTION
    This script stops only the application processes that belong to the
    GATE CS 2027 Tutor:
    1. FastAPI backend (uvicorn on port 8000)
    2. llama.cpp local inference server (port 8080)
    3. Next.js frontend (port 3000)

    It identifies processes by checking which PIDs are listening on the
    application ports, then terminates only those specific processes.
    It does NOT kill unrelated Python or Node.js processes.

.PARAMETER BackendPort
    Port for the FastAPI backend (default: 8000).

.PARAMETER LlamaPort
    Port for the llama.cpp server (default: 8080).

.PARAMETER FrontendPort
    Port for the Next.js frontend (default: 3000).

.PARAMETER SkipBackend
    Skip stopping the backend.

.PARAMETER SkipLlama
    Skip stopping the local AI server.

.PARAMETER SkipFrontend
    Skip stopping the frontend.

.EXAMPLE
    .\stop.ps1
    # Stop all application components on default ports.

.EXAMPLE
    .\stop.ps1 -SkipLlama
    # Stop backend and frontend only, keep local AI server running.

.NOTES
    Run from the project root: G:\MINI-PROJ\gate
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
# Uses Get-NetTCPConnection -State Listen as the authoritative source.
# Filters out PID 0 and the current PowerShell host PID ($PID).
function Get-PortProcessId {
    param([int]$Port)

    $connections = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    if (-not $connections) {
        return $null
    }

    $pids = @()
    foreach ($conn in $connections) {
        $processId = [int]$conn.OwningProcess
        # Skip PID 0 (not a real process) and the current PowerShell host
        if ($processId -eq 0 -or $processId -eq $PID) {
            continue
        }
        $pids += $processId
    }
    return $pids | Select-Object -Unique
}

# Check whether a process positively belongs to the GATE project.
# Returns $true only when both the executable and command line match.
function Test-IsGateProcess {
    param(
        [int]$ProcessId,
        [string]$ExpectedExeName,
        [string[]]$ExpectedCmdLinePatterns
    )

    try {
        $proc = Get-Process -Id $ProcessId -ErrorAction Stop
    } catch {
        return $false
    }

    # Executable name must match
    if ($proc.ProcessName -ne $ExpectedExeName) {
        return $false
    }

    # Command line must match at least one of the expected patterns
    try {
        $cmdLine = (Get-CimInstance Win32_Process -Filter "ProcessId = $ProcessId").CommandLine
        if (-not $cmdLine) {
            return $false
        }
        foreach ($pattern in $ExpectedCmdLinePatterns) {
            if ($cmdLine -match $pattern) {
                return $true
            }
        }
    } catch {
        # WMI may not be available; fall back to executable name only
        return $true
    }

    return $false
}

# Stop a process gracefully, then force-kill if needed.
function Stop-ProcessGraceful {
    param([int]$ProcessId, [string]$ProcessName)

    try {
        $proc = Get-Process -Id $ProcessId -ErrorAction SilentlyContinue
        if (-not $proc) {
            Write-Info "$ProcessName (PID: $ProcessId) is already stopped."
            return
        }

        Write-Info "Stopping $ProcessName (PID: $ProcessId)..."

        # Try graceful termination first
        $proc.CloseMainWindow() | Out-Null
        Start-Sleep -Seconds 2

        # Check if still alive
        $proc = Get-Process -Id $ProcessId -ErrorAction SilentlyContinue
        if ($proc) {
            Write-Info "Graceful stop failed for $ProcessName (PID: $ProcessId), force-killing..."
            Stop-Process -Id $ProcessId -Force -ErrorAction SilentlyContinue
            Start-Sleep -Seconds 1
        }

        # Verify it's gone
        $proc = Get-Process -Id $ProcessId -ErrorAction SilentlyContinue
        if ($proc) {
            Write-Error "Failed to stop $ProcessName (PID: $ProcessId). It may require manual termination."
        } else {
            Write-Success "$ProcessName (PID: $ProcessId) stopped."
        }
    } catch {
        Write-Error "Error stopping $ProcessName (PID: $ProcessId): $_"
    }
}

# ---------------------------------------------------------------------------
# Main shutdown logic
# ---------------------------------------------------------------------------

Write-Header "GATE CS 2027 Tutor - Shutdown"

$stoppedAny = $false

# Stop backend
if (-not $SkipBackend) {
    $backendPids = Get-PortProcessId -Port $BackendPort
    if ($backendPids) {
        foreach ($processId in $backendPids) {
            # Validate the PID still exists before inspecting
            if (-not (Get-Process -Id $processId -ErrorAction SilentlyContinue)) {
                Write-Info "PID $processId on port $BackendPort no longer exists. Skipping."
                continue
            }
            # Protect against killing the current PowerShell host
            if ($processId -eq $PID) {
                Write-Warning "PID $processId on port $BackendPort is the current PowerShell host. Skipping."
                continue
            }

            # Positively identify as GATE backend (python + uvicorn + app.main module)
            if (Test-IsGateProcess -ProcessId $processId -ExpectedExeName "python" -ExpectedCmdLinePatterns @("uvicorn", "app.main")) {
                Stop-ProcessGraceful -ProcessId $processId -ProcessName "Backend (uvicorn)"
                $stoppedAny = $true
            } else {
                Write-Warning "PID $processId on port $BackendPort is not a GATE backend process. Skipping."
            }
        }
    } else {
        Write-Info "No process found on backend port $BackendPort."
    }
} else {
    Write-Info "Skipping backend stop (-SkipBackend)"
}

# Stop llama.cpp server
if (-not $SkipLlama) {
    $llamaPids = Get-PortProcessId -Port $LlamaPort
    if ($llamaPids) {
        foreach ($processId in $llamaPids) {
            # Validate the PID still exists before inspecting
            if (-not (Get-Process -Id $processId -ErrorAction SilentlyContinue)) {
                Write-Info "PID $processId on port $LlamaPort no longer exists. Skipping."
                continue
            }
            # Protect against killing the current PowerShell host
            if ($processId -eq $PID) {
                Write-Warning "PID $processId on port $LlamaPort is the current PowerShell host. Skipping."
                continue
            }

            # Positively identify as llama-server
            if (Test-IsGateProcess -ProcessId $processId -ExpectedExeName "llama-server" -ExpectedCmdLinePatterns @("llama-server")) {
                Stop-ProcessGraceful -ProcessId $processId -ProcessName "llama-server"
                $stoppedAny = $true
            } else {
                Write-Warning "PID $processId on port $LlamaPort is not llama-server. Skipping."
            }
        }
    } else {
        Write-Info "No process found on llama server port $LlamaPort."
    }
} else {
    Write-Info "Skipping llama server stop (-SkipLlama)"
}

# Stop frontend
if (-not $SkipFrontend) {
    $frontendPids = Get-PortProcessId -Port $FrontendPort
    if ($frontendPids) {
        foreach ($processId in $frontendPids) {
            # Validate the PID still exists before inspecting
            if (-not (Get-Process -Id $processId -ErrorAction SilentlyContinue)) {
                Write-Info "PID $processId on port $FrontendPort no longer exists. Skipping."
                continue
            }
            # Protect against killing the current PowerShell host
            if ($processId -eq $PID) {
                Write-Warning "PID $processId on port $FrontendPort is the current PowerShell host. Skipping."
                continue
            }

            # Positively identify as Next.js frontend (node + next.js or npm run dev in cmd)
            if (Test-IsGateProcess -ProcessId $processId -ExpectedExeName "node" -ExpectedCmdLinePatterns @("next", "npm run dev", "node.*next")) {
                Stop-ProcessGraceful -ProcessId $processId -ProcessName "Frontend (Next.js)"
                $stoppedAny = $true
            } else {
                Write-Warning "PID $processId on port $FrontendPort is not a GATE frontend process. Skipping."
            }
        }
    } else {
        Write-Info "No process found on frontend port $FrontendPort."
    }
} else {
    Write-Info "Skipping frontend stop (-SkipFrontend)"
}

# Also attempt to stop the backend-managed llama-server via API
# (in case it was started through the backend manager and we want clean shutdown)
if (-not $SkipLlama -and -not $SkipBackend) {
    $statusUrl = "http://127.0.0.1:$BackendPort/api/ai/local/stop"
    try {
        $stopResp = Invoke-RestMethod -Uri $statusUrl -Method Post -TimeoutSec 10 -ErrorAction SilentlyContinue
        if ($stopResp) {
            Write-Info "Requested local AI server stop via backend manager."
        }
    } catch {
        # Backend may already be stopped; ignore
    }
}

# ---------------------------------------------------------------------------
# Post-shutdown port recheck
# ---------------------------------------------------------------------------

Write-Info "Rechecking ports after shutdown..."
$remainingPorts = @()

$remainingBackend = Get-PortProcessId -Port $BackendPort
if ($remainingBackend) {
    $remainingPorts += @{ Port = $BackendPort; PIDs = $remainingBackend }
}

$remainingLlama = Get-PortProcessId -Port $LlamaPort
if ($remainingLlama) {
    $remainingPorts += @{ Port = $LlamaPort; PIDs = $remainingLlama }
}

$remainingFrontend = Get-PortProcessId -Port $FrontendPort
if ($remainingFrontend) {
    $remainingPorts += @{ Port = $FrontendPort; PIDs = $remainingFrontend }
}

if ($remainingPorts.Count -gt 0) {
    Write-Warning "Some ports remain occupied after shutdown:"
    foreach ($rp in $remainingPorts) {
        Write-Warning "  Port $($rp.Port): PID(s) $($rp.PIDs -join ', ')"
    }
    Write-Warning "These processes could not be positively identified as GATE components."
} else {
    Write-Success "All application ports ($BackendPort, $LlamaPort, $FrontendPort) are free."
}

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

Write-Header "GATE CS 2027 Tutor - Shutdown Summary"

if ($stoppedAny) {
    Write-Success "Application components stopped."
} else {
    Write-Info "No application components were running."
}

Write-Host ""
Write-Host "To start again: .\start.ps1" -ForegroundColor Cyan
Write-Host ""