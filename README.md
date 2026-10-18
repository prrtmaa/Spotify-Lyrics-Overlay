# Spotify Lyrics Overlay

A lightweight lyrics overlay for Spotify on Windows. It displays synced lyrics, track information, album art, and playback controls. Minimize it to a compact clock at the top center of your screen.

## Features

- Synced lyrics from LRCLIB
- Spotify playback and track information through Windows media controls
- Previous, play/pause, and next controls
- Compact, animated clock island
- Adjustable font, colors, opacity, size, and lyric lines
- Optional click-through, always-on-top, and Windows startup

## Run from source

Requirements: Windows 10 or 11 and Python 3.11 or later.

```powershell
pip install -r spotify_lyrics_overlay/requirements.txt
python run.py
```

Keep Spotify Desktop open and play a track. Lyrics require an internet connection and may not be available for every song.

## Shortcuts

| Shortcut | Action |
| --- | --- |
| `Ctrl+Alt+L` | Show or hide the overlay |
| `Ctrl+Alt+I` | Minimize to or restore the clock island |
| `Ctrl+Alt+M` | Cycle lyric line mode |
| `Ctrl+Alt+T` | Cycle background opacity |
| `Ctrl+Alt+Up` | Increase lyric font size |
| `Ctrl+Alt+Down` | Decrease lyric font size |

Right-click the overlay or the system tray icon for more options. Open **Settings** to change appearance and behavior. Font size can be set from 6 to 32 pt.

## Build

Run `build.bat` to create a standalone Windows executable with PyInstaller.

## License

MIT. See [LICENSE](LICENSE).
