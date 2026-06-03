# agy-once.ps1
# Translated from agy-once.sh

$PSScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Definition
$PromptPath = Join-Path $PSScriptRoot "prompt.md"

if (Test-Path $PromptPath) {
    $Prompt = Get-Content -Raw $PromptPath
    $null | agy --dangerously-skip-permissions --sandbox -p "$Prompt"
} else {
    Write-Error "Prompt file not found at $PromptPath"
    exit 1
}
