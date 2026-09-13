import datetime

from google.protobuf import timestamp_pb2 as _timestamp_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class AuthorizationKind(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    AUTHORIZATION_KIND_UNSPECIFIED: _ClassVar[AuthorizationKind]
    AUTHORIZATION_KIND_NATIVE: _ClassVar[AuthorizationKind]
    AUTHORIZATION_KIND_PROVIDER: _ClassVar[AuthorizationKind]

class AuthorizationErrorCode(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    AUTHORIZATION_ERROR_CODE_UNSPECIFIED: _ClassVar[AuthorizationErrorCode]
    AUTHORIZATION_ERROR_CODE_CREDENTIALS_REQUIRED: _ClassVar[AuthorizationErrorCode]
    AUTHORIZATION_ERROR_CODE_CREDENTIALS_INVALID: _ClassVar[AuthorizationErrorCode]
    AUTHORIZATION_ERROR_CODE_ATTEMPT_INVALID: _ClassVar[AuthorizationErrorCode]
    AUTHORIZATION_ERROR_CODE_ATTEMPT_NOT_FOUND: _ClassVar[AuthorizationErrorCode]
    AUTHORIZATION_ERROR_CODE_ATTEMPT_FORBIDDEN: _ClassVar[AuthorizationErrorCode]
    AUTHORIZATION_ERROR_CODE_ATTEMPT_EXPIRED: _ClassVar[AuthorizationErrorCode]
    AUTHORIZATION_ERROR_CODE_PHONE_INVALID: _ClassVar[AuthorizationErrorCode]
    AUTHORIZATION_ERROR_CODE_PHONE_BANNED: _ClassVar[AuthorizationErrorCode]
    AUTHORIZATION_ERROR_CODE_CODE_INVALID: _ClassVar[AuthorizationErrorCode]
    AUTHORIZATION_ERROR_CODE_CODE_EXPIRED: _ClassVar[AuthorizationErrorCode]
    AUTHORIZATION_ERROR_CODE_PASSWORD_INVALID: _ClassVar[AuthorizationErrorCode]
    AUTHORIZATION_ERROR_CODE_PASSWORD_NOT_EXPECTED: _ClassVar[AuthorizationErrorCode]
    AUTHORIZATION_ERROR_CODE_SIGN_UP_REQUIRED: _ClassVar[AuthorizationErrorCode]
    AUTHORIZATION_ERROR_CODE_SESSION_ACCESS_DISABLED: _ClassVar[AuthorizationErrorCode]
    AUTHORIZATION_ERROR_CODE_PROVIDER_UNAVAILABLE: _ClassVar[AuthorizationErrorCode]
    AUTHORIZATION_ERROR_CODE_PERMISSION_DENIED: _ClassVar[AuthorizationErrorCode]
    AUTHORIZATION_ERROR_CODE_RATE_LIMITED: _ClassVar[AuthorizationErrorCode]
    AUTHORIZATION_ERROR_CODE_CONCURRENT_LIMIT: _ClassVar[AuthorizationErrorCode]

class AuthorizationCodeProviderKind(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    AUTHORIZATION_CODE_PROVIDER_KIND_UNSPECIFIED: _ClassVar[AuthorizationCodeProviderKind]
    AUTHORIZATION_CODE_PROVIDER_KIND_TELEGRAM_GATEWAY: _ClassVar[AuthorizationCodeProviderKind]
    AUTHORIZATION_CODE_PROVIDER_KIND_TELEGRAM_BOT: _ClassVar[AuthorizationCodeProviderKind]

class PhoneAuthorizationState(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    PHONE_AUTHORIZATION_STATE_UNSPECIFIED: _ClassVar[PhoneAuthorizationState]
    PHONE_AUTHORIZATION_STATE_PASSWORD_REQUIRED: _ClassVar[PhoneAuthorizationState]
    PHONE_AUTHORIZATION_STATE_AUTHORIZED: _ClassVar[PhoneAuthorizationState]
AUTHORIZATION_KIND_UNSPECIFIED: AuthorizationKind
AUTHORIZATION_KIND_NATIVE: AuthorizationKind
AUTHORIZATION_KIND_PROVIDER: AuthorizationKind
AUTHORIZATION_ERROR_CODE_UNSPECIFIED: AuthorizationErrorCode
AUTHORIZATION_ERROR_CODE_CREDENTIALS_REQUIRED: AuthorizationErrorCode
AUTHORIZATION_ERROR_CODE_CREDENTIALS_INVALID: AuthorizationErrorCode
AUTHORIZATION_ERROR_CODE_ATTEMPT_INVALID: AuthorizationErrorCode
AUTHORIZATION_ERROR_CODE_ATTEMPT_NOT_FOUND: AuthorizationErrorCode
AUTHORIZATION_ERROR_CODE_ATTEMPT_FORBIDDEN: AuthorizationErrorCode
AUTHORIZATION_ERROR_CODE_ATTEMPT_EXPIRED: AuthorizationErrorCode
AUTHORIZATION_ERROR_CODE_PHONE_INVALID: AuthorizationErrorCode
AUTHORIZATION_ERROR_CODE_PHONE_BANNED: AuthorizationErrorCode
AUTHORIZATION_ERROR_CODE_CODE_INVALID: AuthorizationErrorCode
AUTHORIZATION_ERROR_CODE_CODE_EXPIRED: AuthorizationErrorCode
AUTHORIZATION_ERROR_CODE_PASSWORD_INVALID: AuthorizationErrorCode
AUTHORIZATION_ERROR_CODE_PASSWORD_NOT_EXPECTED: AuthorizationErrorCode
AUTHORIZATION_ERROR_CODE_SIGN_UP_REQUIRED: AuthorizationErrorCode
AUTHORIZATION_ERROR_CODE_SESSION_ACCESS_DISABLED: AuthorizationErrorCode
AUTHORIZATION_ERROR_CODE_PROVIDER_UNAVAILABLE: AuthorizationErrorCode
AUTHORIZATION_ERROR_CODE_PERMISSION_DENIED: AuthorizationErrorCode
AUTHORIZATION_ERROR_CODE_RATE_LIMITED: AuthorizationErrorCode
AUTHORIZATION_ERROR_CODE_CONCURRENT_LIMIT: AuthorizationErrorCode
AUTHORIZATION_CODE_PROVIDER_KIND_UNSPECIFIED: AuthorizationCodeProviderKind
AUTHORIZATION_CODE_PROVIDER_KIND_TELEGRAM_GATEWAY: AuthorizationCodeProviderKind
AUTHORIZATION_CODE_PROVIDER_KIND_TELEGRAM_BOT: AuthorizationCodeProviderKind
PHONE_AUTHORIZATION_STATE_UNSPECIFIED: PhoneAuthorizationState
PHONE_AUTHORIZATION_STATE_PASSWORD_REQUIRED: PhoneAuthorizationState
PHONE_AUTHORIZATION_STATE_AUTHORIZED: PhoneAuthorizationState

class SubscribeRequest(_message.Message):
    __slots__ = ("interface", "close_other", "tl_layer")
    INTERFACE_FIELD_NUMBER: _ClassVar[int]
    CLOSE_OTHER_FIELD_NUMBER: _ClassVar[int]
    TL_LAYER_FIELD_NUMBER: _ClassVar[int]
    interface: int
    close_other: bool
    tl_layer: int
    def __init__(self, interface: _Optional[int] = ..., close_other: _Optional[bool] = ..., tl_layer: _Optional[int] = ...) -> None: ...

class UpdateEnvelope(_message.Message):
    __slots__ = ("session_peer_id", "session_kind", "body", "received_at", "tl_layer")
    SESSION_PEER_ID_FIELD_NUMBER: _ClassVar[int]
    SESSION_KIND_FIELD_NUMBER: _ClassVar[int]
    BODY_FIELD_NUMBER: _ClassVar[int]
    RECEIVED_AT_FIELD_NUMBER: _ClassVar[int]
    TL_LAYER_FIELD_NUMBER: _ClassVar[int]
    session_peer_id: int
    session_kind: str
    body: bytes
    received_at: _timestamp_pb2.Timestamp
    tl_layer: int
    def __init__(self, session_peer_id: _Optional[int] = ..., session_kind: _Optional[str] = ..., body: _Optional[bytes] = ..., received_at: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ..., tl_layer: _Optional[int] = ...) -> None: ...

class InvokeRequest(_message.Message):
    __slots__ = ("session_peer_id", "body", "dc_id", "tl_layer")
    SESSION_PEER_ID_FIELD_NUMBER: _ClassVar[int]
    BODY_FIELD_NUMBER: _ClassVar[int]
    DC_ID_FIELD_NUMBER: _ClassVar[int]
    TL_LAYER_FIELD_NUMBER: _ClassVar[int]
    session_peer_id: int
    body: bytes
    dc_id: int
    tl_layer: int
    def __init__(self, session_peer_id: _Optional[int] = ..., body: _Optional[bytes] = ..., dc_id: _Optional[int] = ..., tl_layer: _Optional[int] = ...) -> None: ...

class InvokeResponse(_message.Message):
    __slots__ = ("body", "error", "rpc_error")
    BODY_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    RPC_ERROR_FIELD_NUMBER: _ClassVar[int]
    body: bytes
    error: str
    rpc_error: TelegramRpcError
    def __init__(self, body: _Optional[bytes] = ..., error: _Optional[str] = ..., rpc_error: _Optional[_Union[TelegramRpcError, _Mapping]] = ...) -> None: ...

class TelegramRpcError(_message.Message):
    __slots__ = ("code", "name", "value", "caused_by")
    CODE_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    CAUSED_BY_FIELD_NUMBER: _ClassVar[int]
    code: int
    name: str
    value: int
    caused_by: int
    def __init__(self, code: _Optional[int] = ..., name: _Optional[str] = ..., value: _Optional[int] = ..., caused_by: _Optional[int] = ...) -> None: ...

class GetIntegrationSnapshotRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class IntegrationSnapshot(_message.Message):
    __slots__ = ("integration_id", "client_id", "name", "enabled", "allow_user_sessions", "telegram_credentials_configured", "granted_scopes", "default_interface", "default_close_other", "proxy_pool_size", "user_session_day_price_cents", "created_at", "updated_at", "metrics")
    INTEGRATION_ID_FIELD_NUMBER: _ClassVar[int]
    CLIENT_ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    ENABLED_FIELD_NUMBER: _ClassVar[int]
    ALLOW_USER_SESSIONS_FIELD_NUMBER: _ClassVar[int]
    TELEGRAM_CREDENTIALS_CONFIGURED_FIELD_NUMBER: _ClassVar[int]
    GRANTED_SCOPES_FIELD_NUMBER: _ClassVar[int]
    DEFAULT_INTERFACE_FIELD_NUMBER: _ClassVar[int]
    DEFAULT_CLOSE_OTHER_FIELD_NUMBER: _ClassVar[int]
    PROXY_POOL_SIZE_FIELD_NUMBER: _ClassVar[int]
    USER_SESSION_DAY_PRICE_CENTS_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    UPDATED_AT_FIELD_NUMBER: _ClassVar[int]
    METRICS_FIELD_NUMBER: _ClassVar[int]
    integration_id: str
    client_id: int
    name: str
    enabled: bool
    allow_user_sessions: bool
    telegram_credentials_configured: bool
    granted_scopes: _containers.RepeatedScalarFieldContainer[str]
    default_interface: int
    default_close_other: bool
    proxy_pool_size: int
    user_session_day_price_cents: float
    created_at: _timestamp_pb2.Timestamp
    updated_at: _timestamp_pb2.Timestamp
    metrics: IntegrationMetricsSnapshot
    def __init__(self, integration_id: _Optional[str] = ..., client_id: _Optional[int] = ..., name: _Optional[str] = ..., enabled: _Optional[bool] = ..., allow_user_sessions: _Optional[bool] = ..., telegram_credentials_configured: _Optional[bool] = ..., granted_scopes: _Optional[_Iterable[str]] = ..., default_interface: _Optional[int] = ..., default_close_other: _Optional[bool] = ..., proxy_pool_size: _Optional[int] = ..., user_session_day_price_cents: _Optional[float] = ..., created_at: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ..., updated_at: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ..., metrics: _Optional[_Union[IntegrationMetricsSnapshot, _Mapping]] = ...) -> None: ...

class IntegrationMetricsSnapshot(_message.Message):
    __slots__ = ("user_sessions_total", "user_sessions_updates_enabled", "usage_days_total", "bot_access_total", "active_connections", "active_interfaces", "captured_at")
    USER_SESSIONS_TOTAL_FIELD_NUMBER: _ClassVar[int]
    USER_SESSIONS_UPDATES_ENABLED_FIELD_NUMBER: _ClassVar[int]
    USAGE_DAYS_TOTAL_FIELD_NUMBER: _ClassVar[int]
    BOT_ACCESS_TOTAL_FIELD_NUMBER: _ClassVar[int]
    ACTIVE_CONNECTIONS_FIELD_NUMBER: _ClassVar[int]
    ACTIVE_INTERFACES_FIELD_NUMBER: _ClassVar[int]
    CAPTURED_AT_FIELD_NUMBER: _ClassVar[int]
    user_sessions_total: int
    user_sessions_updates_enabled: int
    usage_days_total: int
    bot_access_total: int
    active_connections: int
    active_interfaces: int
    captured_at: _timestamp_pb2.Timestamp
    def __init__(self, user_sessions_total: _Optional[int] = ..., user_sessions_updates_enabled: _Optional[int] = ..., usage_days_total: _Optional[int] = ..., bot_access_total: _Optional[int] = ..., active_connections: _Optional[int] = ..., active_interfaces: _Optional[int] = ..., captured_at: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ...) -> None: ...

class GetSessionSnapshotsRequest(_message.Message):
    __slots__ = ("session_peer_ids",)
    SESSION_PEER_IDS_FIELD_NUMBER: _ClassVar[int]
    session_peer_ids: _containers.RepeatedScalarFieldContainer[int]
    def __init__(self, session_peer_ids: _Optional[_Iterable[int]] = ...) -> None: ...

class GetSessionSnapshotsResponse(_message.Message):
    __slots__ = ("sessions",)
    SESSIONS_FIELD_NUMBER: _ClassVar[int]
    sessions: _containers.RepeatedCompositeFieldContainer[SessionSnapshot]
    def __init__(self, sessions: _Optional[_Iterable[_Union[SessionSnapshot, _Mapping]]] = ...) -> None: ...

class SessionSnapshot(_message.Message):
    __slots__ = ("session_peer_id", "state", "alive", "fatal", "proxy_broken", "uptime_ms", "updates_per_second", "invokes_per_second", "invokes_in_flight", "memory_bytes", "updates_total", "invokes_total", "last_error", "updated_at", "media_upload_bytes", "media_download_bytes", "media_requests_total", "media_requests_in_flight", "tl_layer", "usage_days", "last_usage_at", "updates_enabled", "updates_state_changed_at")
    SESSION_PEER_ID_FIELD_NUMBER: _ClassVar[int]
    STATE_FIELD_NUMBER: _ClassVar[int]
    ALIVE_FIELD_NUMBER: _ClassVar[int]
    FATAL_FIELD_NUMBER: _ClassVar[int]
    PROXY_BROKEN_FIELD_NUMBER: _ClassVar[int]
    UPTIME_MS_FIELD_NUMBER: _ClassVar[int]
    UPDATES_PER_SECOND_FIELD_NUMBER: _ClassVar[int]
    INVOKES_PER_SECOND_FIELD_NUMBER: _ClassVar[int]
    INVOKES_IN_FLIGHT_FIELD_NUMBER: _ClassVar[int]
    MEMORY_BYTES_FIELD_NUMBER: _ClassVar[int]
    UPDATES_TOTAL_FIELD_NUMBER: _ClassVar[int]
    INVOKES_TOTAL_FIELD_NUMBER: _ClassVar[int]
    LAST_ERROR_FIELD_NUMBER: _ClassVar[int]
    UPDATED_AT_FIELD_NUMBER: _ClassVar[int]
    MEDIA_UPLOAD_BYTES_FIELD_NUMBER: _ClassVar[int]
    MEDIA_DOWNLOAD_BYTES_FIELD_NUMBER: _ClassVar[int]
    MEDIA_REQUESTS_TOTAL_FIELD_NUMBER: _ClassVar[int]
    MEDIA_REQUESTS_IN_FLIGHT_FIELD_NUMBER: _ClassVar[int]
    TL_LAYER_FIELD_NUMBER: _ClassVar[int]
    USAGE_DAYS_FIELD_NUMBER: _ClassVar[int]
    LAST_USAGE_AT_FIELD_NUMBER: _ClassVar[int]
    UPDATES_ENABLED_FIELD_NUMBER: _ClassVar[int]
    UPDATES_STATE_CHANGED_AT_FIELD_NUMBER: _ClassVar[int]
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
    last_error: str
    updated_at: _timestamp_pb2.Timestamp
    media_upload_bytes: int
    media_download_bytes: int
    media_requests_total: int
    media_requests_in_flight: int
    tl_layer: int
    usage_days: int
    last_usage_at: _timestamp_pb2.Timestamp
    updates_enabled: bool
    updates_state_changed_at: _timestamp_pb2.Timestamp
    def __init__(self, session_peer_id: _Optional[int] = ..., state: _Optional[str] = ..., alive: _Optional[bool] = ..., fatal: _Optional[bool] = ..., proxy_broken: _Optional[bool] = ..., uptime_ms: _Optional[int] = ..., updates_per_second: _Optional[float] = ..., invokes_per_second: _Optional[float] = ..., invokes_in_flight: _Optional[int] = ..., memory_bytes: _Optional[int] = ..., updates_total: _Optional[int] = ..., invokes_total: _Optional[int] = ..., last_error: _Optional[str] = ..., updated_at: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ..., media_upload_bytes: _Optional[int] = ..., media_download_bytes: _Optional[int] = ..., media_requests_total: _Optional[int] = ..., media_requests_in_flight: _Optional[int] = ..., tl_layer: _Optional[int] = ..., usage_days: _Optional[int] = ..., last_usage_at: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ..., updates_enabled: _Optional[bool] = ..., updates_state_changed_at: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ...) -> None: ...

class GetSessionSubscriptionRequest(_message.Message):
    __slots__ = ("session_peer_id",)
    SESSION_PEER_ID_FIELD_NUMBER: _ClassVar[int]
    session_peer_id: int
    def __init__(self, session_peer_id: _Optional[int] = ...) -> None: ...

class SetSessionUpdatesEnabledRequest(_message.Message):
    __slots__ = ("session_peer_id", "enabled")
    SESSION_PEER_ID_FIELD_NUMBER: _ClassVar[int]
    ENABLED_FIELD_NUMBER: _ClassVar[int]
    session_peer_id: int
    enabled: bool
    def __init__(self, session_peer_id: _Optional[int] = ..., enabled: _Optional[bool] = ...) -> None: ...

class SessionSubscription(_message.Message):
    __slots__ = ("session_peer_id", "updates_enabled", "changed_at")
    SESSION_PEER_ID_FIELD_NUMBER: _ClassVar[int]
    UPDATES_ENABLED_FIELD_NUMBER: _ClassVar[int]
    CHANGED_AT_FIELD_NUMBER: _ClassVar[int]
    session_peer_id: int
    updates_enabled: bool
    changed_at: _timestamp_pb2.Timestamp
    def __init__(self, session_peer_id: _Optional[int] = ..., updates_enabled: _Optional[bool] = ..., changed_at: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ...) -> None: ...

class ListUserSessionsRequest(_message.Message):
    __slots__ = ("page_size", "page_token", "updates_enabled")
    PAGE_SIZE_FIELD_NUMBER: _ClassVar[int]
    PAGE_TOKEN_FIELD_NUMBER: _ClassVar[int]
    UPDATES_ENABLED_FIELD_NUMBER: _ClassVar[int]
    page_size: int
    page_token: str
    updates_enabled: bool
    def __init__(self, page_size: _Optional[int] = ..., page_token: _Optional[str] = ..., updates_enabled: _Optional[bool] = ...) -> None: ...

class ListUserSessionsResponse(_message.Message):
    __slots__ = ("sessions", "next_page_token")
    SESSIONS_FIELD_NUMBER: _ClassVar[int]
    NEXT_PAGE_TOKEN_FIELD_NUMBER: _ClassVar[int]
    sessions: _containers.RepeatedCompositeFieldContainer[IntegrationUserSession]
    next_page_token: str
    def __init__(self, sessions: _Optional[_Iterable[_Union[IntegrationUserSession, _Mapping]]] = ..., next_page_token: _Optional[str] = ...) -> None: ...

class IntegrationUserSession(_message.Message):
    __slots__ = ("session_peer_id", "phone_number", "username", "first_name", "last_name", "state", "updates_enabled", "updates_state_changed_at", "usage_days", "last_usage_at", "linked_at")
    SESSION_PEER_ID_FIELD_NUMBER: _ClassVar[int]
    PHONE_NUMBER_FIELD_NUMBER: _ClassVar[int]
    USERNAME_FIELD_NUMBER: _ClassVar[int]
    FIRST_NAME_FIELD_NUMBER: _ClassVar[int]
    LAST_NAME_FIELD_NUMBER: _ClassVar[int]
    STATE_FIELD_NUMBER: _ClassVar[int]
    UPDATES_ENABLED_FIELD_NUMBER: _ClassVar[int]
    UPDATES_STATE_CHANGED_AT_FIELD_NUMBER: _ClassVar[int]
    USAGE_DAYS_FIELD_NUMBER: _ClassVar[int]
    LAST_USAGE_AT_FIELD_NUMBER: _ClassVar[int]
    LINKED_AT_FIELD_NUMBER: _ClassVar[int]
    session_peer_id: int
    phone_number: str
    username: str
    first_name: str
    last_name: str
    state: str
    updates_enabled: bool
    updates_state_changed_at: _timestamp_pb2.Timestamp
    usage_days: int
    last_usage_at: _timestamp_pb2.Timestamp
    linked_at: _timestamp_pb2.Timestamp
    def __init__(self, session_peer_id: _Optional[int] = ..., phone_number: _Optional[str] = ..., username: _Optional[str] = ..., first_name: _Optional[str] = ..., last_name: _Optional[str] = ..., state: _Optional[str] = ..., updates_enabled: _Optional[bool] = ..., updates_state_changed_at: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ..., usage_days: _Optional[int] = ..., last_usage_at: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ..., linked_at: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ...) -> None: ...

class AuthorizationCodeProvider(_message.Message):
    __slots__ = ("kind", "url", "code_secret", "requires_open_url")
    KIND_FIELD_NUMBER: _ClassVar[int]
    URL_FIELD_NUMBER: _ClassVar[int]
    CODE_SECRET_FIELD_NUMBER: _ClassVar[int]
    REQUIRES_OPEN_URL_FIELD_NUMBER: _ClassVar[int]
    kind: AuthorizationCodeProviderKind
    url: str
    code_secret: str
    requires_open_url: bool
    def __init__(self, kind: _Optional[_Union[AuthorizationCodeProviderKind, str]] = ..., url: _Optional[str] = ..., code_secret: _Optional[str] = ..., requires_open_url: _Optional[bool] = ...) -> None: ...

class BeginPhoneAuthorizationRequest(_message.Message):
    __slots__ = ("phone_number",)
    PHONE_NUMBER_FIELD_NUMBER: _ClassVar[int]
    phone_number: str
    def __init__(self, phone_number: _Optional[str] = ...) -> None: ...

class BeginPhoneAuthorizationResponse(_message.Message):
    __slots__ = ("authorization_id", "expires_at", "code_length", "authorization_kind", "code_provider")
    AUTHORIZATION_ID_FIELD_NUMBER: _ClassVar[int]
    EXPIRES_AT_FIELD_NUMBER: _ClassVar[int]
    CODE_LENGTH_FIELD_NUMBER: _ClassVar[int]
    AUTHORIZATION_KIND_FIELD_NUMBER: _ClassVar[int]
    CODE_PROVIDER_FIELD_NUMBER: _ClassVar[int]
    authorization_id: str
    expires_at: _timestamp_pb2.Timestamp
    code_length: int
    authorization_kind: AuthorizationKind
    code_provider: AuthorizationCodeProvider
    def __init__(self, authorization_id: _Optional[str] = ..., expires_at: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ..., code_length: _Optional[int] = ..., authorization_kind: _Optional[_Union[AuthorizationKind, str]] = ..., code_provider: _Optional[_Union[AuthorizationCodeProvider, _Mapping]] = ...) -> None: ...

class BeginExistingSessionAuthorizationRequest(_message.Message):
    __slots__ = ("session_peer_id",)
    SESSION_PEER_ID_FIELD_NUMBER: _ClassVar[int]
    session_peer_id: int
    def __init__(self, session_peer_id: _Optional[int] = ...) -> None: ...

class BeginExistingSessionAuthorizationResponse(_message.Message):
    __slots__ = ("authorization_id", "expires_at", "code_length", "authorization_kind", "code_provider")
    AUTHORIZATION_ID_FIELD_NUMBER: _ClassVar[int]
    EXPIRES_AT_FIELD_NUMBER: _ClassVar[int]
    CODE_LENGTH_FIELD_NUMBER: _ClassVar[int]
    AUTHORIZATION_KIND_FIELD_NUMBER: _ClassVar[int]
    CODE_PROVIDER_FIELD_NUMBER: _ClassVar[int]
    authorization_id: str
    expires_at: _timestamp_pb2.Timestamp
    code_length: int
    authorization_kind: AuthorizationKind
    code_provider: AuthorizationCodeProvider
    def __init__(self, authorization_id: _Optional[str] = ..., expires_at: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ..., code_length: _Optional[int] = ..., authorization_kind: _Optional[_Union[AuthorizationKind, str]] = ..., code_provider: _Optional[_Union[AuthorizationCodeProvider, _Mapping]] = ...) -> None: ...

class CompleteExistingSessionAuthorizationRequest(_message.Message):
    __slots__ = ("authorization_id", "code")
    AUTHORIZATION_ID_FIELD_NUMBER: _ClassVar[int]
    CODE_FIELD_NUMBER: _ClassVar[int]
    authorization_id: str
    code: str
    def __init__(self, authorization_id: _Optional[str] = ..., code: _Optional[str] = ...) -> None: ...

class CompleteExistingSessionAuthorizationResponse(_message.Message):
    __slots__ = ("session",)
    SESSION_FIELD_NUMBER: _ClassVar[int]
    session: SessionRegistration
    def __init__(self, session: _Optional[_Union[SessionRegistration, _Mapping]] = ...) -> None: ...

class CompletePhoneAuthorizationRequest(_message.Message):
    __slots__ = ("authorization_id", "code")
    AUTHORIZATION_ID_FIELD_NUMBER: _ClassVar[int]
    CODE_FIELD_NUMBER: _ClassVar[int]
    authorization_id: str
    code: str
    def __init__(self, authorization_id: _Optional[str] = ..., code: _Optional[str] = ...) -> None: ...

class CompletePhoneAuthorizationResponse(_message.Message):
    __slots__ = ("state", "password_hint", "session")
    STATE_FIELD_NUMBER: _ClassVar[int]
    PASSWORD_HINT_FIELD_NUMBER: _ClassVar[int]
    SESSION_FIELD_NUMBER: _ClassVar[int]
    state: PhoneAuthorizationState
    password_hint: str
    session: SessionRegistration
    def __init__(self, state: _Optional[_Union[PhoneAuthorizationState, str]] = ..., password_hint: _Optional[str] = ..., session: _Optional[_Union[SessionRegistration, _Mapping]] = ...) -> None: ...

class CompletePasswordAuthorizationRequest(_message.Message):
    __slots__ = ("authorization_id", "password")
    AUTHORIZATION_ID_FIELD_NUMBER: _ClassVar[int]
    PASSWORD_FIELD_NUMBER: _ClassVar[int]
    authorization_id: str
    password: str
    def __init__(self, authorization_id: _Optional[str] = ..., password: _Optional[str] = ...) -> None: ...

class CompletePasswordAuthorizationResponse(_message.Message):
    __slots__ = ("session",)
    SESSION_FIELD_NUMBER: _ClassVar[int]
    session: SessionRegistration
    def __init__(self, session: _Optional[_Union[SessionRegistration, _Mapping]] = ...) -> None: ...

class CancelAuthorizationRequest(_message.Message):
    __slots__ = ("authorization_id",)
    AUTHORIZATION_ID_FIELD_NUMBER: _ClassVar[int]
    authorization_id: str
    def __init__(self, authorization_id: _Optional[str] = ...) -> None: ...

class CancelAuthorizationResponse(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class SessionRegistration(_message.Message):
    __slots__ = ("session_peer_id", "state")
    SESSION_PEER_ID_FIELD_NUMBER: _ClassVar[int]
    STATE_FIELD_NUMBER: _ClassVar[int]
    session_peer_id: int
    state: str
    def __init__(self, session_peer_id: _Optional[int] = ..., state: _Optional[str] = ...) -> None: ...
