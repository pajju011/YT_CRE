@echo off
setlocal
cd /d "%~dp0"
title VideoAI Studio

set "PY_CMD=python"
if exist "%~dp0.venv-kokoro\Scripts\python.exe" (
    set "PY_CMD=%~dp0.venv-kokoro\Scripts\python.exe"
) else if exist "%~dp0venv\Scripts\python.exe" (
    set "PY_CMD=%~dp0venv\Scripts\python.exe"
)

if /i "%~1"=="freefield" goto opt_freefield
if /i "%~1"=="menu" goto menu
if /i "%~1"=="help" goto help

cls
echo =======================================================================
echo               VIDEOAI STUDIO - 100%% FREE AI VIDEO FACTORY
echo =======================================================================
echo.
echo   * Phase 1: Multilingual Voice Studio (80+ Languages) and Talking Head
echo   * Phase 2: Multi-Scene Storyboard and Character Consistency Engine
echo   * Phase 3: Auto-Music Scoring Bed, SFX Sound Design and Audio Ducking
echo   * Phase 4: Face Swapping, Identity Recast and Poisson Blending
echo   * Cinema:  Freefield 33 Dynamic Camera Moves and Optical Film Look
echo   * Cloud:   Google Colab T4 Cloud GPU Bridge
echo.
echo =======================================================================
echo   Starting Studio at http://localhost:5000 ...
echo   (Press Ctrl+C in this window anytime to stop the server)
echo =======================================================================
echo.

start "" cmd /c "timeout /t 1 /nobreak >nul && start http://localhost:5000"
"%PY_CMD%" server.py
exit /b %ERRORLEVEL%

:opt_freefield
cls
echo =======================================================================
echo   Launching Freefield Standalone Suite (120+ Open-Weights Apps)...
echo =======================================================================
cd /d "%~dp0freefield"
start "" cmd /c "timeout /t 1 /nobreak >nul && start http://127.0.0.1:3005"
node --env-file-if-exists=.env --experimental-strip-types --disable-warning=ExperimentalWarning server/server.ts
exit /b 0

:menu
cls
echo =======================================================================
echo                    VIDEOAI STUDIO CONTROL PANEL
echo =======================================================================
echo.
echo   [1] Launch VideoAI Web Studio (Default - http://localhost:5000)
echo   [2] Launch Freefield Standalone Suite (120+ Apps - http://localhost:3005)
echo   [3] Test Local Kokoro TTS Voice Engine
echo   [4] Test Face Swap and Video Recast (Phase 4)
echo   [5] Launch Remotion Studio (Canvas Animation Preview)
echo   [0] Exit
echo.
echo =======================================================================
set "choice=1"
set /p "choice=Enter choice [0-5] (Default: 1): "

if "%choice%"=="1" (
    cd /d "%~dp0"
    start "" cmd /c "timeout /t 1 /nobreak >nul && start http://localhost:5000"
    "%PY_CMD%" server.py
    exit /b 0
)
if "%choice%"=="2" goto opt_freefield
if "%choice%"=="3" (
    "%PY_CMD%" tools/test_kokoro.py
    pause
    goto menu
)
if "%choice%"=="4" (
    "%PY_CMD%" tools/face_swap_engine.py --source media/projects/dancing-girl/b2-dance.png --target media/projects/dancing-girl/b1-dance.png --out shorts/faceswap-results/menu_test.jpg
    pause
    goto menu
)
if "%choice%"=="5" (
    cd /d "%~dp0remotion"
    call npm run studio
    pause
    goto menu
)
if "%choice%"=="0" exit /b 0
goto menu

:help
echo Usage:
echo   run.bat            : Launch VideoAI Web Studio (http://localhost:5000)
echo   run.bat menu       : Open interactive tool selector
echo   run.bat freefield  : Launch standalone Freefield Suite (http://localhost:3005)
exit /b 0
