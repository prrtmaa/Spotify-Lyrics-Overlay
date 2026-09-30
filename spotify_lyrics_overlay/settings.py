"""
settings.py - Konfigurasi dan Antarmuka Pengaturan Spotify Lyrics Overlay.
Mengelola config.json, Windows Registry (Auto-start), preset tampilan, dan dialog pengaturan GUI PyQt6.
"""

import os
import sys
import json
import winreg
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QSlider, QCheckBox,
    QPushButton, QComboBox, QColorDialog, QTabWidget, QWidget,
    QFrame, QMessageBox, QGraphicsDropShadowEffect, QButtonGroup,
    QScrollArea
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QIcon


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
    "window_x": 340,
    "window_y": 550,
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
        "toggle_transparency": "ctrl+alt+t"
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
        self.resize(610, 660)
        self.setMinimumSize(570, 580)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)

        icon_path = get_asset_path("icon.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        # Modern Dark Theme Stylesheet
        self.setStyleSheet("""
            QDialog {
                background-color: #12141A;
                color: #FFFFFF;
                font-family: 'Segoe UI', sans-serif;
            }
            QTabWidget::pane {
                border: 1px solid #232733;
                background-color: #161821;
                border-radius: 10px;
                padding: 10px;
            }
            QTabBar::tab {
                background-color: #1A1D27;
                color: #8C92A4;
                padding: 10px 22px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                margin-right: 4px;
                font-weight: 600;
                font-size: 13px;
            }
            QTabBar::tab:selected {
                background-color: #161821;
                color: #1ED760;
                border-bottom: 2px solid #1ED760;
            }
            QLabel {
                color: #E1E4EA;
                font-size: 13px;
            }
            QComboBox {
                background-color: #202433;
                color: #FFFFFF;
                border: 1px solid #2F354A;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 13px;
            }
            QComboBox::drop-down {
                border: none;
                width: 24px;
            }
            QComboBox QAbstractItemView {
                background-color: #202433;
                color: #FFFFFF;
                selection-background-color: #1ED760;
                selection-color: #000000;
                border: 1px solid #2F354A;
            }
            QSlider::groove:horizontal {
                height: 6px;
                background: #252A3B;
                border-radius: 3px;
            }
            QSlider::sub-page:horizontal {
                background: #1ED760;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #FFFFFF;
                border: 2px solid #1ED760;
                width: 16px;
                margin-top: -6px;
                margin-bottom: -6px;
                border-radius: 8px;
            }
            QCheckBox {
                color: #E1E4EA;
                font-size: 13px;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border-radius: 4px;
                border: 1px solid #373E54;
                background-color: #1A1D27;
            }
            QCheckBox::indicator:checked {
                background-color: #1ED760;
                border: 1px solid #1ED760;
            }
            QPushButton {
                background-color: #242838;
                color: #FFFFFF;
                border: 1px solid #353B52;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: 600;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #2C3246;
                border-color: #48506E;
            }
            QPushButton#btnSave {
                background-color: #1ED760;
                color: #000000;
                border: none;
            }
            QPushButton#btnSave:hover {
                background-color: #25EC6E;
            }
            QPushButton.presetBtn {
                background-color: #1E222F;
                border: 1px solid #2F364B;
                border-radius: 6px;
                font-size: 12px;
                padding: 6px 12px;
            }
            QPushButton.presetBtn:hover {
                background-color: #2A3043;
                border-color: #1ED760;
            }
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(18, 16, 18, 16)
        main_layout.setSpacing(12)

        # Header Title
        title_label = QLabel("Spotify Lyrics Overlay Settings")
        title_label.setStyleSheet("font-size: 17px; font-weight: bold; color: #FFFFFF;")
        main_layout.addWidget(title_label)

        # Tab Widget
        tabs = QTabWidget()
        tabs.addTab(self.create_appearance_tab(), "Appearance & Transparency")
        tabs.addTab(self.create_behavior_tab(), "Behavior")
        tabs.addTab(self.create_hotkeys_tab(), "Hotkeys & Gestures")
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
        layout.setSpacing(14)
        layout.setContentsMargins(10, 10, 14, 14)

        # 1. Preset Tema Cepat
        preset_box = QFrame()
        preset_box.setStyleSheet("background-color: #1A1D27; border: 1px solid #282C3C; border-radius: 8px; padding: 8px;")
        preset_vlayout = QVBoxLayout(preset_box)
        preset_vlayout.setContentsMargins(6, 6, 6, 6)
        preset_vlayout.setSpacing(6)

        lbl_preset = QLabel("⚡ Quick Appearance Presets:")
        lbl_preset.setStyleSheet("font-weight: bold; color: #FFFFFF; font-size: 12px;")
        preset_vlayout.addWidget(lbl_preset)

        preset_hlayout = QHBoxLayout()
        preset_hlayout.setSpacing(6)

        btn_preset_pure = QPushButton("🌟 Pure Floating\n(0% Transparent)")
        btn_preset_pure.setProperty("class", "presetBtn")
        btn_preset_pure.clicked.connect(lambda: self.apply_preset(0, 20, 2, 600, 108))

        btn_preset_glass = QPushButton("🌌 Frosted Glass\n(20% Subtle Glass)")
        btn_preset_glass.setProperty("class", "presetBtn")
        btn_preset_glass.clicked.connect(lambda: self.apply_preset(20, 20, 2, 600, 108))

        btn_preset_single = QPushButton("⚡ Compact Bar\n(1 Line Slim)")
        btn_preset_single.setProperty("class", "presetBtn")
        btn_preset_single.clicked.connect(lambda: self.apply_preset(15, 18, 1, 480, 78))

        btn_preset_dark = QPushButton("🌑 Dark Modern\n(60% Obsidian)")
        btn_preset_dark.setProperty("class", "presetBtn")
        btn_preset_dark.clicked.connect(lambda: self.apply_preset(60, 22, 3, 640, 135))

        preset_hlayout.addWidget(btn_preset_pure)
        preset_hlayout.addWidget(btn_preset_glass)
        preset_hlayout.addWidget(btn_preset_single)
        preset_hlayout.addWidget(btn_preset_dark)
        preset_vlayout.addLayout(preset_hlayout)
        layout.addWidget(preset_box)

        # 2. Ukuran Jendela Overlay (Width & Height)
        size_box = QFrame()
        size_box.setObjectName("sizeBox")
        size_box.setStyleSheet("""
            QFrame#sizeBox {
                background-color: #1A1D27;
                border: 1px solid #282C3C;
                border-radius: 8px;
            }
        """)
        size_box_layout = QVBoxLayout(size_box)
        size_box_layout.setContentsMargins(12, 10, 12, 10)
        size_box_layout.setSpacing(10)

        size_header = QHBoxLayout()
        lbl_size_title = QLabel("📐 Window Dimensions:")
        lbl_size_title.setStyleSheet("font-weight: bold; color: #FFFFFF; font-size: 12px;")
        size_header.addWidget(lbl_size_title)
        size_header.addStretch()

        btn_reset_sz = QPushButton("↺ Default (600×108)")
        btn_reset_sz.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_reset_sz.setStyleSheet("""
            QPushButton {
                background-color: #232736;
                color: #A0A6B8;
                border: 1px solid #33394E;
                border-radius: 4px;
                padding: 3px 8px;
                font-size: 11px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #2D3245;
                color: #1ED760;
                border-color: #1ED760;
            }
        """)
        btn_reset_sz.clicked.connect(self.reset_window_size)
        size_header.addWidget(btn_reset_sz)
        size_box_layout.addLayout(size_header)

        # Slider Lebar
        w_layout = QHBoxLayout()
        lbl_w = QLabel("Window Width:")
        lbl_w.setFixedWidth(135)
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
        lbl_h.setFixedWidth(135)
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

        # 3. Background Opacity (Bisa 0% Pure Transparent)
        opacity_layout = QHBoxLayout()
        opacity_label = QLabel("Background Opacity:")
        opacity_label.setFixedWidth(145)
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

        # 4. Jumlah Baris Lirik
        lines_layout = QHBoxLayout()
        lines_label = QLabel("Lyric Lines Display:")
        lines_label.setFixedWidth(145)
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
        size_label.setFixedWidth(145)
        self.slider_font_size = QSlider(Qt.Orientation.Horizontal)
        self.slider_font_size.setRange(14, 38)
        cur_size = self.config_manager.get("font_size", 20)
        self.slider_font_size.setValue(cur_size)
        self.lbl_font_size_val = QLabel(f"{cur_size} pt")
        self.lbl_font_size_val.setFixedWidth(120)
        self.slider_font_size.valueChanged.connect(lambda v: self.lbl_font_size_val.setText(f"{v} pt"))
        size_layout.addWidget(size_label)
        size_layout.addWidget(self.slider_font_size, 1)
        size_layout.addWidget(self.lbl_font_size_val)
        layout.addLayout(size_layout)

        # 6. Font Family
        font_layout = QHBoxLayout()
        font_label = QLabel("Font Family:")
        font_label.setFixedWidth(145)
        self.combo_font = QComboBox()
        common_fonts = ["Segoe UI", "Segoe UI Variable Text", "Montserrat", "Inter", "Arial", "Roboto", "Helvetica"]
        self.combo_font.addItems(common_fonts)
        current_font = self.config_manager.get("font_family", "Segoe UI")
        idx = self.combo_font.findText(current_font)
        if idx >= 0:
            self.combo_font.setCurrentIndex(idx)
        else:
            self.combo_font.addItem(current_font)
            self.combo_font.setCurrentText(current_font)
        font_layout.addWidget(font_label)
        font_layout.addWidget(self.combo_font, 1)
        layout.addLayout(font_layout)

        # 7. Text Alignment
        align_layout = QHBoxLayout()
        align_label = QLabel("Text Alignment:")
        align_label.setFixedWidth(145)
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
        color_label.setFixedWidth(145)
        self.btn_color = QPushButton()
        self.btn_color.setFixedWidth(100)
        self.update_color_button_preview()
        self.btn_color.clicked.connect(self.choose_color)
        color_layout.addWidget(color_label)
        color_layout.addWidget(self.btn_color)
        color_layout.addStretch()
        layout.addLayout(color_layout)

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
        layout.setSpacing(18)
        layout.setContentsMargins(12, 16, 12, 16)

        # Always on Top
        self.chk_top = QCheckBox("Always on Top")
        self.chk_top.setChecked(self.config_manager.get("always_on_top", True))
        desc_top = QLabel("Keeps the overlay floating above all other windows and games.")
        desc_top.setStyleSheet("color: #8C92A4; font-size: 12px; margin-left: 26px;")
        layout.addWidget(self.chk_top)
        layout.addWidget(desc_top)

        # Click Through
        self.chk_clickthrough = QCheckBox("Mouse Click-Through")
        self.chk_clickthrough.setChecked(self.config_manager.get("click_through", False))
        desc_click = QLabel("Mouse clicks pass directly through the overlay to underlying windows.\n"
                            "⚠️ When enabled, toggle off via the System Tray icon in the Windows taskbar.")
        desc_click.setStyleSheet("color: #8C92A4; font-size: 12px; margin-left: 26px;")
        layout.addWidget(self.chk_clickthrough)
        layout.addWidget(desc_click)

        # Auto Start
        self.chk_autostart = QCheckBox("Start with Windows (Auto-Start)")
        self.chk_autostart.setChecked(self.config_manager.is_autostart_enabled())
        desc_auto = QLabel("Automatically launch Spotify Lyrics Overlay on system startup.")
        desc_auto.setStyleSheet("color: #8C92A4; font-size: 12px; margin-left: 26px;")
        layout.addWidget(self.chk_autostart)
        layout.addWidget(desc_auto)

        # Hide When Paused
        self.chk_hide_paused = QCheckBox("Hide Automatically When Paused")
        self.chk_hide_paused.setChecked(self.config_manager.get("hide_when_paused", False))
        desc_paused = QLabel("Automatically hides overlay when Spotify playback is paused or stopped.")
        desc_paused.setStyleSheet("color: #8C92A4; font-size: 12px; margin-left: 26px;")
        layout.addWidget(self.chk_hide_paused)
        layout.addWidget(desc_paused)

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
        layout.setSpacing(11)
        layout.setContentsMargins(8, 8, 12, 10)

        # Header Keyboard Hotkeys
        sec1_title = QLabel("⌨️ Global Keyboard Hotkeys")
        sec1_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #FFFFFF;")
        layout.addWidget(sec1_title)

        sec1_sub = QLabel("Works system-wide even while games or other applications are focused:")
        sec1_sub.setStyleSheet("color: #8C92A4; font-size: 12px; margin-bottom: 2px;")
        layout.addWidget(sec1_sub)

        def make_keycap(key_text: str) -> QLabel:
            lbl = QLabel(key_text)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet("""
                QLabel {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #282D3E, stop:1 #1C202C);
                    color: #1ED760;
                    font-family: 'Segoe UI', 'Consolas', monospace;
                    font-size: 11px;
                    font-weight: 700;
                    border: 1px solid #3A435B;
                    border-bottom: 2px solid #141620;
                    border-radius: 5px;
                    padding: 3px 8px;
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

        def make_hotkey_card(icon_char: str, title: str, subtitle: str, keys: list) -> QFrame:
            frame = QFrame()
            frame.setObjectName("hotkeyCard")
            frame.setStyleSheet("""
                QFrame#hotkeyCard {
                    background-color: #1A1D27;
                    border: 1px solid #282C3C;
                    border-radius: 9px;
                }
                QFrame#hotkeyCard:hover {
                    background-color: #202432;
                    border-color: #384058;
                }
                QLabel {
                    background: transparent;
                }
            """)
            f_layout = QHBoxLayout(frame)
            f_layout.setContentsMargins(12, 8, 12, 8)
            f_layout.setSpacing(10)

            icon_badge = QLabel(icon_char)
            icon_badge.setFixedSize(34, 34)
            icon_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            icon_badge.setStyleSheet("""
                QLabel {
                    background-color: rgba(30, 215, 96, 0.12);
                    color: #1ED760;
                    border-radius: 17px;
                    font-size: 15px;
                    font-weight: bold;
                }
            """)
            f_layout.addWidget(icon_badge)

            text_vbox = QVBoxLayout()
            text_vbox.setContentsMargins(0, 0, 0, 0)
            text_vbox.setSpacing(2)

            lbl_title = QLabel(title)
            lbl_title.setStyleSheet("color: #FFFFFF; font-weight: 600; font-size: 13px;")
            lbl_sub = QLabel(subtitle)
            lbl_sub.setStyleSheet("color: #8C92A4; font-size: 11px;")

            text_vbox.addWidget(lbl_title)
            text_vbox.addWidget(lbl_sub)
            f_layout.addLayout(text_vbox, 1)

            caps_widget = make_hotkey_caps(keys)
            f_layout.addWidget(caps_widget, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

            return frame

        def make_mouse_row(icon_char: str, action: str, how_to: str) -> QFrame:
            frame = QFrame()
            frame.setObjectName("mouseRow")
            frame.setStyleSheet("""
                QFrame#mouseRow {
                    background-color: #171A24;
                    border: 1px solid #232736;
                    border-radius: 8px;
                }
                QFrame#mouseRow:hover {
                    background-color: #1C202E;
                    border-color: #30374D;
                }
                QLabel {
                    background: transparent;
                }
            """)
            h_layout = QHBoxLayout(frame)
            h_layout.setContentsMargins(12, 8, 12, 8)
            h_layout.setSpacing(10)

            icon_lbl = QLabel(icon_char)
            icon_lbl.setFixedSize(28, 28)
            icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            icon_lbl.setStyleSheet("""
                QLabel {
                    background-color: rgba(255, 255, 255, 0.07);
                    color: #FFFFFF;
                    border-radius: 14px;
                    font-size: 13px;
                }
            """)
            h_layout.addWidget(icon_lbl)

            lbl_action = QLabel(f"<b>{action}:</b> <span style='color: #A6ACB9;'>{how_to}</span>")
            lbl_action.setStyleSheet("font-size: 12px; color: #FFFFFF;")
            lbl_action.setWordWrap(True)
            h_layout.addWidget(lbl_action, 1)

            return frame

        # Hotkey rows
        layout.addWidget(make_hotkey_card("👁", "Toggle Overlay Visibility", "Show or hide the floating lyrics widget", ["Ctrl", "Alt", "L"]))
        layout.addWidget(make_hotkey_card("⇄", "Cycle Lyric Line Mode", "Switch between 1 Line ⇋ 2 Lines ⇋ 3 Lines", ["Ctrl", "Alt", "M"]))
        layout.addWidget(make_hotkey_card("💧", "Cycle Transparency Level", "Cycle 0% (Pure Transparent) ⇋ 20% ⇋ 40% ⇋ 60%", ["Ctrl", "Alt", "T"]))
        layout.addWidget(make_hotkey_card("🔍", "Increase Font Size", "Increase active lyric font size by +2 pt", ["Ctrl", "Alt", "▲"]))
        layout.addWidget(make_hotkey_card("🔎", "Decrease Font Size", "Decrease active lyric font size by -2 pt", ["Ctrl", "Alt", "▼"]))

        # Mouse controls header
        sec2_title = QLabel("🖱️ Mouse Gestures & Shortcuts")
        sec2_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #FFFFFF; margin-top: 8px;")
        layout.addWidget(sec2_title)

        layout.addWidget(make_mouse_row("✋", "Move Window (Drag)", "Left-click and hold anywhere on the card to move the widget."))
        layout.addWidget(make_mouse_row("📐", "Resize Window", "Drag any window border or corner, or drag the bottom-right grip (⋱)."))
        layout.addWidget(make_mouse_row("⚡", "Dynamic Island Pill", "Double-click anywhere on the widget to toggle mini-pill mode."))
        layout.addWidget(make_mouse_row("📋", "Quick Context Menu", "Right-click the widget for playback controls, transparency, font size, & reset."))

        # Callout Tip
        tip_frame = QFrame()
        tip_frame.setObjectName("tipBox")
        tip_frame.setStyleSheet("""
            QFrame#tipBox {
                background-color: rgba(30, 215, 96, 0.08);
                border: 1px solid rgba(30, 215, 96, 0.25);
                border-left: 3px solid #1ED760;
                border-radius: 6px;
            }
            QLabel {
                background: transparent;
            }
        """)
        tip_layout = QHBoxLayout(tip_frame)
        tip_layout.setContentsMargins(10, 8, 10, 8)
        lbl_tip = QLabel("💡 <b>Tip:</b> You can also adjust window dimensions precisely with the sliders in the <b>Appearance & Transparency</b> tab.")
        lbl_tip.setWordWrap(True)
        lbl_tip.setStyleSheet("color: #D2D7E2; font-size: 11px;")
        tip_layout.addWidget(lbl_tip)
        layout.addWidget(tip_frame)

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
