"""The only module that constructs a Sarvam client.

prompt.md section 7: one function per call, typed in and out, retries with
backoff on TooManyRequestsError, other ApiErrors raised as domain errors.
Nothing outside app/sarvam/ imports the SDK.
"""

from __future__ import annotations

import logging
import time
from functools import lru_cache
from typing import Callable, TypeVar

from ..config import settings

log = logging.getLogger(__name__)

T = TypeVar("T")


class SarvamUnavailable(Exception):
    """A Sarvam call failed in a way the caller has to handle (domain error)."""


class SarvamNotConfigured(Exception):
    """A live call was attempted with no API key and no mock fallback."""


@lru_cache
def client():
    from sarvamai import SarvamAI  # imported lazily so mock mode needs no SDK

    s = settings()
    if not s.SARVAM_API_KEY:
        raise SarvamNotConfigured("SARVAM_API_KEY is not set")
    return SarvamAI(api_subscription_key=s.SARVAM_API_KEY)


def live() -> bool:
    """True when real Sarvam calls should be made."""
    return settings().live


def with_retries(fn: Callable[[], T], *, attempts: int = 4, base_delay: float = 0.5) -> T:
    """Retry with backoff on rate limits. Everything else becomes a domain error."""
    from sarvamai.core.api_error import ApiError
    from sarvamai.errors import TooManyRequestsError

    last: Exception | None = None
    for attempt in range(attempts):
        try:
            return fn()
        except TooManyRequestsError as exc:
            last = exc
            delay = base_delay * (2**attempt)
            log.warning("sarvam rate limited, retrying in %.1fs (%d/%d)", delay, attempt + 1, attempts)
            time.sleep(delay)
        except ApiError as exc:
            raise SarvamUnavailable(f"{type(exc).__name__}: {exc}") from exc
    raise SarvamUnavailable(f"rate limited after {attempts} attempts: {last}")
