"""
spotify_controller.py - Monitor Sesi Media Windows Global System Media Transport Controls (GSMTC).
Mendeteksi lagu yang sedang diputar di Spotify Desktop secara realtime, mengekstrak judul, artis,
durasi, posisi playback, thumbnail cover album, serta menyediakan kontrol media (Play/Pause/Skip).
"""

import asyncio
import time
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from PyQt6.QtCore import QThread, pyqtSignal
from winsdk.windows.media.control import (
    GlobalSystemMediaTransportControlsSessionManager as SMTCManager,
    GlobalSystemMediaTransportControlsSessionPlaybackStatus as PlaybackStatus
)
from winsdk.windows.storage.streams import Buffer, InputStreamOptions


class PlaybackInfo:
    """Menyimpan snapshot informasi pemutaran lagu saat ini."""

    def __init__(
        self,
        title: str = "",
        artist: str = "",
        album: str = "",
        duration: float = 0.0,
        position: float = 0.0,
        last_updated_time: Optional[datetime] = None,
        is_playing: bool = False,
        status_code: int = 0,
        app_id: str = "",
        thumbnail_bytes: Optional[bytes] = None
    ):
        self.title = title
        self.artist = artist
        self.album = album
        self.duration = duration
        self.base_position = position
        self.last_updated_time = last_updated_time
        self.is_playing = is_playing
        self.status_code = status_code
        self.app_id = app_id
        self.thumbnail_bytes = thumbnail_bytes

    def get_current_position(self) -> float:
        """
        Menghitung estimasi posisi playback terkini secara realtime
        dengan menambahkan selisih waktu sejak GSMTC terakhir diperbarui.
        """
        if not self.is_playing or not self.last_updated_time:
            return self.base_position

        try:
            now_utc = datetime.now(timezone.utc)
            elapsed = (now_utc - self.last_updated_time).total_seconds()
            curr = self.base_position + max(0.0, elapsed)
            if self.duration > 0:
                curr = min(curr, self.duration)
            return curr
        except Exception:
            return self.base_position

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "artist": self.artist,
            "album": self.album,
            "duration": self.duration,
            "position": self.get_current_position(),
            "is_playing": self.is_playing,
            "status_code": self.status_code,
            "app_id": self.app_id,
            "thumbnail_bytes": self.thumbnail_bytes
        }


