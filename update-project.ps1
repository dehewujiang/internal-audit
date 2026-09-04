# update-project.ps1 — Incremental upgrade script for audit projects
# Usage: powershell -File update-project.ps1 -ProjectDir "D:\path\to\project"
#
# Compares local VERSION.lock.json against gold-source VERSION.json,
# shows diff, and upgrades files with user confirmation.
# Never touches audit-topics/, memory/, internal-audit-workspace/.
# Backs up old files to .backup/ (keeps last 3 upgrades).

param(
    [Parameter(Mandatory=$true)]
    [string]$ProjectDir,

    [Parameter(Mandatory=$false)]
    [switch]$Force  # skip confirmation, still creates backup
)

$GOLD = "D:\Nut\00_my_digital\12_AGI\skills\internal-audit"

# ── Validate ────────────────────────────────────────────

if (-not (Test-Path $GOLD)) {
    Write-Host "[FAIL] Gold source not found: $GOLD" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $ProjectDir)) {
    Write-Host "[FAIL] Project directory not found: $ProjectDir" -ForegroundColor Red
    exit 1
}

$lockPath = Join-Path $ProjectDir "VERSION.lock.json"
if (-not (Test-Path $lockPath)) {
    Write-Host "[FAIL] VERSION.lock.json not found in project — not a deployed audit project" -ForegroundColor Red
    exit 1
}

$versionPath = Join-Path $GOLD "VERSION.json"
if (-not (Test-Path $versionPath)) {
    Write-Host "[WARN] Gold source has no VERSION.json — cannot compute diff" -ForegroundColor Yellow
    Write-Host "       Try running setup-project.ps1 again to redeploy from scratch." -ForegroundColor Yellow
    exit 2
}

# ── Load versions ───────────────────────────────────────

try {
    $lock = Get-Content $lockPath -Raw -Encoding UTF8 | ConvertFrom-Json
} catch {
    Write-Host "[FAIL] Cannot parse VERSION.lock.json: $_" -ForegroundColor Red
    exit 1
}

try {
    $goldVersion = Get-Content $versionPath -Raw -Encoding UTF8 | ConvertFrom-Json
} catch {
    Write-Host "[FAIL] Cannot parse gold VERSION.json: $_" -ForegroundColor Red
    exit 1
}

$localVer  = $lock.locked_version
$remoteVer = $goldVersion.version
$localCommit = $lock.git_commit
$remoteCommit = $goldVersion.git_commit

# ── Display diff ────────────────────────────────────────

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Upgrade Check" -ForegroundColor White
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Project       : $ProjectDir" -ForegroundColor White
Write-Host "  Deployed with : $($lock.deployed_with)" -ForegroundColor White
Write-Host "  Locked at     : $($lock.locked_at)" -ForegroundColor White
Write-Host ""
Write-Host "  Local  version : $localVer  (commit $localCommit)" -ForegroundColor Yellow
Write-Host "  Remote version : $remoteVer  (commit $remoteCommit)" -ForegroundColor Green
Write-Host ""

if ($localVer -eq $remoteVer) {
    Write-Host "  ✅ Already up to date. No upgrade needed." -ForegroundColor Green
    Write-Host ""
    exit 0
}

# ── Show what changed ───────────────────────────────────

$changes = $goldVersion.changes
if (-not $changes -or $changes.Count -eq 0) {
    Write-Host "  ⚠️  VERSION.json has no changes array — cannot show detailed diff" -ForegroundColor Yellow
    Write-Host "  Will upgrade all junction/copy paths (excluding data dirs)." -ForegroundColor Yellow
    Write-Host ""
} else {
    Write-Host "── Changes since your version ──" -ForegroundColor Cyan
    Write-Host ""

    # Risk classification
    $highRisk = @(); $medRisk = @(); $lowRisk = @()
    foreach ($c in $changes) {
        $type = $c.type
        $file = $c.file
        $summary = $c.summary
        $risk = switch ($type) {
            "schema"   { "HIGH" }
            "data"     { "HIGH" }
            "config"   { "MED"  }
            "skill"    { "MED"  }
            "script"   { "LOW"  }
            "doc"      { "LOW"  }
            default    { "MED"  }
        }
        $icon = switch ($risk) {
            "HIGH" { "🔴" }
            "MED"  { "🟡" }
            "LOW"  { "🟢" }
        }
        Write-Host "  $icon [$risk] $file" -ForegroundColor $(switch ($risk) { "HIGH" { "Red" } "MED" { "Yellow" } "LOW" { "DarkGray" } })
        Write-Host "      $summary"
    }
    Write-Host ""
}

