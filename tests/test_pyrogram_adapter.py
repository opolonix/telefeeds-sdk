from __future__ import annotations

import asyncio
from io import BytesIO
from types import SimpleNamespace

import grpc
import pytest
from pyrogram import Client, raw
from pyrogram.errors import FilePartMissing
from pyrogram.file_id import FileType
from pyrogram.raw.core import BoolTrue, TLObject

from telefeeds import SubscriptionReplacedError, TelegramRPCError
from telefeeds.pyrogram import Router, Telefeeds


class FakeGateway:
    def __init__(self) -> None:
        self.requests: list[tuple[int, object, int | None]] = []
        self.tl_layers: list[int] = []
        self.rpc_error: TelegramRPCError | None = None
        self.open_errors: list[BaseException] = []
        self.open_attempts = 0
        self.subscription_events: asyncio.Queue[object] = asyncio.Queue()
        self.subscription_attempts = 0

    async def open(self, *, timeout: float | None = None):
        self.open_attempts += 1
        if self.open_errors:
            raise self.open_errors.pop(0)
        return self

    async def close(self) -> None:
        return None

    async def subscribe(
        self,
        *,
        interface: int | None = None,
        close_other: bool | None = None,
        tl_layer: int,
    ):
        self.subscription_attempts += 1
        event = await self.subscription_events.get()
        if isinstance(event, BaseException):
            raise event
        yield event

    async def invoke_raw(
        self,
        session_peer_id: int,
        body: bytes,
        *,
        dc_id: int | None = None,
        tl_layer: int,
        timeout: float | None = None,
    ) -> bytes:
        request = TLObject.read(BytesIO(body))
        self.requests.append((session_peer_id, request, dc_id))
        self.tl_layers.append(tl_layer)
        if self.rpc_error is not None:
            raise self.rpc_error
        if isinstance(request, raw.functions.upload.GetFile):
            return raw.types.upload.File(
                type=raw.types.storage.FileUnknown(),
                mtime=0,
                bytes=b"downloaded",
            ).write()
        return BoolTrue()


@pytest.mark.asyncio
async def test_clients_are_isolated_and_use_selected_client() -> None:
    class SelectedClient(Client):
        pass

    gateway = FakeGateway()
    app = Telefeeds("token", default_client=SelectedClient, gateway=gateway)
    first = await app.get_client(100)
    second = await app.get_client(200)

    assert isinstance(first, SelectedClient)
    assert first is not second
    assert first.storage is not second.storage
    assert first.session.session_peer_id == 100
    assert second.session.session_peer_id == 200

    await app.stop_async()


def test_tl_layer_uses_installed_schema_and_allows_override() -> None:
    assert Telefeeds("token", gateway=FakeGateway()).tl_layer == raw.all.layer
    assert Telefeeds("token", tl_layer=227, gateway=FakeGateway()).tl_layer == 227
    with pytest.raises(ValueError, match="between 227 and 229"):
        Telefeeds("token", tl_layer=226, gateway=FakeGateway())


@pytest.mark.asyncio
async def test_start_retries_until_server_is_available() -> None:
    gateway = FakeGateway()
    gateway.open_errors.append(TimeoutError())
    app = Telefeeds(
        "token",
        gateway=gateway,
        reconnect_initial_delay=0.001,
        reconnect_max_delay=0.002,
    )

    await app.start_async()

    assert gateway.open_attempts == 2
    await app.stop_async()


@pytest.mark.asyncio
async def test_update_stream_reconnects_after_unavailable() -> None:
    gateway = FakeGateway()
    await gateway.subscription_events.put(
        grpc.aio.AioRpcError(grpc.StatusCode.UNAVAILABLE)
    )
    app = Telefeeds(
        "token",
        gateway=gateway,
        reconnect_initial_delay=0.001,
        reconnect_max_delay=0.002,
    )
    await app.start_async()

    for attempt in range(100):
        if gateway.subscription_attempts >= 2:
            break
        await asyncio.sleep(0.001)

    assert attempt < 99
    assert gateway.subscription_attempts == 2
    await app.stop_async()


@pytest.mark.asyncio
async def test_close_other_revocation_is_not_reconnected() -> None:
    gateway = FakeGateway()
    await gateway.subscription_events.put(
        grpc.aio.AioRpcError(
            grpc.StatusCode.CANCELLED,
            details="channel was replaced by close_other",
        )
    )
    app = Telefeeds(
        "token",
        gateway=gateway,
        reconnect_initial_delay=0.001,
        reconnect_max_delay=0.002,
    )
    await app.start_async()
    assert app.subscription_task is not None

    with pytest.raises(SubscriptionReplacedError):
        await app.subscription_task

    assert gateway.subscription_attempts == 1
    await app.stop_async()


@pytest.mark.asyncio
async def test_router_dispatches_raw_update_with_owning_client() -> None:
    gateway = FakeGateway()
    app = Telefeeds("token", gateway=gateway)
    router = Router()
    received: list[tuple[int, int]] = []

    @router.on_raw_update()
    async def handle(client: Client, update, users, chats) -> None:
        received.append((client.session_peer_id, update.user_id))

    app.include_router(router)
    client = await app.get_client(100)
    update = raw.types.UpdateUserStatus(
        user_id=42,
        status=raw.types.UserStatusOnline(expires=1),
    )
    await app.resolve(client, update)

    assert received == [(100, 42)]
    await app.stop_async()


@pytest.mark.asyncio
async def test_structured_file_part_error_becomes_pyrogram_error() -> None:
    gateway = FakeGateway()
    gateway.rpc_error = TelegramRPCError(400, "FILE_PART_MISSING", value=7)
    app = Telefeeds("token", gateway=gateway)
    client = await app.get_client(100)

    with pytest.raises(FilePartMissing) as raised:
        await client.invoke(
            raw.functions.upload.SaveFilePart(file_id=1, file_part=7, bytes=b"x")
        )

    assert getattr(raised.value, "file_part", raised.value.value) == 7
    await app.stop_async()


@pytest.mark.asyncio
async def test_download_forces_cdn_off_and_routes_to_file_dc() -> None:
    gateway = FakeGateway()
    app = Telefeeds("token", gateway=gateway)
    client = await app.get_client(100)
    file_id = SimpleNamespace(
        file_type=FileType.DOCUMENT,
        media_id=11,
        access_hash=22,
        file_reference=b"reference",
        thumbnail_size="",
        dc_id=4,
    )

    chunks = [chunk async for chunk in client.get_file(file_id)]

    assert chunks == [b"downloaded"]
    session_peer_id, request, dc_id = gateway.requests[-1]
    assert session_peer_id == 100
    assert dc_id == 4
    assert request.cdn_supported is False
    assert gateway.tl_layers[-1] == raw.all.layer
    await app.stop_async()


@pytest.mark.asyncio
async def test_upload_uses_file_parts_through_grpc_session() -> None:
    gateway = FakeGateway()
    app = Telefeeds("token", gateway=gateway)
    client = await app.get_client(100)
    source = BytesIO(b"upload payload")
    source.name = "payload.bin"

    uploaded = await client.save_file(source)

    assert isinstance(uploaded, raw.types.InputFile)
    session_peer_id, request, dc_id = gateway.requests[-1]
    assert session_peer_id == 100
    assert dc_id is None
    assert isinstance(request, raw.functions.upload.SaveFilePart)
    assert request.bytes == b"upload payload"
    assert gateway.tl_layers[-1] == raw.all.layer
    assert client.media_stats.uploaded_bytes == len(request.bytes)
    await app.stop_async()
