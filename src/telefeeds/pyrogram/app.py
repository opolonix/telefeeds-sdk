from __future__ import annotations

import asyncio
import logging
from io import BytesIO
from typing import Any

import grpc
import pyrogram
from pyrogram import handlers
from pyrogram.raw.core import TLObject
from typing_extensions import Self

from telefeeds._core import TelefeedsClient

from .client import MediaStats, TelefeedsClientMixin
from .registrar import HandlerRegistrar
from .session import GrpcSession

log = logging.getLogger(__name__)


class Telefeeds(HandlerRegistrar):
    """Multi-session Pyrogram facade over one Telefeeds gRPC connection."""

    def __init__(
        self,
        token: str,
        *,
        endpoint: str = "telegram.telefeeds.ru:443",
        interface: int | None = None,
        close_other: bool | None = None,
        default_client: type[pyrogram.Client] = pyrogram.Client,
        client_kwargs: dict[str, Any] | None = None,
        secure: bool = True,
        root_certificates: bytes | None = None,
        connect_timeout: float = 15.0,
        invoke_timeout: float = 30.0,
        media_part_timeout: float = 95.0,
        media_retries: int = 3,
        reconnect_max_delay: float = 30.0,
        gateway: TelefeedsClient | None = None,
    ) -> None:
        super().__init__(name="Telefeeds")
        if not isinstance(default_client, type) or not issubclass(
            default_client, pyrogram.Client
        ):
            raise TypeError(
                "default_client must inherit from the installed pyrogram.Client"
            )
        supplied_kwargs = dict(client_kwargs or {})
        managed = {
            "name",
            "session_string",
            "storage_engine",
            "in_memory",
            "no_updates",
            "bot_token",
        }
        conflict = sorted(managed.intersection(supplied_kwargs))
        if conflict:
            raise ValueError(
                f"Telefeeds manages these client_kwargs: {', '.join(conflict)}"
            )
        supplied_kwargs.setdefault("workers", 1)
        supplied_kwargs.setdefault("max_concurrent_transmissions", 4)
        self.default_client = default_client
        self.client_kwargs = supplied_kwargs
        self.interface = interface
        self.close_other = close_other
        self.connect_timeout = connect_timeout
        self.media_part_timeout = media_part_timeout
        self.media_retries = media_retries
        self.reconnect_max_delay = reconnect_max_delay
        self.gateway = gateway or TelefeedsClient(
            token,
            endpoint,
            secure=secure,
            root_certificates=root_certificates,
            default_timeout=invoke_timeout,
        )
        self.client_type = type(
            f"Telefeeds{default_client.__name__}",
            (TelefeedsClientMixin, default_client),
            {"__module__": default_client.__module__},
        )
        self.clients: dict[tuple[str, int], pyrogram.Client] = {}
        self.subscription_task: asyncio.Task[None] | None = None
        self.stopping = False
        self.client_lock = asyncio.Lock()

    async def start_async(self) -> Self:
        if self.subscription_task is not None:
            return self
        await self.gateway.open(timeout=self.connect_timeout)
        self.stopping = False
        self.subscription_task = asyncio.create_task(
            self.consume_updates(),
            name="telefeeds-updates",
        )
        return self

    def start(self) -> Telefeeds | Any:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            try:
                asyncio.run(self.run_async())
            except KeyboardInterrupt:
                pass
            return self
        return self.start_async()

    async def run_async(self) -> None:
        await self.start_async()
        assert self.subscription_task is not None
        try:
            await self.subscription_task
        finally:
            await self.stop_async()

    def run(self) -> None | Any:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return self.start()
        return self.run_async()

    async def stop_async(self) -> None:
        self.stopping = True
        task = self.subscription_task
        self.subscription_task = None
        current_task = asyncio.current_task()
        if task is not None and task is not current_task:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        for client in list(self.clients.values()):
            disconnect_handler = getattr(handlers, "DisconnectHandler", None)
            stop_handler = getattr(handlers, "StopHandler", None)
            if disconnect_handler is not None:
                lifecycle_args = (
                    (client.session,) if hasattr(handlers, "ConnectHandler") else ()
                )
                await self.emit_lifecycle(client, disconnect_handler, *lifecycle_args)
            if stop_handler is not None:
                await self.emit_lifecycle(client, stop_handler)
            await client.storage.close()
            client.executor.shutdown(wait=False, cancel_futures=True)
            client.is_connected = False
            client.is_initialized = False
        self.clients.clear()
        await self.gateway.close()

    def stop(self) -> None | Any:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self.stop_async())
        return self.stop_async()

    async def __aenter__(self) -> Self:
        return await self.start_async()

    async def __aexit__(self, *exc_info: object) -> None:
        await self.stop_async()

    async def get_client(
        self,
        session_peer_id: int,
        session_kind: str = "user",
    ) -> pyrogram.Client:
        key = (session_kind, session_peer_id)
        current = self.clients.get(key)
        if current is not None:
            return current
        async with self.client_lock:
            current = self.clients.get(key)
            if current is not None:
                return current
            kwargs = dict(self.client_kwargs)
            client = self.client_type(
                name=f"telefeeds-{session_kind}-{session_peer_id}",
                in_memory=True,
                no_updates=False,
                **kwargs,
            )
            client.session_peer_id = session_peer_id
            client.session_kind = session_kind
            client.telefeeds = self
            client.media_stats = MediaStats()
            client.media_part_timeout = self.media_part_timeout
            client.media_retries = self.media_retries
            client.loop = asyncio.get_running_loop()
            await client.storage.open()
            await client.storage.user_id(session_peer_id)
            await client.storage.is_bot(session_kind == "bot")
            client.session = GrpcSession(self.gateway, session_peer_id, client)
            client.is_connected = True
            client.is_initialized = True
            self.clients[key] = client
            connect_handler = getattr(handlers, "ConnectHandler", None)
            start_handler = getattr(handlers, "StartHandler", None)
            if connect_handler is not None:
                await self.emit_lifecycle(client, connect_handler, client.session)
            if start_handler is not None:
                await self.emit_lifecycle(client, start_handler)
            return client

    async def invoke(
        self,
        session_peer_id: int,
        query: Any,
        *,
        session_kind: str = "user",
        dc_id: int | None = None,
        **kwargs: Any,
    ) -> Any:
        client = await self.get_client(session_peer_id, session_kind)
        if dc_id is not None:
            return await client.session.invoke_in_dc(query, dc_id, **kwargs)
        return await client.invoke(query, **kwargs)

    async def consume_updates(self) -> None:
        reconnect_delay = 0.5
        while not self.stopping:
            try:
                async for envelope in self.gateway.subscribe(
                    interface=self.interface,
                    close_other=self.close_other,
                ):
                    reconnect_delay = 0.5
                    client = await self.get_client(
                        envelope.session_peer_id,
                        envelope.session_kind,
                    )
                    try:
                        updates = TLObject.read(BytesIO(envelope.body))
                    except (KeyError, TypeError, ValueError) as error:
                        log.error(
                            "Cannot decode TL update for session %s with %s: %s",
                            envelope.session_peer_id,
                            self.default_client.__module__,
                            error,
                        )
                        continue
                    await client.handle_updates(updates)
                    while not client.dispatcher.updates_queue.empty():
                        update, users, chats = (
                            client.dispatcher.updates_queue.get_nowait()
                        )
                        await self.resolve(client, update, users, chats)
            except asyncio.CancelledError:
                raise
            except grpc.aio.AioRpcError as error:
                if error.code() in {
                    grpc.StatusCode.PERMISSION_DENIED,
                    grpc.StatusCode.UNAUTHENTICATED,
                }:
                    raise
                log.warning(
                    "Telefeeds update stream disconnected (%s); reconnecting in %.1fs",
                    error.code().name,
                    reconnect_delay,
                )
                await asyncio.sleep(reconnect_delay)
                reconnect_delay = min(reconnect_delay * 2, self.reconnect_max_delay)

    async def get_session_snapshots(
        self, session_peer_ids: list[int] | tuple[int, ...] = ()
    ):
        return await self.gateway.get_session_snapshots(session_peer_ids)

    async def begin_phone_authorization(self, phone_number: str):
        return await self.gateway.begin_phone_authorization(phone_number)

    async def complete_phone_authorization(self, authorization_id: str, code: str):
        return await self.gateway.complete_phone_authorization(authorization_id, code)

    async def complete_password_authorization(
        self, authorization_id: str, password: str
    ):
        return await self.gateway.complete_password_authorization(
            authorization_id, password
        )
