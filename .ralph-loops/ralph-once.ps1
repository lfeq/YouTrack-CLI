$ScriptDir = $PSScriptRoot
$PromptPath = Join-Path $ScriptDir "prompt.md"
if (-Not (Test-Path $PromptPath)) {
    Write-Error "prompt.md not found at $PromptPath"
    exit 1
}
$Prompt = Get-Content -Path $PromptPath -Raw

# claude-code uses 'claude' command
claude --permission-mode acceptEdits "$Prompt"
