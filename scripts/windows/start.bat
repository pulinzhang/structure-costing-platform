@echo off
chcp 65001 >nul
setlocal EnableExtensions EnableDelayedExpansion

REM 生产启动：走 run_prod.py（多 Worker，无 reload）
REM workers / port 由 run_prod.py 读环境变量与 .env
cd /d "%~dp0..\.."

if not exist ".venv\Scripts\python.exe" (
  echo [ERROR] 未找到 .venv，请先运行 scripts\windows\setup.bat
  pause
  exit /b 1
)

if not exist ".env" (
  echo [WARN] 缺少 .env，正在从 .env.production.example 复制 ...
  if exist ".env.production.example" (
    copy /Y ".env.production.example" ".env" >nul
  ) else (
    echo [ERROR] 缺少 .env.production.example
    pause
    exit /b 1
  )
)

set "APP_ENV=production"
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"

REM 从 .env 粗读，仅用于启动横幅展示（真正启服由 run_prod.py 再读一遍）
set "UVICORN_WORKERS=4"
set "PORT=8000"
for /f "usebackq eol=# tokens=1,* delims==" %%A in (".env") do (
  if /I "%%A"=="UVICORN_WORKERS" set "UVICORN_WORKERS=%%B"
  if /I "%%A"=="PORT" set "PORT=%%B"
)
set "UVICORN_WORKERS=!UVICORN_WORKERS: =!"
set "PORT=!PORT: =!"

echo.
echo ============================================================
echo   生产启动  APP_ENV=%APP_ENV%  workers=!UVICORN_WORKERS!  port=!PORT!
echo   入口: run_prod.py
echo   登录页: http://127.0.0.1:!PORT!/login
echo   主应用: http://127.0.0.1:!PORT!/app
echo   按 Ctrl+C 结束
echo ============================================================
echo.

".venv\Scripts\python.exe" run_prod.py
set "EC=%ERRORLEVEL%"
echo.
echo 进程已退出，代码 %EC%
pause
exit /b %EC%