# ── Confirm ─────────────────────────────────────────────

if (-not $Force) {
    $confirm = Read-Host "Upgrade? (y/n)"
    if ($confirm -ne "y") {
        Write-Host "  Cancelled." -ForegroundColor Yellow
        exit 0
    }
}

# ── Backup ──────────────────────────────────────────────

$ts = Get-Date -Format "yyyyMMdd-HHmmss"
$backupDir = Join-Path $ProjectDir ".backup\$ts"
New-Item -ItemType Directory -Path $backupDir -Force | Out-Null

Write-Host ""
Write-Host "── Backup → .backup/$ts ──" -ForegroundColor Cyan

# ── Determine upgrade mode ──────────────────────────────

$isStable = $lock.deployed_with -eq "stable"

if ($isStable) {
    # ── Stable mode: re-copy all directories ──
    Write-Host "── Upgrading (stable mode — recopy) ──" -ForegroundColor Cyan

    # Auto-discover audit skills at repo root by SKILL.md marker (merge, not replace).
    # Single source of truth is the repo root; dev-only .claude/skills/ is NOT a source.
    $skillNames = Get-ChildItem $GOLD -Directory |
        Where-Object { Test-Path (Join-Path $_.FullName "SKILL.md") } |
        ForEach-Object { $_.Name }
    if ($skillNames.Count -eq 0) {
        Write-Host "  [WARN] No skill dirs found at repo root (SKILL.md marker)" -ForegroundColor Yellow
    } else {
        foreach ($skill in $skillNames) {
            $destPath = Join-Path $ProjectDir ".claude\skills\$skill"
            $srcPath = Join-Path $GOLD $skill
            # Backup old
            if (Test-Path $destPath) {
                $backupTarget = Join-Path $backupDir ".claude\skills\$skill"
                $backupParent = Split-Path $backupTarget -Parent
                if (-not (Test-Path $backupParent)) { New-Item -ItemType Directory -Path $backupParent -Force | Out-Null }
                try {
                    Copy-Item -Path $destPath -Destination $backupTarget -Recurse -Force -ErrorAction Stop
                    Write-Host "  [OK]   backed up .claude/skills/$skill" -ForegroundColor DarkGray
                } catch {
                    Write-Host "  [WARN] backup failed for .claude/skills/$skill`: $_" -ForegroundColor Yellow
                }
            }
            # Overwrite with new
            try {
                if (Test-Path $destPath) { Remove-Item $destPath -Recurse -Force }
                Copy-Item -Path $srcPath -Destination $destPath -Recurse -Force -ErrorAction Stop
                Write-Host "  [OK]   .claude/skills/$skill upgraded" -ForegroundColor Green
                $upOk++
            } catch {
                Write-Host "  [FAIL] .claude/skills/$skill — $_" -ForegroundColor Red
                $upFail++
            }
        }
    }

    $dirs = @(
        @{Dest="_shared"; Source=(Join-Path $GOLD "_shared")},
        @{Dest="tools"; Source=(Join-Path $GOLD "tools")},
        @{Dest="ledger"; Source=(Join-Path $GOLD "ledger")}
    )

    $upOk = 0; $upFail = 0

    foreach ($d in $dirs) {
        $destPath = Join-Path $ProjectDir $d.Dest
        $srcPath = $d.Source

        # Backup old
        if (Test-Path $destPath) {
            $backupTarget = Join-Path $backupDir $d.Dest
            $backupParent = Split-Path $backupTarget -Parent
            if (-not (Test-Path $backupParent)) { New-Item -ItemType Directory -Path $backupParent -Force | Out-Null }
            try {
                Copy-Item -Path $destPath -Destination $backupTarget -Recurse -Force -ErrorAction Stop
                Write-Host "  [OK]   backed up $($d.Dest)" -ForegroundColor DarkGray
            } catch {
                Write-Host "  [WARN] backup failed for $($d.Dest): $_" -ForegroundColor Yellow
            }
        }

        # Overwrite with new (delete first: Copy-Item -Recurse nests if dest exists)
        try {
            if (Test-Path $destPath) { Remove-Item $destPath -Recurse -Force }
            Copy-Item -Path $srcPath -Destination $destPath -Recurse -Force -ErrorAction Stop
            Write-Host "  [OK]   $($d.Dest) upgraded" -ForegroundColor Green
            $upOk++
        } catch {
            Write-Host "  [FAIL] $($d.Dest) — $_" -ForegroundColor Red
            $upFail++
        }
    }

    # Root files
    $rootFiles = @("CLAUDE-project.md", "constitution.md", "OPS.md")
    foreach ($rf in $rootFiles) {
        $src = Join-Path $GOLD $rf
        if (-not (Test-Path $src)) { continue }
        if ($rf -eq "CLAUDE-project.md") {
            $dest = Join-Path $ProjectDir "CLAUDE.md"
        } else {
            $dest = Join-Path $ProjectDir $rf
        }
        # Backup
        if (Test-Path $dest) {
            $backupTarget = Join-Path $backupDir (Split-Path $dest -Leaf)
            try {
                Copy-Item -Path $dest -Destination $backupTarget -Force -ErrorAction Stop
            } catch { }
        }
        # Upgrade
        try {
            Copy-Item -Path $src -Destination $dest -Force -ErrorAction Stop
            $fileLabel = if ($rf -eq "CLAUDE-project.md") { "CLAUDE.md" } else { $rf }
            Write-Host "  [OK]   $fileLabel upgraded" -ForegroundColor Green
            $upOk++
        } catch {
            Write-Host "  [FAIL] $rf — $_" -ForegroundColor Red
            $upFail++
        }
    }

    # .claude/settings.json
    $settingsDest = Join-Path $ProjectDir ".claude\settings.json"
    $settingsSrc  = Join-Path $GOLD ".claude\settings.json"
    if (Test-Path $settingsSrc) {
        if (Test-Path $settingsDest) {
            $backupTarget = Join-Path $backupDir ".claude\settings.json"
            $backupParent = Split-Path $backupTarget -Parent
            if (-not (Test-Path $backupParent)) { New-Item -ItemType Directory -Path $backupParent -Force | Out-Null }
            try { Copy-Item -Path $settingsDest -Destination $backupTarget -Force -ErrorAction Stop } catch {}
        }
        try {
            $settingsParent = Split-Path $settingsDest -Parent
            if (-not (Test-Path $settingsParent)) { New-Item -ItemType Directory -Path $settingsParent -Force | Out-Null }
            Copy-Item -Path $settingsSrc -Destination $settingsDest -Force -ErrorAction Stop
            Write-Host "  [OK]   .claude/settings.json upgraded" -ForegroundColor Green
            $upOk++
        } catch {
            Write-Host "  [FAIL] .claude/settings.json — $_" -ForegroundColor Red
            $upFail++
        }
    }

    # .claude/rules/ — recopy from gold source
    $rulesDest = Join-Path $ProjectDir ".claude\rules"
    $rulesSrc  = Join-Path $GOLD ".claude\rules"
    if (Test-Path $rulesSrc) {
        if (Test-Path $rulesDest) {
            $backupTarget = Join-Path $backupDir ".claude\rules"
            $backupParent = Split-Path $backupTarget -Parent
            if (-not (Test-Path $backupParent)) { New-Item -ItemType Directory -Path $backupParent -Force | Out-Null }
            try { Copy-Item -Path $rulesDest -Destination $backupTarget -Recurse -Force -ErrorAction Stop } catch {}
        }
        try {
            if (Test-Path $rulesDest) { Remove-Item $rulesDest -Recurse -Force }
            Copy-Item -Path $rulesSrc -Destination $rulesDest -Recurse -Force -ErrorAction Stop
            Write-Host "  [OK]   .claude/rules/ upgraded" -ForegroundColor Green
            $upOk++
        } catch {
            Write-Host "  [FAIL] .claude/rules/ — $_" -ForegroundColor Red
            $upFail++
        }
    }

} else {
    # ── Junction mode: only update root config files ──
    Write-Host "── Upgrading (junction mode — config files only) ──" -ForegroundColor Cyan

    $upOk = 0; $upFail = 0

    $rootFiles = @("CLAUDE-project.md", "constitution.md", "OPS.md")
    foreach ($rf in $rootFiles) {
        $src = Join-Path $GOLD $rf
        if (-not (Test-Path $src)) { continue }
        if ($rf -eq "CLAUDE-project.md") {
            $dest = Join-Path $ProjectDir "CLAUDE.md"
        } else {
            $dest = Join-Path $ProjectDir $rf
        }
        # Backup
        if (Test-Path $dest) {
            $backupTarget = Join-Path $backupDir (Split-Path $dest -Leaf)
            try {
                Copy-Item -Path $dest -Destination $backupTarget -Force -ErrorAction Stop
            } catch { }
        }
        # Upgrade
        try {
            Copy-Item -Path $src -Destination $dest -Force -ErrorAction Stop
            $fileLabel = if ($rf -eq "CLAUDE-project.md") { "CLAUDE.md" } else { $rf }
            Write-Host "  [OK]   $fileLabel upgraded" -ForegroundColor Green
            $upOk++
        } catch {
            Write-Host "  [FAIL] $rf — $_" -ForegroundColor Red
            $upFail++
        }
    }

    Write-Host ""
    Write-Host "  ℹ️  Skills, _shared/, tools/, ledger/ are junction-linked — already live." -ForegroundColor DarkGray
    Write-Host "     Only config files (CLAUDE.md, constitution.md, OPS.md) were updated." -ForegroundColor DarkGray
}

