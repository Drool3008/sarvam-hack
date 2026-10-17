"""Family Health Agent — backend for the two functionalities in this build.

1. Voice-note intake  (Saaras v4)      POST /intake/voice-note
2. Spoken status update (Mayura + Bulbul v4 Flash)  POST /notify/spoken-update

Everything else from README.md is out of scope here and is not stubbed in a
production path.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from . import audit, store
from .api import intake, notify
from .config import settings

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
        "Two slices of README.md: verbatim voice-note intake (Saaras v4) and the "
        "role-filtered spoken status update (Mayura v1 + Bulbul v4 Flash)."
    ),
    lifespan=lifespan,
)

app.include_router(intake.router)
app.include_router(notify.router)


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
