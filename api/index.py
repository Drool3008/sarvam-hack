"""Vercel serverless entrypoint.

Vercel's Python runtime looks for a module-level ASGI app. The backend lives
under backend/, so that directory goes on the path before the import.

Set on the deployment (see vercel.json):
  AUDIO_DIR=/tmp/out     the only writable path in a serverless function
  AUDIO_INLINE=1         return the WAV in the JSON response, because a second
                         request for a file in /tmp may land on another instance
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "backend"))

from app.main import app  # noqa: E402

__all__ = ["app"]
