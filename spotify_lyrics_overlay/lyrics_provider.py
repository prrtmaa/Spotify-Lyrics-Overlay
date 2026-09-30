"""
lyrics_provider.py - Penyedia Lirik Realtime dari LRCLIB API.
Mendukung sinkronisasi LRC, fallback pencarian fleksibel, pembersihan judul lagu Spotify,
serta caching lokal untuk penghematan bandwidth dan pemuatan instan.
"""

import os
import re
import json
import hashlib
import requests
from bisect import bisect_right
from typing import List, Tuple, Optional
from PyQt6.QtCore import QThread, pyqtSignal
from settings import get_app_dir

CACHE_DIR = os.path.join(get_app_dir(), "cache")
try:
    os.makedirs(CACHE_DIR, exist_ok=True)
except Exception:
    pass

LRCLIB_GET_URL = "https://lrclib.net/api/get"
LRCLIB_SEARCH_URL = "https://lrclib.net/api/search"
USER_AGENT = "SpotifyLyricsOverlay/1.0 (Windows; PyQt6 desktop app; +https://github.com/spotify-lyrics-overlay)"


def clean_track_title(raw_title: str) -> str:
    """
    Membersihkan judul lagu Spotify dari embel-embel seperti:
    ' - Remastered', ' (feat. ...)', ' - Bonus Track', ' (Radio Edit)', dll.
    """
    if not raw_title:
        return ""

    title = raw_title.strip()

    # Hapus keterangan dalam kurung/tanda kurung siku yang umum
    patterns = [
        r"\s*[\(\[](?:feat|ft|with|bonus|live|remaster|radio|edit|mono|stereo|acoustic|version|deluxe|from|ost|original).*?[\)\]]",
        r"\s*-\s*(?:feat|ft|with|bonus|live|remaster|radio|edit|mono|stereo|acoustic|version|deluxe|single|original).*?$",
        r"\s*-\s*\d{4}\s*remaster.*?$",
    ]

    for pat in patterns:
        title = re.sub(pat, "", title, flags=re.IGNORECASE)

    return title.strip() or raw_title.strip()


def parse_lrc(lrc_text: str) -> List[Tuple[float, str]]:
    """
    Mengurai format lirik LRC menjadi daftar (timestamp_detik, teks_lirik).
    Mendukung multiple timestamp per baris dan format milidetik [mm:ss.xx].
    """
    if not lrc_text:
        return []

    lines = []
    pattern = re.compile(r"\[(\d{1,2}):(\d{1,2}(?:\.\d+)?)\]")

    for raw_line in lrc_text.splitlines():
        raw_line = raw_line.strip()
        if not raw_line:
            continue

        matches = list(pattern.finditer(raw_line))
        if not matches:
            continue

        text = pattern.sub("", raw_line).strip()
        for match in matches:
            mins, secs = match.groups()
            try:
                t = int(mins) * 60 + float(secs)
                lines.append((t, text))
            except ValueError:
                continue

    # Urutkan berdasarkan waktu
    lines.sort(key=lambda x: x[0])
    return lines


