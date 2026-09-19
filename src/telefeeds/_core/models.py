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
    tl_layer: int


@dataclass(frozen=True, slots=True)
class IntegrationMetricsSnapshot:
    user_sessions_total: int
    user_sessions_updates_enabled: int
    usage_days_total: int
    bot_access_total: int
    active_connections: int
    active_interfaces: int
    captured_at: datetime | None


@dataclass(frozen=True, slots=True)
class IntegrationSnapshot:
    integration_id: str
    client_id: int
    name: str
    enabled: bool
    allow_user_sessions: bool
    telegram_credentials_configured: bool
    granted_scopes: tuple[str, ...]
    default_interface: int
    default_close_other: bool
    proxy_pool_size: int
    user_session_day_price_cents: float
    created_at: datetime | None
    updated_at: datetime | None
    metrics: IntegrationMetricsSnapshot


@dataclass(frozen=True, slots=True)
class SessionSnapshot:
    session_peer_id: int
    state: str
    alive: bool
    fatal: bool
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
    usage_days: int
    last_usage_at: datetime | None
    updates_enabled: bool
    updates_state_changed_at: datetime | None


@dataclass(frozen=True, slots=True)
class SessionSubscription:
    session_peer_id: int
    updates_enabled: bool
    changed_at: datetime | None


@dataclass(frozen=True, slots=True)
class IntegrationUserSession:
    session_peer_id: int
    phone_number: str | None
    username: str | None
    first_name: str | None
    last_name: str | None
    state: str
    updates_enabled: bool
    updates_state_changed_at: datetime | None
    usage_days: int
    last_usage_at: datetime | None
    linked_at: datetime | None


@dataclass(frozen=True, slots=True)
class UserSessionPage:
    sessions: tuple[IntegrationUserSession, ...]
    next_page_token: str | None


@dataclass(frozen=True, slots=True)
class SessionRegistration:
    session_peer_id: int
    state: str


class AuthorizationKind(IntEnum):
    UNSPECIFIED = 0
    NATIVE = 1
    PROVIDER = 2


class AuthorizationCodeProviderKind(IntEnum):
    UNSPECIFIED = 0
    TELEGRAM_GATEWAY = 1
    TELEGRAM_BOT = 2


@dataclass(frozen=True, slots=True)
class AuthorizationCodeProvider:
    kind: AuthorizationCodeProviderKind
    url: str | None
    code_secret: str | None
    requires_open_url: bool


@dataclass(frozen=True, slots=True)
class AuthorizationChallenge:
    authorization_id: str
    expires_at: datetime | None
    code_length: int | None
    authorization_kind: AuthorizationKind
    code_provider: AuthorizationCodeProvider | None


class AuthorizationState(IntEnum):
    UNSPECIFIED = 0
    PASSWORD_REQUIRED = 1
    AUTHORIZED = 2


@dataclass(frozen=True, slots=True)
class AuthorizationResult:
    state: AuthorizationState
    password_hint: str | None
    session: SessionRegistration | None