# ── Rotate old backups (keep last 3) ────────────────────

$allBackups = Get-ChildItem (Join-Path $ProjectDir ".backup") -Directory | Sort-Object Name -Descending
$keep = 3
if ($allBackups.Count -gt $keep) {
    foreach ($old in $allBackups[$keep..($allBackups.Count - 1)]) {
        Remove-Item $old.FullName -Recurse -Force
        Write-Host "  [DEL] old backup $($old.Name)" -ForegroundColor DarkGray
    }
}

# ── Update VERSION.lock.json ────────────────────────────

try {
    $lock.locked_version = $remoteVer
    $lock.git_commit     = $remoteCommit
    $lock | Add-Member -MemberType NoteProperty -Name "updated_at" -Value (Get-Date -Format "yyyy-MM-ddTHH:mm:sszzz") -Force
    $lock | Add-Member -MemberType NoteProperty -Name "last_upgrade" -Value (Get-Date -Format "yyyy-MM-ddTHH:mm:sszzz") -Force
    $lock | ConvertTo-Json -Depth 4 | Set-Content $lockPath -Encoding UTF8
    Write-Host "  [OK]   VERSION.lock.json updated → $remoteVer" -ForegroundColor Green
} catch {
    Write-Host "  [WARN] VERSION.lock.json update failed: $_" -ForegroundColor Yellow
}

# ── Summary ─────────────────────────────────────────────

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Upgrade complete" -ForegroundColor White
Write-Host "  $localVer → $remoteVer" -ForegroundColor Green
Write-Host "  $upOk upgraded / $upFail failed" -ForegroundColor $(if ($upFail -eq 0) { "Green" } else { "Red" })
Write-Host "  Backup: $backupDir" -ForegroundColor White
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

if ($upFail -eq 0) {
    Write-Host "Next: cd `"$ProjectDir`" ; claude" -ForegroundColor Yellow
} else {
    Write-Host "Some files failed. Check .backup/ and retry." -ForegroundColor Red
    exit 1
}
