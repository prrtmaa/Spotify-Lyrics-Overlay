"""
run.py - Root Launcher for Spotify Lyrics Overlay
Runs spotify_lyrics_overlay.main directly from workspace root.
"""

import sys
import os

os.environ["PYTHONUNBUFFERED"] = "1"

# Tambahkan direktori spotify_lyrics_overlay ke sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.join(BASE_DIR, "spotify_lyrics_overlay")
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

from main import main

if __name__ == "__main__":
    main()
