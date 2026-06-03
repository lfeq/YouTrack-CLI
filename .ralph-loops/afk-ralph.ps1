<#
.SYNOPSIS
    Runs Ralph (claude) loop iterations on Windows inside a persistent Docker sandbox.
.DESCRIPTION
    PowerShell translation of afk-ralph.sh. Ensures a persistent Docker sandbox is running,
    forwards host Claude Code credentials into the sandbox if it is not logged in, and runs
    Ralph iterations against prompt.md until the loop completes or signals <promise>COMPLETE</promise>.
.PARAMETER Iterations
    The number of iterations to run.
.EXAMPLE
    .\afk-ralph.ps1 5
#>
param(
    [Parameter(Mandatory=$true, Position=0)]
    [int]$Iterations
)

$ErrorActionPreference = "Stop"

$SandboxName = "claude-ralph"
$ScriptDir = $PSScriptRoot

# Ensure the sandbox is created and running
$existing = docker sandbox ls 2>$null | Select-String -SimpleMatch $SandboxName
if (-not $existing) {
    Write-Host "Creating persistent Docker sandbox: $SandboxName..." -ForegroundColor Cyan
    docker sandbox run --name $SandboxName claude . -- --help | Out-Null
}

# Self-healing check: Verify sandbox is logged in, and forward host credentials if missing
docker sandbox exec $SandboxName claude -p "echo checking login status" *> $null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Sandbox is not logged in. Attempting to forward host credentials..." -ForegroundColor Yellow

    # On Windows, Claude Code stores credentials at %USERPROFILE%\.claude\.credentials.json
    $HostCredsPath = Join-Path $env:USERPROFILE ".claude\.credentials.json"
    if (Test-Path $HostCredsPath) {
        $TokenJson = Get-Content -Path $HostCredsPath -Raw

        docker sandbox exec $SandboxName mkdir -p /home/agent/.claude | Out-Null

        # Write credentials into the sandbox via stdin to avoid quoting issues
        $TokenJson | docker sandbox exec -i $SandboxName sh -c "cat > /home/agent/.claude/.credentials.json"
        docker sandbox exec $SandboxName chmod 600 /home/agent/.claude/.credentials.json | Out-Null

        Write-Host "Host OAuth credentials successfully injected into sandbox '$SandboxName'!" -ForegroundColor Green
    } else {
        Write-Warning "Could not locate Claude Code credentials at $HostCredsPath."
        Write-Warning "Please run 'docker sandbox run $SandboxName' manually to log in."
    }
}

for ($i = 1; $i -le $Iterations; $i++) {
    Write-Host "Starting Ralph iteration $i of $Iterations inside isolated Docker sandbox..." -ForegroundColor Cyan

    # Start the live event log streamer in the background to show real-time progress
    $StreamerPath = Join-Path $ScriptDir "..\.claude\stream_sandbox_logs.py"
    $Streamer = $null
    if (Test-Path $StreamerPath) {
        $Streamer = Start-Process python -ArgumentList "`"$StreamerPath`"" -NoNewWindow -PassThru
    } else {
        Write-Warning "Streamer not found at $StreamerPath - continuing without live logs."
    }

    # Load prompt
    $PromptPath = Join-Path $ScriptDir "..\prompt.md"
    if (-Not (Test-Path $PromptPath)) {
        Write-Error "prompt.md not found at $PromptPath"
        exit 1
    }
    $Prompt = Get-Content -Path $PromptPath -Raw

    # Run the agent loop step inside the persistent, isolated Docker sandbox
    $result = docker sandbox run $SandboxName -- --permission-mode acceptEdits -p $Prompt

    # Safely terminate the streamer once the iteration is complete
    if ($Streamer) {
        Stop-Process -Id $Streamer.Id -Force -ErrorAction SilentlyContinue
    }

    Write-Output $result

    # Sub-string matching
    $resultString = $result -join "`n"
    if ($resultString -like "*<promise>COMPLETE</promise>*") {
        Write-Host "PRD complete after $i iterations." -ForegroundColor Green
        exit 0
    }
}
