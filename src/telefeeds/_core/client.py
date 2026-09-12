from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Sequence
from datetime import timezone

import grpc
from typing_extensions import Self

from telefeeds._generated import telefeeds_gateway_v1_pb2 as gateway
from telefeeds._generated import telefeeds_gateway_v1_pb2_grpc as gateway_grpc

from .errors import GatewayInvokeError, TelegramRPCError
from .models import (
    AuthorizationChallenge,
    AuthorizationResult,
    AuthorizationState,
    SessionRegistration,
    SessionSnapshot,
    UpdateEnvelope,
)


class TelefeedsClient:
    """Low-level asynchronous client for the versioned Telefeeds gRPC API."""

    def __init__(
        self,
        token: str,
        endpoint: str = "telegram.telefeeds.ru:443",
        *,
        secure: bool = True,
        root_certificates: bytes | None = None,
        default_timeout: float = 30.0,
        max_message_bytes: int = 16 * 1024 * 1024,
    ) -> None:
        if not token:
            raise ValueError("token must not be empty")
        self.token = token
        self.endpoint = (
            endpoint.removeprefix("https://").removeprefix("http://").rstrip("/")
        )
        self.secure = secure
        self.root_certificates = root_certificates
        self.default_timeout = default_timeout
        self.max_message_bytes = max_message_bytes
        self.channel: grpc.aio.Channel | None = None
        self.stub: gateway_grpc.TelegramGatewayStub | None = None

    @property
    def metadata(self) -> tuple[tuple[str, str], ...]:
        return (("authorization", f"Bearer {self.token}"),)

    async def open(self, *, timeout: float | None = 15.0) -> Self:
        if self.channel is not None:
            return self
        options = (
            ("grpc.max_send_message_length", self.max_message_bytes),
            ("grpc.max_receive_message_length", self.max_message_bytes),
            ("grpc.keepalive_time_ms", 30_000),
            ("grpc.keepalive_timeout_ms", 10_000),
            ("grpc.keepalive_permit_without_calls", 1),
        )
        if self.secure:
            credentials = grpc.ssl_channel_credentials(
                root_certificates=self.root_certificates
            )
            channel = grpc.aio.secure_channel(
                self.endpoint, credentials, options=options
            )
        else:
            channel = grpc.aio.insecure_channel(self.endpoint, options=options)
        try:
            ready = channel.channel_ready()
            if timeout is None:
                await ready
            else:
                await asyncio.wait_for(ready, timeout)
        except BaseException:
            await channel.close()
            raise
        self.channel = channel
        self.stub = gateway_grpc.TelegramGatewayStub(channel)
        return self

    async def close(self) -> None:
        if self.channel is None:
            return
        await self.channel.close()
        self.channel = None
        self.stub = None

    async def __aenter__(self) -> Self:
        return await self.open()

    async def __aexit__(self, *exc_info: object) -> None:
        await self.close()

    def require_stub(self) -> gateway_grpc.TelegramGatewayStub:
        if self.stub is None:
            raise RuntimeError("TelefeedsClient is not open")
        return self.stub

    async def subscribe(
        self,
        *,
        interface: int | None = None,
        close_other: bool | None = None,
        tl_layer: int,
    ) -> AsyncIterator[UpdateEnvelope]:
        request = gateway.SubscribeRequest(tl_layer=tl_layer)
        if interface is not None:
            request.interface = interface
        if close_other is not None:
            request.close_other = close_other
        call = self.require_stub().Subscribe(request, metadata=self.metadata)
        await call.initial_metadata()
        async for event in call:
            received_at = (
                event.received_at.ToDatetime(tzinfo=timezone.utc)
                if event.HasField("received_at")
                else None
            )
            yield UpdateEnvelope(
                session_peer_id=event.session_peer_id,
                session_kind=event.session_kind,
                body=event.body,
                received_at=received_at,
                tl_layer=event.tl_layer,
            )

    async def invoke_raw(
        self,
        session_peer_id: int,
        body: bytes,
        *,
        dc_id: int | None = None,
        tl_layer: int,
        timeout: float | None = None,
    ) -> bytes:
        request = gateway.InvokeRequest(
            session_peer_id=session_peer_id,
            body=body,
            tl_layer=tl_layer,
        )
        if dc_id is not None:
            request.dc_id = dc_id
        response = await self.require_stub().Invoke(
            request,
            metadata=self.metadata,
            timeout=self.default_timeout if timeout is None else timeout,
        )
        if response.HasField("rpc_error"):
            error = response.rpc_error
            raise TelegramRPCError(
                code=error.code,
                name=error.name,
                value=error.value if error.HasField("value") else None,
                caused_by=error.caused_by if error.HasField("caused_by") else None,
            )
        if response.HasField("error"):
            raise GatewayInvokeError(response.error)
        return response.body

    async def get_session_snapshots(
        self,
        session_peer_ids: Sequence[int] = (),
        *,
        timeout: float | None = None,
    ) -> list[SessionSnapshot]:
        response = await self.require_stub().GetSessionSnapshots(
            gateway.GetSessionSnapshotsRequest(session_peer_ids=session_peer_ids),
            metadata=self.metadata,
            timeout=self.default_timeout if timeout is None else timeout,
        )
        return [
            SessionSnapshot(
                session_peer_id=session.session_peer_id,
                state=session.state,
                alive=session.alive,
                fatal=session.fatal,
                proxy_broken=session.proxy_broken,
                uptime_ms=session.uptime_ms,
                updates_per_second=session.updates_per_second,
                invokes_per_second=session.invokes_per_second,
                invokes_in_flight=session.invokes_in_flight,
                memory_bytes=session.memory_bytes,
                updates_total=session.updates_total,
                invokes_total=session.invokes_total,
                last_error=session.last_error
                if session.HasField("last_error")
                else None,
                updated_at=(
                    session.updated_at.ToDatetime(tzinfo=timezone.utc)
                    if session.HasField("updated_at")
                    else None
                ),
                media_upload_bytes=session.media_upload_bytes,
                media_download_bytes=session.media_download_bytes,
                media_requests_total=session.media_requests_total,
                media_requests_in_flight=session.media_requests_in_flight,
                tl_layer=session.tl_layer if session.HasField("tl_layer") else None,
            )
            for session in response.sessions
        ]

    async def begin_phone_authorization(
        self,
        phone_number: str,
        *,
        timeout: float | None = None,
    ) -> AuthorizationChallenge:
        response = await self.require_stub().BeginPhoneAuthorization(
            gateway.BeginPhoneAuthorizationRequest(phone_number=phone_number),
            metadata=self.metadata,
            timeout=self.default_timeout if timeout is None else timeout,
        )
        return AuthorizationChallenge(
            authorization_id=response.authorization_id,
            expires_at=(
                response.expires_at.ToDatetime(tzinfo=timezone.utc)
                if response.HasField("expires_at")
                else None
            ),
        )

    async def complete_phone_authorization(
        self,
        authorization_id: str,
        code: str,
        *,
        timeout: float | None = None,
    ) -> AuthorizationResult:
        response = await self.require_stub().CompletePhoneAuthorization(
            gateway.CompletePhoneAuthorizationRequest(
                authorization_id=authorization_id,
                code=code,
            ),
            metadata=self.metadata,
            timeout=self.default_timeout if timeout is None else timeout,
        )
        session = (
            SessionRegistration(
                session_peer_id=response.session.session_peer_id,
                state=response.session.state,
            )
            if response.HasField("session")
            else None
        )
        return AuthorizationResult(
            state=AuthorizationState(response.state),
            password_hint=response.password_hint
            if response.HasField("password_hint")
            else None,
            session=session,
        )

    async def complete_password_authorization(
        self,
        authorization_id: str,
        password: str,
        *,
        timeout: float | None = None,
    ) -> SessionRegistration:
        response = await self.require_stub().CompletePasswordAuthorization(
            gateway.CompletePasswordAuthorizationRequest(
                authorization_id=authorization_id,
                password=password,
            ),
            metadata=self.metadata,
            timeout=self.default_timeout if timeout is None else timeout,
        )
        return SessionRegistration(
            session_peer_id=response.session.session_peer_id,
            state=response.session.state,
        )
