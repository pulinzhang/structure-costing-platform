@echo off
chcp 65001 >nul
setlocal EnableExtensions

REM 卸载 Windows 服务（需管理员）
cd /d "%~dp0"

net session >nul 2>&1
if errorlevel 1 (
  echo [ERROR] 请右键本文件 →「以管理员身份运行」
  pause
  exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0uninstall-service.ps1"
set "EC=%ERRORLEVEL%"
echo.
pause
exit /b %EC%
