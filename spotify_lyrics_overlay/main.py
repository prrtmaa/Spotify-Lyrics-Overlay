"""
main.py - Titik Masuk Utama Spotify Lyrics Overlay.
Menginisialisasi QApplication, System Tray Icon, Global Hotkeys (Ctrl+Alt+L, Ctrl+Alt+Up/Down),
jendela Overlay, serta thread pemantau Spotify Controller.
"""

import os
import sys

import functools

# Pastikan output konsol Windows aman dari UnicodeEncodeError (cp1252/ANSI) & langsung di-flush
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

print = functools.partial(print, flush=True)

import keyboard
from PyQt6.QtWidgets import (
    QApplication, QSystemTrayIcon, QMenu
)
from PyQt6.QtCore import Qt, QObject, pyqtSignal
from PyQt6.QtGui import QIcon, QAction

# Import modul lokal
from settings import ConfigManager, SettingsDialog, get_asset_path
from lyrics_provider import LyricsProvider
from spotify_controller import SpotifyController
from overlay import OverlayWindow

ICON_PNG = get_asset_path("icon.png")
ICON_ICO = get_asset_path("icon.ico")


class HotkeyBridge(QObject):
    """Bridge thread-safe untuk menghubungkan hotkey global ke slot PyQt."""
    toggle_overlay_signal = pyqtSignal()
    font_increase_signal = pyqtSignal()
    font_decrease_signal = pyqtSignal()
    toggle_mode_signal = pyqtSignal()
    toggle_transparency_signal = pyqtSignal()


