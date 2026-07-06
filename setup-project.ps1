# setup-project.ps1 - Internal Audit Project Initializer
# Usage: powershell -File setup-project.ps1 -ProjectDir "D:\path\to\project"
#
# Uses mklink /J (directory junction) - no admin required, same drive only.
# Files (constitution.md / CLAUDE.md) are copied, not linked - edit gold source, re-run to sync.

param(
    [Parameter(Mandatory=$true)]
    [string]$ProjectDir
)

$GOLD = "D:\Nut\00_my_digital\12_AGI\skills\internal-audit"

if (-not (Test-Path $GOLD)) {
    Write-Host "[FAIL] Gold source not found: $GOLD" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $ProjectDir)) {
    Write-Host "[INFO] Creating project directory..." -ForegroundColor Yellow
    New-Item -ItemType Directory -Path $ProjectDir -Force | Out-Null
}

# ---- .claude/skills/ (9 junction dirs) ----
$skillsDir = Join-Path $ProjectDir ".claude\skills"
New-Item -ItemType Directory -Path $skillsDir -Force | Out-Null

$SKILLS = @(
    "project-init", "document-organizer", "internal-audit-program-generator",
    "audit-execution-assistant", "audit-finding-debate", "audit-interview-designer",
    "internal-audit-report-generator", "internal-audit-evaluator", "topic-wizard"
)

$ok = 0; $fail = 0
foreach ($skill in $SKILLS) {
    $link = Join-Path $skillsDir $skill
    $target = Join-Path $GOLD $skill
    if (Test-Path $link) { Write-Host "[SKIP] skills/$skill" -ForegroundColor DarkGray; $ok++; continue }
    cmd /c mklink /J "$link" "$target" 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) { Write-Host "[OK] skills/$skill" -ForegroundColor Green; $ok++ }
    else { Write-Host "[FAIL] skills/$skill" -ForegroundColor Red; $fail++ }
}
Write-Host "Skills: $ok OK / $fail FAIL" -ForegroundColor Cyan

# ---- Project root files (copy, not link) ----
$ROOT_FILES = @("constitution.md", "CLAUDE.md")
$ok = 0; $fail = 0
foreach ($name in $ROOT_FILES) {
    $dest = Join-Path $ProjectDir $name
    $src  = Join-Path $GOLD $name
    if (Test-Path $dest) { Write-Host "[SKIP] $name" -ForegroundColor DarkGray; $ok++; continue }
    try { Copy-Item -Path $src -Destination $dest -Force -ErrorAction Stop; Write-Host "[OK] $name" -ForegroundColor Green; $ok++ }
    catch { Write-Host "[FAIL] $name -- $_" -ForegroundColor Red; $fail++ }
}
Write-Host "Config files: $ok OK / $fail FAIL" -ForegroundColor Cyan

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Project : $ProjectDir" -ForegroundColor White
Write-Host "  Source  : $GOLD" -ForegroundColor White
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next step: cd `"$ProjectDir`" ; claude" -ForegroundColor Yellow
