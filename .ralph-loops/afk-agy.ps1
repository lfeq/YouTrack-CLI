<#
.SYNOPSIS
    Runs Antigravity (agy) loop iterations on Windows.
.DESCRIPTION
    This script is a PowerShell translation of afk-agy.sh. It runs agy in an isolated sandbox,
    streaming logs in the background and executing iteration tasks until complete or the limit is reached.
.PARAMETER Iterations
    The number of iterations to run.
.EXAMPLE
    .\afk-agy.ps1 5
#>
param(
    [Parameter(Mandatory=$true, Position=0)]
    [int]$Iterations
)

$ErrorActionPreference = "Stop"

# Determine script directory
$ScriptDir = $PSScriptRoot

for ($i = 1; $i -le $Iterations; $i++) {
    Write-Host "Starting Antigravity (agy) iteration $i of $Iterations in isolated sandbox..." -ForegroundColor Cyan

    # Start the live event log streamer in the background to show real-time progress
    $StreamerPath = Join-Path $ScriptDir "..\.antigravitycli\stream_agy_logs.py"
    $Streamer = Start-Process python -ArgumentList "`"$StreamerPath`"" -NoNewWindow -PassThru

    # Define prompt for agy
    $PromptPath = Join-Path $ScriptDir "prompt.md"
    if (-Not (Test-Path $PromptPath)) {
        Write-Error "prompt.md not found at $PromptPath"
        exit 1
    }
    $Prompt = Get-Content -Path $PromptPath -Raw

    # Run the agent loop step using the host agy binary with --sandbox and --dangerously-skip-permissions
    # Piping $null simulates "< /dev/null" to avoid hung stdin.
    $result = $null | agy --dangerously-skip-permissions --sandbox -p $Prompt

    # Safely terminate the streamer once the iteration is complete
    if ($Streamer) {
        Stop-Process -Id $Streamer.Id -Force -ErrorAction SilentlyContinue
    }

    # Output the result
    Write-Output $result

    # Sub-string matching structure
    $resultString = $result -join "`n"
    if ($resultString -like "*<promise>COMPLETE</promise>*") {
        Write-Host "PRD complete after $i iterations." -ForegroundColor Green
        exit 0
    }
}