class SpotifyLyricsApp:
    """Manajer aplikasi utama yang mengoordinasikan seluruh subsistem."""

    def __init__(self, qapp: QApplication):
        self.qapp = qapp
        self.qapp.setQuitOnLastWindowClosed(False)

        # Inisialisasi icon aplikasi
        self.app_icon = QIcon(ICON_ICO if os.path.exists(ICON_ICO) else ICON_PNG)
        self.qapp.setWindowIcon(self.app_icon)

        # 1. Konfigurasi
        self.config_manager = ConfigManager()

        # 2. Penyedia Lirik
        self.lyrics_provider = LyricsProvider()

        # 3. Jendela Overlay
        self.overlay = OverlayWindow(self.config_manager, self.lyrics_provider)
        self.overlay.settings_requested.connect(self.open_settings)
        self.overlay.clickthrough_changed.connect(self.on_clickthrough_toggled_from_overlay)

        # 4. Monitor Pemutaran Spotify (Background QThread)
        self.spotify_controller = SpotifyController(poll_interval_ms=350)
        self.spotify_controller.track_changed.connect(self.on_track_changed)
        self.spotify_controller.playback_updated.connect(self.overlay.handle_playback_updated)
        self.spotify_controller.status_changed.connect(self.on_status_changed)

        # Sambungkan kontrol media overlay (Lock Screen Widget) ke Spotify Controller
        self.overlay.play_pause_requested.connect(self.spotify_controller.toggle_play_pause)
        self.overlay.next_requested.connect(self.spotify_controller.skip_next)
        self.overlay.prev_requested.connect(self.spotify_controller.skip_previous)

        # 5. System Tray Icon
        self.init_tray_icon()

        # 6. Global Hotkeys
        self.init_global_hotkeys()

        # Dialog pengaturan (lazy initialized)
        self.settings_dialog = None

    def start(self):
        """Menjalankan aplikasi dan memulai pemantauan Spotify."""
        self.overlay.show()
        self.spotify_controller.start()

        # Print informative console startup logs
        screen = self.qapp.primaryScreen().geometry()
        geo = self.overlay.geometry()
        cfg = self.config_manager
        print("\n" + "=" * 62)
        print("  [SPOTIFY LYRICS OVERLAY] - Windows 11 Desktop")
        print("=" * 62)
        print(f"[System] Screen Detected  : {screen.width()}x{screen.height()} (DPI: {self.qapp.primaryScreen().devicePixelRatio()}x)")
        print(f"[Overlay] Window Position  : x={geo.x()}, y={geo.y()} (Width: {geo.width()}px, Height: {geo.height()}px)")
        print(f"[Overlay] Configuration    : {cfg.get('display_lines')} Lines, Opacity: {int(cfg.get('background_opacity', 0.35)*100)}%, Font: {cfg.get('font_size')}pt")
        print(f"[Overlay] Always on Top    : {'Enabled' if cfg.get('always_on_top') else 'Disabled'}")
        print("[Hotkeys] Active Global Shortcuts:")
        print("  * Ctrl + Alt + L : Toggle Overlay Visibility")
        print("  * Ctrl + Alt + M : Cycle Line Mode (1L <-> 2L <-> 3L)")
        print("  * Ctrl + Alt + T : Cycle Transparency (0% <-> 20% <-> 60%)")
        print("  * Ctrl + Alt + Up/Down : Increase / Decrease Font Size")
        print("[System Tray] Icon active in Windows taskbar tray.")
        print("[Spotify] Connecting to Windows SMTC Media Session API...")
        print("=" * 62 + "\n")

        # Show welcome system tray balloon
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray_icon.showMessage(
                "Spotify Lyrics Overlay",
                "Application is running in the background.\nPress Ctrl+Alt+L to show or hide the overlay.",
                QSystemTrayIcon.MessageIcon.Information,
                3500
            )

    def init_tray_icon(self):
        """Membuat ikon System Tray di taskbar Windows (dekat jam)."""
        self.tray_icon = QSystemTrayIcon(self.app_icon, self.qapp)
        self.tray_icon.setToolTip("Spotify Lyrics Overlay")

        self.tray_menu = QMenu()
        self.tray_menu.setStyleSheet("""
            QMenu {
                background-color: #1A1D27;
                color: #FFFFFF;
                border: 1px solid #282C3C;
                border-radius: 8px;
                padding: 6px;
                font-family: 'Segoe UI', sans-serif;
                font-size: 13px;
            }
            QMenu::item {
                padding: 6px 18px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #1DB954;
                color: #000000;
            }
            QMenu::separator {
                height: 1px;
                background-color: #282C3C;
                margin: 4px 8px;
            }
        """)

        # Item info lagu aktif di tray
        self.act_tray_track = QAction("Spotify: Waiting...", self.tray_menu)
        self.act_tray_track.setEnabled(False)
        self.tray_menu.addAction(self.act_tray_track)

        self.tray_menu.addSeparator()

        # Toggle Show / Hide Overlay
        self.act_toggle_show = QAction("Hide Overlay (Ctrl+Alt+L)", self.tray_menu)
        self.act_toggle_show.triggered.connect(self.toggle_overlay_visibility)
        self.tray_menu.addAction(self.act_toggle_show)

        # Toggle Mode Baris (1L / 2L / 3L)
        self.act_tray_mode = QAction("Cycle Line Mode (Ctrl+Alt+M)", self.tray_menu)
        self.act_tray_mode.triggered.connect(self.overlay.cycle_display_lines)
        self.tray_menu.addAction(self.act_tray_mode)

        # Toggle Opasitas (Transparan Penuh ⇋ Kaca)
        self.act_tray_trans = QAction("Cycle Transparency (Ctrl+Alt+T)", self.tray_menu)
        self.act_tray_trans.triggered.connect(self.overlay.cycle_transparency)
        self.tray_menu.addAction(self.act_tray_trans)

        self.tray_menu.addSeparator()

        # Toggle Click-Through
        self.act_tray_clickthrough = QAction("Mouse Click-Through", self.tray_menu)
        self.act_tray_clickthrough.setCheckable(True)
        self.act_tray_clickthrough.setChecked(self.config_manager.get("click_through", False))
        self.act_tray_clickthrough.triggered.connect(self.toggle_click_through)
        self.tray_menu.addAction(self.act_tray_clickthrough)

        # Toggle Always on Top
        self.act_tray_top = QAction("Always on Top", self.tray_menu)
        self.act_tray_top.setCheckable(True)
        self.act_tray_top.setChecked(self.config_manager.get("always_on_top", True))
        self.act_tray_top.triggered.connect(self.toggle_always_on_top)
        self.tray_menu.addAction(self.act_tray_top)

        self.tray_menu.addSeparator()

        # Settings
        act_settings = QAction("Settings...", self.tray_menu)
        act_settings.triggered.connect(self.open_settings)
        self.tray_menu.addAction(act_settings)

        self.tray_menu.addSeparator()

        # Exit
        act_quit = QAction("Exit", self.tray_menu)
        act_quit.triggered.connect(self.quit_app)
        self.tray_menu.addAction(act_quit)

        self.tray_icon.setContextMenu(self.tray_menu)
        self.tray_icon.activated.connect(self.on_tray_activated)
        self.tray_icon.show()

    def on_tray_activated(self, reason):
        """Klik kiri pada ikon tray akan men-toggle visibilitas overlay."""
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.toggle_overlay_visibility()

    def init_global_hotkeys(self):
        """Mendaftarkan pintasan keyboard global menggunakan library keyboard."""
        self.hotkey_bridge = HotkeyBridge()
        self.hotkey_bridge.toggle_overlay_signal.connect(self.toggle_overlay_visibility)
        self.hotkey_bridge.font_increase_signal.connect(self.overlay.increase_font)
        self.hotkey_bridge.font_decrease_signal.connect(self.overlay.decrease_font)
        self.hotkey_bridge.toggle_mode_signal.connect(self.overlay.cycle_display_lines)
        self.hotkey_bridge.toggle_transparency_signal.connect(self.overlay.cycle_transparency)

        hotkeys = self.config_manager.get("hotkeys", {})
        hk_toggle = hotkeys.get("toggle_overlay", "ctrl+alt+l")
        hk_up = hotkeys.get("font_increase", "ctrl+alt+up")
        hk_down = hotkeys.get("font_decrease", "ctrl+alt+down")
        hk_mode = hotkeys.get("toggle_mode", "ctrl+alt+m")
        hk_trans = hotkeys.get("toggle_transparency", "ctrl+alt+t")

        try:
            keyboard.add_hotkey(hk_toggle, lambda: self.hotkey_bridge.toggle_overlay_signal.emit())
            keyboard.add_hotkey(hk_up, lambda: self.hotkey_bridge.font_increase_signal.emit())
            keyboard.add_hotkey(hk_down, lambda: self.hotkey_bridge.font_decrease_signal.emit())
            keyboard.add_hotkey(hk_mode, lambda: self.hotkey_bridge.toggle_mode_signal.emit())
            keyboard.add_hotkey(hk_trans, lambda: self.hotkey_bridge.toggle_transparency_signal.emit())
        except Exception as e:
            print(f"[Main] Peringatan: Gagal mendaftarkan hotkey global: {e}")

    def toggle_overlay_visibility(self):
        """Toggle showing or hiding the overlay."""
        if self.overlay.isVisible():
            self.overlay.hide()
            self.act_toggle_show.setText("Show Overlay (Ctrl+Alt+L)")
        else:
            self.overlay.show()
            self.overlay.activateWindow()
            self.act_toggle_show.setText("Hide Overlay (Ctrl+Alt+L)")

    def toggle_click_through(self):
        self.overlay.toggle_click_through()
        is_ct = self.config_manager.get("click_through", False)
        self.act_tray_clickthrough.setChecked(is_ct)

    def on_clickthrough_toggled_from_overlay(self, is_enabled: bool):
        self.act_tray_clickthrough.setChecked(is_enabled)
        if is_enabled and QSystemTrayIcon.isSystemTrayAvailable():
            self.tray_icon.showMessage(
                "Click-Through Enabled",
                "Mouse clicks now pass through the overlay.\nTo disable, right-click the system tray icon near the clock.",
                QSystemTrayIcon.MessageIcon.Information,
                3000
            )

    def toggle_always_on_top(self):
        self.overlay.toggle_always_on_top()
        self.act_tray_top.setChecked(self.config_manager.get("always_on_top", True))

    def on_track_changed(self, track_info: dict):
        """Update info ke overlay dan tooltip tray."""
        self.overlay.handle_track_changed(track_info)
        title = track_info.get("title", "")
        artist = track_info.get("artist", "")
        duration = track_info.get("duration", 0.0)
        if title:
            text = f"{title} - {artist}"
            print(f"[Spotify] [TRACK] '{title}' by '{artist}' ({int(duration)}s)")
            self.act_tray_track.setText(f"♪ {text[:38]}..." if len(text) > 40 else f"♪ {text}")
            self.tray_icon.setToolTip(f"Spotify: {text}")
        else:
            self.act_tray_track.setText("Spotify: Waiting...")
            self.tray_icon.setToolTip("Spotify Lyrics Overlay")

    def on_status_changed(self, status: str):
        self.overlay.handle_status_changed(status)
        if status == "waiting_spotify":
            print("[Spotify] [WAITING] Waiting for Spotify playback...")
            self.act_tray_track.setText("Spotify: Inactive")
        elif status == "playing":
            print("[Spotify] [PLAYING] Music playing")
        elif status == "paused":
            print("[Spotify] [PAUSED] Playback paused")

    def open_settings(self):
        """Membuka jendela pengaturan aplikasi."""
        if not self.settings_dialog:
            self.settings_dialog = SettingsDialog(self.config_manager)
            self.settings_dialog.settings_applied.connect(self.on_settings_applied)

        self.settings_dialog.show()
        self.settings_dialog.raise_()
        self.settings_dialog.activateWindow()

    def on_settings_applied(self, new_config: dict):
        self.overlay.apply_new_settings(new_config)
        self.act_tray_clickthrough.setChecked(new_config.get("click_through", False))
        self.act_tray_top.setChecked(new_config.get("always_on_top", True))

    def quit_app(self):
        """Menutup aplikasi secara bersih."""
        try:
            keyboard.unhook_all_hotkeys()
        except Exception:
            pass
        self.spotify_controller.stop()
        self.tray_icon.hide()
        self.qapp.quit()


def main():
    # Mengaktifkan penyesuaian DPI tinggi di Windows
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"

    app = QApplication(sys.argv)
    app.setApplicationName("Spotify Lyrics Overlay")
    app.setOrganizationName("SpotifyLyrics")

    overlay_app = SpotifyLyricsApp(app)
    overlay_app.start()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
