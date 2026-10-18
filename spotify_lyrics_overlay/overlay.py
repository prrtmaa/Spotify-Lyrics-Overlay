"""
overlay.py - Jendela Desktop Floating Lyrics Overlay (PyQt6).
Desain: Aurora Glass lyrics card with a top-center Dynamic Island clock.
Fitur:
- Desain murni tanpa outline/border abu-abu DWM Windows 11 (border: none, DWMWA_COLOR_NONE)
- Header controls (🔴 Hide, 🟢 Cycle lyric lines); click the empty header space to minimize
- Equalizer Audio Animatif (4-bar visualizer bergoyang mengikuti musik)
- Cover Album Squircle Artistik (dengan bayangan ambient halus)
- Mode Fleksibel: Full Lyrics Widget ⇋ Top-Center Clock Island
- Terpasang di tengah atas layar; ukuran dapat disesuaikan tanpa mengubah posisinya
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
from PyQt6.QtCore import (
    Qt, QPoint, QRectF, QTimer, pyqtSignal, QRect, QEvent,
    QPropertyAnimation, QEasingCurve, QDateTime, QLocale
)
from PyQt6.QtGui import (
    QColor, QFont, QCursor, QAction, QPainter, QBrush,
    QLinearGradient, QRadialGradient, QPen, QMouseEvent, QIcon, QPixmap, QPainterPath,
    QFontMetrics,
    QGuiApplication
)

from settings import (
    ConfigManager, SettingsDialog, get_asset_path, MIN_FONT_SIZE, MAX_FONT_SIZE,
)
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


class MochiIndicator(QWidget):
    """A softly wobbling mint mochi accent for the compact island."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(16, 16)
        self.phase = 0.0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.advance)

    def showEvent(self, event):
        super().showEvent(event)
        self.timer.start(40)

    def hideEvent(self, event):
        self.timer.stop()
        super().hideEvent(event)

    def advance(self):
        self.phase = (self.phase + 0.075) % (math.pi * 2)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        pulse = (math.sin(self.phase) + 1.0) * 0.5
        center_x = self.width() / 2
        center_y = self.height() / 2
        radius_x = 6.4 + pulse * 0.7
        radius_y = 6.0 + (1.0 - pulse) * 0.8

        glow = QRadialGradient(center_x, center_y, 11)
        glow.setColorAt(0, QColor(100, 244, 164, 105))
        glow.setColorAt(1, QColor(100, 244, 164, 0))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(glow))
        painter.drawEllipse(QRectF(0, 0, self.width(), self.height()))

        wobble = math.sin(self.phase * 1.7) * 1.1
        blob = QPainterPath()
        blob.moveTo(center_x, center_y - radius_y)
        blob.cubicTo(
            center_x + radius_x + wobble, center_y - radius_y,
            center_x + radius_x + wobble, center_y + radius_y * 0.55,
            center_x + wobble * 0.35, center_y + radius_y
        )
        blob.cubicTo(
            center_x - radius_x * 0.6, center_y + radius_y + wobble,
            center_x - radius_x - wobble * 0.35, center_y + radius_y * 0.4,
            center_x - radius_x, center_y - wobble * 0.25
        )
        blob.cubicTo(
            center_x - radius_x * 0.8, center_y - radius_y - wobble * 0.3,
            center_x - radius_x * 0.2, center_y - radius_y * 0.85,
            center_x, center_y - radius_y
        )
        blob.closeSubpath()

        body = QLinearGradient(
            center_x - radius_x, center_y - radius_y,
            center_x + radius_x, center_y + radius_y
        )
        body.setColorAt(0, QColor("#C7FFE0"))
        body.setColorAt(0.48, QColor("#77EBA9"))
        body.setColorAt(1, QColor("#38C879"))
        painter.setBrush(QBrush(body))
        painter.drawPath(blob)

        highlight = QRadialGradient(
            center_x - 2.0, center_y - 3.0, 4.5
        )
        highlight.setColorAt(0, QColor(255, 255, 255, 125))
        highlight.setColorAt(1, QColor(255, 255, 255, 0))
        painter.setBrush(QBrush(highlight))
        painter.drawEllipse(QRectF(center_x - 6, center_y - 7, 9, 8))
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


