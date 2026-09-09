param(
    [switch]$DryRun
)

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$claudePath = Join-Path $root "CLAUDE.md"
$agentsPath = Join-Path $root "AGENTS.md"

if (-not (Test-Path $claudePath)) {
    Write-Error "CLAUDE.md not found at $claudePath"
    exit 1
}

$content = Get-Content $claudePath -Raw -Encoding UTF8

$content = $content -replace '^# CLAUDE\.md', '# AGENTS.md'
$content = $content -replace 'This file provides guidance to Claude Code \(claude\.ai/code\) when working with code in this repository\.', 'This file provides guidance to AI coding agents (Claude Code, Codex, OpenCode, WorkBuddy) when working with code in this repository.'

if ($DryRun) {
    Write-Output "--- Dry run: would write the following to AGENTS.md ---"
    Write-Output $content.Substring(0, [Math]::Min(500, $content.Length))
    Write-Output "..."
    exit 0
}

Set-Content $agentsPath -Value $content -Encoding UTF8 -NoNewline
Write-Output "AGENTS.md synced from CLAUDE.md successfully."
