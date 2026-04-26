@echo off
chcp 65001 > nul
setlocal EnableExtensions

REM ============================================================
REM  Pro-Techno PROD - build frontend and serve through FastAPI.
REM ============================================================

set "BACKEND_DIR=%~dp0"
set "FRONTEND_DIR=D:\DS\Pro-Techno"

echo.
echo ====== Pro-Techno PROD ======
echo Backend:  %BACKEND_DIR%
echo Frontend: %FRONTEND_DIR%
echo =============================
echo.

REM --- 1) Python ---
set "PYTHON_CMD="
where python >nul 2>nul && set "PYTHON_CMD=python"
if not defined PYTHON_CMD if defined CONDA_PREFIX if exist "%CONDA_PREFIX%\python.exe" set "PYTHON_CMD=%CONDA_PREFIX%\python.exe"
if not defined PYTHON_CMD if exist "D:\Conda\python.exe" set "PYTHON_CMD=D:\Conda\python.exe"
if not defined PYTHON_CMD (
  echo [!] Python not found in PATH or conda.
  echo     Install Python 3.10+ or run from an activated conda environment.
  pause & exit /b 1
)
echo [bk] Python: %PYTHON_CMD%

REM --- 2) Backend deps ---
echo [bk] Checking fastapi/uvicorn/sqlalchemy/asyncpg/pydantic-settings...
"%PYTHON_CMD%" -c "import fastapi, uvicorn, sqlalchemy, asyncpg, pydantic_settings, multipart" 2>nul
if errorlevel 1 (
  echo [bk] Installing missing backend packages from requirements.txt...
  "%PYTHON_CMD%" -m pip install --disable-pip-version-check -r "%BACKEND_DIR%requirements.txt"
  if errorlevel 1 (
    echo [!] pip install failed.
    pause & exit /b 1
  )
)

REM --- 3) Backend env ---
if not exist "%BACKEND_DIR%.env" (
  echo [!] %BACKEND_DIR%.env not found. Backend cannot start without it.
  pause & exit /b 1
)

REM --- 4) Node + npm ---
where node >nul 2>nul
if errorlevel 1 (
  echo [!] Node.js not found in PATH. Install Node.js 20+ and rerun.
  pause & exit /b 1
)
if not exist "%FRONTEND_DIR%\node_modules" (
  echo [fe] Running npm install...
  pushd "%FRONTEND_DIR%"
  call npm install || (popd & pause & exit /b 1)
  popd
)

REM --- 5) Build frontend ---
echo [fe] npm run build...
pushd "%FRONTEND_DIR%"
call npm run build
if errorlevel 1 (
  echo [!] Frontend build failed.
  popd & pause & exit /b 1
)
popd

if not exist "%FRONTEND_DIR%\dist\index.html" (
  echo [!] %FRONTEND_DIR%\dist\index.html not found after build.
  pause & exit /b 1
)

REM --- 6) Show IPv4 ---
echo.
echo --- IPv4 of this machine ---
for /f "tokens=2 delims=:" %%A in ('ipconfig ^| findstr /C:"IPv4"') do (
  for /f "tokens=* delims= " %%B in ("%%A") do echo   http://%%B:8000/
)
echo (local PC - http://localhost:8000/)
echo.
echo Stop with Ctrl+C in this window.
echo =============================
echo.

REM --- 7) Run FastAPI with dist ---
cd /d "%BACKEND_DIR%"
set "BACKEND_HOST=0.0.0.0"
set "BACKEND_PORT=8000"
set "BACKEND_RELOAD=false"
set "FRONTEND_DIST=%FRONTEND_DIR%\dist"
"%PYTHON_CMD%" -m backend.app.main

endlocal