class LyricLineLabel(QLabel):
    """Label lirik dengan drop shadow berkualitas tinggi agar terbaca jelas."""

    def __init__(self, role: str = "active", parent=None):
        super().__init__(parent)
        self.role = role
        self.setWordWrap(True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(4)
        shadow.setColor(QColor(0, 0, 0, 165))
        shadow.setOffset(0, 1)
        self.setGraphicsEffect(shadow)


class TrackInfoLabel(QLabel):
    """Keep long track metadata on one clean line without clipping."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.full_text = ""
        self.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)

    def set_track_info(self, text: str, tooltip: Optional[str] = None):
        self.full_text = text
        self.setToolTip(tooltip or text)
        self.update_elided_text()

    def setText(self, text: str):
        self.full_text = ""
        self.setToolTip(text)
        super().setText(text)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_elided_text()

    def update_elided_text(self):
        if self.full_text:
            QLabel.setText(self, self.fontMetrics().elidedText(
                self.full_text, Qt.TextElideMode.ElideRight, max(0, self.width())
            ))


class OverlayWindow(QWidget):
    """
    Aurora Glass lyrics card with borderless desktop rendering, playback status,
    album artwork, a live equalizer, and a top-center date and time capsule.
    """
    settings_requested = pyqtSignal()
    clickthrough_changed = pyqtSignal(bool)
    pill_mode_changed = pyqtSignal(bool)
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

        # Mode Tampilan: True = compact clock island, False = full lyrics widget
        self.is_pill_mode = False
        self._expanded_geometry = QRect()
        self._pill_animation = QPropertyAnimation(self, b"geometry", self)
        self._pill_animation.setDuration(620)
        self._pill_animation.setEasingCurve(QEasingCurve.Type.OutCubic)

        # Data lirik & pekerja fetch
        self.lyrics_data: Optional[LyricsData] = None
        self.lyrics_worker: Optional[LyricsFetchWorker] = None
        self.last_active_index = -99

        self._header_click_start: Optional[QPoint] = None
        self._pill_click_start: Optional[QPoint] = None

        # State edge resizing
        self.resizing = False
        self.resize_edge = EDGE_NONE
        self.active_edge = EDGE_NONE
        self.resize_start_pos = QPoint()
        self.resize_start_geo: Optional[QRect] = None

        # State hover
        self.is_hovered = False

        self.init_window_flags()
        self._expanded_geometry = self.geometry()
        self.init_ui()
        self.apply_config_styles()
        self.update_minimum_overlay_height()
        self._expanded_geometry = self.geometry()

        # Aktifkan pelacakan mouse agar kursor otomatis berubah di tepi jendela
        self.setMouseTracking(True)
        self.container.setMouseTracking(True)
        self.container.installEventFilter(self)
        self.compact_widget.setMouseTracking(True)
        self.compact_widget.installEventFilter(self)
        self.top_row_frame.setMouseTracking(True)
        self.top_row_frame.installEventFilter(self)

        # Pesan inisialisasi awal
        self.set_single_message("Waiting for Spotify...", "Buka Spotify Desktop dan putar lagu")

        # Timer sinkronisasi lirik realtime (50ms)
        self.sync_timer = QTimer(self)
        self.sync_timer.timeout.connect(self.sync_lyrics_tick)
        self.sync_timer.start(50)

        self.datetime_timer = QTimer(self)
        self.datetime_timer.timeout.connect(self.update_compact_datetime)
        self.datetime_timer.start(1000)

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

        x = screen.left() + (screen.width() - w) // 2
        self.setGeometry(x, screen.top(), w, h)
        self.setMinimumSize(260, 48)

    def showEvent(self, event):
        super().showEvent(event)
        hwnd = int(self.winId())
        remove_dwm_border(hwnd)
        set_click_through(
            hwnd,
            self.config_manager.get("click_through", False) and not self.is_pill_mode
        )

    def init_ui(self):
        """Menyusun antarmuka macOS Now Playing & Dynamic Island Widget."""
        self.root_layout = QVBoxLayout(self)
        self.root_layout.setContentsMargins(10, 0, 10, 10)

        # Container Utama (Kartu Kaca Melengkung Bebas Border)
        self.container = QFrame(self)
        self.container.setObjectName("macOverlayContainer")

        self.root_layout.addWidget(self.container)

        # Layout horizontal utama
        self.main_hlayout = QHBoxLayout(self.container)
        self.main_hlayout.setContentsMargins(14, 10, 16, 10)
        self.main_hlayout.setSpacing(12)

        self.compact_widget = QFrame(self.container)
        self.compact_widget.setObjectName("clockIsland")
        self.compact_widget.setCursor(Qt.CursorShape.PointingHandCursor)
        self.compact_widget.setToolTip("Click to restore lyrics • Ctrl+Alt+I to toggle")
        self.compact_widget.setStyleSheet("""
            QFrame#clockIsland {
                background: transparent;
                border: none;
            }
        """)
        compact_layout = QHBoxLayout(self.compact_widget)
        compact_layout.setContentsMargins(4, 0, 4, 0)
        compact_layout.setSpacing(4)

        self.compact_indicator = MochiIndicator(self.compact_widget)
        self.compact_indicator.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        compact_layout.addWidget(self.compact_indicator)

        self.compact_date = QLabel()
        date_font = QFont("Segoe UI")
        date_font.setPixelSize(9)
        date_font.setWeight(QFont.Weight.DemiBold)
        self.compact_date.setFont(date_font)
        self.compact_date.setStyleSheet(
            "color: rgba(226, 232, 242, 0.74);"
        )
        self.compact_date.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        compact_layout.addWidget(self.compact_date)

        self.compact_separator = QFrame()
        self.compact_separator.setFixedSize(1, 14)
        self.compact_separator.setStyleSheet("background-color: rgba(255, 255, 255, 0.20);")
        compact_layout.addWidget(self.compact_separator)

        self.compact_time = QLabel()
        time_font = QFont("Segoe UI Variable Display", 11, QFont.Weight.Bold)
        time_font.setPixelSize(11)
        self.compact_time.setFont(time_font)
        self.compact_time.setStyleSheet("""
            QLabel {
                color: #F7F9FC;
            }
        """)
        self.compact_time.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        compact_layout.addWidget(self.compact_time)
        self.main_hlayout.addWidget(self.compact_widget, 1)
        self.compact_widget.hide()
        self.update_compact_datetime()

        # --- COVER ALBUM SQUIRCLE ---
        self.cover_container = QWidget()
        self.cover_vlayout = QVBoxLayout(self.cover_container)
        self.cover_vlayout.setContentsMargins(0, 0, 0, 0)
        self.cover_vlayout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.lbl_cover = QLabel()
        self.lbl_cover.setFixedSize(58, 58)
        self.lbl_cover.setPixmap(create_default_cover(58))

        cover_shadow = QGraphicsDropShadowEffect(self.lbl_cover)
        cover_shadow.setBlurRadius(10)
        cover_shadow.setColor(QColor(0, 0, 0, 125))
        cover_shadow.setOffset(0, 2)
        self.lbl_cover.setGraphicsEffect(cover_shadow)

        self.cover_vlayout.addWidget(self.lbl_cover)
        self.main_hlayout.addWidget(self.cover_container)

        # --- KONTEN KANAN ---
        self.content_widget = QWidget(self.container)
        self.right_layout = QVBoxLayout(self.content_widget)
        self.right_layout.setContentsMargins(0, 0, 0, 0)
        self.right_layout.setSpacing(5)

        # 1. Header controls, track information, equalizer, and playback controls
        self.top_row_frame = QFrame()
        self.top_hlayout = QHBoxLayout(self.top_row_frame)
        self.top_hlayout.setContentsMargins(0, 0, 0, 0)
        self.top_hlayout.setSpacing(4)
        self.top_hlayout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        self.top_row_frame.setMinimumHeight(36)

        self.track_info_widget = QWidget(self.top_row_frame)
        self.track_info_widget.setMinimumWidth(0)
        self.track_info_widget.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        self.track_info_widget.setMinimumHeight(32)
        self.track_info_layout = QVBoxLayout(self.track_info_widget)
        self.track_info_layout.setContentsMargins(2, 0, 2, 0)
        self.track_info_layout.setSpacing(0)

        self.lbl_song_info = TrackInfoLabel()
        self.lbl_song_info.setText("Spotify Lyrics")
        self.lbl_song_info.setStyleSheet(
            "color: #F3F6F8; font-size: 9pt; font-weight: 650;"
        )
        self.lbl_song_info.setMinimumWidth(0)
        self.lbl_song_info.setMaximumHeight(19)
        self.track_info_layout.addWidget(self.lbl_song_info)

        self.lbl_artist_info = TrackInfoLabel()
        self.lbl_artist_info.setText("Waiting for playback")
        self.lbl_artist_info.setStyleSheet(
            "color: rgba(220, 229, 236, 0.58); font-size: 8pt; font-weight: 450;"
        )
        self.lbl_artist_info.setMinimumWidth(0)
        self.lbl_artist_info.setMaximumHeight(16)
        self.track_info_layout.addWidget(self.lbl_artist_info)
        self.top_hlayout.addWidget(self.track_info_widget, 1)

        self.status_dot = QLabel("●")
        self.status_dot.setFixedWidth(8)
        self.status_dot.setToolTip("Playback: Ready")
        self.status_dot.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_dot.setStyleSheet("color: #87919D; font-size: 7px;")
        self.top_hlayout.addWidget(self.status_dot)

        # Equalizer Animatif (Audio Visualizer)
        self.animated_eq = AnimatedEqualizer()
        self.animated_eq.setToolTip("Audio activity")
        self.top_hlayout.addWidget(self.animated_eq)

        # Compact glass media controls (⏮ ⏯ ⏭)
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

        self.media_group = QFrame(self.top_row_frame)
        self.media_group.setObjectName("mediaControlGroup")
        media_layout = QHBoxLayout(self.media_group)
        media_layout.setContentsMargins(2, 2, 2, 2)
        media_layout.setSpacing(1)
        self.media_btns = [self.btn_prev, self.btn_play, self.btn_next]
        for b in self.media_btns:
            b.setFixedSize(20, 20)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            media_layout.addWidget(b)
        self.top_hlayout.addWidget(self.media_group)

        self.tool_sep = QFrame(self.top_row_frame)
        self.tool_sep.setFixedSize(1, 14)
        self.tool_sep.setStyleSheet("background-color: rgba(255, 255, 255, 0.12);")
        self.top_hlayout.addWidget(self.tool_sep)

        # Tombol Alat Tambahan (Transparansi, Pengaturan)
        self.btn_trans = QPushButton("◐")
        self.btn_trans.setToolTip("Cycle Background Opacity (0% ⇋ 20% ⇋ 40% ⇋ 60%) [Ctrl+Alt+T]")
        self.btn_trans.setProperty("class", "toolBtn")
        self.btn_trans.clicked.connect(self.cycle_transparency)

        self.btn_settings = QPushButton("⋯")
        self.btn_settings.setToolTip("Full Settings")
        self.btn_settings.setProperty("class", "toolBtn")
        self.btn_settings.clicked.connect(lambda: self.settings_requested.emit())

        self.tool_group = QFrame(self.top_row_frame)
        self.tool_group.setObjectName("utilityControlGroup")
        tool_layout = QHBoxLayout(self.tool_group)
        tool_layout.setContentsMargins(1, 1, 1, 1)
        tool_layout.setSpacing(1)
        self.tool_btns = [self.btn_trans, self.btn_settings]
        for b in self.tool_btns:
            b.setFixedSize(18, 18)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            tool_layout.addWidget(b)
        self.top_hlayout.addWidget(self.tool_group)

        self.right_layout.addWidget(self.top_row_frame)

        # 2. Area Baris Lirik Realtime
        self.lyrics_container = QWidget()
        self.lyrics_layout = QVBoxLayout(self.lyrics_container)
        self.lyrics_layout.setContentsMargins(0, 1, 0, 1)
        self.lyrics_layout.setSpacing(3)
        self.lyrics_container.setMinimumHeight(0)

        self.line_labels: List[LyricLineLabel] = []
        self.rebuild_lyric_labels()

        self.right_layout.addWidget(self.lyrics_container, 1)

        # 3. Baris Bawah: Waktu Berjalan, Progress Bar Playback, Durasi & Resize Grip
        self.progress_container = QWidget()
        self.bottom_row = QHBoxLayout(self.progress_container)
        self.bottom_row.setContentsMargins(1, 2, 1, 0)
        self.bottom_row.setSpacing(8)

        self.lbl_time_cur = QLabel("0:00")
        self.lbl_time_cur.setFixedWidth(34)
        self.lbl_time_cur.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.lbl_time_cur.setStyleSheet(
            "color: rgba(226, 232, 242, 0.58); font-size: 9px; font-weight: 600;"
        )
        self.bottom_row.addWidget(self.lbl_time_cur)

        # Slim playback progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(4)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setRange(0, 1000)
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: rgba(255, 255, 255, 0.12);
                border: none;
                border-radius: 2px;
            }
            QProgressBar::chunk {
                background-color: #1ED760;
                border-radius: 2px;
            }
        """)
        self.bottom_row.addWidget(self.progress_bar, 1)

        self.lbl_time_total = QLabel("0:00")
        self.lbl_time_total.setFixedWidth(34)
        self.lbl_time_total.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.lbl_time_total.setStyleSheet(
            "color: rgba(226, 232, 242, 0.58); font-size: 9px; font-weight: 600;"
        )
        self.bottom_row.addWidget(self.lbl_time_total)

        self.resize_grip = CornerResizeGrip(self, self.progress_container)
        self.bottom_row.addWidget(self.resize_grip)

        self.right_layout.addWidget(self.progress_container)
        self.main_hlayout.addWidget(self.content_widget, 1)
        self.top_row_frame.hide()

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
        font_size = max(MIN_FONT_SIZE, min(MAX_FONT_SIZE, self.config_manager.get("font_size", 17)))
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
        if hasattr(self, "compact_widget"):
            self.compact_widget.setVisible(self.is_pill_mode)
        if hasattr(self, "top_row_frame"):
            self.top_row_frame.setVisible(not self.is_pill_mode)
        if hasattr(self, "content_widget"):
            self.content_widget.setVisible(not self.is_pill_mode)

        align_flag = Qt.AlignmentFlag.AlignCenter if text_align == "center" else (
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )

        # Gaya Kartu Kaca macOS:
        # border: none; TOTAL tanpa garis abu-abu DWM atau outline kotak
        if self.is_pill_mode:
            container_style = """
                QFrame#macOverlayContainer {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                        stop:0 rgba(8, 11, 15, 0.99),
                        stop:0.48 rgba(17, 21, 28, 0.99),
                        stop:1 rgba(8, 11, 15, 0.99));
                    border: 1px solid rgba(217, 237, 225, 0.18);
                    border-top-left-radius: 0px;
                    border-top-right-radius: 0px;
                    border-bottom-left-radius: 20px;
                    border-bottom-right-radius: 20px;
                }
            """
        elif bg_opacity <= 0.05:
            # Mode Pure Transparent
            if self.is_hovered or self.is_pill_mode:
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
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                        stop:0 rgba(31, 38, 48, {alpha_top:.2f}),
                        stop:0.52 rgba(19, 23, 31, {alpha_bot:.2f}),
                        stop:1 rgba(15, 20, 27, {alpha_bot:.2f}));
                    border: 1px solid rgba(225, 240, 232, 0.09);
                    border-radius: 24px;
                }}
            """

        # Aurora Glass media and utility button styling
        button_styles = """
            QFrame#mediaControlGroup {
                background-color: rgba(255, 255, 255, 0.045);
                border: 1px solid rgba(255, 255, 255, 0.065);
                border-radius: 8px;
            }
            QFrame#utilityControlGroup {
                background: transparent;
                border: none;
            }
            QPushButton.mediaBtn {
                font-family: 'Segoe UI Symbol', 'Segoe UI', sans-serif;
                background-color: transparent;
                color: rgba(235, 242, 247, 0.76);
                border: none;
                border-radius: 6px;
                font-size: 10px;
                font-weight: bold;
            }
            QPushButton.mediaBtn:hover {
                background-color: rgba(114, 227, 160, 0.20);
                color: #A4F4C0;
            }
            QPushButton.toolBtn {
                background-color: transparent;
                color: rgba(220, 231, 225, 0.62);
                border: none;
                border-radius: 6px;
                font-size: 9px;
                font-weight: 600;
            }
            QPushButton.toolBtn:hover {
                background-color: rgba(114, 227, 160, 0.16);
                color: #FFFFFF;
            }
        """

        self.container.setStyleSheet(container_style + button_styles)

        # Style teks lirik aktif & sekunder
        sec_font_size = max(MIN_FONT_SIZE, int(font_size * 0.76))
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
                        color: rgba(232, 238, 244, 0.58);
                        font-family: '{font_family}', sans-serif;
                        font-size: {sec_font_size}pt;
                        font-weight: 500;
                        padding: 0px;
                    }}
                """)
            lbl.setMinimumHeight(QFontMetrics(lbl.font()).height())

    # --- Animated Dynamic Island Clock Mode ---

    def toggle_pill_mode(self):
        """Animate between the full lyrics widget and the top-center clock island."""
        animation_was_running = (
            self._pill_animation.state() == QPropertyAnimation.State.Running
        )
        self._pill_animation.stop()
        entering_pill_mode = not self.is_pill_mode
        if entering_pill_mode and not animation_was_running:
            self._expanded_geometry = QRect(self.geometry())
        self.is_pill_mode = entering_pill_mode
        self.pill_mode_changed.emit(self.is_pill_mode)

        if self.is_pill_mode:
            self.setMinimumSize(140, 40)
            self.root_layout.setContentsMargins(0, 0, 0, 0)
            self.main_hlayout.setContentsMargins(0, 0, 0, 0)
            self.main_hlayout.setSpacing(0)
            screen = QGuiApplication.primaryScreen().geometry()
            island_width = min(
                max(self.compact_widget.sizeHint().width(), 140),
                screen.width()
            )
            island_height = 40
            island_position = QPoint(
                screen.left() + (screen.width() - island_width) // 2,
                screen.top()
            )
            target_geometry = QRect(
                island_position.x(), island_position.y(), island_width, island_height
            )
            print("[Overlay] Switched to top-center clock island mode")
        else:
            self.setMinimumSize(260, 48)
            self.root_layout.setContentsMargins(10, 0, 10, 10)
            self.main_hlayout.setContentsMargins(14, 10, 16, 10)
            self.main_hlayout.setSpacing(14)
            target_geometry = QRect(self._expanded_geometry)
            print("[Overlay] Switched to Full Lyrics Widget Mode")

        self.update_compact_datetime()
        self.apply_config_styles()
        set_click_through(
            int(self.winId()),
            self.config_manager.get("click_through", False) and not self.is_pill_mode
        )

        self._pill_animation.setStartValue(self.geometry())
        self._pill_animation.setEndValue(target_geometry)
        self._pill_animation.start()

    def update_compact_datetime(self):
        """Update the compact island clock with English date names and 24-hour time."""
        if hasattr(self, "compact_date"):
            locale = QLocale(QLocale.Language.English, QLocale.Country.UnitedStates)
            now = QDateTime.currentDateTime()
            date_text = locale.toString(now, "ddd, d MMM yy")
            time_text = locale.toString(now, "HH:mm")
            self.compact_date.setText(date_text)
            self.compact_date.setFixedWidth(self.compact_date.fontMetrics().horizontalAdvance(date_text))
            self.compact_time.setText(time_text)
            self.compact_time.setFixedWidth(self.compact_time.fontMetrics().horizontalAdvance(time_text))

    def update_expanded_geometry(self):
        """Remember the full widget geometry for the next restore."""
        if not self.is_pill_mode:
            self._expanded_geometry = self.geometry()

    def update_minimum_overlay_height(self):
        """Keep configured lyric lines fully visible at the selected font size."""
        if self.is_pill_mode:
            return

        font_family = self.config_manager.get("font_family", "Segoe UI")
        font_size = max(MIN_FONT_SIZE, min(MAX_FONT_SIZE, self.config_manager.get("font_size", 17)))
        line_count = self.config_manager.get("display_lines", 2)
        active_font = QFont(font_family)
        active_font.setPointSize(font_size)
        secondary_font = QFont(font_family)
        secondary_font.setPointSize(max(MIN_FONT_SIZE, int(font_size * 0.76)))

        active_height = QFontMetrics(active_font).height()
        secondary_height = QFontMetrics(secondary_font).height()
        required_height = (
            104
            + active_height
            + max(0, line_count - 1) * (secondary_height + 3)
        )
        screen = QGuiApplication.primaryScreen().availableGeometry()
        minimum_height = min(required_height, screen.height() - 30)
        self.setMinimumHeight(minimum_height)

        if self.height() < minimum_height:
            width = self.width()
            self.resize(width, minimum_height)
            self.center_on_screen()

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
        if hasattr(self, "tool_group"):
            self.tool_group.setVisible(visible)
        if hasattr(self, "tool_sep"):
            self.tool_sep.setVisible(visible)
        if hasattr(self, "resize_grip") and not self.is_pill_mode:
            self.resize_grip.setVisible(visible)

    def set_playback_badge(self, status: str):
        badge_colors = {
            "playing": ("PLAYING", "#79E8A5"),
            "paused": ("PAUSED", "#F3C970"),
            "waiting_spotify": ("READY", "#9AA5B1")
        }
        label, color = badge_colors.get(status, ("READY", "#9AA5B1"))
        self.status_dot.setToolTip(f"Playback: {label.title()}")
        self.status_dot.setStyleSheet(f"color: {color}; font-size: 7px;")

    # --- Penanganan Peristiwa Spotify & Lirik ---

    def handle_status_changed(self, status: str):
        self.app_status = status
        self.set_playback_badge(status)
        if status == "waiting_spotify":
            self.lbl_song_info.setText("Spotify Lyrics Overlay")
            self.lbl_artist_info.setText("Waiting for playback")
            self.set_single_message("Waiting for Spotify...", "Play a song in Spotify Desktop")
            self.lbl_cover.setPixmap(create_default_cover(58))
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
        self.set_playback_badge("playing")
        self.btn_play.setText("⏸")
        self.animated_eq.set_active(True)

        self.lbl_song_info.set_track_info(title, f"{title} · {artist}" if artist else title)
        self.lbl_artist_info.set_track_info(artist or "Unknown artist", artist or "Unknown artist")
        self.lbl_time_total.setText(format_time(duration))
        self.set_single_message(title, f"Searching lyrics: {artist}")

        # Render Thumbnail Album Art
        cover_set = False
        if thumb_bytes:
            pix = QPixmap()
            if pix.loadFromData(thumb_bytes):
                self.lbl_cover.setPixmap(get_rounded_pixmap(pix, 12.0, 58))
                cover_set = True

        if not cover_set:
            self.lbl_cover.setPixmap(create_default_cover(58))

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
                self.lbl_cover.setPixmap(get_rounded_pixmap(pix, 12.0, 58))

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
        self.update_minimum_overlay_height()
        self.resize(self.width(), target_h)
        self.center_on_screen()
        self.update_expanded_geometry()
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
        new_val = min(MAX_FONT_SIZE, max(MIN_FONT_SIZE, cur) + 2)
        self.config_manager.set("font_size", new_val)
        self.apply_config_styles()
        self.update_minimum_overlay_height()
        print(f"[Overlay] Font size: {new_val} pt")

    def decrease_font(self):
        cur = self.config_manager.get("font_size", 17)
        new_val = max(MIN_FONT_SIZE, min(MAX_FONT_SIZE, cur) - 2)
        self.config_manager.set("font_size", new_val)
        self.apply_config_styles()
        self.update_minimum_overlay_height()
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
        set_click_through(hwnd, new_val and not self.is_pill_mode)
        self.clickthrough_changed.emit(new_val)
        print(f"[Overlay] Click-Through: {'Enabled' if new_val else 'Disabled'}")

    def center_on_screen(self):
        screen = QGuiApplication.primaryScreen().geometry()
        x = screen.left() + (screen.width() - self.width()) // 2
        self.setGeometry(x, screen.top(), self.width(), self.height())
        self.update_expanded_geometry()
        print(f"[Overlay] Overlay pinned to top center: x={x}, y={screen.top()}")

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
        if watched is self.compact_widget:
            if event.type() == QEvent.Type.MouseButtonPress:
                if event.button() == Qt.MouseButton.LeftButton:
                    self._pill_click_start = event.globalPosition().toPoint()
                    return True
                if event.button() == Qt.MouseButton.RightButton:
                    self.show_context_menu(event.globalPosition().toPoint())
                    return True
            elif event.type() == QEvent.Type.MouseButtonRelease:
                if event.button() == Qt.MouseButton.LeftButton and self._pill_click_start is not None:
                    start = self._pill_click_start
                    self._pill_click_start = None
                    if (event.globalPosition().toPoint() - start).manhattanLength() <= 8:
                        self.toggle_pill_mode()
                    return True

        if watched is self.top_row_frame and not self.is_pill_mode:
            if event.type() == QEvent.Type.MouseButtonPress:
                if event.button() == Qt.MouseButton.LeftButton:
                    self._header_click_start = event.globalPosition().toPoint()
                    return True
            elif event.type() == QEvent.Type.MouseButtonRelease:
                if event.button() == Qt.MouseButton.LeftButton and self._header_click_start:
                    start = self._header_click_start
                    self._header_click_start = None
                    if (event.globalPosition().toPoint() - start).manhattanLength() <= 8:
                        self.toggle_pill_mode()
                    return True

        if watched is self.container:
            if event.type() == QEvent.Type.MouseMove:
                if not self.resizing:
                    win_pos = self.mapFromGlobal(event.globalPosition().toPoint())
                    edge = self.get_resize_edge(win_pos)
                    self.active_edge = edge
                    self.update_cursor_for_edge(edge)
                elif self.resizing:
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
                elif event.button() == Qt.MouseButton.RightButton:
                    self.show_context_menu(event.globalPosition().toPoint())
                    return True
            elif event.type() == QEvent.Type.MouseButtonRelease:
                if self.resizing:
                    self.mouseReleaseEvent(event)
                    return True
            elif event.type() == QEvent.Type.Leave:
                if not self.resizing:
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
                event.accept()
                return
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

            new_w = orig.width()
            new_h = orig.height()

            if self.resize_edge & EDGE_RIGHT:
                new_w = max(min_w, min(max_w, orig.width() + delta.x()))
            elif self.resize_edge & EDGE_LEFT:
                w_cand = orig.width() - delta.x()
                if min_w <= w_cand <= max_w:
                    new_w = w_cand

            if self.resize_edge & EDGE_BOTTOM:
                new_h = max(min_h, min(max_h, orig.height() + delta.y()))
            elif self.resize_edge & EDGE_TOP:
                h_cand = orig.height() - delta.y()
                if min_h <= h_cand <= max_h:
                    new_h = h_cand

            self.setGeometry(
                screen.left() + (screen.width() - new_w) // 2,
                screen.top(),
                new_w,
                new_h
            )
            event.accept()
        else:
            edge = self.get_resize_edge(event.position().toPoint())
            self.update_cursor_for_edge(edge)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            if self.resizing:
                self.resizing = False
                self.resize_edge = EDGE_NONE
                self.setCursor(Qt.CursorShape.ArrowCursor)
                if not self.is_pill_mode:
                    self.update_expanded_geometry()
                    self.config_manager.set("window_width", self.width(), auto_save=False)
                    self.config_manager.set("window_height", self.height(), auto_save=True)
            event.accept()

    def on_resize_finished(self):
        """Dipanggil ketika ukuran jendela selesai diubah via grip pojok."""
        if not self.is_pill_mode:
            self.center_on_screen()
            self.config_manager.set("window_width", self.width(), auto_save=False)
            self.config_manager.set("window_height", self.height(), auto_save=True)
            self.update_expanded_geometry()
            print(f"[Overlay] Window size saved: {self.width()}x{self.height()}px")

    def reset_to_default_size(self):
        """Mereset ukuran overlay ke default 600x108 px."""
        if self.is_pill_mode:
            self.toggle_pill_mode()
            self._pill_animation.stop()
            self.setGeometry(self._expanded_geometry)
        self.resize(600, 108)
        self.on_resize_finished()
        print("[Overlay] Window size reset to default (600x108 px)")

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
            act_pill = menu.addAction("Minimize to Dynamic Island Clock [Ctrl+Alt+I]")
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

        act_center = menu.addAction("🎯 Recenter at Top")
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
        set_click_through(hwnd, ct and not self.is_pill_mode)

        if not self.is_pill_mode:
            w = new_config.get("window_width", self.width())
            h = new_config.get("window_height", self.height())
            if w != self.width() or h != self.height():
                self.resize(w, h)
                self.center_on_screen()
            self.update_expanded_geometry()

        if len(self.line_labels) != new_config.get("display_lines", 2):
            self.rebuild_lyric_labels()
        else:
            self.apply_config_styles()

        self.update_minimum_overlay_height()
        self.show()
