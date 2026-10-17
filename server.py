"""Vercel entrypoint.

Vercel's Python runtime looks for a top-level `app` in one of a fixed set of
filenames at the project root. This file is named `server.py` rather than
`app.py` deliberately: the backend package is itself called `app`, and a root
`app.py` would shadow it on the import path.

Set on the deployment (see vercel.json):
  AUDIO_DIR=/tmp/out   the only writable path in a serverless function
  AUDIO_INLINE=1       return the WAV with the reply, because a second request
                       for a file in /tmp may land on a different instance
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent / "backend"))

from app.main import app  # noqa: E402

__all__ = ["app"]
