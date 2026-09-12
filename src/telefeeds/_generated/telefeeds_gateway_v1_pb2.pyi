import datetime

from google.protobuf import timestamp_pb2 as _timestamp_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class PhoneAuthorizationState(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    PHONE_AUTHORIZATION_STATE_UNSPECIFIED: _ClassVar[PhoneAuthorizationState]
    PHONE_AUTHORIZATION_STATE_PASSWORD_REQUIRED: _ClassVar[PhoneAuthorizationState]
    PHONE_AUTHORIZATION_STATE_AUTHORIZED: _ClassVar[PhoneAuthorizationState]
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
    __slots__ = ("session_peer_id", "session_kind", "body", "received_at")
    SESSION_PEER_ID_FIELD_NUMBER: _ClassVar[int]
    SESSION_KIND_FIELD_NUMBER: _ClassVar[int]
    BODY_FIELD_NUMBER: _ClassVar[int]
    RECEIVED_AT_FIELD_NUMBER: _ClassVar[int]
    session_peer_id: int
    session_kind: str
    body: bytes
    received_at: _timestamp_pb2.Timestamp
    def __init__(self, session_peer_id: _Optional[int] = ..., session_kind: _Optional[str] = ..., body: _Optional[bytes] = ..., received_at: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ...) -> None: ...

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
    __slots__ = ("session_peer_id", "state", "alive", "fatal", "proxy_broken", "uptime_ms", "updates_per_second", "invokes_per_second", "invokes_in_flight", "memory_bytes", "updates_total", "invokes_total", "last_error", "updated_at", "media_upload_bytes", "media_download_bytes", "media_requests_total", "media_requests_in_flight", "tl_layer")
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
    def __init__(self, session_peer_id: _Optional[int] = ..., state: _Optional[str] = ..., alive: _Optional[bool] = ..., fatal: _Optional[bool] = ..., proxy_broken: _Optional[bool] = ..., uptime_ms: _Optional[int] = ..., updates_per_second: _Optional[float] = ..., invokes_per_second: _Optional[float] = ..., invokes_in_flight: _Optional[int] = ..., memory_bytes: _Optional[int] = ..., updates_total: _Optional[int] = ..., invokes_total: _Optional[int] = ..., last_error: _Optional[str] = ..., updated_at: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ..., media_upload_bytes: _Optional[int] = ..., media_download_bytes: _Optional[int] = ..., media_requests_total: _Optional[int] = ..., media_requests_in_flight: _Optional[int] = ..., tl_layer: _Optional[int] = ...) -> None: ...

class BeginPhoneAuthorizationRequest(_message.Message):
    __slots__ = ("phone_number",)
    PHONE_NUMBER_FIELD_NUMBER: _ClassVar[int]
    phone_number: str
    def __init__(self, phone_number: _Optional[str] = ...) -> None: ...

class BeginPhoneAuthorizationResponse(_message.Message):
    __slots__ = ("authorization_id", "expires_at")
    AUTHORIZATION_ID_FIELD_NUMBER: _ClassVar[int]
    EXPIRES_AT_FIELD_NUMBER: _ClassVar[int]
    authorization_id: str
    expires_at: _timestamp_pb2.Timestamp
    def __init__(self, authorization_id: _Optional[str] = ..., expires_at: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ...) -> None: ...

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

class SessionRegistration(_message.Message):
    __slots__ = ("session_peer_id", "state")
    SESSION_PEER_ID_FIELD_NUMBER: _ClassVar[int]
    STATE_FIELD_NUMBER: _ClassVar[int]
    session_peer_id: int
    state: str
    def __init__(self, session_peer_id: _Optional[int] = ..., state: _Optional[str] = ...) -> None: ...
