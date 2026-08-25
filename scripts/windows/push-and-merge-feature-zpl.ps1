#Requires -Version 5.1
<#
.SYNOPSIS
  将 feature-zpl 推到远程，合并进 master 并推送；主工作区不切换 HEAD。

.DESCRIPTION
  1. 确保在仓库根目录、工作区无已跟踪的未提交改动
  2. 若尚未在 feature-zpl 则检出，再 push 到 origin
  3. 用临时 worktree 在 master 上 merge feature-zpl（不改主工作区 HEAD，避免 Cursor 锁文件）
  4. 将 master push 到 origin
  5. 主工作区保持 feature-zpl

  合并冲突时临时 worktree 会保留，需在该目录手动解决或删除 worktree。
#>
$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

$FeatureBranch = "feature-zpl"
$MasterBranch = "master"
$RemoteName = "origin"

function Write-Step([string]$Message) {
    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Write-Ok([string]$Message) {
    Write-Host "[OK] $Message" -ForegroundColor Green
}

function Invoke-Git {
    param(
        [Parameter(Mandatory = $true, ValueFromRemainingArguments = $true)]
        [string[]]$GitArgs
    )
    Write-Host ("    git " + ($GitArgs -join " ")) -ForegroundColor DarkGray
    & git @GitArgs
    if ($LASTEXITCODE -ne 0) {
        throw "git $($GitArgs -join ' ') failed (exit $LASTEXITCODE)"
    }
}

function Get-CurrentBranch {
    $name = & git rev-parse --abbrev-ref HEAD
    if ($LASTEXITCODE -ne 0) {
        throw "git rev-parse --abbrev-ref HEAD failed (exit $LASTEXITCODE)"
    }
    return $name.Trim()
}

function Switch-BranchIfNeeded {
    param([Parameter(Mandatory = $true)][string]$Branch)
    $current = Get-CurrentBranch
    if ($current -eq $Branch) {
        Write-Ok "already on $Branch, skip checkout"
        return
    }
    Invoke-Git checkout $Branch
}

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Set-Location $repoRoot
Write-Ok "repo root: $repoRoot"

Write-Step "check working tree"
$dirty = & git status --porcelain --untracked-files=no
if ($LASTEXITCODE -ne 0) {
    throw "git status failed (exit $LASTEXITCODE)"
}
if (-not [string]::IsNullOrWhiteSpace($dirty)) {
    Write-Host $dirty
    throw "tracked files have uncommitted changes; commit or stash first"
}
Write-Ok "tracked working tree is clean"

Write-Step "fetch remote"
Invoke-Git fetch $RemoteName
Write-Ok "fetch done"

Write-Step "checkout and push $FeatureBranch"
Switch-BranchIfNeeded $FeatureBranch
Invoke-Git push $RemoteName $FeatureBranch
Write-Ok "$FeatureBranch pushed to $RemoteName"

Write-Step "merge $FeatureBranch into $MasterBranch (temporary worktree)"
$worktreePath = Join-Path $env:TEMP "stamping-costing-platform-master-merge"
if (Test-Path $worktreePath) {
    Write-Host "    removing leftover worktree $worktreePath" -ForegroundColor DarkGray
    & git worktree remove --force $worktreePath 2>$null
    if (Test-Path $worktreePath) {
        Remove-Item -Recurse -Force $worktreePath
    }
    & git worktree prune
}

Invoke-Git worktree add $worktreePath $MasterBranch
$mergeFailed = $false
$inWorktree = $false
try {
    Push-Location $worktreePath
    $inWorktree = $true
    $remoteMaster = "$RemoteName/$MasterBranch"
    $remoteMasterExists = & git rev-parse --verify --quiet $remoteMaster
    if ($LASTEXITCODE -eq 0 -and -not [string]::IsNullOrWhiteSpace($remoteMasterExists)) {
        Invoke-Git pull --ff-only $RemoteName $MasterBranch
    } else {
        Write-Host "    remote has no $MasterBranch yet, skip pull" -ForegroundColor Yellow
    }

    try {
        Invoke-Git merge --no-edit $FeatureBranch
    } catch {
        $mergeFailed = $true
        Write-Host ""
        Write-Host "[FAIL] merge conflict or merge failed in worktree:" -ForegroundColor Red
        Write-Host "       $worktreePath" -ForegroundColor Yellow
        Write-Host "       continue: cd that dir ; git add . ; git commit ; git push $RemoteName $MasterBranch" -ForegroundColor Yellow
        Write-Host "       abort:    git -C `"$repoRoot`" worktree remove --force `"$worktreePath`"" -ForegroundColor Yellow
        throw
    }
    Write-Ok "$FeatureBranch merged into $MasterBranch"

    Write-Step "push $MasterBranch"
    Invoke-Git push $RemoteName $MasterBranch
    Write-Ok "$MasterBranch pushed to $RemoteName"
} finally {
    if ($inWorktree) {
        Pop-Location
    }
    if (-not $mergeFailed -and (Test-Path $worktreePath)) {
        Write-Step "remove temporary worktree"
        & git -C $repoRoot worktree remove --force $worktreePath
        if ($LASTEXITCODE -ne 0) {
            Write-Host "[WARN] worktree remove failed, prune leftover: git worktree prune" -ForegroundColor Yellow
        } else {
            Write-Ok "worktree removed"
        }
    }
}

Write-Ok "current branch: $(Get-CurrentBranch)"

Write-Host ""
Write-Host "done: $FeatureBranch pushed, merged into $MasterBranch and pushed. Main worktree stayed on $FeatureBranch." -ForegroundColor Green
