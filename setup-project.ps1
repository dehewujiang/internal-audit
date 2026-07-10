# setup-project.ps1 - Internal Audit Project Initializer
# Usage: powershell -File setup-project.ps1 -ProjectDir "D:\path\to\project"
#
# Junction (live sync with gold source — edit gold, changes appear everywhere):
#   .claude/skills/  8 skill dirs
#   _shared/         phase_gate, validate, queries, project_init
#   tools/           pdf_ocr_extractor.py + 13 capability declarations
#
# Copy (snapshot at setup time — re-run this script to sync):
#   CLAUDE.md ← CLAUDE-project.md (project version, stripped dev-only noise)
#   constitution.md
#
# Mkdir (empty, project-owned data):
#   audit-topics/  memory/  internal-audit-workspace/

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

$ok = 0; $fail = 0

# ── Helper ──────────────────────────────────────────────
function New-Junction {
    param([string]$Link, [string]$Target)
    if (Test-Path $Link) {
        Write-Host "  [SKIP] $Link" -ForegroundColor DarkGray
        $script:ok++
        return
    }
    # Ensure parent exists
    $parent = Split-Path $Link -Parent
    if (-not (Test-Path $parent)) { New-Item -ItemType Directory -Path $parent -Force | Out-Null }
    cmd /c mklink /J "$Link" "$Target" 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  [OK]   $Link" -ForegroundColor Green
        $script:ok++
    } else {
        Write-Host "  [FAIL] $Link  (target: $Target)" -ForegroundColor Red
        $script:fail++
    }
}

# ════════════════════════════════════════════════════════
# 1. Skills — junction (8 dirs)
# ════════════════════════════════════════════════════════
Write-Host "── Skills ──" -ForegroundColor Cyan

$SKILLS = @(
    "project-init", "topic-wizard",
    "document-organizer", "audit-interview-designer",
    "internal-audit-program-generator", "audit-execution-assistant",
    "audit-finding-debate", "internal-audit-report-generator",
    "internal-audit-evaluator", "program-quality-evaluator"
)
foreach ($skill in $SKILLS) {
    $link   = Join-Path $ProjectDir ".claude\skills\$skill"
    $target = Join-Path $GOLD $skill
    New-Junction -Link $link -Target $target
}

# ════════════════════════════════════════════════════════
# 2. _shared/ — junction (Python tools)
# ════════════════════════════════════════════════════════
Write-Host "── _shared/ ──" -ForegroundColor Cyan
New-Junction -Link (Join-Path $ProjectDir "_shared") -Target (Join-Path $GOLD "_shared")

# ════════════════════════════════════════════════════════
# 3. tools/ — junction (OCR script + capability docs)
# ════════════════════════════════════════════════════════
Write-Host "── tools/ ──" -ForegroundColor Cyan
New-Junction -Link (Join-Path $ProjectDir "tools") -Target (Join-Path $GOLD "tools")

# ════════════════════════════════════════════════════════
# 4. Root files — copy (CLAUDE-project.md → CLAUDE.md, constitution.md)
# ════════════════════════════════════════════════════════
Write-Host "── Config ──" -ForegroundColor Cyan

# CLAUDE-project.md → CLAUDE.md (project edition, stripped of dev-only content)
$claudeSrc  = Join-Path $GOLD "CLAUDE-project.md"
$claudeDest = Join-Path $ProjectDir "CLAUDE.md"
if (Test-Path $claudeDest) {
    Write-Host "  [SKIP] CLAUDE.md" -ForegroundColor DarkGray; $ok++
} else {
    try {
        Copy-Item -Path $claudeSrc -Destination $claudeDest -Force -ErrorAction Stop
        Write-Host "  [OK]   CLAUDE.md (from CLAUDE-project.md)" -ForegroundColor Green; $ok++
    }
    catch {
        Write-Host "  [FAIL] CLAUDE.md -- $_" -ForegroundColor Red; $fail++
    }
}

# constitution.md
$constDest = Join-Path $ProjectDir "constitution.md"
$constSrc  = Join-Path $GOLD "constitution.md"
if (Test-Path $constDest) {
    Write-Host "  [SKIP] constitution.md" -ForegroundColor DarkGray; $ok++
} else {
    try {
        Copy-Item -Path $constSrc -Destination $constDest -Force -ErrorAction Stop
        Write-Host "  [OK]   constitution.md" -ForegroundColor Green; $ok++
    }
    catch {
        Write-Host "  [FAIL] constitution.md -- $_" -ForegroundColor Red; $fail++
    }
}

# ════════════════════════════════════════════════════════
# 5. Data dirs — mkdir (project-owned, empty)
# ════════════════════════════════════════════════════════
Write-Host "── Data ──" -ForegroundColor Cyan

$DATA_DIRS = @("audit-topics", "memory", "internal-audit-workspace")
foreach ($dir in $DATA_DIRS) {
    $path = Join-Path $ProjectDir $dir
    if (Test-Path $path) {
        Write-Host "  [SKIP] $dir/" -ForegroundColor DarkGray; $ok++; continue
    }
    try {
        New-Item -ItemType Directory -Path $path -Force -ErrorAction Stop | Out-Null
        Write-Host "  [OK]   $dir/" -ForegroundColor Green; $ok++
    }
    catch {
        Write-Host "  [FAIL] $dir/ -- $_" -ForegroundColor Red; $fail++
    }
}

# ════════════════════════════════════════════════════════
# 6. Quick self-check
# ════════════════════════════════════════════════════════
Write-Host ""
Write-Host "── Self-check ──" -ForegroundColor Cyan

$checks = @(
    @{ Label="_shared/phase_gate.py"; Path=(Join-Path $ProjectDir "_shared\scripts\phase_gate.py") },
    @{ Label="tools/pdf_ocr_extractor.py"; Path=(Join-Path $ProjectDir "tools\pdf_ocr_extractor.py") },
    @{ Label=".claude/skills/project-init"; Path=(Join-Path $ProjectDir ".claude\skills\project-init") },
    @{ Label="CLAUDE.md"; Path=(Join-Path $ProjectDir "CLAUDE.md") },
    @{ Label="constitution.md"; Path=(Join-Path $ProjectDir "constitution.md") },
    @{ Label="audit-topics/"; Path=(Join-Path $ProjectDir "audit-topics") },
    @{ Label="memory/"; Path=(Join-Path $ProjectDir "memory") },
    @{ Label="internal-audit-workspace/"; Path=(Join-Path $ProjectDir "internal-audit-workspace") }
)

$check_ok = 0; $check_ng = 0
foreach ($c in $checks) {
    if (Test-Path $c.Path) {
        Write-Host "  [OK]   $($c.Label)" -ForegroundColor Green
        $check_ok++
    } else {
        Write-Host "  [MISS] $($c.Label)  ($($c.Path))" -ForegroundColor Red
        $check_ng++
    }
}

# ── Summary ─────────────────────────────────────────────
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Project : $ProjectDir" -ForegroundColor White
Write-Host "  Source  : $GOLD" -ForegroundColor White
Write-Host "  Setup   : $ok OK / $fail FAIL" -ForegroundColor $(if ($fail -eq 0) { "Green" } else { "Red" })
Write-Host "  Check   : $check_ok OK / $check_ng MISS" -ForegroundColor $(if ($check_ng -eq 0) { "Green" } else { "Red" })
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

if ($fail -eq 0 -and $check_ng -eq 0) {
    Write-Host "Next: cd `"$ProjectDir`" ; claude" -ForegroundColor Yellow
} else {
    Write-Host "Fix failures above, then: cd `"$ProjectDir`" ; claude" -ForegroundColor Red
}
