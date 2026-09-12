from __future__ import annotations

from io import BytesIO
from types import SimpleNamespace

import pytest
from pyrogram import Client, raw
from pyrogram.errors import FilePartMissing
from pyrogram.file_id import FileType
from pyrogram.raw.core import TLObject

from telefeeds import TelegramRPCError
from telefeeds.pyrogram import Router, Telefeeds


class FakeGateway:
    def __init__(self) -> None:
        self.requests: list[tuple[int, object, int | None]] = []
        self.rpc_error: TelegramRPCError | None = None

    async def open(self, *, timeout: float | None = None):
        return self

    async def close(self) -> None:
        return None

    async def invoke_raw(
        self,
        session_peer_id: int,
        body: bytes,
        *,
        dc_id: int | None = None,
        timeout: float | None = None,
    ) -> bytes:
        request = TLObject.read(BytesIO(body))
        self.requests.append((session_peer_id, request, dc_id))
        if self.rpc_error is not None:
            raise self.rpc_error
        if isinstance(request, raw.functions.upload.GetFile):
            return raw.types.upload.File(
                type=raw.types.storage.FileUnknown(),
                mtime=0,
                bytes=b"downloaded",
            ).write()
        return raw.types.BoolTrue().write()


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
    await app.stop_async()