class LyricsData:
    """Representasi data lirik yang telah diproses."""

    def __init__(
        self,
        track_name: str,
        artist_name: str,
        duration: float = 0.0,
        synced_lines: Optional[List[Tuple[float, str]]] = None,
        plain_text: str = "",
        is_synced: bool = False,
        source: str = "none"
    ):
        self.track_name = track_name
        self.artist_name = artist_name
        self.duration = duration
        self.lines: List[Tuple[float, str]] = synced_lines or []
        self.plain_text = plain_text
        self.is_synced = is_synced
        self.source = source
        self.timestamps = [t for t, _ in self.lines]

    def has_lyrics(self) -> bool:
        return bool(self.lines or self.plain_text.strip())

    def get_active_index(self, position_seconds: float) -> int:
        """
        Menemukan indeks baris lirik aktif saat ini menggunakan pencarian biner.
        Mengembalikan -1 jika playback masih di bagian intro sebelum lirik pertama.
        """
        if not self.lines:
            return -1

        # bisect_right menemukan posisi sisipan pertama setelah position_seconds
        idx = bisect_right(self.timestamps, position_seconds) - 1
        return idx

    def get_display_lines(self, current_index: int, total_lines: int = 3) -> List[Tuple[str, str]]:
        """
        Menghasilkan daftar baris teks beserta perannya ('active', 'previous', 'next')
        untuk ditampilkan di UI floating overlay.
        """
        if not self.lines:
            if self.plain_text:
                return [(self.plain_text[:80] + "...", "active")]
            return [("Lyrics Not Available", "active")]

        n = len(self.lines)

        # Jika masih intro sebelum lirik pertama dimulai
        if current_index < 0:
            first_text = self.lines[0][1] if n > 0 else ""
            if total_lines == 1:
                return [("♪ ♪ ♪", "active")]
            elif total_lines == 2:
                return [
                    ("♪ ♪ ♪", "active"),
                    (first_text, "next")
                ]
            elif total_lines == 3:
                return [
                    ("", "previous"),
                    ("♪ ♪ ♪", "active"),
                    (first_text, "next")
                ]
            else:
                second_text = self.lines[1][1] if n > 1 else ""
                return [
                    ("", "previous"),
                    ("", "previous"),
                    ("♪ ♪ ♪", "active"),
                    (first_text, "next"),
                    (second_text, "next")
                ]

        active_text = self.lines[current_index][1] if 0 <= current_index < n else ""
        if not active_text.strip():
            active_text = "♪ ♪ ♪"

        if total_lines == 1:
            return [(active_text, "active")]

        elif total_lines == 2:
            next_text = self.lines[current_index + 1][1] if current_index + 1 < n else ""
            return [
                (active_text, "active"),
                (next_text, "next")
            ]

        elif total_lines == 3:
            prev_text = self.lines[current_index - 1][1] if current_index - 1 >= 0 else ""
            next_text = self.lines[current_index + 1][1] if current_index + 1 < n else ""
            return [
                (prev_text, "previous"),
                (active_text, "active"),
                (next_text, "next")
            ]

        else:  # 5 lines
            prev_2 = self.lines[current_index - 2][1] if current_index - 2 >= 0 else ""
            prev_1 = self.lines[current_index - 1][1] if current_index - 1 >= 0 else ""
            next_1 = self.lines[current_index + 1][1] if current_index + 1 < n else ""
            next_2 = self.lines[current_index + 2][1] if current_index + 2 < n else ""
            return [
                (prev_2, "previous"),
                (prev_1, "previous"),
                (active_text, "active"),
                (next_1, "next"),
                (next_2, "next")
            ]


