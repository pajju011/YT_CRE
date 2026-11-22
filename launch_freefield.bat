@echo off
title Freefield Studio - Higgsfield Open-Weights Suite (120+ Apps)
cd /d "%~dp0"

if not exist "freefield\package.json" (
    echo [Setup] Freefield directory not found. Cloning neuregex/freefield...
    git clone --depth 1 https://github.com/neuregex/freefield.git freefield
    cd freefield
    echo [Setup] Installing dependencies...
    call npm install
    cd ..
)

cd /d "%~dp0freefield"

if not exist ".env" (
    echo [Setup] Initializing Freefield environment...
    (
        echo COMFY_BASE_URL=http://127.0.0.1:8188
        echo FREEFIELD_TOKEN=comfyui-0b1dcfe5c7324da252be50a9ade0ac6a008232c513068e53acdafdfa419f720d
        echo PORT=3005
        echo FREEFIELD_HOST=127.0.0.1
        echo FREEFIELD_DRAFTS=1
    ) > .env
)

echo =======================================================================
echo   Freefield Studio (120+ Open-Weights Image, Video, VFX ^& Audio Apps)
echo =======================================================================
echo.
echo Starting Freefield Studio Server on http://127.0.0.1:3005...
echo.

start "" "http://127.0.0.1:3005"
node --env-file-if-exists=.env --experimental-strip-types --disable-warning=ExperimentalWarning server/server.ts
pause
