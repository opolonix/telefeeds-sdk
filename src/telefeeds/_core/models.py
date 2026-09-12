from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import IntEnum


@dataclass(frozen=True, slots=True)
class UpdateEnvelope:
    session_peer_id: int
    session_kind: str
    body: bytes
    received_at: datetime | None


@dataclass(frozen=True, slots=True)
class SessionSnapshot:
    session_peer_id: int
    state: str
    alive: bool
    fatal: bool
    proxy_broken: bool
    uptime_ms: int
    updates_per_second: float
    invokes_per_second: float
    invokes_in_flight: int
    memory_bytes: int
    updates_total: int
    invokes_total: int
    last_error: str | None
    updated_at: datetime | None
    media_upload_bytes: int
    media_download_bytes: int
    media_requests_total: int
    media_requests_in_flight: int
    tl_layer: int | None


@dataclass(frozen=True, slots=True)
class SessionRegistration:
    session_peer_id: int
    state: str


@dataclass(frozen=True, slots=True)
class AuthorizationChallenge:
    authorization_id: str
    expires_at: datetime | None


class AuthorizationState(IntEnum):
    UNSPECIFIED = 0
    PASSWORD_REQUIRED = 1
    AUTHORIZED = 2


@dataclass(frozen=True, slots=True)
class AuthorizationResult:
    state: AuthorizationState
    password_hint: str | None
    session: SessionRegistration | None
