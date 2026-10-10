# setup-project.ps1 - Internal Audit Project Initializer（单模式：新项目一律锁定版）
# Usage: powershell -File setup-project.ps1 -ProjectDir "D:\path\to\project"
#
# Copy — snapshot at setup time, immune to gold-source changes (B3 起唯一模式，
# junction 路已删；历史 -Stable 参数不再接受，传了会报错）:
#   .claude/skills/  all audit skill dirs copied, not linked
#   _shared/         all scripts copied, not linked
#   tools/           all tools copied, not linked
#   ledger/          all ledger scripts copied, not linked
#
# Copy (always snapshot, regardless of mode):
#   CLAUDE.md ← CLAUDE-project.md (project version, stripped dev-only noise)
#   constitution.md
#   OPS.md (user-facing operation manual)
#
# Mkdir (empty, project-owned data):
#   audit-topics/  memory/  internal-audit-workspace/
#
# Write:
#   VERSION.lock.json — locks deployed version for future update-project.ps1 use

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

# ── Helpers ──────────────────────────────────────────────
function New-StableCopy {
    param([string]$Dest, [string]$Source)
    if (Test-Path $Dest) {
        Write-Host "  [SKIP] $Dest" -ForegroundColor DarkGray
        $script:ok++
        return
    }
    $parent = Split-Path $Dest -Parent
    if (-not (Test-Path $parent)) { New-Item -ItemType Directory -Path $parent -Force | Out-Null }
    try {
        Copy-Item -Path $Source -Destination $Dest -Recurse -Force -ErrorAction Stop
        Write-Host "  [OK]   $Dest (copy)" -ForegroundColor Green
        $script:ok++
    }
    catch {
        Write-Host "  [FAIL] $Dest  (source: $Source) — $_" -ForegroundColor Red
        $script:fail++
    }
}

# ════════════════════════════════════════════════════════
# 1. Skills — copy (B3 起唯一模式）
# ════════════════════════════════════════════════════════
Write-Host "── Skills (Copy stable) ──" -ForegroundColor Cyan

# Auto-discover audit skills: a repo-root directory containing SKILL.md is a deployable skill.
# Single source of truth is the repo root. The dev-only .claude/skills/ (geb-*) is NOT a source.
$SKILLS = Get-ChildItem $GOLD -Directory |
    Where-Object { Test-Path (Join-Path $_.FullName "SKILL.md") } |
    ForEach-Object { $_.Name }
if ($SKILLS.Count -eq 0) {
    Write-Host "  [WARN] No skill dirs found at repo root (SKILL.md marker) — no skills deployed" -ForegroundColor Yellow
} else {
    foreach ($skill in $SKILLS) {
        $link   = Join-Path $ProjectDir ".claude\skills\$skill"
        $target = Join-Path $GOLD $skill
        New-StableCopy -Dest $link -Source $target
    }
}

# ════════════════════════════════════════════════════════
# 2. _shared/ — copy (B3 起唯一模式）
# ════════════════════════════════════════════════════════
Write-Host "── _shared/ (Copy stable) ──" -ForegroundColor Cyan
$sharedLink = Join-Path $ProjectDir "_shared"
$sharedTarget = Join-Path $GOLD "_shared"
New-StableCopy -Dest $sharedLink -Source $sharedTarget

# ════════════════════════════════════════════════════════
# 3b. ledger/ — copy (B3 起唯一模式）
# ════════════════════════════════════════════════════════
Write-Host "── ledger/ (Copy stable) ──" -ForegroundColor Cyan
$ledgerLink = Join-Path $ProjectDir "ledger"
$ledgerTarget = Join-Path $GOLD "ledger"
New-StableCopy -Dest $ledgerLink -Source $ledgerTarget

# ════════════════════════════════════════════════════════
# 3. tools/ — copy (B3 起唯一模式）
# ════════════════════════════════════════════════════════
Write-Host "── tools/ (Copy stable) ──" -ForegroundColor Cyan
$toolsLink = Join-Path $ProjectDir "tools"
$toolsTarget = Join-Path $GOLD "tools"
New-StableCopy -Dest $toolsLink -Source $toolsTarget

# ════════════════════════════════════════════════════════
# 4. Root files — copy (CLAUDE-project.md → CLAUDE.md, constitution.md, OPS.md)
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

# OPS.md — user-facing operation manual
$opsDest = Join-Path $ProjectDir "OPS.md"
$opsSrc  = Join-Path $GOLD "OPS.md"
if (Test-Path $opsDest) {
    Write-Host "  [SKIP] OPS.md" -ForegroundColor DarkGray; $ok++
} else {
    try {
        Copy-Item -Path $opsSrc -Destination $opsDest -Force -ErrorAction Stop
        Write-Host "  [OK]   OPS.md" -ForegroundColor Green; $ok++
    }
    catch {
        Write-Host "  [FAIL] OPS.md -- $_" -ForegroundColor Red; $fail++
    }
}

