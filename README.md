# Spotify Lyrics Overlay

A modern Spotify lyrics overlay for Windows built with Python and PyQt6. Display synchronized lyrics directly on your desktop with a clean floating interface inspired by Dynamic Island and modern desktop widgets.

![Python](https://img.shields.io/badge/Python-3.11+-blue)
![PyQt6](https://img.shields.io/badge/PyQt6-GUI-green)
![Platform](https://img.shields.io/badge/Platform-Windows%2010%20%2F%2011-blue)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## Features

- Real-time synchronized lyrics
- Floating desktop overlay
- Dynamic Island inspired mini mode
- Album artwork display
- Media controls (Previous, Play/Pause, Next)
- Animated audio visualizer
- Always-on-top support
- Click-through mode
- Auto-start with Windows
- Adjustable transparency
- Customizable font size
- Global keyboard shortcuts
- Offline lyrics cache

---

## Screenshots

### Full Overlay Mode

![Full Overlay](screenshots/full-overlay.png)

### Mini Mode

![Mini Mode](screenshots/mini-mode.png)

---

## Tech Stack

- Python 3.11+
- PyQt6
- Windows GSMTC API
- LRCLIB API
- PyInstaller

---

## Installation

### Requirements

- Windows 10 / 11
- Python 3.11+
- Spotify Desktop

### Clone Repository

```bash
git clone https://github.com/prrtmaa/Spotify-Lyrics-Overlay.git
cd Spotify-Lyrics-Overlay
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Run Application

```bash
python run.py
```

---

## Build Executable

Using PyInstaller:

```bash
pyinstaller --noconsole ^
--onefile ^
--name="SpotifyLyricsOverlay" ^
--icon="spotify_lyrics_overlay/assets/icon.ico" ^
spotify_lyrics_overlay/main.py
```

The executable will be generated inside:

```text
dist/
```

---

## Project Structure

```text
Spotify-Lyrics-Overlay/
│
├── spotify_lyrics_overlay/
│   ├── main.py
│   ├── overlay.py
│   ├── spotify_controller.py
│   ├── lyrics_provider.py
│   ├── settings.py
│   ├── config.json
│   └── assets/
│
├── run.py
├── requirements.txt
├── README.md
└── LICENSE
```

---

## Keyboard Shortcuts

| Shortcut | Action |
|-----------|---------|
| Ctrl + Alt + L | Show / Hide Overlay |
| Ctrl + Alt + M | Change Lyrics Mode |
| Ctrl + Alt + T | Change Transparency |
| Ctrl + Alt + Up | Increase Font Size |
| Ctrl + Alt + Down | Decrease Font Size |

---

## Configuration

User preferences are stored in:

```text
spotify_lyrics_overlay/config.json
```

Available settings include:

- Font size
- Display mode
- Transparency
- Window position
- Always on top
- Auto-start
- Hotkeys

---

## License

This project is released under the MIT License.

---

## Bahasa Indonesia

Spotify Lyrics Overlay adalah aplikasi desktop untuk Windows yang menampilkan lirik Spotify secara sinkron langsung di desktop dengan tampilan modern dan ringan.

### Fitur Utama

- Lirik sinkron realtime
- Mode overlay mengambang
- Mode mini ala Dynamic Island
- Cover album Spotify
- Kontrol media
- Visualizer animasi
- Always on Top
- Click-through mode
- Transparansi yang dapat diatur
- Auto-start Windows
- Hotkey global

### Menjalankan Aplikasi

```bash
pip install -r requirements.txt
python run.py
```

### Lisensi

MIT License.
