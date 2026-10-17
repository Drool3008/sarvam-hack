"""Append-only audit log (section 5, AuditEvent).

Every agent action lands here with its actor and the source of its data, because
"every rupee to the responsible person" needs a trail behind it.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class AuditEvent:
    action: str
    actor: str
    data_source: str
    detail: dict[str, Any] = field(default_factory=dict)
    at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


_LOG: list[AuditEvent] = []


def record(action: str, actor: str, data_source: str, **detail: Any) -> AuditEvent:
    event = AuditEvent(action=action, actor=actor, data_source=data_source, detail=detail)
    _LOG.append(event)
    return event


def events() -> list[dict[str, Any]]:
    return [asdict(e) | {"at": e.at.isoformat()} for e in _LOG]


def clear() -> None:
    _LOG.clear()
