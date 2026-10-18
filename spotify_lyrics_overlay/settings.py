"""
settings.py - Konfigurasi dan Antarmuka Pengaturan Spotify Lyrics Overlay.
Mengelola config.json, Windows Registry (Auto-start), preset tampilan, dan dialog pengaturan GUI PyQt6.
"""

import os
import sys
import json
import math
import winreg
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QSlider, QCheckBox,
    QPushButton, QComboBox, QColorDialog, QTabWidget, QWidget,
    QFrame, QMessageBox, QScrollArea
)
from PyQt6.QtCore import Qt, pyqtSignal, QDateTime, QLocale, QTimer
from PyQt6.QtGui import (
    QColor, QFont, QIcon, QPainter, QPainterPath, QBrush, QLinearGradient,
    QFontDatabase,
)

MIN_FONT_SIZE = 6
MAX_FONT_SIZE = 32


def get_app_dir() -> str:
    """Mengembalikan direktori aplikasi yang persisten (tempat file .exe atau skrip python berada)."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def get_asset_path(filename: str) -> str:
    """Mengembalikan path file aset, mendukung bundling PyInstaller onefile (_MEIPASS) dan mode script."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        cand1 = os.path.join(sys._MEIPASS, "assets", filename)
        if os.path.exists(cand1):
            return cand1
        cand2 = os.path.join(sys._MEIPASS, filename)
        if os.path.exists(cand2):
            return cand2
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", filename)


# Lokasi file konfigurasi yang persisten
BASE_DIR = get_app_dir()
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")

DEFAULT_CONFIG = {
    "font_family": "Segoe UI",
    "font_size": 20,
    "active_color": "#1ED760",
    "inactive_color": "rgba(255, 255, 255, 0.45)",
    "background_opacity": 0.45,
    "always_on_top": True,
    "click_through": False,
    "auto_hide_header": False,
    "show_progress_bar": True,
    "show_album_cover": True,
    "window_width": 600,
    "window_height": 108,
    "display_lines": 2,
    "text_alignment": "center",
    "auto_start": False,
    "hide_when_paused": False,
    "hotkeys": {
        "toggle_overlay": "ctrl+alt+l",
        "font_increase": "ctrl+alt+up",
        "font_decrease": "ctrl+alt+down",
        "toggle_mode": "ctrl+alt+m",
        "toggle_transparency": "ctrl+alt+t",
        "toggle_island": "ctrl+alt+i"
    }
}


class ConfigManager:
    """Mengelola pembacaan, penulisan, dan sinkronisasi config.json."""

    def __init__(self, filepath=CONFIG_FILE):
        self.filepath = filepath
        self.config = {}
        self.load()

    def load(self):
        """Memuat konfigurasi dari file atau membuat default jika belum ada."""
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    self.config = {**DEFAULT_CONFIG, **loaded}
                    if "hotkeys" in loaded:
                        self.config["hotkeys"] = {**DEFAULT_CONFIG["hotkeys"], **loaded["hotkeys"]}
            except Exception as e:
                print(f"[ConfigManager] Failed to read config: {e}. Using defaults.")
                self.config = DEFAULT_CONFIG.copy()
        else:
            self.config = DEFAULT_CONFIG.copy()
            self.save()

    def save(self):
        """Saves current configuration to config.json file."""
        try:
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[ConfigManager] Failed to save config: {e}")

    def get(self, key, default=None):
        return self.config.get(key, default)

    def set(self, key, value, auto_save=True):
        self.config[key] = value
        if auto_save:
            self.save()

    def reset_to_defaults(self):
        self.config = DEFAULT_CONFIG.copy()
        self.save()

    # --- Windows Registry Auto-Start ---
    @staticmethod
    def is_autostart_enabled() -> bool:
        """Memeriksa apakah aplikasi terdaftar di Windows Run Registry."""
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0,
                winreg.KEY_READ
            )
            _, _ = winreg.QueryValueEx(key, "SpotifyLyricsOverlay")
            winreg.CloseKey(key)
            return True
        except FileNotFoundError:
            return False
        except Exception as e:
            print(f"[ConfigManager] Registry read error: {e}")
            return False

    @staticmethod
    def set_autostart(enabled: bool) -> bool:
        """Mendaftarkan atau menghapus aplikasi dari Windows Run Registry."""
        app_name = "SpotifyLyricsOverlay"
        reg_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, reg_path, 0, winreg.KEY_SET_VALUE)
            if enabled:
                if getattr(sys, "frozen", False):
                    exe_path = f'"{sys.executable}"'
                else:
                    main_py = os.path.join(os.path.dirname(os.path.abspath(__file__)), "main.py")
                    exe_path = f'"{sys.executable}" "{main_py}"'
                winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, exe_path)
            else:
                try:
                    winreg.DeleteValue(key, app_name)
                except FileNotFoundError:
                    pass
            winreg.CloseKey(key)
            return True
        except Exception as e:
            print(f"[ConfigManager] Failed to update Registry autostart: {e}")
            return False


