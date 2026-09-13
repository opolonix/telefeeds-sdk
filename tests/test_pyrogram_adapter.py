from __future__ import annotations

import asyncio
from io import BytesIO
from types import SimpleNamespace

import pytest
from pyrogram import Client, raw
from pyrogram.errors import FilePartMissing
from pyrogram.file_id import FileType
from pyrogram.raw.core import BoolTrue, TLObject

from telefeeds import (
    GatewayError,
    GatewayErrorCode,
    SubscriptionReplacedError,
    TelegramRPCError,
    UpdateEnvelope,
)
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
        self.session_subscriptions: dict[int, bool] = {}

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
        while True:
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
        if isinstance(request, raw.functions.users.GetFullUser):
            return raw.types.users.UserFull(
                full_user=raw.types.UserFull(
                    id=session_peer_id,
                    settings=raw.types.PeerSettings(),
                    notify_settings=raw.types.PeerNotifySettings(),
                    common_chats_count=0,
                ),
                chats=[],
                users=[
                    raw.types.User(
                        id=session_peer_id,
                        is_self=True,
                        first_name="Telefeeds",
                    )
                ],
            ).write()
        return BoolTrue()

    async def get_session_subscription(self, session_peer_id: int):
        return SimpleNamespace(
            session_peer_id=session_peer_id,
            updates_enabled=self.session_subscriptions.get(session_peer_id, True),
        )

    async def set_session_updates_enabled(self, session_peer_id: int, enabled: bool):
        self.session_subscriptions[session_peer_id] = enabled
        return SimpleNamespace(
            session_peer_id=session_peer_id,
            updates_enabled=enabled,
        )

    async def list_user_sessions(self, **options: object):
        return options

    async def cancel_authorization(self, authorization_id: str) -> None:
        self.cancelled_authorization_id = authorization_id


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
    assert first.me.id == 100
    assert second.me.id == 200
    assert (
        sum(
            isinstance(request, raw.functions.users.GetFullUser)
            for session_peer_id, request, dc_id in gateway.requests
        )
        == 2
    )

    await app.stop_async()