class SpotifyController(QThread):
    """
    Worker QThread untuk memonitor Spotify secara background.
    Menggunakan Windows GSMTC API dan meng-emit sinyal ke antarmuka PyQt6.
    """

    # Sinyal saat lagu berganti (title/artist/duration/thumbnail)
    track_changed = pyqtSignal(dict)
    # Sinyal update posisi dan status playback secara periodik
    playback_updated = pyqtSignal(dict)
    # Sinyal status umum: "playing", "paused", "waiting_spotify"
    status_changed = pyqtSignal(str)

    def __init__(self, poll_interval_ms: int = 350):
        super().__init__()
        self.poll_interval = poll_interval_ms / 1000.0
        self._running = True
        self._loop = None
        self._current_session = None

        self.current_info = PlaybackInfo()
        self._last_title = ""
        self._last_artist = ""
        self._last_is_playing = False
        self._last_status_str = ""

    def stop(self):
        """Menghentikan thread monitor."""
        self._running = False
        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)
        self.wait(1500)

    def run(self):
        """Memulai loop event async untuk polling GSMTC."""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._async_monitor_loop())
        except Exception:
            pass
        finally:
            try:
                self._loop.close()
            except Exception:
                pass

    async def _async_monitor_loop(self):
        """Loop asinkron utama untuk membaca sesi media Windows."""
        mgr = None
        try:
            mgr = await SMTCManager.request_async()
        except Exception as e:
            print(f"[SpotifyController] Failed to initialize SMTC Manager: {e}")

        while self._running:
            try:
                if not mgr:
                    mgr = await SMTCManager.request_async()

                session = self._find_spotify_session(mgr)

                if session:
                    self._current_session = session
                    await self._process_session(session)
                else:
                    self._current_session = None
                    self._handle_no_session()

            except Exception:
                self._handle_no_session()

            await asyncio.sleep(self.poll_interval)

    def _find_spotify_session(self, mgr: SMTCManager):
        """Mencari sesi yang berasal dari Spotify Desktop atau Spotify Store App."""
        try:
            sessions = mgr.get_sessions()
            for s in sessions:
                app_id = s.source_app_user_model_id.lower()
                if "spotify" in app_id:
                    return s

            cur = mgr.get_current_session()
            if cur and "spotify" in cur.source_app_user_model_id.lower():
                return cur
        except Exception:
            pass
        return None

    async def _process_session(self, session):
        """Membaca detail lagu, timeline, status, dan thumbnail dari sesi Spotify."""
        try:
            # 1. Media Properties (Judul, Artis, Album)
            props = await session.try_get_media_properties_async()
            title = props.title if props else ""
            artist = props.artist if props else ""
            album = props.album_title if props else ""

            # 2. Thumbnail Cover Art (dari stream lokal Windows)
            thumb_bytes = None
            if props and props.thumbnail:
                try:
                    stream = await props.thumbnail.open_read_async()
                    buf = Buffer(stream.size)
                    await stream.read_async(buf, stream.size, InputStreamOptions.NONE)
                    thumb_bytes = bytes(buf)
                except Exception:
                    thumb_bytes = None

            # 3. Playback Info (Status Playing/Paused)
            info = session.get_playback_info()
            status_code = info.playback_status if info else 0
            is_playing = (status_code == 4 or status_code == PlaybackStatus.PLAYING)

            # 4. Timeline Properties (Posisi & Durasi)
            tl = session.get_timeline_properties()
            duration = tl.end_time.total_seconds() if tl and tl.end_time else 0.0
            position = tl.position.total_seconds() if tl and tl.position else 0.0
            last_updated = tl.last_updated_time if tl else None

            # Simpan ke objek PlaybackInfo
            self.current_info = PlaybackInfo(
                title=title,
                artist=artist,
                album=album,
                duration=duration,
                position=position,
                last_updated_time=last_updated,
                is_playing=is_playing,
                status_code=int(status_code),
                app_id=session.source_app_user_model_id,
                thumbnail_bytes=thumb_bytes
            )

            # Deteksi lagu berganti
            if (title != self._last_title) or (artist != self._last_artist):
                self._last_title = title
                self._last_artist = artist
                self.track_changed.emit(self.current_info.to_dict())

            # Deteksi perubahan status play/pause
            status_str = "playing" if is_playing else "paused"
            if status_str != self._last_status_str:
                self._last_status_str = status_str
                self.status_changed.emit(status_str)

            # Kirim update playback rutin
            self.playback_updated.emit(self.current_info.to_dict())

        except Exception:
            pass

    def _handle_no_session(self):
        """Dipanggil saat Spotify tidak berjalan atau tidak ada lagu aktif."""
        self.current_info = PlaybackInfo()
        if self._last_status_str != "waiting_spotify":
            self._last_status_str = "waiting_spotify"
            self._last_title = ""
            self._last_artist = ""
            self.status_changed.emit("waiting_spotify")

    # --- Media Playback Controls (Play/Pause, Skip, Prev) ---

    def toggle_play_pause(self):
        """Play / Pause playback Spotify."""
        if self._loop and self._current_session:
            asyncio.run_coroutine_threadsafe(self._async_toggle_play_pause(), self._loop)

    async def _async_toggle_play_pause(self):
        try:
            if self._current_session:
                await self._current_session.try_toggle_play_pause_async()
        except Exception as e:
            print(f"[Spotify] Play/Pause error: {e}")

    def skip_next(self):
        """Lompat ke lagu berikutnya di Spotify."""
        if self._loop and self._current_session:
            asyncio.run_coroutine_threadsafe(self._async_skip_next(), self._loop)

    async def _async_skip_next(self):
        try:
            if self._current_session:
                await self._current_session.try_skip_next_async()
        except Exception as e:
            print(f"[Spotify] Skip Next error: {e}")

    def skip_previous(self):
        """Kembali ke lagu sebelumnya di Spotify."""
        if self._loop and self._current_session:
            asyncio.run_coroutine_threadsafe(self._async_skip_previous(), self._loop)

    async def _async_skip_previous(self):
        try:
            if self._current_session:
                await self._current_session.try_skip_previous_async()
        except Exception as e:
            print(f"[Spotify] Skip Prev error: {e}")
