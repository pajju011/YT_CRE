@echo off
setlocal

cd /d "%~dp0"
title VideoGenerator Web Studio

:: Locate and activate Python Virtual Environment
if exist "%~dp0.venv-kokoro\Scripts\activate.bat" (
    call "%~dp0.venv-kokoro\Scripts\activate.bat"
) else if exist "%~dp0venv\Scripts\activate.bat" (
    call "%~dp0venv\Scripts\activate.bat"
)

echo Starting VideoGenerator Web Studio on http://localhost:5000 ...

:: Launch browser after 1 second delay
start "" cmd /c "timeout /t 1 /nobreak >nul && start http://localhost:5000"

:: Start the Python Web Server
python server.py

pause
