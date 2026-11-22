@echo off
setlocal EnableDelayedExpansion

:: Change directory to the repository root
cd /d "%~dp0"
title VideoGenerator Launcher

:: Locate and configure Python Virtual Environment
if exist "%~dp0.venv-kokoro\Scripts\python.exe" (
    call "%~dp0.venv-kokoro\Scripts\activate.bat"
    set "PY_CMD="%~dp0.venv-kokoro\Scripts\python.exe""
) else if exist "%~dp0venv\Scripts\python.exe" (
    call "%~dp0venv\Scripts\activate.bat"
    set "PY_CMD="%~dp0venv\Scripts\python.exe""
) else (
    set "PY_CMD=python"
)

:: Track if launched interactively or via CLI
set "INTERACTIVE=1"
if not "%~1"=="" (
    set "INTERACTIVE=0"
    if /i "%~1"=="ui" goto opt_web_ui
    if /i "%~1"=="web" goto opt_web_ui
    if /i "%~1"=="studio" goto opt_studio
    if /i "%~1"=="voice" goto opt_voice
    if /i "%~1"=="render" goto opt_render
    if /i "%~1"=="sfx" goto opt_sfx
    if /i "%~1"=="test" goto opt_test
    if /i "%~1"=="auth" goto opt_auth
    if /i "%~1"=="upload" goto opt_upload
    if /i "%~1"=="schedule" goto opt_schedule
    if /i "%~1"=="gen" goto opt_gen
    echo Unknown argument: %~1
    echo Usage: run.bat [ui^|studio^|voice^|render^|sfx^|test^|auth^|upload^|schedule^|gen]
    exit /b 1
)

:menu
cls
echo ================================================================
echo           VIDEO GENERATOR - CONTROL PANEL
echo ================================================================
echo.
echo   [1] Launch Web Studio (Modern Website UI)  ^<-- PRESS ENTER
echo   [2] Launch Remotion Studio (Visual Canvas Preview)
echo   [3] Generate Voice ^& Captions (Kokoro AI: Short 2)
echo   [4] Render Remotion Video (Short2Math / All)
echo   [5] Mix Audio ^& Sound Effects (mix_sfx.py)
echo   [6] Test Local Kokoro AI Voice (test_kokoro.py)
echo   [7] YouTube: OAuth Login (auth_login.py)
echo   [8] YouTube: Upload Video (upload_youtube.py)
echo   [9] YouTube: Schedule Video (schedule_youtube.py)
echo   [10] Regenerate Remotion Registry (npm run gen)
echo   [0] Exit
echo.
echo ================================================================
set "choice=1"
set /p "choice=Enter choice [1-10] (Default is 1 - Web Studio): "

if "%choice%"=="1" goto opt_web_ui
if "%choice%"=="2" goto opt_studio
if "%choice%"=="3" goto opt_voice
if "%choice%"=="4" goto opt_render
if "%choice%"=="5" goto opt_sfx
if "%choice%"=="6" goto opt_test
if "%choice%"=="7" goto opt_auth
if "%choice%"=="8" goto opt_upload
if "%choice%"=="9" goto opt_schedule
if "%choice%"=="10" goto opt_gen
if "%choice%"=="0" goto opt_exit

echo.
echo Invalid option selected: %choice%
pause
goto menu

:opt_web_ui
echo.
echo ================================================================
echo Starting VideoGenerator Web Studio...
echo URL: http://localhost:5000
echo ================================================================
start "" cmd /c "timeout /t 1 /nobreak >nul && start http://localhost:5000"
%PY_CMD% server.py
goto check_return

:opt_studio
echo.
echo ================================================================
echo Starting Remotion Studio in browser...
echo (Press Ctrl+C to stop)
echo ================================================================
cd /d "%~dp0remotion"
call npm run studio
cd /d "%~dp0"
goto check_return

:opt_voice
echo.
echo ================================================================
echo Generating voice with Kokoro ONNX...
echo ================================================================
%PY_CMD% tools\gen_voice_kokoro.py
if errorlevel 1 (
    echo [ERROR] Kokoro voice generation failed.
    goto check_return
)
echo.
echo Updating Remotion word timestamps ^& captions...
%PY_CMD% tools\update_kokoro_captions.py
if errorlevel 1 (
    echo [ERROR] Caption update failed.
    goto check_return
)
echo [SUCCESS] Voice and captions generated successfully!
goto check_return

:opt_render
echo.
echo ================================================================
echo Rendering Short2Math Video via Remotion...
echo ================================================================
cd /d "%~dp0remotion"
call npm run gen
node scripts\render-all.mjs Short2Math
cd /d "%~dp0"
goto check_return

:opt_sfx
echo.
echo ================================================================
echo Auditioning SFX mix...
echo ================================================================
if exist "%~dp0shorts\short-2-math\sfx-plan.json" (
    %PY_CMD% tools\mix_sfx.py shorts\short-2-math\sfx-plan.json
) else (
    echo [ERROR] shorts\short-2-math\sfx-plan.json not found.
)
goto check_return

:opt_test
echo.
echo ================================================================
echo Running Kokoro TTS test...
echo ================================================================
%PY_CMD% test_kokoro.py
goto check_return

:opt_auth
echo.
echo ================================================================
echo Authorizing YouTube Account (Browser OAuth)...
echo ================================================================
%PY_CMD% auth_login.py
goto check_return

:opt_upload
echo.
echo ================================================================
echo Uploading Video to YouTube...
echo ================================================================
%PY_CMD% upload_youtube.py
goto check_return

:opt_schedule
echo.
echo ================================================================
echo Scheduling Video on YouTube...
echo ================================================================
%PY_CMD% schedule_youtube.py
goto check_return

:opt_gen
echo.
echo ================================================================
echo Regenerating Remotion Registry...
echo ================================================================
cd /d "%~dp0remotion"
call npm run gen
cd /d "%~dp0"
echo [SUCCESS] Registry updated.
goto check_return

:check_return
if "%INTERACTIVE%"=="1" (
    echo.
    pause
    goto menu
) else (
    exit /b %errorlevel%
)

:opt_exit
echo Exiting...
exit /b 0
