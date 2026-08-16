@echo off
chcp 65001 >nul
setlocal EnableExtensions

REM 注册为 Windows 服务（需管理员）
cd /d "%~dp0"

net session >nul 2>&1
if errorlevel 1 (
  echo [ERROR] 请右键本文件 →「以管理员身份运行」
  pause
  exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install-service.ps1"
set "EC=%ERRORLEVEL%"
echo.
if not "%EC%"=="0" echo [ERROR] 安装服务失败，退出码 %EC%
pause
exit /b %EC%
