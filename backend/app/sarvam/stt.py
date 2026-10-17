"""Saaras v4 verbatim transcription (prompt.md section 7, one function per call).

Two routes, both verbatim mode: REST for audio of 30s or less, the batch job
(with diarization) for anything longer. Mock mode never calls the SDK; it
replays the recorded fixture and tags the result `source="mock"` so it can
never be presented as a real transcription (rule in config.py).
"""

from __future__ import annotations

import json
import mimetypes
import os
import struct
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from .client import client, live, with_retries

MAX_KEYTERMS = 50  # v4 REST/batch limit
REST_MAX_SECONDS = 30.0
MODEL = "saaras:v4"
MODE = "verbatim"

_FIXTURE = Path(__file__).resolve().parent.parent.parent / "fixtures" / "stt_voice_note.json"


@dataclass
class TranscriptionResult:
    transcript: str
    language_code: str | None
    language_probability: float | None
    stt_job_id: str | None
    route: Literal["rest", "batch"]
    source: Literal["sarvam", "mock"]


def cap_keyterms(names: list[str]) -> list[str]:
    """Saaras v4 keyterm prompting takes at most 50 terms, REST and batch only."""
    return names[:MAX_KEYTERMS]


def wav_duration_seconds(data: bytes) -> float | None:
    """Duration read from a canonical PCM WAV header. None if not parseable."""
    if len(data) < 12 or data[0:4] != b"RIFF" or data[8:12] != b"WAVE":
        return None
    pos = 12
    fmt: tuple | None = None
    data_size: int | None = None
    while pos + 8 <= len(data):
        chunk_id = data[pos : pos + 4]
        chunk_size = struct.unpack("<I", data[pos + 4 : pos + 8])[0]
        body_start = pos + 8
        if chunk_id == b"fmt " and body_start + 16 <= len(data):
            fmt = struct.unpack("<HHIIHH", data[body_start : body_start + 16])
        elif chunk_id == b"data":
            data_size = chunk_size
        pos = body_start + chunk_size + (chunk_size % 2)  # chunks are word-aligned
        if fmt is not None and data_size is not None:
            break
    if fmt is None or data_size is None:
        return None
    _, channels, sample_rate, byte_rate, _block_align, bits_per_sample = fmt
    if byte_rate:
        return data_size / byte_rate
    if sample_rate and channels and bits_per_sample:
        return data_size / (sample_rate * channels * (bits_per_sample / 8))
    return None


def estimate_duration_seconds(data: bytes) -> tuple[float, bool]:
    """Returns (seconds, is_fallback_estimate).

    Only a PCM WAV header gives an exact figure. A WhatsApp voice note (OGG/
    OPUS) has no header this module parses, so this falls back to a bytes-per-
    second guess for compressed speech.
    """
    duration = wav_duration_seconds(data)
    if duration is not None:
        return duration, False
    # DECISION: not a parseable WAV header — estimate from file size using a
    # typical compressed-speech bitrate (16 kbps) rather than failing the
    # REST/batch routing decision. This is an approximation, not a measurement.
    assumed_bytes_per_second = 16_000 / 8
    return len(data) / assumed_bytes_per_second, True


def _mock_response() -> dict:
    return json.loads(_FIXTURE.read_text(encoding="utf-8"))


def transcribe(data: bytes, filename: str, keyterms: list[str]) -> TranscriptionResult:
    """Single entry point for any caller that just has raw audio bytes.

    Picks REST or batch by duration, spools to a temp file for the batch path
    (upload_files() needs a path), and cleans it up. Returns the verbatim
    text, the detected language and its confidence, and the route used — a
    caller (the voice-note intake endpoint, or a live conversation-turn
    orchestrator) never has to know which Saaras call ran underneath.
    """
    keyterms = cap_keyterms(keyterms)
    duration_seconds, _is_estimate = estimate_duration_seconds(data)
    if duration_seconds <= REST_MAX_SECONDS:
        return transcribe_rest(data, filename, keyterms)

    suffix = os.path.splitext(filename or "")[1] or ".wav"
    fd, tmp_path = tempfile.mkstemp(suffix=suffix)
    try:
        with os.fdopen(fd, "wb") as tmp:
            tmp.write(data)
        return transcribe_batch(tmp_path, keyterms)
    finally:
        os.unlink(tmp_path)


def transcribe_rest(data: bytes, filename: str, keyterms: list[str]) -> TranscriptionResult:
    """REST `speech_to_text.transcribe`, for audio of 30s or less.

    `language_code` is deliberately left out so Saaras returns
    `language_probability` alongside the detected language.
    """
    keyterms = cap_keyterms(keyterms)
    if not live():
        payload = _mock_response()
        return TranscriptionResult(
            transcript=payload["transcript"],
            language_code=payload.get("language_code"),
            language_probability=payload.get("language_probability"),
            stt_job_id=None,
            route="rest",
            source="mock",
        )

    # README: Saaras accepts most audio formats (OGG/OPUS WhatsApp voice
    # notes, AMR, WAV, ...) without conversion, so the content type is read
    # from the upload's own extension rather than assumed to be WAV.
    content_type = mimetypes.guess_type(filename)[0] or "audio/wav"

    def _call():
        return client().speech_to_text.transcribe(
            file=(filename, data, content_type),
            model=MODEL,
            mode=MODE,
            keyterms=keyterms,
        )

    resp = with_retries(_call)
    return TranscriptionResult(
        transcript=resp.transcript,
        language_code=resp.language_code,
        language_probability=resp.language_probability,
        stt_job_id=None,
        route="rest",
        source="sarvam",
    )


def transcribe_batch(path: str, keyterms: list[str]) -> TranscriptionResult:
    """Batch `speech_to_text_job`, for audio over 30s. Diarization is batch-only
    and is requested so a secondhand account (someone speaking for the
    affected person) can be told apart from their own voice.

    # OPEN: the batch job's downloaded output file has no typed SDK model —
    # `get_file_results`/`download_outputs` only expose raw dicts — so the
    # exact JSON shape of a diarized transcript is not confirmed against a
    # real response. This path is written against the installed SDK's method
    # signatures and exercised only under mock, per the brief; a live batch
    # call is not attempted here.
    """
    keyterms = cap_keyterms(keyterms)
    if not live():
        payload = _mock_response()
        return TranscriptionResult(
            transcript=payload["transcript"],
            language_code=payload.get("language_code"),
            language_probability=payload.get("language_probability"),
            stt_job_id="mock-job-0001",
            route="batch",
            source="mock",
        )

    def _create():
        return client().speech_to_text_job.create_job(
            model=MODEL,
            mode=MODE,
            with_diarization=True,
            keyterms=keyterms,
        )

    job = with_retries(_create)
    job.upload_files([path])
    job.start()
    job.wait_until_complete()

    with tempfile.TemporaryDirectory() as out_dir:
        job.download_outputs(out_dir)
        transcript = ""
        for name in os.listdir(out_dir):
            output = json.loads(Path(out_dir, name).read_text(encoding="utf-8"))
            transcript = output.get("transcript", transcript)
            break

    return TranscriptionResult(
        transcript=transcript,
        language_code=None,
        language_probability=None,
        stt_job_id=job.job_id,
        route="batch",
        source="sarvam",
    )
