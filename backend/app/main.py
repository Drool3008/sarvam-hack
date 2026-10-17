"""Family Health Agent — backend for the two functionalities in this build.

1. Voice-note intake  (Saaras v4)      POST /intake/voice-note
2. Spoken status update (Mayura + Bulbul v4 Flash)  POST /notify/spoken-update

Everything else from README.md is out of scope here and is not stubbed in a
production path.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from . import audit, store
from .api import clinic, intake, notify, talk
from .config import settings
from .sarvam import tts

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    store.reset()
    s = settings()
    if not s.live:
        log.warning(
            "SARVAM_API_KEY not set (or SARVAM_MOCK=true): serving recorded "
            "fixture responses. Every response is tagged source=mock."
        )
    yield


app = FastAPI(
    title="Family Health Agent — intake and spoken update",
    version="0.1.0",
    description=(
        "Two functionalities from README.md. (1) The person talks to the agent: "
        "Saaras v4 verbatim in, strict-schema assessment, Bulbul v4 Flash back in "
        "their own language. (2) The agent then calls the clinic, books a slot and "
        "hands the parent the line."
    ),
    lifespan=lifespan,
)

app.include_router(talk.router)      # 1. the person talks to the agent
app.include_router(clinic.router)    # 2. the agent calls the clinic
app.include_router(intake.router)
app.include_router(notify.router)


# The browser interface. Mounted after the API routers so a route like
# /agent/talk is never shadowed by a static file.
WEB_DIR = Path(__file__).resolve().parents[2] / "web"
if WEB_DIR.is_dir():
    app.mount("/ui", StaticFiles(directory=WEB_DIR, html=True), name="ui")


@app.get("/", include_in_schema=False, response_model=None)
def index():
    """Serve the interface at the root, so the deployed URL is something to look at."""
    page = WEB_DIR / "index.html"
    if page.is_file():
        return FileResponse(page)
    return JSONResponse({"ok": True, "see": "/docs"})


@app.get("/audio/{name}", include_in_schema=False, response_model=None)
def audio(name: str):
    """Serve a rendered Bulbul WAV back to the page.

    The name is checked against the directory listing rather than joined blindly,
    so a path like ../../.env cannot be read through this route.
    """
    target = (tts.OUT_DIR / name).resolve()
    if not str(target).startswith(str(tts.OUT_DIR.resolve())) or not target.is_file():
        raise HTTPException(404, "no such audio")
    return FileResponse(target, media_type="audio/wav")


@app.get("/healthz")
def healthz() -> dict:
    s = settings()
    return {
        "ok": True,
        "sarvam": "live" if s.live else "mock",
        "key_present": bool(s.SARVAM_API_KEY),  # never the key itself
        "confidence_threshold": s.CONFIDENCE_THRESHOLD,
        "households": [h.id for h in store.households()],
    }


@app.get("/audit")
def audit_log() -> dict:
    """The append-only trail behind both functionalities."""
    return {"events": audit.events()}
