# 🎵 Spotify Lyrics Overlay

[![Windows](https://img.shields.io/badge/Platform-Windows%2010%20%7C%2011-0078D6?style=flat&logo=windows)](https://microsoft.com)
[![Python](https://img.shields.io/badge/Python-3.11%2B-blue?style=flat&logo=python)](https://python.org)
[![PyQt6](https://img.shields.io/badge/GUI-PyQt6-41CD52?style=flat&logo=qt)](https://riverbankcomputing.com)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Author](https://img.shields.io/badge/Author-Pratama-orange.svg)](#-license--author)

> 🌐 **Language / Bahasa:** [English](#-spotify-lyrics-overlay-english) | [Bahasa Indonesia](#-spotify-lyrics-overlay-bahasa-indonesia)

---

## 🇺🇸 Spotify Lyrics Overlay (English)

**Spotify Lyrics Overlay** is a modern, aesthetic, and animated desktop floating lyrics application for **Windows 10 & 11** built with **Python** and **PyQt6**. Designed with the sleek visual language of **macOS Sonoma & Apple Dynamic Island Now Playing Widget**, it features squircle vinyl album covers, an animated equalizer visualizer, native playback controls, and seamless real-time synchronized lyrics floating freely on your desktop with **zero harsh DWM gray borders or rectangular outlines**.

The user interface and all menus are presented in **clean English** for a universal, minimalist, and state-of-the-art desktop experience.

---

### 📸 Screenshots & Preview

<p align="center">
  <img src="spotify_lyrics_overlay/assets/screenshots/preview-full.png" alt="Spotify Lyrics Overlay - Full Widget Mode" width="720" onerror="this.src='https://placehold.co/720x150/121216/1ED760?text=Full+Lyrics+Overlay+Preview+(Place+screenshot+in+assets/screenshots/preview-full.png)';">
  <br>
  <em>Full Lyrics Overlay with Squircle Vinyl Album Cover, Animated Equalizer & Synced Lyrics</em>
</p>

| Full Lyrics Widget Mode | Dynamic Island Mini-Pill Mode |
| :---: | :---: |
| <img src="spotify_lyrics_overlay/assets/screenshots/preview-full.png" alt="Full Widget" width="380" onerror="this.src='https://placehold.co/380x100/121216/1ED760?text=Full+Widget+Mode';"> | <img src="spotify_lyrics_overlay/assets/screenshots/preview-mini.png" alt="Mini Pill" width="380" onerror="this.src='https://placehold.co/380x100/121216/FFD60A?text=Dynamic+Island+Pill';"> |
| *Vinyl cover, animated equalizer, 2-line lyrics, progress bar* | *Ultra-compact Dynamic Island capsule (`340x52px`)* |

---

### 🛠️ Built With & Technology Stack (Deep Dive)

Here is the complete breakdown of all technologies, libraries, and native Windows APIs powering this project:

| Technology / Library | Version / Scope | Role & Implementation Details |
| :--- | :--- | :--- |
| **Python** | `3.11+` | Core programming language offering modern asynchronous event loops and native C-interoperability. |
| **PyQt6** | `>=6.6.0` | **Modern Desktop GUI Engine**: Provides frameless transparent window management (`Qt.WindowType.FramelessWindowHint`), high-DPI scaling, smooth alpha compositing, `QPainter` & `QPainterPath` for anti-aliased squircle rounding, `QGraphicsDropShadowEffect` for crisp text legibility, and custom Qt stylesheets. |
| **Windows WinRT GSMTC (`winsdk`)** | `>=1.0.0b10` | **Native Spotify Bridge**: Directly integrates with Windows Global System Media Transport Controls (`GlobalSystemMediaTransportControlsSessionManager`). Retrieves currently playing song title, artist, album name, timeline position, duration, and album cover thumbnail streams natively—**without requiring a Spotify Developer Account, client ID/secret, or OAuth tokens**. |
| **LRCLIB API & `requests`** | `>=2.31.0` | **Real-time Synchronized Lyrics**: Connects to the community-driven LRCLIB API to fetch synchronized `.lrc` lyrics with millisecond accuracy. Features automatic Spotify track title cleaning (strips remaster, bonus track, radio edit tags) and persistent local offline JSON caching. |
| **Win32 API & DWM (`pywin32` / `ctypes`)** | `>=306` | **Seamless Borderless Window & Click-Through**: Invokes low-level Windows Desktop Window Manager (`DwmSetWindowAttribute`) with `DWMWA_COLOR_NONE` (`0xFFFFFFFE`) and `DWMWCP_DONOTROUND` to completely eliminate the stubborn Windows 11 default 1px gray border. Also manages `WS_EX_TRANSPARENT` for mouse click-through. |
| **Global Keyboard Hooks (`keyboard`)** | `>=0.13.5` | **Global System-Wide Hotkeys**: Listens for global shortcut triggers (`Ctrl+Alt+L`, `Ctrl+Alt+M`, `Ctrl+Alt+T`, font resizing) from any game or application in the background. |
| **Windows Registry (`winreg`)** | Built-in | **Windows Boot Auto-Start**: Manages user entries in `HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Run` to enable clean start-on-boot without third-party services. |
| **PyInstaller** | `>=6.0.0` | **Executable Compilation**: Packages the Python runtime, PyQt6 binaries, WinRT bindings, assets, and configurations into a single standalone `.exe` (`dist/SpotifyLyricsOverlay.exe`). |

---

### ✨ Key Features

* **macOS Sonoma & Dynamic Island Aesthetics**:
  * **English Interface**: All dialogs, menus, presets, tooltips, and status indicators are cleanly crafted in universal English.
  * **100% Seamless Borderless Window**: Utilizes low-level Win32 DWM APIs (`DWMWA_COLOR_NONE` & `DWMWCP_DONOTROUND`) combined with Qt stylesheets (`border: none;`) to eliminate the stubborn Windows 11 default 1px gray border and rectangular outline.
  * **macOS Traffic Light Buttons**:
    * 🔴 **Red**: Hide Overlay (*Restore anytime via `Ctrl+Alt+L` or System Tray*).
    * 🟡 **Yellow**: Minimize to **Dynamic Island Mini-Pill** mode.
    * 🟢 **Green**: Cycle lyric line modes (1 Line ⇋ 2 Lines ⇋ 3 Lines).
  * **Animated Audio Equalizer (`ılı.`)**: 4-bar modern animated visualizer that bounces dynamically to the beat of your music and gently rests when paused.
  * **Squircle Vinyl Album Art**: Rounded squircle (`14px` radius) vinyl disc styling with ambient soft drop shadows.
  * **Integrated Media Controls**: Quick Apple-style circular buttons for *Previous* (`⏮`), *Play/Pause* (`⏯`), and *Next* (`⏭`).
  * **Dual Flexible Modes**:
    * **Full Lyrics Widget Mode**: Displays vinyl cover, track info, visualizer equalizer, synchronized lyrics, and playback progress bar.
    * **Dynamic Island Mini-Pill Mode**: Ultra-compact pill (`340x52px`) with traffic lights, song title, visualizer, and playback buttons.
    * *Double-click anywhere on the widget* to switch instantly between modes!
* **Super Flexible Window Resizing & Dragging**:
  * **8-Direction Edge & Corner Resizing**: Freely grab and drag any window border (left, right, top, bottom) or any of the 4 corners. The mouse cursor automatically turns into directional resize arrows (`↔`, `↕`, `⤡`, `⤢`).
  * **Corner Resize Grip Handle (`⋱`)**: Visual 3-stripe diagonal grip at the bottom-right corner that illuminates in Spotify emerald green on hover and smoothly resizes the widget.
  * **Precision Dimension Sliders**: Adjust exact **Window Width (350–1100 px)** and **Window Height (75–250 px)** via sliders in **Settings > Appearance & Transparency**.
  * **Quick Size Reset**: Right-click the overlay and click **Reset Window Size (600 × 108 px)** to restore default dimensions at any time.
  * **Draggable Anywhere**: Click and hold anywhere on the card to move it freely across your monitor.
* **Native Spotify Integration**: Automatically detects currently playing tracks, playback status, position, and duration via **Windows Global System Media Transport Controls (GSMTC) API**.
* **Real-time Synchronized Lyrics**: Fetches synchronized LRC lyrics via **LRCLIB API** with active-line interpolation, automatic Spotify track title cleaning (strips remaster, bonus track, radio edit tags), and local offline caching.
* **Flexible Translucency & Glassmorphism**:
  * **Dynamic Opacity**: Configurable from 0% (Pure Floating Transparent) to 40%–65% (Cozy Dark Obsidian Glass).
  * **High-Contrast Text Shadows**: Multi-layered drop shadows ensure effortless readability over light, dark, or busy desktop wallpapers.
  * **Smart Auto-Hide**: Header controls neatly fade out when the mouse leaves and re-appear when hovered.
* **Unobtrusive System Tray & Clean UI**:
  * Clean system tray context menu without cluttered icons.
  * **Always on Top**: Keeps lyrics visible over full-screen browser tabs or apps.
  * **Click-Through Mode**: Pass mouse clicks directly through the overlay to underlying windows.
  * **Auto-Start on Boot**: Optional Windows Run Registry integration.

---

### ⌨️ Global Hotkeys & Smart Gestures

| Shortcut / Gesture | Action | Description |
| :--- | :--- | :--- |
| `Ctrl + Alt + L` | **Toggle Overlay** | Hide or show the floating lyrics overlay |
| `Ctrl + Alt + M` | **Cycle Line Mode** | Switch between 1 Line ⇋ 2 Lines ⇋ 3 Lines |
| `Ctrl + Alt + T` | **Cycle Transparency** | Cycle 0% (Pure Transparent) ⇋ 20% ⇋ 40% ⇋ 60% |
| `Ctrl + Alt + Up` | **Increase Font** | Increase active lyric font size by +2 pt |
| `Ctrl + Alt + Down` | **Decrease Font** | Decrease active lyric font size by -2 pt |
| **Left Click + Drag** | **Move Window** | Drag the widget anywhere across the desktop |
| **Edge / Corner Drag** | **Resize Window** | Drag borders or corners to adjust width and height |
| **Corner Grip Drag (`⋱`)** | **Resize Window** | Drag the bottom-right visual grip handle |
| **Double Click** | **Toggle Mini-Pill** | Switch between Full Widget and Dynamic Island Pill |
| **Right Click** | **Context Menu** | Open quick menu for media controls, reset size, & settings |

---

### 📁 Project Structure

```text
Spotify/
├── LICENSE                      # MIT Open Source License (Author: Pratama)
├── README.md                    # Bilingual documentation & setup guide
├── run.py                       # Root launcher script
├── build.bat                    # Automated PyInstaller build script
├── SpotifyLyricsOverlay.spec    # PyInstaller packaging configuration
├── dist/
│   └── SpotifyLyricsOverlay.exe # Standalone zero-dependency executable
├── spotify_lyrics_overlay/
│   ├── main.py                  # Entry point, Global Hotkeys, System Tray
│   ├── overlay.py               # PyQt6 floating widget with corner/edge resize
│   ├── spotify_controller.py    # Windows GSMTC Media Session API integration
│   ├── lyrics_provider.py       # LRCLIB API lyrics fetcher, LRC parser & cache
│   ├── settings.py              # Settings GUI dialog with size sliders & hotkeys
│   ├── config.json              # Persistent user configuration
│   ├── requirements.txt         # Python dependencies
│   └── assets/
│       ├── icon.png             # High-resolution application icon
│       ├── icon.ico             # Windows taskbar/executable icon
│       ├── cache/               # Offline JSON lyrics cache
│       └── screenshots/         # Folder for README screenshots & previews
```

---

### 🚀 Installation & Running from Source

#### 1. Prerequisites
* Windows 10 or Windows 11 (64-bit)
* Python 3.11 or newer
* Spotify Desktop App installed and running

#### 2. Install Dependencies
Open Terminal / PowerShell in the project directory:
```powershell
pip install -r spotify_lyrics_overlay/requirements.txt
```

#### 3. Run the Application
Run via the root launcher:
```powershell
python run.py
```
Or directly from the module:
```powershell
python spotify_lyrics_overlay/main.py
```

---

### 🛠️ Building Standalone `.exe` Executable

You can package the entire application into a single standalone `.exe` that runs without requiring Python to be installed on other PCs.

#### Option 1: Automated Script (`build.bat`)
Simply double-click `build.bat` in the project root.

#### Option 2: Manual PyInstaller Command
Run the following in PowerShell:
```powershell
pyinstaller --noconsole `
    --onefile `
    --name="SpotifyLyricsOverlay" `
    --icon="spotify_lyrics_overlay\assets\icon.ico" `
    --add-data="spotify_lyrics_overlay\assets;assets" `
    --add-data="spotify_lyrics_overlay\config.json;." `
    spotify_lyrics_overlay\main.py
```

The compiled standalone executable will be located in:
```text
dist\SpotifyLyricsOverlay.exe
```

---

### ⚙️ Configuration (`config.json`)

Settings are automatically saved to `config.json` and can be adjusted through the GUI Settings dialog (right-click overlay > **Full Settings...** or click the gear icon `⚙`):

```json
{
  "font_family": "Segoe UI",
  "font_size": 20,
  "active_color": "#1ED760",
  "inactive_color": "rgba(255, 255, 255, 0.45)",
  "background_opacity": 0.20,
  "always_on_top": true,
  "click_through": false,
  "auto_hide_header": true,
  "show_progress_bar": true,
  "show_album_cover": true,
  "window_x": 200,
  "window_y": 780,
  "window_width": 600,
  "window_height": 108,
  "display_lines": 2,
  "text_alignment": "center",
  "auto_start": false,
  "hide_when_paused": false,
  "hotkeys": {
    "toggle_overlay": "ctrl+alt+l",
    "font_increase": "ctrl+alt+up",
    "font_decrease": "ctrl+alt+down",
    "toggle_mode": "ctrl+alt+m",
    "toggle_transparency": "ctrl+alt+t"
  }
}
```

#### Settings Description
| Key | Type | Description |
| :--- | :--- | :--- |
| `font_family` | `string` | Font family for lyric lines (`Segoe UI`, `Montserrat`, `Inter`, `Arial`, etc.) |
| `font_size` | `int` | Font size for the active lyric line in pt (14–38) |
| `active_color` | `hex string` | Highlight color for current active singing lyric line |
| `inactive_color`| `css string` | Color for preceding and upcoming inactive lyric lines |
| `background_opacity`| `float` | Window background opacity from `0.0` (Pure Transparent) to `1.0` (Solid) |
| `always_on_top` | `bool` | Keep lyrics floating over games and all other apps |
| `click_through` | `bool` | Allow mouse clicks to pass through to underlying windows |
| `auto_hide_header`| `bool` | Hide traffic lights and control buttons when mouse leaves |
| `show_progress_bar`| `bool` | Display the thin Apple-style playback progress bar |
| `show_album_cover`| `bool` | Display the rounded squircle vinyl album art |
| `window_width` | `int` | Window width in pixels (350–1100 px) |
| `window_height` | `int` | Window height in pixels (75–250 px) |
| `display_lines` | `int` | Number of lyric lines: `1` (Compact), `2` (Recommended), `3`, or `5` |
| `text_alignment`| `string` | Text alignment: `"center"` or `"left"` |
| `auto_start` | `bool` | Launch application automatically on Windows boot via Registry |
| `hide_when_paused`| `bool` | Automatically hide the overlay when Spotify playback is paused |

---

### 💡 Pro Tips & Tricks

* **Instant Pure Floating (100% Transparent)**: Click the droplet icon `💧` or press `Ctrl + Alt + T` to switch to pure borderless text floating freely over your wallpaper.
* **Auto-Hide Header**: When your mouse is not hovering over the widget, all controls fade away, leaving only the glowing lyrics.
* **Dynamic Island Pill**: Double-click anywhere on the card or click the yellow traffic light button (`🟡`) to minimize into a compact pill widget (`340x52px`).
* **Mouse Pass-Through**: When **Mouse Click-Through** is enabled, clicks pass through the overlay to desktop icons or browser tabs underneath. To re-enable interactivity, right-click the system tray icon near the Windows clock and uncheck **Mouse Click-Through**.

---

### ❓ Troubleshooting & FAQ

* **Lyrics say "Waiting for Spotify..."**:
  * Make sure Spotify Desktop is open and a track is actively playing.
  * Ensure Windows Global System Media Transport Controls (GSMTC) is enabled in Spotify settings (*Settings > Display Options > Show desktop overlay when using media keys*).
* **Lyrics show "Lyrics Not Available"**:
  * Some instrumental, unreleased, or obscure tracks may not have synced lyrics registered on LRCLIB yet.
* **Overlay disappeared**:
  * Press `Ctrl + Alt + L` to toggle visibility back on, or click the tray icon near the Windows taskbar clock.

---

### 📄 License & Author

Distributed under the **MIT License**. See [LICENSE](LICENSE) for more details.

**Author / Developer**: **Pratama**

---
---

## 🇮🇩 Spotify Lyrics Overlay (Bahasa Indonesia)

**Spotify Lyrics Overlay** adalah aplikasi desktop modern, estetik, dan animatif untuk **Windows 10 & 11** berbasis **Python** dan **PyQt6**. Mengusung tampilan bergaya **macOS Sonoma & Apple Dynamic Island Now Playing Widget**, aplikasi ini menampilkan cover album squircle vinyl, visualizer equalizer animatif, kontrol pemutar lagu, serta lirik sinkron *realtime* secara mengambang di desktop **tanpa border/outline kotak abu-abu** sama sekali.

Seluruh antarmuka pengguna (UI), menu konteks, dialog pengaturan, dan notifikasi disajikan dalam **Bahasa Inggris** untuk memberikan tampilan yang bersih, minimalis, dan berkelas internasional.

---

### 📸 Tangkapan Layar & Pratinjau (Screenshots & Preview)

<p align="center">
  <img src="spotify_lyrics_overlay/assets/screenshots/preview-full.png" alt="Spotify Lyrics Overlay - Full Widget Mode" width="720" onerror="this.src='https://placehold.co/720x150/121216/1ED760?text=Full+Lyrics+Overlay+Preview+(Simpan+screenshot+di+assets/screenshots/preview-full.png)';">
  <br>
  <em>Tampilan Full Lyrics Overlay dengan Cover Vinyl Squircle, Equalizer Bergerak & Lirik Realtime</em>
</p>

| Mode Full Lyrics Widget | Mode Dynamic Island Mini-Pill |
| :---: | :---: |
| <img src="spotify_lyrics_overlay/assets/screenshots/preview-full.png" alt="Full Widget" width="380" onerror="this.src='https://placehold.co/380x100/121216/1ED760?text=Full+Widget+Mode';"> | <img src="spotify_lyrics_overlay/assets/screenshots/preview-mini.png" alt="Mini Pill" width="380" onerror="this.src='https://placehold.co/380x100/121216/FFD60A?text=Dynamic+Island+Pill';"> |
| *Cover vinyl, equalizer animatif, lirik 2-baris, progress bar* | *Kapsul ringkas ala Apple Dynamic Island (`340x52px`)* |

---

### 🛠️ Teknologi & Komponen yang Digunakan (Rincian Lengkap Stack)

Aplikasi ini dibangun menggunakan kombinasi pustaka Python modern dan integrasi API native Windows tingkat rendah:

| Teknologi / Library | Versi / Lingkup | Peran & Rincian Implementasi |
| :--- | :--- | :--- |
| **Python** | `3.11+` | Bahasa pemrograman utama, efisien, dengan dukungan penanganan event asinkron dan interoperabilitas C/Win32. |
| **PyQt6** | `>=6.6.0` | **Engine Antarmuka Desktop**: Mengelola jendela transparan tanpa bingkai (`Qt.WindowType.FramelessWindowHint`), penskalaan monitor high-DPI, rendering `QPainter` & `QPainterPath` untuk sudut melengkung squircle anti-aliasing yang sangat halus, efek bayangan teks `QGraphicsDropShadowEffect`, serta styling modern Qt CSS. |
| **Windows WinRT GSMTC (`winsdk`)** | `>=1.0.0b10` | **Koneksi Native Spotify**: Terhubung langsung ke API Windows Global System Media Transport Controls (`GlobalSystemMediaTransportControlsSessionManager`). Menangkap judul lagu, artis, nama album, status play/pause, durasi, timeline detik berjalan, dan stream thumbnail cover art Spotify secara native **tanpa perlu akun Spotify Developer, Client ID/Secret, atau token web OAuth**. |
| **LRCLIB API & `requests`** | `>=2.31.0` | **Sinkronisasi Lirik Realtime**: Mengambil lirik berformat `.lrc` dengan ketepatan milidetik dari LRCLIB (database lirik publik gratis berbasis komunitas). Dilengkapi pembersihan regex otomatis untuk judul Spotify (menghapus label Remaster, Bonus Track, Radio Edit) dan sistem penyimpanan cache lirik JSON offline lokal. |
| **Win32 API & DWM (`pywin32` / `ctypes`)** | `>=306` | **Jendela Murni Tanpa Border & Tembus Klik**: Memanggil API Desktop Window Manager (`DwmSetWindowAttribute`) dengan flag khusus `DWMWA_COLOR_NONE` (`0xFFFFFFFE`) dan `DWMWCP_DONOTROUND` untuk melenyapkan garis outline abu-abu default Windows 11 secara tuntas. Mengontrol `WS_EX_TRANSPARENT` untuk mode klik tembus (*mouse click-through*). |
| **Shortcut Keyboard Global (`keyboard`)** | `>=0.13.5` | **Hotkeys Global Tingkat Sistem**: Menangkap pintasan keyboard global (`Ctrl+Alt+L`, `Ctrl+Alt+M`, `Ctrl+Alt+T`, ubah ukuran font) dari aplikasi atau game apa pun yang sedang aktif di latar depan. |
| **Windows Registry (`winreg`)** | Bawaan Python | **Auto-Start Saat Boot**: Menulis entri registri di `HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Run` untuk menjalankan aplikasi secara otomatis saat Windows dinyalakan tanpa butuh service pihak ketiga. |
| **PyInstaller** | `>=6.0.0` | **Compiler File Executable**: Mengemas runtime Python, dependensi PyQt6, binding WinRT, file aset gambar, dan konfigurasi menjadi satu file executable mandiri (`dist/SpotifyLyricsOverlay.exe`). |

---

### ✨ Fitur Utama

* **Desain macOS Sonoma & Dynamic Island**:
  * **Tampilan Bersih Bahasa Inggris**: Semua dialog, tombol preset, menu tray, dan tooltip disajikan dalam Bahasa Inggris yang ringkas dan rapi.
  * **Bebas Border Abu-Abu Jendela (100% Seamless)**: Menggunakan Win32 DWM API khusus (`DWMWA_COLOR_NONE` & `DWMWCP_DONOTROUND`) dan stylesheet Qt `border: none;` sehingga outline abu-abu Windows 11 dihilangkan secara tuntas.
  * **macOS Traffic Light Buttons**:
    * 🔴 **Merah**: Sembunyikan Overlay (*Kembalikan via `Ctrl+Alt+L` atau System Tray*).
    * 🟡 **Kuning**: Minimalkan ke mode **Dynamic Island Mini-Pill** (kapsul ringkas estetik).
    * 🟢 **Hijau**: Siklus mode baris lirik (1 Baris ⇋ 2 Baris ⇋ 3 Baris).
  * **Audio Visualizer Equalizer Animatif (`ılı.`)**: 4 bar equalizer modern yang bergoyang secara dinamis mengikuti irama lagu saat diputar, dan beristirahat halus saat musik dijeda.
  * **Cover Album Squircle Vinyl Artistik**: Thumbnail album Spotify dengan sudut membulat squircle (`14px`) dan bayangan lembut di sebelah lirik.
  * **Media Controls Apple Style**: Tombol melingkar *Previous* (`⏮`), *Play/Pause* (`⏯`), dan *Next* (`⏭`) langsung di samping judul lagu.
  * **Mode Fleksibel & Animatif**:
    * **Full Lyrics Widget Mode**: Menampilkan cover vinyl, detail lagu, equalizer, lirik sinkron (1/2/3 baris), dan progress bar.
    * **Dynamic Island Mini-Pill Mode**: Kapsul mini berukuran ringkas (`340x52px`) dengan traffic lights, judul lagu, visualizer equalizer, dan kontrol play/pause.
    * *Klik ganda (double-click)* di mana saja pada overlay untuk berganti mode secara instan!
* **Pengaturan Ukuran & Geser Super Fleksibel**:
  * **8-Arah Resize Tepi & Sudut**: Anda dapat langsung menarik tepi jendela mana saja (kiri, kanan, atas, bawah, serta keempat sudut) untuk memperbesar atau memperkecil jendela. Kursor mouse otomatis berubah menjadi panah arah (`↔`, `↕`, `⤡`, `⤢`).
  * **Corner Resize Grip Handle (`⋱`)**: Grip visual 3 garis diagonal di pojok kanan bawah yang menyala hijau Spotify saat kursor diarahkan ke sana.
  * **Slider Ukuran Presisi**: Atur **Window Width (350–1100 px)** dan **Window Height (75–250 px)** secara akurat via slider pada tab **Settings > Appearance & Transparency**.
  * **Reset Ukuran Cepat**: Klik kanan overlay dan pilih **Reset Window Size (600 × 108 px)** untuk mengembalikan ukuran default secara instan.
  * **Bebas Digeser (Draggable Anywhere)**: Cukup klik kiri dan tahan di bagian mana pun pada kartu widget untuk memindahkannya ke posisi layar mana pun.
* **Otomatis Terhubung ke Spotify Desktop**: Mendeteksi lagu secara realtime via **Windows Global System Media Transport Controls (GSMTC) API**.
* **Sinkronisasi Lirik Realtime (LRC)**: Mengambil lirik bersinkronisasi waktu dari **LRCLIB API** dengan highlight baris aktif, pembersihan otomatis judul lagu Spotify (menghapus embel-embel remaster/bonus track), dan offline caching lokal.
* **Transparansi Fleksibel (Pure Floating & Obsidian Glass)**:
  * **Opasitas Dinamis**: Dapat diatur dari 0% (Pure Transparent) hingga 40%–65% (Cozy Dark Obsidian Glass).
  * **Drop Shadow Tajam**: Lirik dilengkapi bayangan kontras tinggi sehingga sangat jelas terbaca di atas wallpaper apa pun.
  * **Auto-Hide Cerdas**: Tombol-tombol utilitas otomatis tersimpan rapi dan hanya muncul saat kursor mouse diarahkan ke widget.
* **Menu System Tray Bersih & Rapi**:
  * Tampilan menu tray teks bersih tanpa ikon individual fitur.
  * **Always on Top**: Mengambang di atas semua jendela aplikasi atau game.
  * **Click-Through Mode**: Kursor mouse dapat menembus overlay (*mouse pass-through* via Win32 API).
  * **Auto-Start**: Dukungan otomatis berjalan saat Windows booting via Windows Registry.

---

### ⌨️ Pintasan Keyboard Global & Gestur Mouse

| Pintasan / Gestur | Aksi | Deskripsi |
| :--- | :--- | :--- |
| `Ctrl + Alt + L` | **Toggle Overlay** | Menampilkan atau menyembunyikan overlay lirik |
| `Ctrl + Alt + M` | **Cycle Line Mode** | Siklus 1 Baris ⇋ 2 Baris ⇋ 3 Baris |
| `Ctrl + Alt + T` | **Cycle Transparency** | Siklus 0% (Transparan Penuh) ⇋ 20% ⇋ 40% ⇋ 60% |
| `Ctrl + Alt + Up` | **Increase Font** | Menambah ukuran font lirik aktif sebesar +2 pt |
| `Ctrl + Alt + Down` | **Decrease Font** | Mengurangi ukuran font lirik aktif sebesar -2 pt |
| **Klik Kiri + Geser** | **Move Window (Drag)** | Geser kartu widget ke posisi mana pun di desktop |
| **Tarik Tepi / Sudut** | **Resize Window** | Tarik border jendela untuk memperbesar/memperkecil |
| **Tarik Grip (`⋱`)** | **Resize Window** | Tarik grip visual di pojok kanan bawah |
| **Klik Ganda** | **Dynamic Island Pill** | Beralih antara mode Full Widget dan Mini-Pill |
| **Klik Kanan** | **Quick Context Menu** | Buka menu kontrol media, reset ukuran, & pengaturan |

---

### 📁 Struktur Project

```text
Spotify/
├── LICENSE                      # Lisensi Open Source MIT (Hak Cipta: Pratama)
├── README.md                    # Dokumentasi lengkap dwibahasa (EN & ID)
├── run.py                       # Root launcher praktis
├── build.bat                    # Script otomatis build PyInstaller
├── SpotifyLyricsOverlay.spec    # Konfigurasi packaging PyInstaller
├── dist/
│   └── SpotifyLyricsOverlay.exe # Standalone Windows Executable
├── spotify_lyrics_overlay/
│   ├── main.py                  # Entry point aplikasi, Hotkeys, Tray Icon
│   ├── overlay.py               # Jendela desktop floating overlay PyQt6
│   ├── spotify_controller.py    # Integrasi Windows SMTC Media Session API
│   ├── lyrics_provider.py       # Pengambil lirik LRCLIB, parser LRC, & cache
│   ├── settings.py              # Dialog GUI pengaturan & ConfigManager
│   ├── config.json              # File konfigurasi pengguna
│   ├── requirements.txt         # Daftar dependensi Python
│   └── assets/
│       ├── icon.png             # Ikon aplikasi PNG resolusi tinggi
│       ├── icon.ico             # Ikon Windows .ico
│       ├── cache/               # Cache lirik JSON offline
│       └── screenshots/         # Folder tangkapan layar untuk README
```

---

### 🚀 Cara Instalasi & Menjalankan dari Source Code

#### 1. Prasyarat
* Windows 10 / Windows 11 (64-bit)
* Python 3.11 atau lebih baru
* Spotify Desktop terpasang dan sedang berjalan

#### 2. Instalasi Dependensi
Buka Terminal / PowerShell di direktori project:
```powershell
pip install -r spotify_lyrics_overlay/requirements.txt
```

#### 3. Menjalankan Aplikasi
Cukup jalankan root launcher:
```powershell
python run.py
```
atau langsung dari folder modul:
```powershell
python spotify_lyrics_overlay/main.py
```

---

### 🛠️ Cara Build Menjadi File `.exe` Standalone

Anda dapat mengompilasi seluruh aplikasi menjadi satu file `.exe` tunggal yang dapat dijalankan tanpa perlu menginstal Python di komputer lain.

#### Cara 1: Menggunakan Script `build.bat` (Otomatis)
Cukup klik ganda pada file `build.bat`.

#### Cara 2: Menjalankan Perintah PyInstaller Secara Manual
Jalankan perintah berikut di PowerShell atau Command Prompt:
```powershell
pyinstaller --noconsole `
    --onefile `
    --name="SpotifyLyricsOverlay" `
    --icon="spotify_lyrics_overlay\assets\icon.ico" `
    --add-data="spotify_lyrics_overlay\assets;assets" `
    --add-data="spotify_lyrics_overlay\config.json;." `
    spotify_lyrics_overlay\main.py
```

Setelah selesai, file executable mandiri akan tersedia di:
```text
dist\SpotifyLyricsOverlay.exe
```

---

### ⚙️ Konfigurasi (`config.json`) & Dialog Pengaturan

Pengaturan disimpan secara otomatis di file `config.json` dan dapat diatur secara visual melalui dialog GUI **Settings** (klik kanan overlay > pilih **Full Settings...** atau klik ikon gear `⚙`):

* **Appearance & Transparency**:
  * **Quick Appearance Presets**: Tombol cepat untuk mode *Pure Floating (0%)*, *Frosted Glass (20%)*, *Compact Bar (1 Line)*, dan *Dark Modern (60%)*.
  * **Window Dimensions**: Slider presisi untuk mengatur lebar (*Width*) dan tinggi (*Height*) serta tombol reset ke default (600×108 px).
  * **Background Opacity**: Pengatur transparansi dari 0% hingga 100%.
  * **Lyric Lines Display**: Pilihan tampilan 1, 2, 3, atau 5 baris lirik.
  * **Active Font Size & Font Family**: Pilihan font (Segoe UI, Inter, Roboto, dll) dan ukuran font aktif.
  * **Auto-Hide Controls**: Opsi otomatis menyembunyikan tombol kontrol saat kursor mouse tidak berada di atas widget.
* **Behavior**:
  * **Always on Top**: Mengambang di atas semua aplikasi atau game.
  * **Mouse Click-Through**: Kursor mouse menembus overlay.
  * **Start with Windows (Auto-Start)**: Otomatis berjalan saat komputer menyala via Registry.
  * **Hide Automatically When Paused**: Otomatis bersembunyi saat musik dijeda.
* **Hotkeys & Gestures**:
  * Daftar panduan visual lengkap seluruh shortcut keyboard dan gestur mouse.

---

### 💡 Tips Penggunaan

* **Ubah Ukuran Jendela Super Fleksibel**: Anda dapat menarik tepi jendela mana pun (kiri, kanan, atas, bawah, serta 4 sudut) atau menarik grip visual di pojok kanan bawah (**⋱**). Anda juga bisa mengatur ukuran lebar & tinggi secara presisi lewat slider di tab **Appearance & Transparency**.
* **Reset Ukuran Cepat**: Jika ukuran jendela berubah secara tidak sengaja, klik kanan overlay lalu pilih **Reset Window Size (600 × 108 px)** atau klik tombol default di dialog Settings.
* **Pure Floating (100% Transparan)**: Tekan tombol `💧` di header atau gunakan pintasan `Ctrl + Alt + T` untuk langsung mengaktifkan mode transparan penuh tanpa latar belakang kotak hitam.
* **Auto-Hide Controls**: Saat mouse dijauhkan dari overlay, header dan tombol otomatis lenyap sehingga hanya lirik lagu yang mengambang murni di desktop.
* **Ganti Mode Baris Cepat**: Tekan tombol `+` di traffic lights atau pintasan `Ctrl + Alt + M` untuk beralih antara 1 Baris (Compact), 2 Baris (Rekomendasi), atau 3 Baris.
* **Click-Through Mode**: Kursor mouse dapat menembus overlay. Jika ingin menonaktifkannya kembali, cukup klik kanan ikon di **System Tray** dekat jam Windows lalu hilangkan centang pada opsi **Mouse Click-Through**.

---

### ❓ Pemecahan Masalah (Troubleshooting) & FAQ

* **Muncul pesan "Waiting for Spotify..."**:
  * Pastikan aplikasi Spotify Desktop sudah terbuka dan lagu sedang diputar.
  * Pastikan integrasi media Windows aktif di Spotify (*Settings > Display Options > Show desktop overlay when using media keys*).
* **Muncul pesan "Lyrics Not Available"**:
  * Beberapa lagu instrumen atau lagu baru mungkin belum tersedia lirik sinkronnya di database LRCLIB.
* **Overlay tidak sengaja tersembunyi**:
  * Tekan tombol pintas `Ctrl + Alt + L` pada keyboard atau klik ikon aplikasi di System Tray dekat jam Windows.

---

### 📄 Lisensi & Pembuat (License & Author)

Didistribusikan di bawah lisensi terbuka **MIT License**. Lihat file [LICENSE](LICENSE) untuk informasi hak cipta dan ketentuan penggunaan secara lengkap.

**Author / Pengembang**: **Pratama**