class LyricsProvider:
    """Mengelola pencarian, pengunduhan, dan caching lirik LRCLIB."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})
        self.memory_cache = {}

    def _get_cache_path(self, artist: str, title: str) -> str:
        key = f"{artist.lower()}_{title.lower()}".encode("utf-8")
        h = hashlib.md5(key).hexdigest()
        return os.path.join(CACHE_DIR, f"{h}.json")

    def _read_disk_cache(self, artist: str, title: str) -> Optional[LyricsData]:
        path = self._get_cache_path(artist, title)
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    synced_lines = parse_lrc(data.get("syncedLyrics", ""))
                    return LyricsData(
                        track_name=data.get("trackName", title),
                        artist_name=data.get("artistName", artist),
                        duration=data.get("duration", 0),
                        synced_lines=synced_lines,
                        plain_text=data.get("plainLyrics", ""),
                        is_synced=bool(synced_lines),
                        source="cache"
                    )
            except Exception as e:
                print(f"[LyricsProvider] Gagal membaca cache: {e}")
        return None

    def _write_disk_cache(self, artist: str, title: str, raw_json: dict):
        path = self._get_cache_path(artist, title)
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(raw_json, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[LyricsProvider] Gagal menulis cache: {e}")

    def fetch_lyrics(self, track_name: str, artist_name: str, duration: float = 0.0) -> LyricsData:
        """
        Mengambil lirik dari cache atau LRCLIB API dengan multiple fallback:
        1. Cek memory cache.
        2. Cek disk cache.
        3. Request LRCLIB GET (judul asli).
        4. Request LRCLIB GET (judul dibersihkan).
        5. Request LRCLIB SEARCH (pencarian teks bebas).
        """
        cache_key = f"{artist_name.lower()} - {track_name.lower()}"

        # 1. Memory Cache
        if cache_key in self.memory_cache:
            return self.memory_cache[cache_key]

        # 2. Disk Cache
        cached = self._read_disk_cache(artist_name, track_name)
        if cached:
            self.memory_cache[cache_key] = cached
            return cached

        # 3. LRCLIB GET (Exact)
        params = {
            "track_name": track_name,
            "artist_name": artist_name
        }
        if duration > 0:
            params["duration"] = int(round(duration))

        data = None
        try:
            resp = self.session.get(LRCLIB_GET_URL, params=params, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
        except Exception as e:
            print(f"[LyricsProvider] LRCLIB exact GET gagal: {e}")

        # 4. Fallback ke judul yang telah dibersihkan jika tidak ada syncedLyrics
        clean_title = clean_track_title(track_name)
        if not data or not data.get("syncedLyrics"):
            if clean_title != track_name:
                try:
                    params_clean = {"track_name": clean_title, "artist_name": artist_name}
                    if duration > 0:
                        params_clean["duration"] = int(round(duration))
                    resp = self.session.get(LRCLIB_GET_URL, params=params_clean, timeout=5)
                    if resp.status_code == 200:
                        data = resp.json()
                except Exception as e:
                    print(f"[LyricsProvider] LRCLIB clean GET gagal: {e}")

        # 5. Fallback ke LRCLIB SEARCH
        if not data or not data.get("syncedLyrics"):
            try:
                search_query = f"{artist_name} {clean_title}"
                s_resp = self.session.get(LRCLIB_SEARCH_URL, params={"q": search_query}, timeout=6)
                if s_resp.status_code == 200:
                    results = s_resp.json()
                    if isinstance(results, list) and results:
                        # Cari hasil terbaik yang memiliki syncedLyrics
                        synced_candidates = [r for r in results if r.get("syncedLyrics")]
                        if synced_candidates:
                            data = synced_candidates[0]
                        elif not data:
                            data = results[0]
            except Exception as e:
                print(f"[LyricsProvider] LRCLIB search failed: {e}")

        # Proses hasil
        if data:
            self._write_disk_cache(artist_name, track_name, data)
            synced_lines = parse_lrc(data.get("syncedLyrics", ""))
            lyrics_obj = LyricsData(
                track_name=data.get("trackName", track_name),
                artist_name=data.get("artistName", artist_name),
                duration=data.get("duration", duration),
                synced_lines=synced_lines,
                plain_text=data.get("plainLyrics", ""),
                is_synced=bool(synced_lines),
                source="lrclib"
            )
        else:
            lyrics_obj = LyricsData(
                track_name=track_name,
                artist_name=artist_name,
                duration=duration,
                synced_lines=[],
                plain_text="",
                is_synced=False,
                source="none"
            )

        self.memory_cache[cache_key] = lyrics_obj
        return lyrics_obj


def fetch_album_art(artist: str, title: str) -> Optional[bytes]:
    """Mengambil artwork album resolusi tinggi dari iTunes Search API (fallback)."""
    try:
        url = "https://itunes.apple.com/search"
        clean = clean_track_title(title)
        params = {"term": f"{artist} {clean}", "entity": "song", "limit": 1}
        r = requests.get(url, params=params, timeout=3)
        if r.status_code == 200:
            res = r.json().get("results", [])
            if res:
                art_url = res[0].get("artworkUrl100", "").replace("100x100bb", "600x600bb")
                if art_url:
                    img_resp = requests.get(art_url, timeout=4)
                    if img_resp.status_code == 200:
                        return img_resp.content
    except Exception:
        pass
    return None


class LyricsFetchWorker(QThread):
    """Worker QThread agar pemanggilan API LRCLIB dan artwork tidak membekukan UI."""
    lyrics_ready = pyqtSignal(object)
    lyrics_error = pyqtSignal(str)
    cover_art_ready = pyqtSignal(bytes)

    def __init__(self, provider: LyricsProvider, track_name: str, artist_name: str, duration: float = 0.0, need_cover: bool = False):
        super().__init__()
        self.provider = provider
        self.track_name = track_name
        self.artist_name = artist_name
        self.duration = duration
        self.need_cover = need_cover

    def run(self):
        try:
            print(f"[LyricsProvider] [SEARCH] Fetching lyrics from LRCLIB: '{self.track_name}' - '{self.artist_name}'...")
            result = self.provider.fetch_lyrics(self.track_name, self.artist_name, self.duration)
            if result.has_lyrics():
                print(f"[LyricsProvider] [OK] Lyrics successfully loaded ({len(result.lines)} synced lines, source: {result.source})")
            else:
                print(f"[LyricsProvider] [WARN] Lyrics not found for this track.")
            self.lyrics_ready.emit(result)

            # Fallback ambil cover jika GSMTC tidak menyediakan thumbnail
            if self.need_cover:
                cover_data = fetch_album_art(self.artist_name, self.track_name)
                if cover_data:
                    self.cover_art_ready.emit(cover_data)

        except Exception as e:
            print(f"[LyricsProvider] [ERROR] Failed to fetch lyrics: {e}")
            self.lyrics_error.emit(str(e))
