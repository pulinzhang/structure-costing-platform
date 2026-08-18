#Requires -Version 5.1
<#
.SYNOPSIS
  Windows 一键安装：无 Python 时可自动安装 Python 3.12、venv、生产依赖。
.NOTES
  由 setup.bat 调用。仓库根目录 = 本脚本目录的上两级。
#>
$ErrorActionPreference = "Stop"

function Write-Step([string]$Message) {
    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Write-Ok([string]$Message) {
    Write-Host "[OK] $Message" -ForegroundColor Green
}

function Write-Warn([string]$Message) {
    Write-Host "[WARN] $Message" -ForegroundColor Yellow
}

function Test-IsAdmin {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Get-RepoRoot {
    return (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
}

function Get-PythonCandidate {
    $commands = @(
        @{ Exe = "py"; Args = @("-3.12", "-c", "import sys; print(sys.executable)") },
        @{ Exe = "py"; Args = @("-3", "-c", "import sys; print(sys.executable)") },
        @{ Exe = "python"; Args = @("-c", "import sys; print(sys.executable)") },
        @{ Exe = "python3"; Args = @("-c", "import sys; print(sys.executable)") }
    )
    foreach ($item in $commands) {
        $cmd = Get-Command $item.Exe -ErrorAction SilentlyContinue
        if (-not $cmd) { continue }
        try {
            $exePath = & $item.Exe @($item.Args) 2>$null
            if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($exePath)) { continue }
            $exePath = $exePath.Trim()
            if (-not (Test-Path $exePath)) { continue }
            $verText = & $exePath -c "import sys; print('%d.%d' % sys.version_info[:2])"
            $parts = $verText.Trim().Split(".")
            $major = [int]$parts[0]
            $minor = [int]$parts[1]
            if ($major -gt 3 -or ($major -eq 3 -and $minor -ge 12)) {
                return $exePath
            }
            Write-Warn "发现 Python $verText，需要 >= 3.12，跳过: $exePath"
        } catch {
            continue
        }
    }
    return $null
}

function Install-PythonWithWinget {
    $winget = Get-Command winget -ErrorAction SilentlyContinue
    if (-not $winget) { return $false }
    Write-Step "尝试 winget 安装 Python 3.12 ..."
    try {
        & winget install -e --id Python.Python.3.12 --accept-package-agreements --accept-source-agreements
        if ($LASTEXITCODE -eq 0) { return $true }
    } catch {
        Write-Warn "winget 安装失败: $($_.Exception.Message)"
    }
    return $false
}

function Install-PythonFromInstaller([string]$InstallerPath) {
    if (-not (Test-Path $InstallerPath)) { return $false }
    Write-Step "静默安装 Python: $InstallerPath"
    $args = @(
        "/quiet",
        "InstallAllUsers=0",
        "PrependPath=1",
        "Include_test=0",
        "Include_launcher=1",
        "Include_pip=1",
        "SimpleInstall=1"
    )
    $proc = Start-Process -FilePath $InstallerPath -ArgumentList $args -Wait -PassThru
    return ($proc.ExitCode -eq 0)
}

function Install-PythonFromWeb([string]$VendorDir) {
    $url = "https://www.python.org/ftp/python/3.12.8/python-3.12.8-amd64.exe"
    $dest = Join-Path $VendorDir "python-3.12.8-amd64.exe"
    New-Item -ItemType Directory -Force -Path $VendorDir | Out-Null
    Write-Step "下载 Python 安装包 ..."
    Write-Host "    $url"
    try {
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
        Invoke-WebRequest -Uri $url -OutFile $dest -UseBasicParsing
    } catch {
        Write-Warn "下载失败: $($_.Exception.Message)"
        return $false
    }
    return (Install-PythonFromInstaller $dest)
}

function Refresh-PathFromMachine {
    $machine = [Environment]::GetEnvironmentVariable("Path", "Machine")
    $user = [Environment]::GetEnvironmentVariable("Path", "User")
    $env:Path = "$machine;$user"
}

function Open-FirewallPort([int]$Port) {
    if (-not (Test-IsAdmin)) {
        Write-Warn "非管理员，跳过防火墙规则。请手动放行 TCP $Port。"
        return
    }
    $ruleName = "StampingCostingPlatform-TCP-$Port"
    $existing = netsh advfirewall firewall show rule name="$ruleName" 2>$null
    if ($existing -match $ruleName) {
        Write-Ok "防火墙规则已存在: $ruleName"
        return
    }
    Write-Step "添加防火墙入站规则 TCP $Port ..."
    netsh advfirewall firewall add rule name="$ruleName" dir=in action=allow protocol=TCP localport=$Port | Out-Null
    Write-Ok "已放行 TCP $Port"
}

# -------------------- main --------------------
$repoRoot = Get-RepoRoot
Set-Location $repoRoot
Write-Host "仓库根目录: $repoRoot"
Write-Host "管理员: $(Test-IsAdmin)"

$vendorDir = Join-Path $PSScriptRoot "vendor"
$wheelsDir = Join-Path $vendorDir "wheels"

$pythonExe = Get-PythonCandidate
if (-not $pythonExe) {
    Write-Step "未检测到 Python >= 3.12，开始自动安装 ..."

    $localInstaller = Get-ChildItem -Path $vendorDir -Filter "python-3.12*-amd64.exe" -ErrorAction SilentlyContinue |
        Sort-Object Name -Descending |
        Select-Object -First 1

    $installed = $false
    if ($localInstaller) {
        $installed = Install-PythonFromInstaller $localInstaller.FullName
    }
    if (-not $installed) {
        $installed = Install-PythonWithWinget
    }
    if (-not $installed) {
        $installed = Install-PythonFromWeb $vendorDir
    }
    if (-not $installed) {
        throw "无法自动安装 Python 3.12。请手动安装后重试，或将安装包放到: $vendorDir"
    }

    Refresh-PathFromMachine
    Start-Sleep -Seconds 2
    $pythonExe = Get-PythonCandidate
    if (-not $pythonExe) {
        $guess = Join-Path $env:LOCALAPPDATA "Programs\Python\Python312\python.exe"
        if (Test-Path $guess) { $pythonExe = $guess }
    }
    if (-not $pythonExe) {
        throw "Python 已安装但当前会话找不到解释器。请关闭窗口后重新运行 setup.bat。"
    }
}

Write-Ok "使用 Python: $pythonExe"
& $pythonExe -c "import sys; print(sys.version)"

$venvDir = Join-Path $repoRoot ".venv"
$venvPython = Join-Path $venvDir "Scripts\python.exe"
$venvPip = Join-Path $venvDir "Scripts\pip.exe"

if (-not (Test-Path $venvPython)) {
    Write-Step "创建虚拟环境 .venv ..."
    & $pythonExe -m venv $venvDir
    if ($LASTEXITCODE -ne 0) { throw "创建 venv 失败" }
} else {
    Write-Ok "已存在虚拟环境: $venvDir"
}

Write-Step "升级 pip ..."
& $venvPython -m pip install -U pip
if ($LASTEXITCODE -ne 0) { throw "升级 pip 失败" }

$req = Join-Path $repoRoot "requirements.txt"
if (-not (Test-Path $req)) { throw "缺少 requirements.txt" }

Write-Step "安装运行依赖（生产，不含 ruff/mypy）..."
if (Test-Path $wheelsDir) {
    Write-Host "使用离线 wheels: $wheelsDir"
    & $venvPip install --no-index --find-links $wheelsDir -r $req
} else {
    & $venvPip install -r $req
}
if ($LASTEXITCODE -ne 0) { throw "pip install 失败" }

foreach ($dirName in @("data", "uploads", "logs")) {
    $path = Join-Path $repoRoot $dirName
    if (-not (Test-Path $path)) {
        New-Item -ItemType Directory -Path $path | Out-Null
        Write-Ok "创建目录 $dirName\"
    }
}

$envFile = Join-Path $repoRoot ".env"
$envExample = Join-Path $repoRoot ".env.production.example"
if (-not (Test-Path $envFile)) {
    if (-not (Test-Path $envExample)) { throw "缺少 .env.production.example" }
    Copy-Item $envExample $envFile
    Write-Ok "已生成 .env（来自 .env.production.example），请修改 PASSWORD_SALT / CORS_ORIGINS"
} else {
    Write-Ok ".env 已存在，未覆盖"
}

Open-FirewallPort -Port 8000

Write-Host ""
Write-Ok "安装流程结束"
Write-Host "下一步:"
Write-Host "  1) 编辑 $envFile"
Write-Host "  2) 运行 scripts\windows\start.bat"
Write-Host "  3) 浏览器打开 http://本机IP:8000/login  （默认 admin / admin123）"
Write-Host ""
