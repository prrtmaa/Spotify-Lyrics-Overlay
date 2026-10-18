@echo off
echo ===================================================
echo   Building Spotify Lyrics Overlay Executable (.exe)
echo ===================================================
echo.

echo Checking dependencies...
pip install -r spotify_lyrics_overlay\requirements.txt

echo.
echo Starting build process with PyInstaller...
pyinstaller --noconsole ^
    --onefile ^
    --name="SpotifyLyricsOverlay" ^
    --icon="spotify_lyrics_overlay\assets\icon.ico" ^
    --add-data="spotify_lyrics_overlay\assets;assets" ^
    --add-data="spotify_lyrics_overlay\config.json;." ^
    spotify_lyrics_overlay\main.py

echo.
if exist "dist\SpotifyLyricsOverlay.exe" (
    echo ===================================================
    echo  BUILD SUCCESSFUL!
    echo  Standalone executable located at: dist\SpotifyLyricsOverlay.exe
    echo ===================================================
) else (
    echo [ERROR] Build failed. Please check the error output above.
)
pause
