# Spotify Lyrics Overlay

[![Python](https://img.shields.io/badge/Python-3.11+-blue)](https://www.python.org/)
[![PyQt6](https://img.shields.io/badge/PyQt6-GUI-green)](https://pypi.org/project/PyQt6/)
[![Platform](https://img.shields.io/badge/Platform-Windows%2010%20%2F%2011-blue)]()
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

A modern desktop lyrics overlay for Spotify built with Python and PyQt6. Display synchronized lyrics directly on your desktop with a customizable floating interface inspired by Dynamic Island and modern media widgets.

Designed for users who enjoy following song lyrics while working, studying, gaming, or simply listening to music without constantly switching back to the Spotify window.

---

## ✨ Features

### 🎵 Lyrics Synchronization

- Real-time synchronized lyrics
- Automatic lyrics retrieval
- Active lyric highlighting
- Offline lyrics caching
- Smooth lyric transitions

### 🖥️ Desktop Overlay

- Floating desktop widget
- Frameless design
- Always-on-top support
- Click-through mode
- Draggable anywhere
- Adjustable transparency

### 🍎 Modern UI

- Dynamic Island inspired design
- Dark glass appearance
- Album artwork display
- Animated audio visualizer
- Smooth animations
- Rounded corners and shadows

### 🎮 Media Controls

- Previous track
- Play / Pause
- Next track
- Live song information
- Playback status detection

### ⚙️ Customization

- Adjustable font size
- Multiple lyric display modes
- Transparency control
- Window position memory
- Custom hotkeys
- Auto-start support

---

## 📸 Screenshots

### Full Overlay Mode

![Full Overlay](screenshots/full-overlay.png)

### Mini Mode

![Mini Mode](screenshots/mini-mode.png)

---

## 🚀 Installation

### Requirements

- Windows 10 or Windows 11
- Python 3.11+
- Spotify Desktop Application

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

## ⌨️ Keyboard Shortcuts

| Shortcut | Action |
|-----------|---------|
| Ctrl + Alt + L | Show / Hide Overlay |
| Ctrl + Alt + M | Change Lyrics Mode |
| Ctrl + Alt + T | Toggle Transparency |
| Ctrl + Alt + Up | Increase Font Size |
| Ctrl + Alt + Down | Decrease Font Size |

---

## 🛠️ Tech Stack

### Backend

- Python 3.11+

### GUI Framework

- PyQt6

### APIs & Services

- Windows GSMTC API
- LRCLIB API

### Packaging

- PyInstaller

---

## 📂 Project Structure

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
├── LICENSE
└── README.md
```

---

## 🔧 Configuration

User settings are stored in:

```text
spotify_lyrics_overlay/config.json
```

You can customize:

- Font size
- Transparency
- Display mode
- Window position
- Always-on-top
- Auto-start
- Hotkeys

---

## 📦 Build Executable

Build a standalone executable using PyInstaller:

```bash
pyinstaller --noconsole ^
--onefile ^
--name="SpotifyLyricsOverlay" ^
--icon="spotify_lyrics_overlay/assets/icon.ico" ^
spotify_lyrics_overlay/main.py
```

After building, the executable will be available in:

```text
dist/
```

---

## 🗺️ Roadmap

### Completed

- [x] Real-time synchronized lyrics
- [x] Floating desktop overlay
- [x] Dynamic Island mini mode
- [x] Album artwork display
- [x] Media controls
- [x] Offline lyrics cache
- [x] Transparency controls

### Planned

- [ ] Lyrics translation
- [ ] Custom themes
- [ ] More visualizer styles
- [ ] Multiple lyric providers
- [ ] Lyrics export
- [ ] Plugin support

---

## 🤝 Contributing

Contributions, suggestions, and bug reports are welcome.

If you find a bug or have an idea for improvement, feel free to open an issue or submit a pull request.

---

## 📄 License

This project is licensed under the MIT License.

See the [LICENSE](LICENSE) file for more information.

---

# 🇮🇩 Bahasa Indonesia

Spotify Lyrics Overlay adalah aplikasi desktop untuk Windows yang menampilkan lirik Spotify secara sinkron langsung di desktop dengan tampilan modern, ringan, dan dapat dikustomisasi.

## Fitur Utama

- Lirik sinkron secara realtime
- Overlay mengambang di desktop
- Mode mini ala Dynamic Island
- Cover album Spotify
- Kontrol media
- Visualizer animasi
- Always on Top
- Click-through mode
- Transparansi yang dapat diatur
- Auto-start Windows
- Hotkey global

## Menjalankan Aplikasi

```bash
pip install -r requirements.txt
python run.py
```

## Lisensi

Project ini menggunakan lisensi MIT.
