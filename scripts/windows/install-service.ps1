#Requires -Version 5.1
<#
.SYNOPSIS
  将本平台注册为 Windows 服务（通过 NSSM 包装 run_prod.py）。
.NOTES
  需管理员运行。首次会尝试下载 nssm 到 scripts\windows\vendor\nssm\
#>
$ErrorActionPreference = "Stop"

function Test-IsAdmin {
    $id = [Security.Principal.WindowsIdentity]::GetCurrent()
    $p = New-Object Security.Principal.WindowsPrincipal($id)
    return $p.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

if (-not (Test-IsAdmin)) {
    throw "请右键「以管理员身份运行」install-service.bat"
}

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Set-Location $repoRoot

$serviceName = "StampingCostingPlatform"
$displayName = "汽车冲压件自动核价平台"
$venvPython = Join-Path $repoRoot ".venv\Scripts\python.exe"
$envFile = Join-Path $repoRoot ".env"

if (-not (Test-Path $venvPython)) {
    throw "未找到 .venv，请先运行 scripts\windows\setup.bat"
}
if (-not (Test-Path $envFile)) {
    throw "未找到 .env，请先完成生产配置（可从 .env.production.example 复制）"
}

# ---------- 准备 NSSM ----------
$vendorNssm = Join-Path $PSScriptRoot "vendor\nssm"
$nssmExe = $null
$candidates = @(
    (Join-Path $vendorNssm "win64\nssm.exe"),
    (Join-Path $vendorNssm "nssm.exe"),
    (Get-Command nssm -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source)
) | Where-Object { $_ -and (Test-Path $_) }

if ($candidates.Count -gt 0) {
    $nssmExe = $candidates[0]
} else {
    Write-Host "==> 下载 NSSM ..." -ForegroundColor Cyan
    New-Item -ItemType Directory -Force -Path $vendorNssm | Out-Null
    $zipPath = Join-Path $vendorNssm "nssm.zip"
    # 2.24 稳定包（SourceForge）
    $url = "https://nssm.cc/release/nssm-2.24.zip"
    try {
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
        Invoke-WebRequest -Uri $url -OutFile $zipPath -UseBasicParsing
    } catch {
        throw "下载 NSSM 失败。请手动下载 https://nssm.cc/download ，解压后将 win64\nssm.exe 放到: $vendorNssm\win64\"
    }
    Expand-Archive -Path $zipPath -DestinationPath $vendorNssm -Force
    $found = Get-ChildItem -Path $vendorNssm -Recurse -Filter "nssm.exe" |
        Where-Object { $_.FullName -match "win64\\nssm\.exe$" } |
        Select-Object -First 1
    if (-not $found) {
        $found = Get-ChildItem -Path $vendorNssm -Recurse -Filter "nssm.exe" | Select-Object -First 1
    }
    if (-not $found) { throw "解压后未找到 nssm.exe" }
    $nssmExe = $found.FullName
}

Write-Host "使用 NSSM: $nssmExe"
Write-Host "仓库根目录: $repoRoot"

# ---------- 若已存在则先移除 ----------
$existing = Get-Service -Name $serviceName -ErrorAction SilentlyContinue
if ($existing) {
    Write-Host "==> 服务已存在，先停止并移除 ..." -ForegroundColor Yellow
    & $nssmExe stop $serviceName confirm 2>$null
    Start-Sleep -Seconds 1
    & $nssmExe remove $serviceName confirm
    Start-Sleep -Seconds 1
}

# ---------- 安装 ----------
$workers = 4
$port = 8000
Get-Content $envFile -Encoding UTF8 | ForEach-Object {
    $line = $_.Trim()
    if ($line -match '^\s*#' -or $line -eq "") { return }
    if ($line -match '^\s*UVICORN_WORKERS\s*=\s*(\d+)') { $workers = [int]$Matches[1] }
    if ($line -match '^\s*PORT\s*=\s*(\d+)') { $port = [int]$Matches[1] }
}

Write-Host "==> 安装服务 $serviceName （via run_prod.py；.env workers=$workers, port=$port）..." -ForegroundColor Cyan
& $nssmExe install $serviceName $venvPython
if ($LASTEXITCODE -ne 0) { throw "nssm install 失败" }

# Application：run_prod.py → uvicorn；workers/port 由 .env / 环境变量决定
$appParams = "run_prod.py"
& $nssmExe set $serviceName Application $venvPython
& $nssmExe set $serviceName AppDirectory $repoRoot
& $nssmExe set $serviceName AppParameters $appParams
& $nssmExe set $serviceName DisplayName $displayName
& $nssmExe set $serviceName Description "Stamping Costing Platform (run_prod.py → uvicorn workers)"
& $nssmExe set $serviceName Start SERVICE_AUTO_START
& $nssmExe set $serviceName AppStdout (Join-Path $repoRoot "logs\service-stdout.log")
& $nssmExe set $serviceName AppStderr (Join-Path $repoRoot "logs\service-stderr.log")
& $nssmExe set $serviceName AppRotateFiles 1
& $nssmExe set $serviceName AppRotateBytes 10485760
& $nssmExe set $serviceName AppExit Default Restart
& $nssmExe set $serviceName AppRestartDelay 5000

# 环境变量（生产）；UVICORN_WORKERS/PORT 写入服务环境，与 .env 一致
& $nssmExe set $serviceName AppEnvironmentExtra "APP_ENV=production" "PYTHONUTF8=1" "PYTHONIOENCODING=utf-8" "UVICORN_WORKERS=$workers" "PORT=$port"

New-Item -ItemType Directory -Force -Path (Join-Path $repoRoot "logs") | Out-Null

Write-Host "==> 启动服务 ..." -ForegroundColor Cyan
& $nssmExe start $serviceName
Start-Sleep -Seconds 2

$svc = Get-Service -Name $serviceName
Write-Host ""
Write-Host "[OK] 服务状态: $($svc.Status)" -ForegroundColor Green
Write-Host "名称: $serviceName"
Write-Host "workers: $workers  port: $port"
Write-Host "访问: http://127.0.0.1:${port}/login"
Write-Host "日志: $repoRoot\logs\service-stdout.log / service-stderr.log"
Write-Host ""
Write-Host "常用命令:"
Write-Host "  net start $serviceName"
Write-Host "  net stop $serviceName"
Write-Host "  scripts\windows\uninstall-service.bat"
Write-Host "改 workers：编辑 .env 中 UVICORN_WORKERS 后，重新以管理员运行 install-service.bat"
Write-Host ""
