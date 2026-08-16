@echo off
chcp 65001 >nul
setlocal EnableExtensions

REM 停止占用 8000 端口的进程（默认生产端口）
set "PORT=8000"
if not "%~1"=="" set "PORT=%~1"

echo 查找占用 TCP %PORT% 的进程 ...
for /f "tokens=5" %%P in ('netstat -ano ^| findstr /R /C:":%PORT% .*LISTENING"') do (
  echo 结束 PID %%P
  taskkill /F /PID %%P >nul 2>&1
)

echo 完成。若服务仍在跑，请在任务管理器中结束 python.exe。
pause
