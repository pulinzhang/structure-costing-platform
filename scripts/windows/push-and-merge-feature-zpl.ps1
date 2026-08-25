#Requires -Version 5.1
<#
.SYNOPSIS
  将 feature-zpl 推到远程，合并进 master 并推送，最后切回 feature-zpl。

.DESCRIPTION
  1. 确保在仓库根目录、工作区无已跟踪的未提交改动
  2. 检出 feature-zpl 并 push 到 origin
  3. 检出 master，拉取最新后 merge feature-zpl
  4. 将 master push 到 origin
  5. 切回 feature-zpl

  合并冲突时停在 master，需手动解决或 git merge --abort。
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
Invoke-Git checkout $FeatureBranch
Invoke-Git push $RemoteName $FeatureBranch
Write-Ok "$FeatureBranch pushed to $RemoteName"

Write-Step "checkout $MasterBranch and merge $FeatureBranch"
Invoke-Git checkout $MasterBranch
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
    Write-Host ""
    Write-Host "[FAIL] merge conflict or merge failed, still on $MasterBranch" -ForegroundColor Red
    Write-Host "       continue: git add . ; git commit ; git push $RemoteName $MasterBranch" -ForegroundColor Yellow
    Write-Host "       abort:    git merge --abort ; git checkout $FeatureBranch" -ForegroundColor Yellow
    throw
}
Write-Ok "$FeatureBranch merged into $MasterBranch"

Write-Step "push $MasterBranch"
Invoke-Git push $RemoteName $MasterBranch
Write-Ok "$MasterBranch pushed to $RemoteName"

Write-Step "switch back to $FeatureBranch"
Invoke-Git checkout $FeatureBranch
Write-Ok "current branch: $FeatureBranch"

Write-Host ""
Write-Host "done: $FeatureBranch pushed, merged into $MasterBranch and pushed, switched back to $FeatureBranch." -ForegroundColor Green
