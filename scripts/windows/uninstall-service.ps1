#Requires -Version 5.1
$ErrorActionPreference = "Stop"

function Test-IsAdmin {
    $id = [Security.Principal.WindowsIdentity]::GetCurrent()
    $p = New-Object Security.Principal.WindowsPrincipal($id)
    return $p.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

if (-not (Test-IsAdmin)) {
    throw "请以管理员身份运行 uninstall-service.bat"
}

$serviceName = "StampingCostingPlatform"
$vendorNssm = Join-Path $PSScriptRoot "vendor\nssm"
$nssmExe = $null

$candidates = @(
    (Join-Path $vendorNssm "win64\nssm.exe"),
    (Get-ChildItem -Path $vendorNssm -Recurse -Filter "nssm.exe" -ErrorAction SilentlyContinue |
        Where-Object { $_.FullName -match "win64" } |
        Select-Object -First 1 -ExpandProperty FullName),
    (Get-Command nssm -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source)
) | Where-Object { $_ -and (Test-Path $_) }

if ($candidates.Count -gt 0) {
    $nssmExe = @($candidates)[0]
}

$svc = Get-Service -Name $serviceName -ErrorAction SilentlyContinue
if (-not $svc) {
    Write-Host "服务 $serviceName 不存在，无需卸载。"
    exit 0
}

if ($nssmExe) {
    & $nssmExe stop $serviceName confirm 2>$null
    Start-Sleep -Seconds 1
    & $nssmExe remove $serviceName confirm
} else {
    Stop-Service -Name $serviceName -Force -ErrorAction SilentlyContinue
    sc.exe delete $serviceName | Out-Null
}

Write-Host "[OK] 已卸载服务 $serviceName" -ForegroundColor Green
