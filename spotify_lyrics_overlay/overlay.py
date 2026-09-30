"""
overlay.py - Jendela Desktop Floating Lyrics Overlay (PyQt6).
Desain: macOS Sonoma & Dynamic Island Now Playing Widget.
Fitur:
- Desain murni tanpa outline/border abu-abu DWM Windows 11 (border: none, DWMWA_COLOR_NONE)
- macOS Traffic Light Buttons (🔴 Sembunyikan, 🟡 Minimalkan ke Dynamic Island Pill, 🟢 Siklus Baris)
- Equalizer Audio Animatif (4-bar visualizer bergoyang mengikuti musik)
- Cover Album Squircle Artistik (dengan bayangan ambient halus)
- Mode Fleksibel: Full Lyrics Widget ⇋ Dynamic Island Mini Pill
- Bebas digeser (draggable) dari mana saja pada kartu widget
- Kontrol media terintegrasi (⏮ ⏯ ⏭) terhubung ke Spotify Windows GSMTC
- Sinkronisasi lirik realtime (LRCLIB API) dengan interpolasi timeline presisi
"""

import os
import sys
import time
import math
import random
import ctypes
import win32gui
import win32con
from typing import Optional, List, Tuple
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QMenu, QGraphicsDropShadowEffect, QFrame, QSizePolicy, QProgressBar
)
from PyQt6.QtCore import Qt, QPoint, QRectF, QTimer, pyqtSignal, QRect, QEvent
from PyQt6.QtGui import (
    QColor, QFont, QCursor, QAction, QPainter, QBrush,
    QLinearGradient, QPen, QMouseEvent, QIcon, QPixmap, QPainterPath,
    QGuiApplication
)

from settings import ConfigManager, SettingsDialog, get_asset_path
from lyrics_provider import LyricsData, LyricsProvider, LyricsFetchWorker


def remove_dwm_border(hwnd: int):
    """Menghilangkan outline/border DWM Windows 11 secara tuntas."""
    try:
        # DWMWA_BORDER_COLOR = 34
        # 0xFFFFFFFE = DWMWA_COLOR_NONE (menonaktifkan border 1px bawaan Windows 11)
        DWMWA_BORDER_COLOR = 34
        color_none = ctypes.c_int(0xFFFFFFFE)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd,
            DWMWA_BORDER_COLOR,
            ctypes.byref(color_none),
            ctypes.sizeof(color_none)
        )
    except Exception:
        pass

    try:
        # DWMWA_WINDOW_CORNER_PREFERENCE = 33
        # DWMWCP_DONOTROUND = 1 (mencegah DWM menggambar border sudut kotak)
        DWMWA_WINDOW_CORNER_PREFERENCE = 33
        corner_pref = ctypes.c_int(1)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd,
            DWMWA_WINDOW_CORNER_PREFERENCE,
            ctypes.byref(corner_pref),
            ctypes.sizeof(corner_pref)
        )
    except Exception:
        pass


def set_click_through(hwnd: int, enable: bool):
    """Mengatur mode tembus klik mouse (WS_EX_TRANSPARENT) via Win32 API."""
    try:
        styles = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
        if enable:
            win32gui.SetWindowLong(
                hwnd,
                win32con.GWL_EXSTYLE,
                styles | win32con.WS_EX_TRANSPARENT | win32con.WS_EX_LAYERED
            )
        else:
            win32gui.SetWindowLong(
                hwnd,
                win32con.GWL_EXSTYLE,
                styles & ~win32con.WS_EX_TRANSPARENT
            )
    except Exception as e:
        print(f"[Overlay] Gagal mengatur click-through: {e}")


def format_time(seconds: float) -> str:
    """Format detik ke format mm:ss."""
    if seconds < 0:
        seconds = 0
    m = int(seconds) // 60
    s = int(seconds) % 60
    return f"{m}:{s:02d}"


def create_default_cover(size: int = 64) -> QPixmap:
    """Membuat cover default bergaya piringan vinyl modern dan estetik."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Squircle clipping
    path = QPainterPath()
    radius = max(8.0, size * 0.22)
    path.addRoundedRect(QRectF(0, 0, size, size), radius, radius)
    painter.setClipPath(path)

    # Ambient deep gradient background
    grad = QLinearGradient(0, 0, size, size)
    grad.setColorAt(0, QColor(36, 40, 56))
    grad.setColorAt(1, QColor(16, 18, 24))
    painter.fillRect(0, 0, size, size, grad)

    # Vinyl disc grooves
    painter.setPen(QPen(QColor(255, 255, 255, 22), 1))
    center = size / 2.0
    for r in [size * 0.42, size * 0.32, size * 0.22]:
        painter.drawEllipse(QRectF(center - r, center - r, r * 2, r * 2))

    # Center Spotify emerald accent dot
    painter.setBrush(QBrush(QColor(30, 215, 96, 230)))
    painter.setPen(Qt.PenStyle.NoPen)
    cr = size * 0.12
    painter.drawEllipse(QRectF(center - cr, center - cr, cr * 2, cr * 2))

    # Center hole
    painter.setBrush(QBrush(QColor(16, 18, 24)))
    hr = size * 0.04
    painter.drawEllipse(QRectF(center - hr, center - hr, hr * 2, hr * 2))

    painter.end()
    return pixmap


def get_rounded_pixmap(src_pixmap: QPixmap, radius: float = 14.0, size: int = 64) -> QPixmap:
    """Mengubah QPixmap menjadi rounded squircle berukuran presisi dengan antialiasing."""
    if src_pixmap.isNull():
        return create_default_cover(size)

    scaled = src_pixmap.scaled(
        size, size,
        Qt.AspectRatioMode.KeepAspectRatioByExpanding,
        Qt.TransformationMode.SmoothTransformation
    )
    if scaled.width() != size or scaled.height() != size:
        x = max(0, (scaled.width() - size) // 2)
        y = max(0, (scaled.height() - size) // 2)
        scaled = scaled.copy(x, y, size, size)

    dest = QPixmap(size, size)
    dest.fill(Qt.GlobalColor.transparent)

    painter = QPainter(dest)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    path = QPainterPath()
    path.addRoundedRect(QRectF(0, 0, size, size), radius, radius)
    painter.setClipPath(path)
    painter.drawPixmap(0, 0, scaled)
    painter.end()

    return dest


class AnimatedEqualizer(QWidget):
    """Mini 4-bar equalizer animatif ala macOS Dynamic Island / Apple Music."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(18, 14)
        self.is_animating = False
        self.bar_count = 4
        self.phases = [random.uniform(0, 6.28) for _ in range(self.bar_count)]
        self.speeds = [0.22, 0.30, 0.25, 0.32]
        self.heights = [0.25, 0.25, 0.25, 0.25]
        self.color = QColor(30, 215, 96)  # Spotify Emerald

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_animation)
        self.timer.start(50)

    def set_active(self, active: bool):
        self.is_animating = active
        if not active:
            self.heights = [0.22, 0.22, 0.22, 0.22]
            self.update()

    def set_color(self, hex_or_color: str):
        self.color = QColor(hex_or_color)
        self.update()

    def update_animation(self):
        if not self.is_animating:
            return
        for i in range(self.bar_count):
            self.phases[i] += self.speeds[i]
            val = (math.sin(self.phases[i]) * 0.5 + 0.5) * 0.72 + (math.cos(self.phases[i] * 1.6) * 0.28) * 0.28
            self.heights[i] = max(0.20, min(1.0, val))
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        bar_w = 2.4
        gap = 1.8
        total_w = self.bar_count * bar_w + (self.bar_count - 1) * gap
        start_x = (w - total_w) / 2.0

        painter.setBrush(self.color)
        painter.setPen(Qt.PenStyle.NoPen)

        for i in range(self.bar_count):
            bh = max(2.5, self.heights[i] * h)
            bx = start_x + i * (bar_w + gap)
            by = h - bh
            path = QPainterPath()
            path.addRoundedRect(QRectF(bx, by, bar_w, bh), 1.2, 1.2)
            painter.drawPath(path)

        painter.end()


