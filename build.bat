@echo off
setlocal
cd /d "%~dp0"

echo ===================================================
echo   Building Spotify Lyrics Overlay Executable (.exe)
echo ===================================================
echo.

if not exist ".venv-build\Scripts\python.exe" (
    echo Creating an isolated build environment...
    python -m venv .venv-build
    if errorlevel 1 goto :error
)

echo Installing build dependencies in .venv-build...
".venv-build\Scripts\python.exe" -m pip install -r spotify_lyrics_overlay\requirements.txt
if errorlevel 1 goto :error

echo.
echo Starting build process with PyInstaller...
".venv-build\Scripts\python.exe" -m PyInstaller --clean --noconfirm --noconsole ^
    --onefile ^
    --name "SpotifyLyricsOverlay" ^
    --icon "spotify_lyrics_overlay\assets\icon.ico" ^
    --add-data "spotify_lyrics_overlay\assets;assets" ^
    --collect-all winsdk ^
    "spotify_lyrics_overlay\main.py"
if errorlevel 1 goto :error

echo.
if not exist "dist\SpotifyLyricsOverlay.exe" goto :error

set "ISCC="
where ISCC.exe >nul 2>nul
if not errorlevel 1 set "ISCC=ISCC.exe"
if not defined ISCC if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not defined ISCC if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"
if not defined ISCC if exist "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" set "ISCC=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"

if defined ISCC (
    echo Building Windows installer with uninstall support...
    "%ISCC%" "installer.iss"
    if errorlevel 1 goto :error
    echo Installer: dist\SpotifyLyricsOverlay-Setup.exe
) else (
    echo Inno Setup 6 was not found. Skipping the installer.
    echo Install Inno Setup 6 and rerun this script to create an installer
    echo with an entry in Windows Installed Apps and an uninstaller.
)

echo.
echo ===================================================
echo  BUILD SUCCESSFUL!
echo  Standalone executable: dist\SpotifyLyricsOverlay.exe
echo  Share the standalone EXE or the installer if it was created.
echo ===================================================
goto :end

:error
echo.
echo [ERROR] Build failed. Review the messages above.
set "BUILD_EXIT_CODE=1"

:end
if not defined BUILD_EXIT_CODE set "BUILD_EXIT_CODE=0"
pause
exit /b %BUILD_EXIT_CODE%