@pytest.mark.asyncio
async def test_session_subscription_controls_use_gateway() -> None:
    gateway = FakeGateway()
    app = Telefeeds("token", gateway=gateway)

    assert await app.is_session_subscribed(100)
    paused = await app.unsubscribe_session(100)
    assert paused.updates_enabled is False
    assert not await app.is_session_subscribed(100)
    resumed = await app.subscribe_session(100)
    assert resumed.updates_enabled is True
    assert await app.list_sessions(page_size=25, updates_enabled=True) == {
        "page_size": 25,
        "page_token": None,
        "updates_enabled": True,
    }
    await app.cancel_authorization("attempt")
    assert gateway.cancelled_authorization_id == "attempt"


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
        GatewayError(GatewayErrorCode.UNAVAILABLE, "temporarily unavailable")
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
        GatewayError(
            GatewayErrorCode.CANCELLED,
            "channel was replaced by close_other",
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
async def test_update_order_is_per_session_and_sessions_run_concurrently() -> None:
    gateway = FakeGateway()
    app = Telefeeds("token", gateway=gateway)
    first_started = asyncio.Event()
    release_first = asyncio.Event()
    second_session_handled = asyncio.Event()
    first_session_finished = asyncio.Event()
    handled: list[tuple[int, int]] = []

    @app.on_raw_update()
    async def handle(client: Client, update, users, chats) -> None:
        handled.append((client.session_peer_id, update.user_id))
        if client.session_peer_id == 100 and update.user_id == 1:
            first_started.set()
            await release_first.wait()
        elif client.session_peer_id == 100 and update.user_id == 2:
            first_session_finished.set()
        elif client.session_peer_id == 200:
            second_session_handled.set()

    await app.start_async()
    for session_peer_id, user_id in ((100, 1), (100, 2), (200, 3)):
        update = raw.types.UpdateShort(
            update=raw.types.UpdateUserStatus(
                user_id=user_id,
                status=raw.types.UserStatusOnline(expires=1),
            ),
            date=1,
        )
        await gateway.subscription_events.put(
            UpdateEnvelope(
                session_peer_id=session_peer_id,
                session_kind="user",
                body=update.write(),
                received_at=None,
                tl_layer=raw.all.layer,
            )
        )

    await asyncio.wait_for(first_started.wait(), 1)
    await asyncio.wait_for(second_session_handled.wait(), 1)
    assert (100, 2) not in handled

    release_first.set()
    await asyncio.wait_for(first_session_finished.wait(), 1)
    assert [item for item in handled if item[0] == 100] == [(100, 1), (100, 2)]
    await app.stop_async()


@pytest.mark.asyncio
async def test_min_peer_refresh_does_not_delay_handler_and_populates_cache() -> None:
    class DifferenceGateway(FakeGateway):
        def __init__(self) -> None:
            super().__init__()
            self.difference_started = asyncio.Event()
            self.release_difference = asyncio.Event()

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
            if isinstance(request, raw.functions.updates.GetChannelDifference):
                self.difference_started.set()
                await self.release_difference.wait()
                return raw.types.updates.ChannelDifference(
                    final=True,
                    pts=2,
                    new_messages=[],
                    other_updates=[],
                    chats=[],
                    users=[
                        raw.types.User(
                            id=7,
                            access_hash=70,
                            first_name="Complete",
                            username="complete_user",
                        )
                    ],
                ).write()
            return await super().invoke_raw(
                session_peer_id,
                body,
                dc_id=dc_id,
                tl_layer=tl_layer,
                timeout=timeout,
            )

    gateway = DifferenceGateway()
    app = Telefeeds(
        "token",
        gateway=gateway,
        peer_refresh_concurrency=1,
        peer_refresh_interval=0,
    )
    received_usernames: list[str | None] = []
    first_handled = asyncio.Event()
    second_handled = asyncio.Event()

    @app.on_raw_update()
    async def handle(client: Client, update, users, chats) -> None:
        received_usernames.append(users[7].username)
        if len(received_usernames) == 1:
            first_handled.set()
        else:
            second_handled.set()

    await app.start_async()
    channel = raw.types.Channel(
        id=123,
        title="Channel",
        photo=raw.types.ChatPhotoEmpty(),
        date=1,
        megagroup=True,
        access_hash=1230,
    )
    for message_id, pts in ((10, 2), (11, 3)):
        updates = raw.types.Updates(
            updates=[
                raw.types.UpdateNewChannelMessage(
                    message=raw.types.Message(
                        id=message_id,
                        peer_id=raw.types.PeerChannel(channel_id=123),
                        from_id=raw.types.PeerUser(user_id=7),
                        date=1,
                        message="message",
                    ),
                    pts=pts,
                    pts_count=1,
                )
            ],
            users=[raw.types.User(id=7, min=True, first_name="Min")],
            chats=[channel],
            date=1,
            seq=pts,
        )
        await gateway.subscription_events.put(
            UpdateEnvelope(
                session_peer_id=100,
                session_kind="user",
                body=updates.write(),
                received_at=None,
                tl_layer=raw.all.layer,
            )
        )
        if message_id == 10:
            await asyncio.wait_for(first_handled.wait(), 1)
            await asyncio.wait_for(gateway.difference_started.wait(), 1)
            assert received_usernames == [None]
            gateway.release_difference.set()
            for attempt in range(100):
                cached = app.peer_cache.get(("user", 100, "user", 7))
                if cached is not None:
                    break
                await asyncio.sleep(0.001)
            assert attempt < 99

    await asyncio.wait_for(second_handled.wait(), 1)
    assert received_usernames == [None, "complete_user"]
    assert not any(
        isinstance(request, raw.functions.updates.GetChannelDifference)
        for session_peer_id, request, dc_id in gateway.requests
    )
    await app.stop_async()


@pytest.mark.asyncio
async def test_structured_file_part_error_becomes_pyrogram_error() -> None:
    gateway = FakeGateway()
    app = Telefeeds("token", gateway=gateway)
    client = await app.get_client(100)
    gateway.rpc_error = TelegramRPCError(400, "FILE_PART_MISSING", value=7)

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