# Konstanta Tepi Resize Jendela Frameless
EDGE_NONE = 0
EDGE_LEFT = 1
EDGE_TOP = 2
EDGE_RIGHT = 4
EDGE_BOTTOM = 8
EDGE_TOP_LEFT = EDGE_TOP | EDGE_LEFT
EDGE_TOP_RIGHT = EDGE_TOP | EDGE_RIGHT
EDGE_BOTTOM_LEFT = EDGE_BOTTOM | EDGE_LEFT
EDGE_BOTTOM_RIGHT = EDGE_BOTTOM | EDGE_RIGHT


class CornerResizeGrip(QWidget):
    """
    Grip pojok kanan bawah dengan visual 3 garis diagonal bergaya modern.
    Mengubah ukuran jendela secara presisi dan mulus saat ditarik dengan mouse.
    """
    def __init__(self, target_window, parent=None):
        super().__init__(parent)
        self.target_window = target_window
        self.setFixedSize(14, 14)
        self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        self.setToolTip("Drag to resize overlay")
        self._is_resizing = False
        self._is_hovered = False
        self._start_pos = QPoint()
        self._start_size = None

    def enterEvent(self, event):
        self._is_hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._is_hovered = False
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        color = QColor(30, 215, 96, 240) if (self._is_hovered or self._is_resizing) else QColor(255, 255, 255, 110)
        painter.setPen(QPen(color, 1.6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        w = self.width()
        h = self.height()
        painter.drawLine(w - 2, h - 10, w - 10, h - 2)
        painter.drawLine(w - 2, h - 6, w - 6, h - 2)
        painter.drawLine(w - 2, h - 2, w - 2, h - 2)
        painter.end()

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_resizing = True
            self._start_pos = event.globalPosition().toPoint()
            self._start_size = self.target_window.size()
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._is_resizing and self._start_size is not None:
            delta = event.globalPosition().toPoint() - self._start_pos
            min_w = 340
            min_h = 70
            new_w = max(min_w, self._start_size.width() + delta.x())
            new_h = max(min_h, self._start_size.height() + delta.y())
            self.target_window.resize(new_w, new_h)
            event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton and self._is_resizing:
            self._is_resizing = False
            self.update()
            if hasattr(self.target_window, "on_resize_finished"):
                self.target_window.on_resize_finished()
            event.accept()


class MacTrafficLights(QWidget):
    """
    Tombol Traffic Lights ikonik macOS:
    🔴 Merah : Sembunyikan Overlay
    🟡 Kuning : Minimalkan ke Dynamic Island Pill Mode
    🟢 Hijau  : Ganti Mode Baris Lirik
    """
    close_clicked = pyqtSignal()
    minimize_clicked = pyqtSignal()
    expand_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.btn_close = QPushButton("✕")
        self.btn_close.setToolTip("Hide Overlay [Ctrl+Alt+L]")
        self.btn_close.clicked.connect(self.close_clicked.emit)

        self.btn_min = QPushButton("−")
        self.btn_min.setToolTip("Minimize to Dynamic Island Mini-Pill [🟡]")
        self.btn_min.clicked.connect(self.minimize_clicked.emit)

        self.btn_expand = QPushButton("+")
        self.btn_expand.setToolTip("Cycle Lyric Line Mode (1L ⇋ 2L ⇋ 3L)")
        self.btn_expand.clicked.connect(self.expand_clicked.emit)

        btns = [
            (self.btn_close, "#FF5F56", "#E0443E"),
            (self.btn_min, "#FFBD2E", "#DEA123"),
            (self.btn_expand, "#27C93F", "#1AAB29")
        ]

        for b, col, hover_col in btns:
            b.setFixedSize(11, 11)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setStyleSheet(f"""
                QPushButton {{
                    background-color: {col};
                    border: none;
                    border-radius: 5px;
                    color: transparent;
                    font-size: 8px;
                    font-weight: bold;
                    padding: 0px;
                }}
                QPushButton:hover {{
                    background-color: {hover_col};
                    color: rgba(0, 0, 0, 0.75);
                }}
            """)
            layout.addWidget(b)


class LyricLineLabel(QLabel):
    """Label lirik dengan drop shadow berkualitas tinggi agar terbaca jelas."""

    def __init__(self, role: str = "active", parent=None):
        super().__init__(parent)
        self.role = role
        self.setWordWrap(True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(8)
        shadow.setColor(QColor(0, 0, 0, 240))
        shadow.setOffset(0, 1)
        self.setGraphicsEffect(shadow)


class OverlayWindow(QWidget):
    """
    Jendela Desktop Floating Lyrics Overlay bergaya macOS Sonoma & Dynamic Island.
    Bebas border kotak/outline Windows 11, dilengkapi traffic lights, animasi equalizer,
    cover squircle, draggable di mana saja, serta mode mini-pill.
    """
    settings_requested = pyqtSignal()
    clickthrough_changed = pyqtSignal(bool)
    play_pause_requested = pyqtSignal()
    next_requested = pyqtSignal()
    prev_requested = pyqtSignal()

    def __init__(self, config_manager: ConfigManager, lyrics_provider: LyricsProvider):
        super().__init__()
        self.config_manager = config_manager
        self.lyrics_provider = lyrics_provider

        # State data pemutaran
        self.current_track = ""
        self.current_artist = ""
        self.current_duration = 0.0
        self.base_position = 0.0
        self.last_update_pos_time = 0.0
        self.is_playing = False
        self.app_status = "waiting_spotify"
        self.current_thumbnail_bytes = None

        # Mode Tampilan: True = Dynamic Island Mini Pill, False = Full macOS Widget
        self.is_pill_mode = False

        # Data lirik & pekerja fetch
        self.lyrics_data: Optional[LyricsData] = None
        self.lyrics_worker: Optional[LyricsFetchWorker] = None
        self.last_active_index = -99

        # State drag and drop
        self.dragging = False
        self.drag_position = QPoint()

        # State edge resizing & dragging
        self.resizing = False
        self.resize_edge = EDGE_NONE
        self.active_edge = EDGE_NONE
        self.resize_start_pos = QPoint()
        self.resize_start_geo: Optional[QRect] = None

        # State hover
        self.is_hovered = False

        self.init_window_flags()
        self.init_ui()
        self.apply_config_styles()

        # Aktifkan pelacakan mouse agar kursor otomatis berubah di tepi jendela
        self.setMouseTracking(True)
        self.container.setMouseTracking(True)
        self.container.installEventFilter(self)

        # Pesan inisialisasi awal
        self.set_single_message("Waiting for Spotify...", "Buka Spotify Desktop dan putar lagu")

        # Timer sinkronisasi lirik realtime (50ms)
        self.sync_timer = QTimer(self)
        self.sync_timer.timeout.connect(self.sync_lyrics_tick)
        self.sync_timer.start(50)

    def init_window_flags(self):
        """Flag: Frameless, Tool Window, Always on Top, Translucent (100% per-pixel alpha)."""
        flags = Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool
        if self.config_manager.get("always_on_top", True):
            flags |= Qt.WindowType.WindowStaysOnTopHint

        self.setWindowFlags(flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        screen = QGuiApplication.primaryScreen().geometry()
        w = min(self.config_manager.get("window_width", 560), screen.width() - 30)
        h = min(self.config_manager.get("window_height", 120), screen.height() - 30)

        x = self.config_manager.get("window_x", 360)
        y = self.config_manager.get("window_y", 540)

        # Validasi batas layar
        if x < 0 or (x + w) > screen.width() or y < 0 or (y + h) > screen.height():
            x = max(10, (screen.width() - w) // 2)
            y = max(10, screen.height() - h - 65)
            self.config_manager.set("window_x", x, auto_save=False)
            self.config_manager.set("window_y", y, auto_save=True)

        self.setGeometry(x, y, w, h)
        self.setMinimumSize(260, 48)

    def showEvent(self, event):
        super().showEvent(event)
        hwnd = int(self.winId())
        remove_dwm_border(hwnd)
        if self.config_manager.get("click_through", False):
            set_click_through(hwnd, True)

    def init_ui(self):
        """Menyusun antarmuka macOS Now Playing & Dynamic Island Widget."""
        self.root_layout = QVBoxLayout(self)
        self.root_layout.setContentsMargins(10, 10, 10, 10)

        # Container Utama (Kartu Kaca Melengkung Bebas Border)
        self.container = QFrame(self)
        self.container.setObjectName("macOverlayContainer")

        # Ambient drop shadow lembut di sekeliling kartu
        self.container_shadow = QGraphicsDropShadowEffect(self.container)
        self.container_shadow.setBlurRadius(26)
        self.container_shadow.setColor(QColor(0, 0, 0, 175))
        self.container_shadow.setOffset(0, 6)
        self.container.setGraphicsEffect(self.container_shadow)

        self.root_layout.addWidget(self.container)

        # Layout horizontal utama
        self.main_hlayout = QHBoxLayout(self.container)
        self.main_hlayout.setContentsMargins(14, 11, 16, 11)
        self.main_hlayout.setSpacing(14)

        # --- COVER ALBUM SQUIRCLE ---
        self.cover_container = QWidget()
        self.cover_vlayout = QVBoxLayout(self.cover_container)
        self.cover_vlayout.setContentsMargins(0, 0, 0, 0)
        self.cover_vlayout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.lbl_cover = QLabel()
        self.lbl_cover.setFixedSize(64, 64)
        self.lbl_cover.setPixmap(create_default_cover(64))

        cover_shadow = QGraphicsDropShadowEffect(self.lbl_cover)
        cover_shadow.setBlurRadius(14)
        cover_shadow.setColor(QColor(0, 0, 0, 180))
        cover_shadow.setOffset(0, 3)
        self.lbl_cover.setGraphicsEffect(cover_shadow)

        self.cover_vlayout.addWidget(self.lbl_cover)
        self.main_hlayout.addWidget(self.cover_container)

        # --- KONTEN KANAN ---
        self.right_layout = QVBoxLayout()
        self.right_layout.setContentsMargins(0, 0, 0, 0)
        self.right_layout.setSpacing(2)

        # 1. Baris Atas: macOS Traffic Lights + Info Lagu + Equalizer Animatif + Kontrol Media
        self.top_row_frame = QFrame()
        self.top_hlayout = QHBoxLayout(self.top_row_frame)
        self.top_hlayout.setContentsMargins(0, 0, 0, 0)
        self.top_hlayout.setSpacing(8)

        # Traffic Lights khas macOS
        self.traffic_lights = MacTrafficLights()
        self.traffic_lights.close_clicked.connect(self.hide)
        self.traffic_lights.minimize_clicked.connect(self.toggle_pill_mode)
        self.traffic_lights.expand_clicked.connect(self.cycle_display_lines)
        self.top_hlayout.addWidget(self.traffic_lights)

        # Judul & Artis Lagu
        self.lbl_song_info = QLabel("Spotify Lyrics Overlay")
        self.lbl_song_info.setStyleSheet("color: #FFFFFF; font-size: 12px; font-weight: bold;")
        self.lbl_song_info.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.top_hlayout.addWidget(self.lbl_song_info, 1)

        # Equalizer Animatif (Audio Visualizer)
        self.animated_eq = AnimatedEqualizer()
        self.top_hlayout.addWidget(self.animated_eq)

        # Tombol Media macOS Style (⏮ ⏯ ⏭)
        self.btn_prev = QPushButton("⏮")
        self.btn_prev.setToolTip("Previous Track")
        self.btn_prev.setProperty("class", "mediaBtn")
        self.btn_prev.clicked.connect(lambda: self.prev_requested.emit())

        self.btn_play = QPushButton("⏯")
        self.btn_play.setToolTip("Play / Pause")
        self.btn_play.setProperty("class", "mediaBtn")
        self.btn_play.clicked.connect(lambda: self.play_pause_requested.emit())

        self.btn_next = QPushButton("⏭")
        self.btn_next.setToolTip("Next Track")
        self.btn_next.setProperty("class", "mediaBtn")
        self.btn_next.clicked.connect(lambda: self.next_requested.emit())

        self.media_btns = [self.btn_prev, self.btn_play, self.btn_next]
        for b in self.media_btns:
            b.setFixedSize(22, 22)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            self.top_hlayout.addWidget(b)

        # Separator Halus
        self.tool_sep = QLabel("|")
        self.tool_sep.setStyleSheet("color: rgba(255, 255, 255, 0.20); font-size: 10px; margin: 0 1px;")
        self.top_hlayout.addWidget(self.tool_sep)

        # Tombol Alat Tambahan (Transparansi, Pengaturan)
        self.btn_trans = QPushButton("💧")
        self.btn_trans.setToolTip("Cycle Background Opacity (0% ⇋ 20% ⇋ 40% ⇋ 60%) [Ctrl+Alt+T]")
        self.btn_trans.setProperty("class", "toolBtn")
        self.btn_trans.clicked.connect(self.cycle_transparency)

        self.btn_settings = QPushButton("⚙")
        self.btn_settings.setToolTip("Full Settings")
        self.btn_settings.setProperty("class", "toolBtn")
        self.btn_settings.clicked.connect(lambda: self.settings_requested.emit())

        self.tool_btns = [self.btn_trans, self.btn_settings]
        for b in self.tool_btns:
            b.setFixedSize(20, 20)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            self.top_hlayout.addWidget(b)

        self.right_layout.addWidget(self.top_row_frame)

        # 2. Area Baris Lirik Realtime
        self.lyrics_container = QWidget()
        self.lyrics_layout = QVBoxLayout(self.lyrics_container)
        self.lyrics_layout.setContentsMargins(0, 2, 0, 2)
        self.lyrics_layout.setSpacing(1)

        self.line_labels: List[LyricLineLabel] = []
        self.rebuild_lyric_labels()

        self.right_layout.addWidget(self.lyrics_container, 1)

        # 3. Baris Bawah: Waktu Berjalan, Progress Bar Playback, Durasi & Resize Grip
        self.progress_container = QWidget()
        self.bottom_row = QHBoxLayout(self.progress_container)
        self.bottom_row.setContentsMargins(0, 2, 0, 0)
        self.bottom_row.setSpacing(6)

        self.lbl_time_cur = QLabel("0:00")
        self.lbl_time_cur.setStyleSheet("color: rgba(255, 255, 255, 0.45); font-size: 9px; font-weight: 500;")
        self.bottom_row.addWidget(self.lbl_time_cur)

        # Apple-style scrub progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(3)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setRange(0, 1000)
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: rgba(255, 255, 255, 0.12);
                border: none;
                border-radius: 1.5px;
            }
            QProgressBar::chunk {
                background-color: #1ED760;
                border-radius: 1.5px;
            }
        """)
        self.bottom_row.addWidget(self.progress_bar, 1)

        self.lbl_time_total = QLabel("0:00")
        self.lbl_time_total.setStyleSheet("color: rgba(255, 255, 255, 0.45); font-size: 9px; font-weight: 500;")
        self.bottom_row.addWidget(self.lbl_time_total)

        self.resize_grip = CornerResizeGrip(self, self.progress_container)
        self.bottom_row.addWidget(self.resize_grip)

        self.right_layout.addWidget(self.progress_container)
        self.main_hlayout.addLayout(self.right_layout, 1)

    def rebuild_lyric_labels(self):
        """Membuat ulang label lirik sesuai mode (1, 2, 3, atau 5 baris)."""
        for lbl in self.line_labels:
            self.lyrics_layout.removeWidget(lbl)
            lbl.deleteLater()
        self.line_labels.clear()

        total_lines = self.config_manager.get("display_lines", 2)

        if total_lines == 1:
            lbl = LyricLineLabel("active", self)
            self.line_labels.append(lbl)
            self.lyrics_layout.addWidget(lbl)
        elif total_lines == 2:
            lbl_act = LyricLineLabel("active", self)
            lbl_next = LyricLineLabel("next", self)
            self.line_labels.extend([lbl_act, lbl_next])
            for l in self.line_labels:
                self.lyrics_layout.addWidget(l)
        elif total_lines == 3:
            lbl_prev = LyricLineLabel("previous", self)
            lbl_act = LyricLineLabel("active", self)
            lbl_next = LyricLineLabel("next", self)
            self.line_labels.extend([lbl_prev, lbl_act, lbl_next])
            for l in self.line_labels:
                self.lyrics_layout.addWidget(l)
        else:
            lbl_p2 = LyricLineLabel("previous", self)
            lbl_p1 = LyricLineLabel("previous", self)
            lbl_act = LyricLineLabel("active", self)
            lbl_n1 = LyricLineLabel("next", self)
            lbl_n2 = LyricLineLabel("next", self)
            self.line_labels.extend([lbl_p2, lbl_p1, lbl_act, lbl_n1, lbl_n2])
            for l in self.line_labels:
                self.lyrics_layout.addWidget(l)

        self.apply_config_styles()
        if self.app_status == "waiting_spotify":
            self.set_single_message("Waiting for Spotify...", "Open Spotify Desktop and play a track")
        else:
            self.update_lyrics_display()

    def apply_config_styles(self):
        """Menerapkan styling estetika macOS tanpa border/outline kotak kaku."""
        font_family = self.config_manager.get("font_family", "Segoe UI")
        font_size = self.config_manager.get("font_size", 17)
        active_color = self.config_manager.get("active_color", "#1ED760")
        bg_opacity = self.config_manager.get("background_opacity", 0.40)
        text_align = self.config_manager.get("text_alignment", "left")
        show_progress = self.config_manager.get("show_progress_bar", True)
        show_cover = self.config_manager.get("show_album_cover", True)

        if hasattr(self, "animated_eq"):
            self.animated_eq.set_color(active_color)

        if hasattr(self, "cover_container"):
            self.cover_container.setVisible(show_cover and not self.is_pill_mode)

        if hasattr(self, "progress_container"):
            self.progress_container.setVisible(show_progress and not self.is_pill_mode)

        if hasattr(self, "lyrics_container"):
            self.lyrics_container.setVisible(not self.is_pill_mode)

        align_flag = Qt.AlignmentFlag.AlignCenter if text_align == "center" else (
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )

        # Gaya Kartu Kaca macOS:
        # border: none; TOTAL tanpa garis abu-abu DWM atau outline kotak
        if bg_opacity <= 0.05:
            # Mode Pure Transparent
            if self.is_hovered:
                container_style = """
                    QFrame#macOverlayContainer {
                        background-color: rgba(18, 20, 28, 0.45);
                        border: none;
                        border-radius: 22px;
                    }
                """
            else:
                container_style = """
                    QFrame#macOverlayContainer {
                        background-color: transparent;
                        border: none;
                    }
                """
        else:
            # Mode Dark Frosted Glass ala macOS
            alpha_top = min(0.96, max(0.20, bg_opacity * 1.20))
            alpha_bot = min(0.98, max(0.18, bg_opacity * 1.10))
            container_style = f"""
                QFrame#macOverlayContainer {{
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 rgba(28, 30, 40, {alpha_top:.2f}),
                        stop:1 rgba(14, 16, 22, {alpha_bot:.2f}));
                    border: none;
                    border-radius: 22px;
                }}
            """

        # Styling tombol media & utility Apple Style
        button_styles = """
            QPushButton.mediaBtn {
                font-family: 'Segoe UI Symbol', 'Segoe UI', sans-serif;
                background-color: rgba(255, 255, 255, 0.12);
                color: #FFFFFF;
                border: none;
                border-radius: 11px;
                font-size: 10px;
                font-weight: bold;
            }
            QPushButton.mediaBtn:hover {
                background-color: #1ED760;
                color: #000000;
            }
            QPushButton.toolBtn {
                background-color: rgba(255, 255, 255, 0.08);
                color: rgba(255, 255, 255, 0.70);
                border: none;
                border-radius: 10px;
                font-size: 10px;
                font-weight: 600;
            }
            QPushButton.toolBtn:hover {
                background-color: rgba(255, 255, 255, 0.22);
                color: #FFFFFF;
            }
        """

        self.container.setStyleSheet(container_style + button_styles)

        # Style teks lirik aktif & sekunder
        sec_font_size = max(11, int(font_size * 0.76))
        for lbl in self.line_labels:
            lbl.setAlignment(align_flag)
            if lbl.role == "active":
                lbl.setStyleSheet(f"""
                    QLabel {{
                        color: {active_color};
                        font-family: '{font_family}', sans-serif;
                        font-size: {font_size}pt;
                        font-weight: 700;
                        padding: 0px;
                    }}
                """)
            else:
                lbl.setStyleSheet(f"""
                    QLabel {{
                        color: rgba(255, 255, 255, 0.48);
                        font-family: '{font_family}', sans-serif;
                        font-size: {sec_font_size}pt;
                        font-weight: 500;
                        padding: 0px;
                    }}
                """)

    # --- Mode Fleksibel: Dynamic Island Mini Pill (Minimize) ---

    def toggle_pill_mode(self):
        """Beralih antara Mode Full Widget (dengan lirik) ⇋ Mode Dynamic Island Mini Pill (ringkas)."""
        self.is_pill_mode = not self.is_pill_mode

        if self.is_pill_mode:
            # Mode Mini Pill
            self.lyrics_container.hide()
            self.progress_container.hide()
            self.cover_container.hide()
            self.resize_grip.hide()
            self.main_hlayout.setContentsMargins(12, 6, 12, 6)
            self.container.setStyleSheet(self.container.styleSheet().replace("border-radius: 22px;", "border-radius: 18px;"))
            self.resize(340, 52)
            print("[Overlay] Switched to Dynamic Island Mini-Pill Mode (Minimized)")
        else:
            # Mode Full Widget
            self.lyrics_container.show()
            if self.config_manager.get("show_progress_bar", True):
                self.progress_container.show()
            if self.config_manager.get("show_album_cover", True):
                self.cover_container.show()
            self.resize_grip.show()
            self.main_hlayout.setContentsMargins(14, 11, 16, 11)
            target_h = self.config_manager.get("window_height", 120)
            target_w = self.config_manager.get("window_width", 560)
            self.resize(target_w, target_h)
            print("[Overlay] Switched to Full Lyrics Widget Mode")

        self.apply_config_styles()

    # --- Mouse Hover: Auto-Hide Controls ---

    def enterEvent(self, event):
        super().enterEvent(event)
        self.is_hovered = True
        self.show_hover_controls(True)
        self.apply_config_styles()

    def leaveEvent(self, event):
        super().leaveEvent(event)
        self.is_hovered = False
        if self.app_status == "playing" and self.config_manager.get("auto_hide_header", True):
            self.show_hover_controls(False)
        self.apply_config_styles()

    def show_hover_controls(self, visible: bool):
        for b in self.tool_btns:
            b.setVisible(visible)
        if hasattr(self, "tool_sep"):
            self.tool_sep.setVisible(visible)
        if hasattr(self, "resize_grip") and not self.is_pill_mode:
            self.resize_grip.setVisible(visible)

    # --- Penanganan Peristiwa Spotify & Lirik ---

    def handle_status_changed(self, status: str):
        self.app_status = status
        if status == "waiting_spotify":
            self.lbl_song_info.setText("Spotify Lyrics Overlay")
            self.set_single_message("Waiting for Spotify...", "Play a song in Spotify Desktop")
            self.lbl_cover.setPixmap(create_default_cover(64))
            self.is_playing = False
            self.btn_play.setText("▶")
            self.animated_eq.set_active(False)

            if hasattr(self, "progress_bar"):
                self.progress_bar.setValue(0)
                self.lbl_time_cur.setText("0:00")
                self.lbl_time_total.setText("0:00")
            self.show_hover_controls(True)
            self.apply_config_styles()

            if self.config_manager.get("hide_when_paused", False):
                self.hide()
        elif status == "paused":
            self.is_playing = False
            self.btn_play.setText("▶")
            self.animated_eq.set_active(False)
            if self.config_manager.get("hide_when_paused", False):
                self.hide()
        elif status == "playing":
            self.is_playing = True
            self.btn_play.setText("⏸")
            self.animated_eq.set_active(True)
            if not self.isVisible():
                self.show()
            if self.config_manager.get("auto_hide_header", True) and not self.is_hovered:
                self.show_hover_controls(False)
            self.apply_config_styles()

    def handle_track_changed(self, track_info: dict):
        title = track_info.get("title", "")
        artist = track_info.get("artist", "")
        duration = track_info.get("duration", 0.0)
        thumb_bytes = track_info.get("thumbnail_bytes")

        if not title and not artist:
            self.handle_status_changed("waiting_spotify")
            return

        self.current_track = title
        self.current_artist = artist
        self.current_duration = duration
        self.current_thumbnail_bytes = thumb_bytes
        self.app_status = "playing"
        self.btn_play.setText("⏸")
        self.animated_eq.set_active(True)

        self.lbl_song_info.setText(f"{title} • {artist}")
        self.lbl_time_total.setText(format_time(duration))
        self.set_single_message(title, f"Searching lyrics: {artist}")

        # Render Thumbnail Album Art
        cover_set = False
        if thumb_bytes:
            pix = QPixmap()
            if pix.loadFromData(thumb_bytes):
                self.lbl_cover.setPixmap(get_rounded_pixmap(pix, 14.0, 64))
                cover_set = True

        if not cover_set:
            self.lbl_cover.setPixmap(create_default_cover(64))

        if self.lyrics_worker and self.lyrics_worker.isRunning():
            self.lyrics_worker.quit()

        self.lyrics_worker = LyricsFetchWorker(
            self.lyrics_provider,
            self.current_track,
            self.current_artist,
            self.current_duration,
            need_cover=(not cover_set)
        )
        self.lyrics_worker.lyrics_ready.connect(self.on_lyrics_loaded)
        self.lyrics_worker.lyrics_error.connect(self.on_lyrics_error)
        self.lyrics_worker.cover_art_ready.connect(self.on_cover_art_loaded)
        self.lyrics_worker.start()

        if self.config_manager.get("auto_hide_header", True) and not self.is_hovered:
            self.show_hover_controls(False)
        self.apply_config_styles()

    def on_cover_art_loaded(self, cover_bytes: bytes):
        if cover_bytes:
            pix = QPixmap()
            if pix.loadFromData(cover_bytes):
                self.lbl_cover.setPixmap(get_rounded_pixmap(pix, 14.0, 64))

    def handle_playback_updated(self, track_info: dict):
        self.base_position = track_info.get("position", 0.0)
        self.current_duration = track_info.get("duration", self.current_duration)
        self.is_playing = track_info.get("is_playing", False)
        self.last_update_pos_time = time.time()
        self.btn_play.setText("⏸" if self.is_playing else "▶")
        self.animated_eq.set_active(self.is_playing)

    def on_lyrics_loaded(self, lyrics_obj: LyricsData):
        self.lyrics_data = lyrics_obj
        self.last_active_index = -99

        if not lyrics_obj.has_lyrics():
            self.set_single_message("Lyrics Not Available", f"{self.current_track} - {self.current_artist}")

        self.sync_lyrics_tick()

    def on_lyrics_error(self, err_msg: str):
        self.set_single_message("Lyrics Not Available", f"{self.current_track} - {self.current_artist}")

    def sync_lyrics_tick(self):
        """Loop sinkronisasi lirik & posisi realtime (50ms)."""
        if self.app_status == "waiting_spotify":
            return

        if self.is_playing and self.last_update_pos_time > 0:
            elapsed = time.time() - self.last_update_pos_time
            curr_pos = self.base_position + max(0.0, elapsed)
        else:
            curr_pos = self.base_position

        self.lbl_time_cur.setText(format_time(curr_pos))
        if self.current_duration > 0:
            self.lbl_time_total.setText(format_time(self.current_duration))

        if self.config_manager.get("show_progress_bar", True):
            if self.current_duration > 0:
                prog = min(1.0, max(0.0, curr_pos / self.current_duration))
                self.progress_bar.setValue(int(prog * 1000))
            else:
                self.progress_bar.setValue(0)

        if not self.lyrics_data or not self.lyrics_data.lines:
            return

        active_idx = self.lyrics_data.get_active_index(curr_pos)
        if active_idx != self.last_active_index:
            self.last_active_index = active_idx
            self.update_lyrics_display()

    def update_lyrics_display(self):
        if not self.lyrics_data or not self.lyrics_data.lines:
            return

        total_lines = self.config_manager.get("display_lines", 2)
        display_lines = self.lyrics_data.get_display_lines(self.last_active_index, total_lines)

        for i, (text, _) in enumerate(display_lines):
            if i < len(self.line_labels):
                self.line_labels[i].setText(text)

    def set_single_message(self, main_msg: str, sub_msg: str = ""):
        if not self.line_labels:
            return
        if len(self.line_labels) == 1:
            self.line_labels[0].setText(main_msg)
        elif len(self.line_labels) == 2:
            self.line_labels[0].setText(main_msg)
            self.line_labels[1].setText(sub_msg)
        else:
            mid = len(self.line_labels) // 2
            for i, lbl in enumerate(self.line_labels):
                if i == mid:
                    lbl.setText(main_msg)
                elif i == mid + 1 and sub_msg and (mid + 1 < len(self.line_labels)):
                    lbl.setText(sub_msg)
                else:
                    lbl.setText("")

    # --- Quick Toggles & Hotkeys ---

    def cycle_display_lines(self):
        """Beralih cepat antara 1 Baris ⇋ 2 Baris ⇋ 3 Baris."""
        if self.is_pill_mode:
            self.toggle_pill_mode()
            return

        cur = self.config_manager.get("display_lines", 2)
        if cur == 1:
            new_lines = 2
            target_h = max(115, self.height() + 25)
        elif cur == 2:
            new_lines = 3
            target_h = max(140, self.height() + 25)
        else:
            new_lines = 1
            target_h = max(88, self.height() - 40)

        self.config_manager.set("display_lines", new_lines)
        self.rebuild_lyric_labels()
        self.resize(self.width(), target_h)
        self.config_manager.set("window_height", target_h)
        print(f"[Overlay] Line mode changed to: {new_lines} Lines (Height: {target_h}px)")

    def cycle_transparency(self):
        """Quickly switch between: 0% ⇋ 20% ⇋ 40% ⇋ 60%."""
        cur = self.config_manager.get("background_opacity", 0.40)
        if cur <= 0.05:
            new_op = 0.20
            mode_name = "Frosted Glass (20%)"
        elif cur <= 0.25:
            new_op = 0.40
            mode_name = "Cozy macOS (40%)"
        elif cur <= 0.45:
            new_op = 0.65
            mode_name = "Dark Obsidian (65%)"
        else:
            new_op = 0.0
            mode_name = "Pure Transparent (0%)"

        self.config_manager.set("background_opacity", new_op)
        self.apply_config_styles()
        print(f"[Overlay] Transparency changed to: {mode_name}")

    def increase_font(self):
        cur = self.config_manager.get("font_size", 17)
        new_val = min(36, cur + 2)
        self.config_manager.set("font_size", new_val)
        self.apply_config_styles()
        print(f"[Overlay] Font size: {new_val} pt")

    def decrease_font(self):
        cur = self.config_manager.get("font_size", 17)
        new_val = max(12, cur - 2)
        self.config_manager.set("font_size", new_val)
        self.apply_config_styles()
        print(f"[Overlay] Font size: {new_val} pt")

    def toggle_always_on_top(self):
        cur = self.config_manager.get("always_on_top", True)
        new_val = not cur
        self.config_manager.set("always_on_top", new_val)
        flags = self.windowFlags()
        if new_val:
            flags |= Qt.WindowType.WindowStaysOnTopHint
        else:
            flags &= ~Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self.show()
        print(f"[Overlay] Always on Top: {'Enabled' if new_val else 'Disabled'}")

    def toggle_click_through(self):
        cur = self.config_manager.get("click_through", False)
        new_val = not cur
        self.config_manager.set("click_through", new_val)
        hwnd = int(self.winId())
        set_click_through(hwnd, new_val)
        self.clickthrough_changed.emit(new_val)
        print(f"[Overlay] Click-Through: {'Enabled' if new_val else 'Disabled'}")

    def center_on_screen(self):
        screen = QGuiApplication.primaryScreen().geometry()
        x = (screen.width() - self.width()) // 2
        y = max(20, screen.height() - self.height() - 70)
        self.move(x, y)
        self.config_manager.set("window_x", x, auto_save=False)
        self.config_manager.set("window_y", y, auto_save=True)
        print(f"[Overlay] Position reset to bottom center: x={x}, y={y}")

    # --- Resizing Jendela, Drag Bebas di Mana Saja & Context Menu ---

    def get_resize_edge(self, pos: QPoint) -> int:
        """Menentukan apakah posisi kursor mouse berada di tepi/sudut jendela untuk resize."""
        if self.is_pill_mode:
            return EDGE_NONE

        edge = EDGE_NONE
        w = self.width()
        h = self.height()
        margin = 14

        if pos.x() <= margin:
            edge |= EDGE_LEFT
        elif pos.x() >= w - margin:
            edge |= EDGE_RIGHT

        if pos.y() <= margin:
            edge |= EDGE_TOP
        elif pos.y() >= h - margin:
            edge |= EDGE_BOTTOM

        return edge

    def update_cursor_for_edge(self, edge: int):
        """Memperbarui bentuk kursor mouse saat mendekati tepi/sudut jendela."""
        if edge in (EDGE_TOP_LEFT, EDGE_BOTTOM_RIGHT):
            self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        elif edge in (EDGE_TOP_RIGHT, EDGE_BOTTOM_LEFT):
            self.setCursor(Qt.CursorShape.SizeBDiagCursor)
        elif edge in (EDGE_LEFT, EDGE_RIGHT):
            self.setCursor(Qt.CursorShape.SizeHorCursor)
        elif edge in (EDGE_TOP, EDGE_BOTTOM):
            self.setCursor(Qt.CursorShape.SizeVerCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)

    def eventFilter(self, watched, event):
        """Mencegat pergerakan mouse pada kontainer agar tepi jendela dapat di-resize dengan mulus."""
        if watched == self.container:
            if event.type() == QEvent.Type.MouseMove:
                if not self.resizing and not self.dragging:
                    win_pos = self.mapFromGlobal(event.globalPosition().toPoint())
                    edge = self.get_resize_edge(win_pos)
                    self.active_edge = edge
                    self.update_cursor_for_edge(edge)
                elif self.resizing or self.dragging:
                    self.mouseMoveEvent(event)
                    return True
            elif event.type() == QEvent.Type.MouseButtonPress:
                win_pos = self.mapFromGlobal(event.globalPosition().toPoint())
                edge = self.get_resize_edge(win_pos)
                if edge != EDGE_NONE:
                    self.resizing = True
                    self.resize_edge = edge
                    self.resize_start_pos = event.globalPosition().toPoint()
                    self.resize_start_geo = self.geometry()
                    return True
                elif event.button() == Qt.MouseButton.LeftButton:
                    self.dragging = True
                    self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                    return True
                elif event.button() == Qt.MouseButton.RightButton:
                    self.show_context_menu(event.globalPosition().toPoint())
                    return True
            elif event.type() == QEvent.Type.MouseButtonRelease:
                if self.resizing or self.dragging:
                    self.mouseReleaseEvent(event)
                    return True
            elif event.type() == QEvent.Type.MouseButtonDblClick:
                if event.button() == Qt.MouseButton.LeftButton:
                    self.toggle_pill_mode()
                    return True
            elif event.type() == QEvent.Type.Leave:
                if not self.resizing and not self.dragging:
                    self.active_edge = EDGE_NONE
                    self.setCursor(Qt.CursorShape.ArrowCursor)
        return super().eventFilter(watched, event)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            win_pos = event.position().toPoint()
            edge = self.get_resize_edge(win_pos)
            if edge != EDGE_NONE:
                self.resizing = True
                self.resize_edge = edge
                self.resize_start_pos = event.globalPosition().toPoint()
                self.resize_start_geo = self.geometry()
            else:
                self.dragging = True
                self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
        elif event.button() == Qt.MouseButton.RightButton:
            self.show_context_menu(event.globalPosition().toPoint())
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent):
        if self.resizing and self.resize_start_geo is not None:
            delta = event.globalPosition().toPoint() - self.resize_start_pos
            orig = self.resize_start_geo
            min_w = 340
            min_h = 70
            screen = QGuiApplication.primaryScreen().geometry()
            max_w = screen.width() - 30
            max_h = screen.height() - 30

            new_x = orig.x()
            new_y = orig.y()
            new_w = orig.width()
            new_h = orig.height()

            if self.resize_edge & EDGE_RIGHT:
                new_w = max(min_w, min(max_w, orig.width() + delta.x()))
            elif self.resize_edge & EDGE_LEFT:
                w_cand = orig.width() - delta.x()
                if min_w <= w_cand <= max_w:
                    new_w = w_cand
                    new_x = orig.x() + delta.x()

            if self.resize_edge & EDGE_BOTTOM:
                new_h = max(min_h, min(max_h, orig.height() + delta.y()))
            elif self.resize_edge & EDGE_TOP:
                h_cand = orig.height() - delta.y()
                if min_h <= h_cand <= max_h:
                    new_h = h_cand
                    new_y = orig.y() + delta.y()

            self.setGeometry(new_x, new_y, new_w, new_h)
            event.accept()
        elif self.dragging:
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()
        else:
            edge = self.get_resize_edge(event.position().toPoint())
            self.update_cursor_for_edge(edge)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            if self.dragging or self.resizing:
                self.dragging = False
                self.resizing = False
                self.resize_edge = EDGE_NONE
                self.setCursor(Qt.CursorShape.ArrowCursor)
                self.config_manager.set("window_x", self.x(), auto_save=False)
                self.config_manager.set("window_y", self.y(), auto_save=False)
                if not self.is_pill_mode:
                    self.config_manager.set("window_width", self.width(), auto_save=False)
                    self.config_manager.set("window_height", self.height(), auto_save=True)
            event.accept()

    def on_resize_finished(self):
        """Dipanggil ketika ukuran jendela selesai diubah via grip pojok."""
        if not self.is_pill_mode:
            self.config_manager.set("window_width", self.width(), auto_save=False)
            self.config_manager.set("window_height", self.height(), auto_save=True)
            print(f"[Overlay] Window size saved: {self.width()}x{self.height()}px")

    def reset_to_default_size(self):
        """Mereset ukuran overlay ke default 600x108 px."""
        if self.is_pill_mode:
            self.toggle_pill_mode()
        self.resize(600, 108)
        self.on_resize_finished()
        print("[Overlay] Window size reset to default (600x108 px)")

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        """Double-click on overlay toggles between Mini Pill and Full Widget."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.toggle_pill_mode()
            event.accept()

    def show_context_menu(self, pos: QPoint):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #1A1D27;
                color: #FFFFFF;
                border: 1px solid #2B3042;
                border-radius: 8px;
                padding: 6px;
                font-family: 'Segoe UI', sans-serif;
            }
            QMenu::item {
                padding: 6px 18px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #1ED760;
                color: #000000;
            }
            QMenu::separator {
                height: 1px;
                background-color: #2B3042;
                margin: 4px 6px;
            }
        """)

        # Option: Minimize / Pill Mode
        if self.is_pill_mode:
            act_pill = menu.addAction("📱 Expand to Full Widget")
        else:
            act_pill = menu.addAction("🟡 Minimize to Dynamic Island Mini-Pill")
        act_pill.triggered.connect(self.toggle_pill_mode)

        act_min_win = menu.addAction("🔽 Minimize Window to Tray")
        act_min_win.triggered.connect(self.showMinimized)

        menu.addSeparator()

        # Media Controls
        act_play = menu.addAction("⏯ Play / Pause")
        act_play.triggered.connect(lambda: self.play_pause_requested.emit())

        act_next = menu.addAction("⏭ Next Track")
        act_next.triggered.connect(lambda: self.next_requested.emit())

        act_prev = menu.addAction("⏮ Previous Track")
        act_prev.triggered.connect(lambda: self.prev_requested.emit())

        menu.addSeparator()

        act_mode = menu.addAction("⇄ Cycle Line Mode (1L ⇋ 2L ⇋ 3L)")
        act_mode.triggered.connect(self.cycle_display_lines)

        act_trans = menu.addAction("💧 Cycle Opacity (Transparent ⇋ Glass ⇋ Dark)")
        act_trans.triggered.connect(self.cycle_transparency)

        menu.addSeparator()

        act_top = menu.addAction("📌 Always on Top")
        act_top.setCheckable(True)
        act_top.setChecked(self.config_manager.get("always_on_top", True))
        act_top.triggered.connect(self.toggle_always_on_top)

        act_click = menu.addAction("🖱 Mouse Click-Through")
        act_click.setCheckable(True)
        act_click.setChecked(self.config_manager.get("click_through", False))
        act_click.triggered.connect(self.toggle_click_through)

        menu.addSeparator()

        act_font_up = menu.addAction("🔍 Increase Font [Ctrl+Alt+Up]")
        act_font_up.triggered.connect(self.increase_font)

        act_font_down = menu.addAction("🔍 Decrease Font [Ctrl+Alt+Down]")
        act_font_down.triggered.connect(self.decrease_font)

        act_reset_size = menu.addAction("📐 Reset Window Size (600 × 108 px)")
        act_reset_size.triggered.connect(self.reset_to_default_size)

        act_center = menu.addAction("🎯 Center on Bottom of Screen")
        act_center.triggered.connect(self.center_on_screen)

        menu.addSeparator()

        act_settings = menu.addAction("⚙ Full Settings...")
        act_settings.triggered.connect(lambda: self.settings_requested.emit())

        act_hide = menu.addAction("👁 Hide Overlay [Ctrl+Alt+L]")
        act_hide.triggered.connect(self.hide)

        act_exit = menu.addAction("🚪 Exit")
        act_exit.triggered.connect(lambda: sys.exit(0))

        menu.exec(pos)

    def apply_new_settings(self, new_config: dict):
        top = new_config.get("always_on_top", True)
        flags = self.windowFlags()
        if top:
            flags |= Qt.WindowType.WindowStaysOnTopHint
        else:
            flags &= ~Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)

        ct = new_config.get("click_through", False)
        hwnd = int(self.winId())
        set_click_through(hwnd, ct)

        if not self.is_pill_mode:
            w = new_config.get("window_width", self.width())
            h = new_config.get("window_height", self.height())
            if w != self.width() or h != self.height():
                self.resize(w, h)

        if len(self.line_labels) != new_config.get("display_lines", 2):
            self.rebuild_lyric_labels()
        else:
            self.apply_config_styles()

        self.show()