class SettingsMochi(QWidget):
    """Small animated mochi mark matching the compact island indicator."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(30, 30)
        self.phase = 0.0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.advance)

    def showEvent(self, event):
        super().showEvent(event)
        self.timer.start(50)

    def hideEvent(self, event):
        self.timer.stop()
        super().hideEvent(event)

    def advance(self):
        self.phase = (self.phase + 0.055) % (math.pi * 2)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pulse = math.sin(self.phase)
        cx, cy = self.width() / 2, self.height() / 2
        rx, ry = 10.2 + pulse * 0.35, 9.1 - pulse * 0.25
        wobble = math.sin(self.phase * 1.4) * 0.45

        shape = QPainterPath()
        shape.moveTo(cx, cy - ry)
        shape.cubicTo(cx + rx + wobble, cy - ry, cx + rx + wobble, cy + ry * 0.55, cx + wobble, cy + ry)
        shape.cubicTo(cx - rx * 0.65, cy + ry + wobble, cx - rx - wobble, cy + ry * 0.35, cx - rx, cy - wobble)
        shape.cubicTo(cx - rx * 0.8, cy - ry - wobble, cx - rx * 0.2, cy - ry * 0.85, cx, cy - ry)
        shape.closeSubpath()

        fill = QLinearGradient(cx - rx, cy - ry, cx + rx, cy + ry)
        fill.setColorAt(0, QColor("#C7FFE0"))
        fill.setColorAt(0.5, QColor("#77EBA9"))
        fill.setColorAt(1, QColor("#38C879"))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(fill))
        painter.drawPath(shape)
        painter.setBrush(QColor(255, 255, 255, 105))
        painter.drawEllipse(int(cx - 5), int(cy - 7), 6, 4)


class SettingsDialog(QDialog):
    """Modern, elegant, and flexible Settings Dialog window."""
    settings_applied = pyqtSignal(dict)

    def __init__(self, config_manager: ConfigManager, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.current_active_color = self.config_manager.get("active_color", "#1ED760")
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Spotify Lyrics Overlay Settings")
        self.resize(700, 650)
        self.setMinimumSize(620, 540)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)

        icon_path = get_asset_path("icon.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        # Restrained dark theme with a single Spotify-green accent.
        self.setStyleSheet("""
            QDialog {
                background-color: #101311;
                color: #F3F5F8;
                font-family: 'Segoe UI', sans-serif;
            }
            QTabWidget {
                background: transparent;
            }
            QTabWidget::pane {
                border: none;
                border-top: 1px solid #2A302C;
                background-color: transparent;
                padding: 8px 0 0 0;
                top: -1px;
            }
            QTabBar::tab {
                background-color: transparent;
                color: #929A94;
                padding: 7px 11px;
                border: none;
                border-bottom: 2px solid transparent;
                margin: 0 8px 0 0;
                font-weight: 500;
                font-size: 11px;
            }
            QTabBar::tab:selected {
                color: #C8F5D8;
                border-bottom: 2px solid #73D998;
            }
            QLabel {
                color: #DCE2E9;
                font-size: 11px;
            }
            QComboBox {
                background-color: #171B18;
                color: #F3F5F8;
                border: 1px solid #303832;
                border-radius: 6px;
                padding: 5px 8px;
                min-height: 16px;
                font-size: 10px;
            }
            QComboBox:hover { border-color: #4A665A; }
            QComboBox:focus { border-color: #66D998; }
            QComboBox::drop-down {
                border: none;
                width: 28px;
            }
            QComboBox QAbstractItemView {
                background-color: #171D26;
                color: #F3F5F8;
                selection-background-color: #244A37;
                selection-color: #B5F5CA;
                border: 1px solid #303A49;
                padding: 5px;
            }
            QSlider::groove:horizontal {
                height: 5px;
                background: #29313D;
                border-radius: 2px;
            }
            QSlider::sub-page:horizontal {
                background: #62D892;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: #EAF8EF;
                border: 3px solid #62D892;
                width: 13px;
                margin-top: -6px;
                margin-bottom: -6px;
                border-radius: 9px;
            }
            QCheckBox {
                color: #DCE2E9;
                font-size: 10px;
                spacing: 7px;
            }
            QCheckBox::indicator {
                width: 15px;
                height: 15px;
                border-radius: 4px;
                border: 1px solid #465047;
                background-color: #171B18;
            }
            QCheckBox::indicator:checked {
                background-color: #62D892;
                border: 1px solid #62D892;
            }
            QPushButton {
                background-color: #1A1F1B;
                color: #E8EDF2;
                border: 1px solid #343B35;
                border-radius: 6px;
                padding: 6px 10px;
                font-weight: 600;
                font-size: 10px;
            }
            QPushButton:hover {
                background-color: #232A24;
                border-color: #526455;
            }
            QPushButton:pressed { background-color: #17231F; }
            QPushButton#btnSave {
                background-color: #72E3A0;
                color: #0A1A10;
                border: none;
            }
            QPushButton#btnSave:hover {
                background-color: #91F2B5;
            }
            QPushButton.presetBtn {
                background-color: #171B18;
                border: 1px solid #303832;
                border-radius: 6px;
                min-height: 40px;
                font-size: 9px;
                padding: 4px 6px;
            }
            QPushButton.presetBtn:hover {
                background-color: #1B2928;
                border-color: #62D892;
            }
            QScrollBar:vertical {
                background: transparent;
                width: 8px;
                margin: 2px;
            }
            QScrollBar::handle:vertical {
                background: #35414C;
                border-radius: 4px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover { background: #62D892; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0;
            }
            QToolTip {
                background-color: #1A222B;
                color: #F3F5F8;
                border: 1px solid #394A53;
                padding: 6px 8px;
                border-radius: 6px;
            }
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 12, 16, 12)
        main_layout.setSpacing(9)

        header = QFrame()
        header.setObjectName("settingsHeader")
        header.setStyleSheet("""
            QFrame#settingsHeader {
                background: transparent;
                border: none;
            }
        """)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(11, 8, 13, 8)
        header_layout.setSpacing(9)
        brand_mark = SettingsMochi()
        header_layout.addWidget(brand_mark)
        header_text = QVBoxLayout()
        header_text.setSpacing(2)
        title_label = QLabel("Spotify Lyrics")
        title_label.setStyleSheet("font-size: 14px; font-weight: 700; color: #F5F7FA;")
        subtitle_label = QLabel("Settings")
        subtitle_label.setStyleSheet("font-size: 10px; color: #9BA8AD;")
        header_text.addWidget(title_label)
        header_text.addWidget(subtitle_label)
        header_layout.addLayout(header_text, 1)
        main_layout.addWidget(header)

        # Tab Widget
        tabs = QTabWidget()
        tabs.setDocumentMode(True)
        tabs.setElideMode(Qt.TextElideMode.ElideNone)
        tabs.addTab(self.create_appearance_tab(), "  Appearance  ")
        tabs.addTab(self.create_behavior_tab(), "  Behavior  ")
        tabs.addTab(self.create_hotkeys_tab(), "  Shortcuts  ")
        main_layout.addWidget(tabs)

        # Bottom Buttons
        btn_layout = QHBoxLayout()
        self.btn_reset = QPushButton("Reset Defaults")
        self.btn_reset.clicked.connect(self.reset_defaults)
        btn_layout.addWidget(self.btn_reset)

        btn_layout.addStretch()

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_cancel)

        self.btn_save = QPushButton("Save & Apply")
        self.btn_save.setObjectName("btnSave")
        self.btn_save.clicked.connect(self.save_and_apply)
        btn_layout.addWidget(self.btn_save)

        main_layout.addLayout(btn_layout)

    def create_appearance_tab(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("""
            QScrollArea {
                background: transparent;
                border: none;
            }
            QScrollBar:vertical {
                background: #161821;
                width: 8px;
                margin: 0px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: #2B3042;
                border-radius: 4px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: #1ED760;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)

        widget = QWidget()
        widget.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(widget)
        layout.setSpacing(6)
        layout.setContentsMargins(4, 4, 7, 7)

        preview_card = QFrame()
        preview_card.setStyleSheet("QFrame { background: transparent; border: none; }")
        preview_layout = QHBoxLayout(preview_card)
        preview_layout.setContentsMargins(3, 2, 3, 4)
        preview_layout.setSpacing(6)
        preview_copy = QVBoxLayout()
        preview_copy.setSpacing(1)
        preview_title = QLabel("Island")
        preview_title.setStyleSheet(
            "color: #DCE2D9; font-size: 11px; font-weight: 600;"
        )
        preview_copy.addWidget(preview_title)
        preview_layout.addLayout(preview_copy, 1)

        clock_preview = QFrame()
        clock_preview.setMinimumWidth(0)
        clock_preview.setFixedHeight(30)
        clock_preview.setStyleSheet("""
            QFrame {
                background-color: #090C0A;
                border: 1px solid #39453A;
                border-top-left-radius: 0px;
                border-top-right-radius: 0px;
                border-bottom-left-radius: 17px;
                border-bottom-right-radius: 17px;
            }
        """)
        clock_preview_layout = QHBoxLayout(clock_preview)
        clock_preview_layout.setContentsMargins(8, 2, 8, 2)
        clock_preview_layout.setSpacing(5)
        preview_dot = QLabel("●")
        preview_dot.setStyleSheet("color: #7CE5A4; font-size: 8px;")
        clock_preview_layout.addWidget(preview_dot)
        self.clock_preview_date = QLabel()
        self.clock_preview_date.setStyleSheet("color: #AAB4BE; font-size: 8px; font-weight: 600;")
        clock_preview_layout.addWidget(self.clock_preview_date)
        preview_divider = QFrame()
        preview_divider.setFixedSize(1, 14)
        preview_divider.setStyleSheet("background-color: #3B444D;")
        clock_preview_layout.addWidget(preview_divider)
        self.clock_preview_time = QLabel()
        self.clock_preview_time.setStyleSheet(
            "color: #F5F7FA; font-size: 11px; font-weight: 700;"
        )
        clock_preview_layout.addWidget(self.clock_preview_time)
        preview_layout.addWidget(clock_preview, 0, Qt.AlignmentFlag.AlignRight)
        layout.addWidget(preview_card)
        self.clock_preview_timer = QTimer(self)
        self.clock_preview_timer.timeout.connect(self.update_clock_preview)
        self.clock_preview_timer.start(1000)
        self.update_clock_preview()

        # 1. Preset Tema Cepat
        preset_vlayout = QVBoxLayout()
        preset_vlayout.setContentsMargins(0, 0, 0, 0)
        preset_vlayout.setSpacing(4)
        preset_hlayout = QHBoxLayout()
        preset_hlayout.setSpacing(4)

        btn_preset_pure = QPushButton("Floating\n0% background")
        btn_preset_pure.setProperty("class", "presetBtn")
        btn_preset_pure.clicked.connect(lambda: self.apply_preset(0, 20, 2, 600, 108))

        btn_preset_glass = QPushButton("Soft glass\n20% background")
        btn_preset_glass.setProperty("class", "presetBtn")
        btn_preset_glass.clicked.connect(lambda: self.apply_preset(20, 20, 2, 600, 108))

        btn_preset_single = QPushButton("Compact\n1 lyric line")
        btn_preset_single.setProperty("class", "presetBtn")
        btn_preset_single.clicked.connect(lambda: self.apply_preset(15, 18, 1, 480, 78))

        btn_preset_dark = QPushButton("Dark\n60% background")
        btn_preset_dark.setProperty("class", "presetBtn")
        btn_preset_dark.clicked.connect(lambda: self.apply_preset(60, 22, 3, 640, 135))

        preset_hlayout.addWidget(btn_preset_pure)
        preset_hlayout.addWidget(btn_preset_glass)
        preset_hlayout.addWidget(btn_preset_single)
        preset_hlayout.addWidget(btn_preset_dark)
        preset_vlayout.addWidget(QLabel("Presets"))
        preset_vlayout.addLayout(preset_hlayout)
        layout.addLayout(preset_vlayout)

        # 2. Ukuran Jendela Overlay (Width & Height)
        size_box = QFrame()
        size_box.setObjectName("sizeBox")
        size_box.setStyleSheet("""
            QFrame#sizeBox {
                background-color: #151915;
                border: 1px solid #2D352E;
                border-radius: 8px;
            }
        """)
        size_box_layout = QVBoxLayout(size_box)
        size_box_layout.setContentsMargins(11, 9, 11, 9)
        size_box_layout.setSpacing(6)

        size_header = QHBoxLayout()
        lbl_size_title = QLabel("Size")
        lbl_size_title.setStyleSheet("font-weight: bold; color: #FFFFFF; font-size: 12px;")
        size_header.addWidget(lbl_size_title)
        size_header.addStretch()

        btn_reset_sz = QPushButton("↺ Default (600×108)")
        btn_reset_sz.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_reset_sz.setStyleSheet("""
            QPushButton {
                background-color: #1A1F1B;
                color: #A0AAA1;
                border: 1px solid #343B35;
                border-radius: 4px;
                padding: 3px 8px;
                font-size: 11px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #232A24;
                color: #A8E9BA;
                border-color: #526455;
            }
        """)
        btn_reset_sz.clicked.connect(self.reset_window_size)
        size_header.addWidget(btn_reset_sz)
        size_box_layout.addLayout(size_header)

        # Slider Lebar
        w_layout = QHBoxLayout()
        lbl_w = QLabel("Window Width:")
        lbl_w.setFixedWidth(112)
        self.slider_width = QSlider(Qt.Orientation.Horizontal)
        self.slider_width.setRange(350, 1100)
        cur_w = self.config_manager.get("window_width", 600)
        self.slider_width.setValue(cur_w)
        self.lbl_width_val = QLabel(f"{cur_w} px")
        self.lbl_width_val.setFixedWidth(70)
        self.slider_width.valueChanged.connect(lambda v: self.lbl_width_val.setText(f"{v} px"))
        w_layout.addWidget(lbl_w)
        w_layout.addWidget(self.slider_width, 1)
        w_layout.addWidget(self.lbl_width_val)
        size_box_layout.addLayout(w_layout)

        # Slider Tinggi
        h_layout = QHBoxLayout()
        lbl_h = QLabel("Window Height:")
        lbl_h.setFixedWidth(112)
        self.slider_height = QSlider(Qt.Orientation.Horizontal)
        self.slider_height.setRange(75, 250)
        cur_h = self.config_manager.get("window_height", 108)
        self.slider_height.setValue(cur_h)
        self.lbl_height_val = QLabel(f"{cur_h} px")
        self.lbl_height_val.setFixedWidth(70)
        self.slider_height.valueChanged.connect(lambda v: self.lbl_height_val.setText(f"{v} px"))
        h_layout.addWidget(lbl_h)
        h_layout.addWidget(self.slider_height, 1)
        h_layout.addWidget(self.lbl_height_val)
        size_box_layout.addLayout(h_layout)

        layout.addWidget(size_box)

        appearance_section = QLabel("OVERLAY APPEARANCE")
        appearance_section.setStyleSheet(
            "color: #91EAB1; font-size: 9px; font-weight: 700; letter-spacing: 1px;"
        )
        layout.addWidget(appearance_section)

        # 3. Background Opacity (Bisa 0% Pure Transparent)
        opacity_layout = QHBoxLayout()
        opacity_layout.setSpacing(10)
        opacity_label = QLabel("Background Opacity:")
        opacity_label.setFixedWidth(122)
        self.slider_opacity = QSlider(Qt.Orientation.Horizontal)
        self.slider_opacity.setRange(0, 100)
        cur_opacity = int(self.config_manager.get("background_opacity", 0.20) * 100)
        self.slider_opacity.setValue(cur_opacity)
        self.lbl_opacity_val = QLabel(f"{cur_opacity}%" if cur_opacity > 0 else "0% (Pure Transparent)")
        self.lbl_opacity_val.setFixedWidth(120)
        self.slider_opacity.valueChanged.connect(self.on_opacity_slider_changed)
        opacity_layout.addWidget(opacity_label)
        opacity_layout.addWidget(self.slider_opacity, 1)
        opacity_layout.addWidget(self.lbl_opacity_val)
        layout.addLayout(opacity_layout)
        lyrics_section = QLabel("LYRICS & TYPOGRAPHY")
        lyrics_section.setStyleSheet(
            "color: #91EAB1; font-size: 9px; font-weight: 700; letter-spacing: 1px;"
        )
        layout.addWidget(lyrics_section)

        # 4. Jumlah Baris Lirik
        lines_layout = QHBoxLayout()
        lines_label = QLabel("Lyric Lines Display:")
        lines_label.setFixedWidth(122)
        self.combo_lines = QComboBox()
        self.combo_lines.addItem("1 Line (Compact / Ultra-Minimal)", 1)
        self.combo_lines.addItem("2 Lines (Active & Next - Recommended)", 2)
        self.combo_lines.addItem("3 Lines (Previous, Active, Next)", 3)
        self.combo_lines.addItem("5 Lines (Full / Expanded)", 5)
        cur_lines = self.config_manager.get("display_lines", 2)
        for i in range(self.combo_lines.count()):
            if self.combo_lines.itemData(i) == cur_lines:
                self.combo_lines.setCurrentIndex(i)
                break
        lines_layout.addWidget(lines_label)
        lines_layout.addWidget(self.combo_lines, 1)
        layout.addLayout(lines_layout)

        # 5. Font Size
        size_layout = QHBoxLayout()
        size_label = QLabel("Active Font Size:")
        size_label.setFixedWidth(122)
        self.slider_font_size = QSlider(Qt.Orientation.Horizontal)
        self.slider_font_size.setRange(MIN_FONT_SIZE, MAX_FONT_SIZE)
        cur_size = self.config_manager.get("font_size", 20)
        self.slider_font_size.setValue(cur_size)
        self.lbl_font_size_val = QLabel(f"{self.slider_font_size.value()} pt")
        self.        lbl_font_size_val.setFixedWidth(46)
        self.slider_font_size.valueChanged.connect(lambda v: self.lbl_font_size_val.setText(f"{v} pt"))
        size_layout.addWidget(size_label)
        size_layout.addWidget(self.slider_font_size, 1)
        size_layout.addWidget(self.lbl_font_size_val)
        layout.addLayout(size_layout)

        # 6. Font Family
        font_layout = QHBoxLayout()
        font_label = QLabel("Font Family:")
        font_label.setFixedWidth(122)
        self.combo_font = QComboBox()
        font_choices = set(QFontDatabase.families())
        font_choices.update({
            "Aptos", "Arial", "Calibri", "Cambria", "Consolas", "Courier New",
            "Georgia", "Inter", "Montserrat", "Roboto", "Segoe UI", "Tahoma",
            "Times New Roman", "Trebuchet MS", "Verdana",
        })
        available_fonts = sorted(font_choices, key=str.casefold)
        current_font = self.config_manager.get("font_family", "Segoe UI")
        if current_font.casefold() not in {family.casefold() for family in available_fonts}:
            available_fonts.append(current_font)
            available_fonts.sort(key=str.casefold)
        for family in available_fonts:
            self.combo_font.addItem(family)
            self.combo_font.setItemData(
                self.combo_font.count() - 1,
                QFont(family),
                Qt.ItemDataRole.FontRole,
            )
        self.combo_font.setCurrentText(current_font)
        font_layout.addWidget(font_label)
        font_layout.addWidget(self.combo_font, 1)
        layout.addLayout(font_layout)

        # 7. Text Alignment
        align_layout = QHBoxLayout()
        align_label = QLabel("Text Alignment:")
        align_label.setFixedWidth(122)
        self.combo_align = QComboBox()
        self.combo_align.addItem("Center", "center")
        self.combo_align.addItem("Left", "left")
        cur_align = self.config_manager.get("text_alignment", "center")
        for i in range(self.combo_align.count()):
            if self.combo_align.itemData(i) == cur_align:
                self.combo_align.setCurrentIndex(i)
                break
        align_layout.addWidget(align_label)
        align_layout.addWidget(self.combo_align, 1)
        layout.addLayout(align_layout)

        # 8. Active Lyric Color
        color_layout = QHBoxLayout()
        color_label = QLabel("Active Lyric Color:")
        color_label.setFixedWidth(122)
        self.btn_color = QPushButton()
        self.btn_color.setFixedWidth(100)
        self.update_color_button_preview()
        self.btn_color.clicked.connect(self.choose_color)
        color_layout.addWidget(color_label)
        color_layout.addWidget(self.btn_color)
        color_layout.addStretch()
        layout.addLayout(color_layout)

        options_section = QLabel("DISPLAY OPTIONS")
        options_section.setStyleSheet(
            "color: #91EAB1; font-size: 9px; font-weight: 700; letter-spacing: 1px;"
        )
        layout.addWidget(options_section)

        # 9. Auto Hide Header
        self.chk_auto_hide = QCheckBox("Auto-Hide Controls when Mouse Leaves Overlay")
        self.chk_auto_hide.setChecked(self.config_manager.get("auto_hide_header", True))
        self.chk_auto_hide.setToolTip("Only floating lyrics remain visible on screen when not hovering.")
        layout.addWidget(self.chk_auto_hide)

        # 10. Show Progress Bar
        self.chk_progress = QCheckBox("Show Lyric Progress Bar")
        self.chk_progress.setChecked(self.config_manager.get("show_progress_bar", True))
        layout.addWidget(self.chk_progress)

        # 11. Show Album Cover
        self.chk_cover = QCheckBox("Show Album Artwork")
        self.chk_cover.setChecked(self.config_manager.get("show_album_cover", True))
        layout.addWidget(self.chk_cover)

        layout.addStretch()
        scroll.setWidget(widget)
        return scroll

    def update_clock_preview(self):
        locale = QLocale(QLocale.Language.English, QLocale.Country.UnitedStates)
        now = QDateTime.currentDateTime()
        self.clock_preview_date.setText(locale.toString(now, "ddd, d MMM yy"))
        self.clock_preview_time.setText(locale.toString(now, "HH:mm"))

    def reset_window_size(self):
        """Mereset ukuran slider ke default 600x108 px."""
        self.slider_width.setValue(DEFAULT_CONFIG["window_width"])
        self.slider_height.setValue(DEFAULT_CONFIG["window_height"])

    def on_opacity_slider_changed(self, v: int):
        if v == 0:
            self.lbl_opacity_val.setText("0% (Pure Transparent)")
        else:
            self.lbl_opacity_val.setText(f"{v}%")

    def apply_preset(self, opacity: int, font_size: int, lines: int, width: int = 600, height: int = 108):
        self.slider_opacity.setValue(opacity)
        self.slider_font_size.setValue(font_size)
        self.slider_width.setValue(width)
        self.slider_height.setValue(height)
        for i in range(self.combo_lines.count()):
            if self.combo_lines.itemData(i) == lines:
                self.combo_lines.setCurrentIndex(i)
                break

    def create_behavior_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(6)
        layout.setContentsMargins(9, 9, 9, 9)

        def add_behavior_card(title: str, description: str, checkbox: QCheckBox):
            card = QFrame()
            card.setObjectName("behaviorCard")
            card.setStyleSheet("""
                QFrame#behaviorCard {
                    background: transparent;
                    border: none;
                    border-bottom: 1px solid #29312A;
                }
            """)
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(2, 5, 2, 5)
            card_layout.setSpacing(1)
            checkbox.setText(title)
            card_layout.addWidget(checkbox)
            detail = QLabel(description)
            detail.setWordWrap(True)
            detail.setStyleSheet("color: #929A94; font-size: 10px; padding-left: 25px;")
            card_layout.addWidget(detail)
            layout.addWidget(card)

        self.chk_top = QCheckBox()
        self.chk_top.setChecked(self.config_manager.get("always_on_top", True))
        add_behavior_card(
            "Always on Top",
            "Keep the overlay above other windows.",
            self.chk_top
        )

        self.chk_clickthrough = QCheckBox()
        self.chk_clickthrough.setChecked(self.config_manager.get("click_through", False))
        add_behavior_card(
            "Mouse Click-Through",
            "Pass mouse clicks through the overlay.",
            self.chk_clickthrough
        )

        self.chk_autostart = QCheckBox()
        self.chk_autostart.setChecked(self.config_manager.is_autostart_enabled())
        add_behavior_card(
            "Start with Windows",
            "Launch automatically when you sign in.",
            self.chk_autostart
        )

        self.chk_hide_paused = QCheckBox()
        self.chk_hide_paused.setChecked(self.config_manager.get("hide_when_paused", False))
        add_behavior_card(
            "Hide when playback is paused",
            "Hide the overlay when playback stops.",
            self.chk_hide_paused
        )

        layout.addStretch()
        return widget

    def create_hotkeys_tab(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("""
            QScrollArea {
                background: transparent;
                border: none;
            }
            QScrollBar:vertical {
                background: #161821;
                width: 7px;
                margin: 0px;
                border-radius: 3px;
            }
            QScrollBar::handle:vertical {
                background: #2B3042;
                border-radius: 3px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: #1ED760;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)

        widget = QWidget()
        widget.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(widget)
        layout.setSpacing(5)
        layout.setContentsMargins(4, 4, 7, 6)

        # Header Keyboard Hotkeys
        sec1_title = QLabel("Keyboard shortcuts")
        sec1_title.setStyleSheet("font-size: 13px; font-weight: 600; color: #E5EAE5;")
        layout.addWidget(sec1_title)

        def make_keycap(key_text: str) -> QLabel:
            lbl = QLabel(key_text)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet("""
                QLabel {
                    background-color: #1B211C;
                    color: #A8E9BA;
                    font-family: 'Segoe UI', 'Consolas', monospace;
                    font-size: 11px;
                    font-weight: 700;
                    border: 1px solid #364238;
                    border-radius: 4px;
                    padding: 2px 7px;
                    min-width: 22px;
                }
            """)
            return lbl

        def make_plus() -> QLabel:
            lbl = QLabel("+")
            lbl.setStyleSheet("color: #6C748C; font-size: 11px; font-weight: bold; padding: 0 2px;")
            return lbl

        def make_hotkey_caps(keys: list) -> QWidget:
            w = QWidget()
            w.setStyleSheet("background: transparent;")
            h = QHBoxLayout(w)
            h.setContentsMargins(0, 0, 0, 0)
            h.setSpacing(4)
            for i, k in enumerate(keys):
                if i > 0:
                    h.addWidget(make_plus())
                h.addWidget(make_keycap(k))
            return w

        def make_hotkey_card(title: str, keys: list) -> QFrame:
            frame = QFrame()
            frame.setObjectName("hotkeyCard")
            frame.setStyleSheet("""
                QFrame#hotkeyCard {
                    background: transparent;
                    border: none;
                    border-bottom: 1px solid #29312A;
                }
            """)
            f_layout = QHBoxLayout(frame)
            f_layout.setContentsMargins(2, 4, 2, 4)
            f_layout.setSpacing(8)

            lbl_title = QLabel(title)
            lbl_title.setStyleSheet("color: #DCE2D9; font-size: 11px;")
            f_layout.addWidget(lbl_title, 1)

            caps_widget = make_hotkey_caps(keys)
            f_layout.addWidget(caps_widget, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

            return frame

        def make_mouse_row(action: str, how_to: str) -> QFrame:
            frame = QFrame()
            frame.setObjectName("mouseRow")
            frame.setStyleSheet("""
                QFrame#mouseRow {
                    background: transparent;
                    border: none;
                    border-bottom: 1px solid #29312A;
                }
            """)
            h_layout = QHBoxLayout(frame)
            h_layout.setContentsMargins(2, 5, 2, 5)
            h_layout.setSpacing(12)
            lbl_action = QLabel(f"<b>{action}</b>")
            lbl_action.setStyleSheet("font-size: 11px; color: #DCE2D9;")
            lbl_action.setMinimumWidth(112)
            h_layout.addWidget(lbl_action)
            lbl_detail = QLabel(how_to)
            lbl_detail.setStyleSheet("font-size: 10px; color: #929A94;")
            lbl_detail.setWordWrap(True)
            h_layout.addWidget(lbl_detail, 1)

            return frame

        # Hotkey rows
        layout.addWidget(make_hotkey_card("Toggle overlay", ["Ctrl", "Alt", "L"]))
        layout.addWidget(make_hotkey_card("Toggle island", ["Ctrl", "Alt", "I"]))
        layout.addWidget(make_hotkey_card("Cycle lyric lines", ["Ctrl", "Alt", "M"]))
        layout.addWidget(make_hotkey_card("Cycle transparency", ["Ctrl", "Alt", "T"]))
        layout.addWidget(make_hotkey_card("Increase font size", ["Ctrl", "Alt", "▲"]))
        layout.addWidget(make_hotkey_card("Decrease font size", ["Ctrl", "Alt", "▼"]))

        # Mouse controls header
        sec2_title = QLabel("Mouse and window")
        sec2_title.setStyleSheet("font-size: 13px; font-weight: 600; color: #E5EAE5; margin-top: 8px;")
        layout.addWidget(sec2_title)

        layout.addWidget(make_mouse_row("Pinned position", "The overlay stays top-centered."))
        layout.addWidget(make_mouse_row("Resize window", "Drag an edge or the bottom-right grip."))
        layout.addWidget(make_mouse_row("Dynamic Island", "Click the capsule or use Ctrl + Alt + I."))
        layout.addWidget(make_mouse_row("Context menu", "Right-click the overlay for playback and display controls."))

        layout.addStretch()
        scroll.setWidget(widget)
        return scroll

    def update_color_button_preview(self):
        self.btn_color.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.current_active_color};
                border: 2px solid #FFFFFF;
                border-radius: 6px;
                height: 24px;
            }}
        """)

    def choose_color(self):
        color = QColorDialog.getColor(QColor(self.current_active_color), self, "Choose Active Lyric Color")
        if color.isValid():
            self.current_active_color = color.name()
            self.update_color_button_preview()

    def reset_defaults(self):
        reply = QMessageBox.question(
            self,
            "Reset Confirmation",
            "Are you sure you want to reset all settings to defaults?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.config_manager.reset_to_defaults()
            self.slider_font_size.setValue(DEFAULT_CONFIG["font_size"])
            self.slider_opacity.setValue(int(DEFAULT_CONFIG["background_opacity"] * 100))
            self.current_active_color = DEFAULT_CONFIG["active_color"]
            self.update_color_button_preview()
            self.chk_top.setChecked(DEFAULT_CONFIG["always_on_top"])
            self.chk_clickthrough.setChecked(DEFAULT_CONFIG["click_through"])
            self.chk_hide_paused.setChecked(DEFAULT_CONFIG["hide_when_paused"])
            self.chk_auto_hide.setChecked(DEFAULT_CONFIG["auto_hide_header"])
            self.chk_progress.setChecked(DEFAULT_CONFIG["show_progress_bar"])
            self.chk_cover.setChecked(DEFAULT_CONFIG["show_album_cover"])
            self.slider_width.setValue(DEFAULT_CONFIG["window_width"])
            self.slider_height.setValue(DEFAULT_CONFIG["window_height"])
            self.save_and_apply()

    def save_and_apply(self):
        """Menyimpan seluruh konfigurasi dan meng-emit sinyal pembaruan."""
        self.config_manager.set("font_family", self.combo_font.currentText(), auto_save=False)
        self.config_manager.set("font_size", self.slider_font_size.value(), auto_save=False)
        self.config_manager.set("display_lines", self.combo_lines.currentData(), auto_save=False)
        self.config_manager.set("text_alignment", self.combo_align.currentData(), auto_save=False)
        self.config_manager.set("active_color", self.current_active_color, auto_save=False)
        self.config_manager.set("background_opacity", self.slider_opacity.value() / 100.0, auto_save=False)
        self.config_manager.set("auto_hide_header", self.chk_auto_hide.isChecked(), auto_save=False)
        self.config_manager.set("show_progress_bar", self.chk_progress.isChecked(), auto_save=False)
        self.config_manager.set("show_album_cover", self.chk_cover.isChecked(), auto_save=False)
        self.config_manager.set("always_on_top", self.chk_top.isChecked(), auto_save=False)
        self.config_manager.set("click_through", self.chk_clickthrough.isChecked(), auto_save=False)
        self.config_manager.set("hide_when_paused", self.chk_hide_paused.isChecked(), auto_save=False)
        self.config_manager.set("window_width", self.slider_width.value(), auto_save=False)
        self.config_manager.set("window_height", self.slider_height.value(), auto_save=False)

        # Update Windows Registry Auto-start
        autostart_checked = self.chk_autostart.isChecked()
        self.config_manager.set_autostart(autostart_checked)
        self.config_manager.set("auto_start", autostart_checked, auto_save=False)

        self.config_manager.save()
        self.settings_applied.emit(self.config_manager.config)
        self.accept()
