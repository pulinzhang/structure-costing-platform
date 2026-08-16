@echo off
chcp 65001 >nul
setlocal EnableExtensions

REM ============================================================
REM  汽车冲压件自动核价平台 - Windows 一键安装（可无 Python 环境）
REM  双击或「以管理员身份运行」本文件即可
REM ============================================================

cd /d "%~dp0"
set "PS1=%~dp0setup.ps1"

if not exist "%PS1%" (
  echo [ERROR] 找不到 setup.ps1: %PS1%
  pause
  exit /b 1
)

echo.
echo ============================================================
echo   Stamping Costing Platform - Setup
echo ============================================================
echo.

REM 优先用 Windows PowerShell；失败再试 pwsh
where powershell >nul 2>&1
if errorlevel 1 (
  echo [ERROR] 本机没有 PowerShell，无法自动安装。
  pause
  exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%PS1%"
set "EC=%ERRORLEVEL%"

echo.
if "%EC%"=="0" (
  echo [OK] 安装完成。请编辑项目根目录 .env 后运行 start.bat
) else (
  echo [ERROR] 安装失败，退出码 %EC%。请向上翻看日志。
)
echo.
pause
exit /b %EC%
