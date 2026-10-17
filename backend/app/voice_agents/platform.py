"""Indus Voice Agents platform client (prompt.md section 9, "Platform
clients (voice_agents/)").

Every call here goes to `https://apps.sarvam.ai` (overridable via
`SARVAM_VA_BASE_URL`) with header `X-API-Key`. Three workspace variables gate
it — `SARVAM_VA_API_KEY`, `SARVAM_ORG_ID`, `SARVAM_WORKSPACE_ID` — and none of
them is set in this environment (`.env` leaves all three blank), so every
function below raises `IndusNotConfigured`, naming exactly which ones are
missing, before any HTTP request is attempted. No `attempt_id` is ever
fabricated: a caller either gets the platform's own id or this exception,
never a placeholder that could be mistaken for one.

Only `app/voice_agents/` talks to this platform directly, matching the
house rule that only one module per external surface owns the wire format.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from ..config import settings

_TIMEOUT = 30.0


class IndusNotConfigured(Exception):
    """A real telephony action was attempted without the Indus workspace vars."""


@dataclass
class PlaceCallResult:
    attempt_id: str
    raw: dict[str, Any]


def _require_indus():
    s = settings()
    if not s.indus_ready:
        missing = ", ".join(s.missing_indus_vars())
        raise IndusNotConfigured(
            f"Indus Voice Agents is not configured: missing {missing}"
        )
    return s


def _headers(s) -> dict[str, str]:
    return {"X-API-Key": s.SARVAM_VA_API_KEY}


# Per-agent app configuration on the Indus platform: the app id, its
# deployed version, the connection (telephony provider) and the number the
# agent calls from. prompt.md section 9 lists the agents (intake, check_in,
# clinic, chemist) but not these ids, because they only exist once an app has
# actually been authored in an Indus workspace.
# OPEN: no Indus workspace has been created in this environment, so these
# per-agent app ids are unknown and this map is left empty. A real deployment
# would populate it (or load it from settings) before place_call() could
# succeed even with the three workspace vars present.
AGENT_APP_CONFIG: dict[str, dict[str, str]] = {}


def place_call(agent: str, to_phone: str, variables: dict) -> dict:
    """`POST /api/outbounds/v1/orgs/{org_id}/workspaces/{workspace_id}/outbounds`

    Starts an instant outbound call for `agent` (e.g. "clinic") to `to_phone`,
    passing `variables` to the call (this is how the affected person's own
    phone number reaches the agent for `call_transfer`). Returns the
    platform's `attempt_id`. Raises `IndusNotConfigured` — never a faked
    `attempt_id` — when the workspace vars are not set.
    """
    s = _require_indus()
    app_config = AGENT_APP_CONFIG.get(agent, {})
    url = (
        f"{s.SARVAM_VA_BASE_URL}/api/outbounds/v1/orgs/{s.SARVAM_ORG_ID}"
        f"/workspaces/{s.SARVAM_WORKSPACE_ID}/outbounds"
    )
    # OPEN: the exact field names inside app_config/user_config/webhook_config
    # (and how `variables` is attached — top-level, or nested under
    # app_config) are taken from the README/prompt.md prose, not confirmed
    # against a live API reference, since no Indus workspace is reachable
    # from this environment. This is the shape prompt.md section 9 describes;
    # confirm it against the real API reference before relying on it.
    body = {
        "app_config": {
            "agent": agent,
            "app_id": app_config.get("app_id"),
            "version": app_config.get("version"),
            "connection": app_config.get("connection"),
            "agent_phone_number": app_config.get("agent_phone_number"),
        },
        "user_config": {"user_phone_number": to_phone},
        "webhook_config": {},  # OPEN: webhook URL / shared secret, section 9
        "variables": variables,
    }
    resp = httpx.post(url, headers=_headers(s), json=body, timeout=_TIMEOUT)
    resp.raise_for_status()
    data = resp.json()
    return {"attempt_id": data.get("attempt_id"), "raw": data}


def get_transcript(interaction_id: str, *, app_id: str | None = None) -> dict:
    """`GET /api/analytics/v1/{org_id}/{workspace_id}/{app_id}/transcripts/{interaction_id}`

    # OPEN: `app_id` is part of this URL per prompt.md section 9, but no
    # `SARVAM_APP_ID` setting exists (it is specific to the deployed agent,
    # not the workspace) — pass it explicitly until that is resolved.
    """
    s = _require_indus()
    if not app_id:
        raise IndusNotConfigured(
            "Indus Voice Agents app id is required for get_transcript() and "
            "is not configured anywhere in this environment"
        )
    url = (
        f"{s.SARVAM_VA_BASE_URL}/api/analytics/v1/{s.SARVAM_ORG_ID}"
        f"/{s.SARVAM_WORKSPACE_ID}/{app_id}/transcripts/{interaction_id}"
    )
    resp = httpx.get(url, headers=_headers(s), timeout=_TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def get_recording(interaction_id: str, *, app_id: str | None = None) -> bytes:
    """`GET /api/analytics/v1/{org_id}/{workspace_id}/{app_id}/recordings/{interaction_id}`

    Returns WAV bytes, not JSON. Same `app_id` gap as `get_transcript()`.
    """
    s = _require_indus()
    if not app_id:
        raise IndusNotConfigured(
            "Indus Voice Agents app id is required for get_recording() and "
            "is not configured anywhere in this environment"
        )
    url = (
        f"{s.SARVAM_VA_BASE_URL}/api/analytics/v1/{s.SARVAM_ORG_ID}"
        f"/{s.SARVAM_WORKSPACE_ID}/{app_id}/recordings/{interaction_id}"
    )
    resp = httpx.get(url, headers=_headers(s), timeout=60.0)
    resp.raise_for_status()
    return resp.content