# .claude/settings.json — project-level skill/rule configuration
$settingsDest = Join-Path $ProjectDir ".claude\settings.json"
$settingsSrc  = Join-Path $GOLD ".claude\settings.json"
if (Test-Path $settingsDest) {
    Write-Host "  [SKIP] .claude/settings.json" -ForegroundColor DarkGray; $ok++
} elseif (Test-Path $settingsSrc) {
    try {
        $settingsParent = Split-Path $settingsDest -Parent
        if (-not (Test-Path $settingsParent)) { New-Item -ItemType Directory -Path $settingsParent -Force | Out-Null }
        Copy-Item -Path $settingsSrc -Destination $settingsDest -Force -ErrorAction Stop
        Write-Host "  [OK]   .claude/settings.json" -ForegroundColor Green; $ok++
    }
    catch {
        Write-Host "  [FAIL] .claude/settings.json -- $_" -ForegroundColor Red; $fail++
    }
}

# .claude/rules/ — 不再搬运（2026-09-11）
# 规则由 Claude Code 自动从 ~/.claude/rules/ 加载（用户级，对本机所有项目生效）。
# 项目级副本会让同一份规则被加载两遍；且现场项目只做审计、不写源码，
# 编码类规则（good-taste / geb-l3 / compat）本就用不上。故不再向现场项目拷贝 rules。

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
# 6. VERSION.lock.json — lock deployed version
# ════════════════════════════════════════════════════════
Write-Host "── Version lock ──" -ForegroundColor Cyan

$versionSrc = Join-Path $GOLD "VERSION.json"
$versionLockDest = Join-Path $ProjectDir "VERSION.lock.json"

if (Test-Path $versionLockDest) {
    Write-Host "  [SKIP] VERSION.lock.json" -ForegroundColor DarkGray; $ok++
} else {
    try {
        $versionData = Get-Content $versionSrc -Raw -Encoding UTF8 | ConvertFrom-Json
        $lockData = @{
            locked_version = $versionData.version
            git_commit     = $versionData.git_commit
            locked_at      = (Get-Date -Format "yyyy-MM-ddTHH:mm:sszzz")
            deployed_with  = "stable"  # B1：语义冻结为历史标记，新项目统一锁定版
            gold_source    = $GOLD
        }
        $lockData | ConvertTo-Json -Depth 4 | Set-Content $versionLockDest -Encoding UTF8
        Write-Host "  [OK]   VERSION.lock.json ($($versionData.version))" -ForegroundColor Green; $ok++
    }
    catch {
        # If VERSION.json can't be read (very old gold source), still create a minimal lock
        try {
            $lockData = @{
                locked_version = "unknown"
                git_commit     = "unknown"
                locked_at      = (Get-Date -Format "yyyy-MM-ddTHH:mm:sszzz")
                deployed_with  = "stable"  # B1：语义冻结为历史标记，新项目统一锁定版
                gold_source    = $GOLD
            }
            $lockData | ConvertTo-Json -Depth 4 | Set-Content $versionLockDest -Encoding UTF8
            Write-Host "  [OK]   VERSION.lock.json (unknown — VERSION.json not found)" -ForegroundColor Green; $ok++
        }
        catch {
            Write-Host "  [FAIL] VERSION.lock.json -- $_" -ForegroundColor Red; $fail++
        }
    }
}

# ════════════════════════════════════════════════════════
# 7. Quick self-check
# ════════════════════════════════════════════════════════
Write-Host ""
Write-Host "── Self-check ──" -ForegroundColor Cyan

$checks = @(
    @{ Label="_shared/phase_gate.py"; Path=(Join-Path $ProjectDir "_shared\scripts\phase_gate.py") },
    @{ Label="tools/pdf_ocr_extractor.py"; Path=(Join-Path $ProjectDir "tools\pdf_ocr_extractor.py") },
    @{ Label="ledger/ledger.py"; Path=(Join-Path $ProjectDir "ledger\ledger.py") },
    @{ Label=".claude/skills/project-init"; Path=(Join-Path $ProjectDir ".claude\skills\project-init") },
    @{ Label="CLAUDE.md"; Path=(Join-Path $ProjectDir "CLAUDE.md") },
    @{ Label="constitution.md"; Path=(Join-Path $ProjectDir "constitution.md") },
    @{ Label="OPS.md"; Path=(Join-Path $ProjectDir "OPS.md") },
    @{ Label="VERSION.lock.json"; Path=(Join-Path $ProjectDir "VERSION.lock.json") },
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
Write-Host "  Mode    : STABLE (copy — immune to gold-source changes)" -ForegroundColor Yellow
Write-Host "  Setup   : $ok OK / $fail FAIL" -ForegroundColor $(if ($fail -eq 0) { "Green" } else { "Red" })
Write-Host "  Check   : $check_ok OK / $check_ng MISS" -ForegroundColor $(if ($check_ng -eq 0) { "Green" } else { "Red" })
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

if ($fail -eq 0 -and $check_ng -eq 0) {
    Write-Host "Next: cd `"$ProjectDir`" ; claude" -ForegroundColor Yellow
    Write-Host "      (upgrade with: update-project.ps1 -ProjectDir `"$ProjectDir`")" -ForegroundColor DarkGray
    Write-Host "      (register with: python _shared/scripts/queries.py register --path `"$ProjectDir`" --topic <主题> --period <期间>)" -ForegroundColor DarkGray
} else {
    Write-Host "Fix failures above, then: cd `"$ProjectDir`" ; claude" -ForegroundColor Red
}
