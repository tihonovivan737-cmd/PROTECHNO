@echo off
chcp 65001 > nul
setlocal EnableExtensions

REM ============================================================
REM  Pro-Techno DEV - uvicorn (8000) + Vite (5173).
REM ============================================================

set "BACKEND_DIR=%~dp0"
set "FRONTEND_DIR=D:\DS\Pro-Techno"

echo.
echo ====== Pro-Techno DEV ======
echo Backend:  %BACKEND_DIR%
echo Frontend: %FRONTEND_DIR%
echo ============================
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
  echo [bk] Missing packages - installing from requirements.txt
  "%PYTHON_CMD%" -m pip install --disable-pip-version-check -r "%BACKEND_DIR%requirements.txt"
  if errorlevel 1 (
    echo [!] pip install failed. Fix the error above and rerun.
    pause & exit /b 1
  )
) else (
  echo [bk] Python packages are present.
)

REM --- 3) Backend env ---
if not exist "%BACKEND_DIR%.env" (
  echo.
  echo [!] File not found: %BACKEND_DIR%.env
  echo     Backend will not start without DB_*, ACCESS_TOKEN, GROUP_ID and related variables.
  pause & exit /b 1
)

REM --- 4) Node + npm ---
where node >nul 2>nul
if errorlevel 1 (
  echo [!] Node.js not found in PATH. Install Node.js 20+ and rerun.
  pause & exit /b 1
)

if not exist "%FRONTEND_DIR%\node_modules" (
  echo [fe] node_modules missing - running npm install...
  pushd "%FRONTEND_DIR%"
  call npm install
  if errorlevel 1 (
    echo [!] npm install failed.
    popd & pause & exit /b 1
  )
  popd
) else (
  echo [fe] node_modules present.
)

REM --- 5) Show IPv4 for mobile ---
echo.
echo --- IPv4 of this machine ---
for /f "tokens=2 delims=:" %%A in ('ipconfig ^| findstr /C:"IPv4"') do (
  for /f "tokens=* delims= " %%B in ("%%A") do echo   http://%%B:5173/
)
echo (local PC - http://localhost:5173/)
echo.

REM --- 6) Run ---
echo [run] Starting backend on port 8000...
start "Pro-Techno backend" cmd /k "cd /d %BACKEND_DIR% && set BACKEND_HOST=0.0.0.0&& set BACKEND_PORT=8000&& set BACKEND_RELOAD=true&& \"%PYTHON_CMD%\" -m backend.app.main"

timeout /t 2 /nobreak > nul

echo [run] Starting frontend on port 5173...
start "Pro-Techno frontend" cmd /k "cd /d %FRONTEND_DIR% && npm run dev"

echo.
echo ============================
echo Done. Backend and frontend are running in separate windows.
echo Close those windows to stop the services.
echo ============================
echo.
pause
endlocal
