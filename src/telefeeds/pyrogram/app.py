from __future__ import annotations

import asyncio
import logging
from collections import OrderedDict
from io import BytesIO
from typing import Any

import pyrogram
from pyrogram import handlers, raw, utils
from pyrogram.raw.core import TLObject
from typing_extensions import Self

from telefeeds._core import (
    AuthorizationChallenge,
    AuthorizationResult,
    GatewayError,
    GatewayErrorCode,
    IntegrationSnapshot,
    SessionRegistration,
    SessionSnapshot,
    SessionSubscription,
    SubscriptionReplacedError,
    TelefeedsClient,
    UpdateEnvelope,
    UserSessionPage,
)

from .client import MediaStats, TelefeedsClientMixin
from .registrar import HandlerRegistrar
from .session import GrpcSession

log = logging.getLogger(__name__)

RETRYABLE_SUBSCRIPTION_CODES = {
    GatewayErrorCode.ABORTED,
    GatewayErrorCode.DEADLINE_EXCEEDED,
    GatewayErrorCode.INTERNAL,
    GatewayErrorCode.RESOURCE_EXHAUSTED,
    GatewayErrorCode.UNAVAILABLE,
    GatewayErrorCode.UNKNOWN,
}


class Telefeeds(HandlerRegistrar):
    """Multi-session Pyrogram facade over one Telefeeds gRPC connection."""

    def __init__(
        self,
        token: str,
        *,
        endpoint: str = "telegram.telefeeds.ru:443",
        interface: int | None = None,
        close_other: bool | None = None,
        tl_layer: int | None = None,
        default_client: type[pyrogram.Client] = pyrogram.Client,
        client_kwargs: dict[str, Any] | None = None,
        secure: bool = True,
        root_certificates: bytes | None = None,
        connect_timeout: float = 15.0,
        invoke_timeout: float = 30.0,
        media_part_timeout: float = 95.0,
        media_retries: int = 3,
        reconnect_initial_delay: float = 0.5,
        reconnect_max_delay: float = 30.0,
        peer_refresh_concurrency: int = 4,
        peer_refresh_interval: float = 300.0,
        peer_cache_size: int = 10_000,
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
        supplied_kwargs.setdefault("fetch_replies", False)
        self.default_client = default_client
        self.tl_layer = int(pyrogram.raw.all.layer) if tl_layer is None else tl_layer
        if not 227 <= self.tl_layer <= 229:
            raise ValueError("tl_layer must be between 227 and 229")
        self.client_kwargs = supplied_kwargs
        self.interface = interface
        self.close_other = close_other
        self.connect_timeout = connect_timeout
        self.media_part_timeout = media_part_timeout
        self.media_retries = media_retries
        if reconnect_initial_delay <= 0:
            raise ValueError("reconnect_initial_delay must be greater than zero")
        if reconnect_max_delay < reconnect_initial_delay:
            raise ValueError(
                "reconnect_max_delay must be greater than or equal to "
                "reconnect_initial_delay"
            )
        self.reconnect_initial_delay = reconnect_initial_delay
        self.reconnect_max_delay = reconnect_max_delay
        if peer_refresh_concurrency <= 0:
            raise ValueError("peer_refresh_concurrency must be greater than zero")
        if peer_refresh_interval < 0:
            raise ValueError("peer_refresh_interval must not be negative")
        if peer_cache_size <= 0:
            raise ValueError("peer_cache_size must be greater than zero")
        self.peer_refresh_concurrency = peer_refresh_concurrency
        self.peer_refresh_interval = peer_refresh_interval
        self.peer_cache_size = peer_cache_size
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
        self.gateway.providers.interface_id = interface or 0
        self.make_set = self.gateway.make_set
        self.make_dataset = self.gateway.make_dataset
        self.clients: dict[tuple[str, int], pyrogram.Client] = {}
        self.client_initializers: dict[
            tuple[str, int], asyncio.Task[pyrogram.Client]
        ] = {}
        self.update_queues: dict[tuple[str, int], asyncio.Queue[UpdateEnvelope]] = {}
        self.update_workers: dict[tuple[str, int], asyncio.Task[None]] = {}
        self.peer_cache: OrderedDict[tuple[str, int, str, int], Any] = OrderedDict()
        self.peer_refresh_queue: asyncio.Queue[tuple[str, int, int]] = asyncio.Queue()
        self.peer_refresh_pending: dict[
            tuple[str, int, int], tuple[pyrogram.Client, int, int, int]
        ] = {}
        self.peer_refresh_inflight: set[tuple[str, int, int]] = set()
        self.peer_refresh_next_at: dict[tuple[str, int, int], float] = {}
        self.peer_refresh_workers: list[asyncio.Task[None]] = []
        self.subscription_task: asyncio.Task[None] | None = None
        self.stopping = False

    async def start_async(self) -> Self:
        if self.subscription_task is not None:
            if self.subscription_task.done():
                self.subscription_task.result()
            return self
        self.stopping = False
        reconnect_delay = self.reconnect_initial_delay
        while True:
            try:
                await self.gateway.open(timeout=self.connect_timeout)
                break
            except TimeoutError as error:
                log.warning(
                    "Telefeeds server is unavailable during startup (%s); "
                    "reconnecting in %.1fs",
                    type(error).__name__,
                    reconnect_delay,
                )
            except GatewayError as error:
                if error.code not in RETRYABLE_SUBSCRIPTION_CODES:
                    raise
                log.warning(
                    "Telefeeds server is unavailable during startup (%s); "
                    "reconnecting in %.1fs",
                    error.code.value,
                    reconnect_delay,
                )
            await asyncio.sleep(reconnect_delay)
            reconnect_delay = min(
                reconnect_delay * 2,
                self.reconnect_max_delay,
            )
        self.subscription_task = asyncio.create_task(
            self.consume_updates(),
            name="telefeeds-updates",
        )
        self.peer_refresh_workers = [
            asyncio.create_task(
                self.consume_peer_refreshes(),
                name=f"telefeeds-peer-refresh-{worker_index}",
            )
            for worker_index in range(self.peer_refresh_concurrency)
        ]
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
            if task.cancelled():
                pass
            elif task.done():
                task.exception()
            else:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        background_tasks = [
            *self.update_workers.values(),
            *self.client_initializers.values(),
            *self.peer_refresh_workers,
        ]
        for background_task in background_tasks:
            if background_task is not current_task and not background_task.done():
                background_task.cancel()
        awaited_tasks = [
            background_task
            for background_task in background_tasks
            if background_task is not current_task
        ]
        if awaited_tasks:
            results = await asyncio.gather(*awaited_tasks, return_exceptions=True)
            for result in results:
                if isinstance(result, BaseException) and not isinstance(
                    result, asyncio.CancelledError
                ):
                    log.error(
                        "Telefeeds background task failed during shutdown: %r",
                        result,
                    )
        self.update_queues.clear()
        self.update_workers.clear()
        self.client_initializers.clear()
        self.peer_cache.clear()
        self.peer_refresh_pending.clear()
        self.peer_refresh_inflight.clear()
        self.peer_refresh_next_at.clear()
        self.peer_refresh_workers.clear()
        self.peer_refresh_queue = asyncio.Queue()
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
        initializer = self.client_initializers.get(key)
        if initializer is None:
            initializer = asyncio.create_task(
                self.create_client(session_peer_id, session_kind),
                name=f"telefeeds-client-{session_kind}-{session_peer_id}",
            )
            self.client_initializers[key] = initializer
        try:
            return await asyncio.shield(initializer)
        finally:
            if initializer.done() and self.client_initializers.get(key) is initializer:
                del self.client_initializers[key]

    async def create_client(
        self, session_peer_id: int, session_kind: str
    ) -> pyrogram.Client:
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
        try:
            client.me = await client.get_me()
        except BaseException:
            await client.storage.close()
            client.executor.shutdown(wait=False, cancel_futures=True)
            client.is_connected = False
            client.is_initialized = False
            raise
        self.clients[(session_kind, session_peer_id)] = client
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
        reconnect_delay = self.reconnect_initial_delay
        while not self.stopping:
            try:
                async for envelope in self.gateway.subscribe(
                    interface=self.interface,
                    close_other=self.close_other,
                    tl_layer=self.tl_layer,
                ):
                    if envelope.tl_layer != self.tl_layer:
                        raise RuntimeError(
                            "ClientHub returned TL layer "
                            f"{envelope.tl_layer}, expected {self.tl_layer}"
                        )
                    reconnect_delay = 0.5
                    key = (envelope.session_kind, envelope.session_peer_id)
                    queue = self.update_queues.get(key)
                    if queue is None:
                        queue = asyncio.Queue()
                        self.update_queues[key] = queue
                        self.update_workers[key] = asyncio.create_task(
                            self.consume_session_updates(key, queue),
                            name=(
                                f"telefeeds-updates-{envelope.session_kind}-"
                                f"{envelope.session_peer_id}"
                            ),
                        )
                    queue.put_nowait(envelope)
                if self.stopping:
                    return
                log.warning(
                    "Telefeeds update stream ended; reconnecting in %.1fs",
                    reconnect_delay,
                )
            except asyncio.CancelledError:
                raise
            except GatewayError as error:
                if (
                    error.code == GatewayErrorCode.CANCELLED
                    and error.details == "channel was replaced by close_other"
                ):
                    raise SubscriptionReplacedError(
                        "update subscription was replaced by a close_other connection"
                    ) from error
                if error.code not in RETRYABLE_SUBSCRIPTION_CODES:
                    raise
                log.warning(
                    "Telefeeds update stream disconnected (%s); reconnecting in %.1fs",
                    error.code.value,
                    reconnect_delay,
                )
            await asyncio.sleep(reconnect_delay)
            reconnect_delay = min(reconnect_delay * 2, self.reconnect_max_delay)

    async def consume_session_updates(
        self,
        key: tuple[str, int],
        queue: asyncio.Queue[UpdateEnvelope],
    ) -> None:
        while not self.stopping:
            envelope = await queue.get()
            try:
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

                refreshes: list[tuple[int, int, int, int]] = []
                if isinstance(updates, (raw.types.Updates, raw.types.UpdatesCombined)):
                    missing_min_peers = False
                    for peer_kind, attribute in (
                        ("user", "users"),
                        ("chat", "chats"),
                    ):
                        peers = getattr(updates, attribute)
                        resolved_peers = []
                        for peer in peers:
                            peer_id = getattr(peer, "id", None)
                            cache_key = (
                                key[0],
                                key[1],
                                peer_kind,
                                peer_id,
                            )
                            if getattr(peer, "min", False) and peer_id is not None:
                                cached_peer = self.peer_cache.get(cache_key)
                                if cached_peer is None:
                                    missing_min_peers = True
                                else:
                                    peer = cached_peer
                                    self.peer_cache.move_to_end(cache_key)
                            elif peer_id is not None:
                                self.cache_peer(cache_key, peer)
                            resolved_peers.append(peer)
                        setattr(updates, attribute, resolved_peers)

                    if missing_min_peers:
                        for update in updates.updates:
                            if not isinstance(
                                update, raw.types.UpdateNewChannelMessage
                            ):
                                continue
                            channel_id = getattr(
                                getattr(update.message, "peer_id", None),
                                "channel_id",
                                None,
                            )
                            if channel_id is not None:
                                refreshes.append(
                                    (
                                        channel_id,
                                        update.message.id,
                                        update.pts,
                                        update.pts_count,
                                    )
                                )

                await client.handle_updates(updates)
                now = asyncio.get_running_loop().time()
                for channel_id, message_id, pts, pts_count in refreshes:
                    refresh_key = (key[0], key[1], channel_id)
                    if refresh_key in self.peer_refresh_inflight:
                        continue
                    if now < self.peer_refresh_next_at.get(refresh_key, 0.0):
                        continue
                    pending = refresh_key in self.peer_refresh_pending
                    self.peer_refresh_pending[refresh_key] = (
                        client,
                        message_id,
                        pts,
                        pts_count,
                    )
                    if not pending:
                        self.peer_refresh_queue.put_nowait(refresh_key)

                while not client.dispatcher.updates_queue.empty():
                    update, users, chats = client.dispatcher.updates_queue.get_nowait()
                    await self.resolve(client, update, users, chats)
            except asyncio.CancelledError:
                raise
            except Exception:
                log.exception(
                    "Cannot process TL update for session %s", envelope.session_peer_id
                )
            finally:
                queue.task_done()

    async def consume_peer_refreshes(self) -> None:
        while not self.stopping:
            refresh_key = await self.peer_refresh_queue.get()
            request = self.peer_refresh_pending.pop(refresh_key, None)
            if request is None:
                self.peer_refresh_queue.task_done()
                continue
            client, message_id, pts, pts_count = request
            self.peer_refresh_inflight.add(refresh_key)
            try:
                channel_id = refresh_key[2]
                channel = await client.resolve_peer(utils.get_channel_id(channel_id))
                difference = await client.invoke(
                    raw.functions.updates.GetChannelDifference(
                        channel=channel,
                        filter=raw.types.ChannelMessagesFilter(
                            ranges=[
                                raw.types.MessageRange(
                                    min_id=message_id,
                                    max_id=message_id,
                                )
                            ]
                        ),
                        pts=max(0, pts - pts_count),
                        limit=max(1, pts),
                        force=False,
                    )
                )
                peers = [
                    *getattr(difference, "users", ()),
                    *getattr(difference, "chats", ()),
                ]
                for peer in peers:
                    peer_id = getattr(peer, "id", None)
                    if peer_id is None or getattr(peer, "min", False):
                        continue
                    peer_kind = "user" if isinstance(peer, raw.types.User) else "chat"
                    cache_key = (
                        refresh_key[0],
                        refresh_key[1],
                        peer_kind,
                        peer_id,
                    )
                    self.cache_peer(cache_key, peer)
            except asyncio.CancelledError:
                raise
            except (
                pyrogram.errors.ChannelPrivate,
                pyrogram.errors.PersistentTimestampEmpty,
                pyrogram.errors.PersistentTimestampInvalid,
                pyrogram.errors.PersistentTimestampOutdated,
            ) as error:
                log.debug(
                    "Cannot refresh min peers for session %s channel %s: %s",
                    refresh_key[1],
                    refresh_key[2],
                    error,
                )
            except Exception:
                log.exception(
                    "Cannot refresh min peers for session %s channel %s",
                    refresh_key[1],
                    refresh_key[2],
                )
            finally:
                self.peer_refresh_inflight.discard(refresh_key)
                self.peer_refresh_next_at[refresh_key] = (
                    asyncio.get_running_loop().time() + self.peer_refresh_interval
                )
                self.peer_refresh_queue.task_done()

    def cache_peer(
        self,
        cache_key: tuple[str, int, str, int],
        peer: Any,
    ) -> None:
        self.peer_cache[cache_key] = peer
        self.peer_cache.move_to_end(cache_key)
        while len(self.peer_cache) > self.peer_cache_size:
            expired_key = self.peer_cache.popitem(last=False)[0]
            if expired_key[2] == "chat":
                self.peer_refresh_next_at.pop(
                    (expired_key[0], expired_key[1], expired_key[3]),
                    None,
                )

    async def get_session_snapshots(
        self, session_peer_ids: list[int] | tuple[int, ...] = ()
    ) -> list[SessionSnapshot]:
        return await self.gateway.get_session_snapshots(session_peer_ids)

    async def get_integration_snapshot(self) -> IntegrationSnapshot:
        return await self.gateway.get_integration_snapshot()

    async def get_session_subscription(
        self, session_peer_id: int
    ) -> SessionSubscription:
        return await self.gateway.get_session_subscription(session_peer_id)

    async def is_session_subscribed(self, session_peer_id: int) -> bool:
        subscription = await self.get_session_subscription(session_peer_id)
        return subscription.updates_enabled

    async def unsubscribe_session(self, session_peer_id: int) -> SessionSubscription:
        return await self.gateway.set_session_updates_enabled(session_peer_id, False)

    async def subscribe_session(self, session_peer_id: int) -> SessionSubscription:
        return await self.gateway.set_session_updates_enabled(session_peer_id, True)

    async def list_sessions(
        self,
        *,
        page_size: int = 300,
        page_token: str | None = None,
        updates_enabled: bool | None = None,
    ) -> UserSessionPage:
        return await self.gateway.list_user_sessions(
            page_size=page_size,
            page_token=page_token,
            updates_enabled=updates_enabled,
        )

    async def begin_phone_authorization(
        self, phone_number: str
    ) -> AuthorizationChallenge:
        return await self.gateway.begin_phone_authorization(phone_number)

    async def begin_existing_session_authorization(
        self, session_peer_id: int
    ) -> AuthorizationChallenge:
        return await self.gateway.begin_existing_session_authorization(session_peer_id)

    async def complete_existing_session_authorization(
        self, authorization_id: str, code: str
    ) -> SessionRegistration:
        return await self.gateway.complete_existing_session_authorization(
            authorization_id, code
        )

    async def complete_phone_authorization(
        self, authorization_id: str, code: str
    ) -> AuthorizationResult:
        return await self.gateway.complete_phone_authorization(authorization_id, code)

    async def complete_password_authorization(
        self, authorization_id: str, password: str
    ) -> SessionRegistration:
        return await self.gateway.complete_password_authorization(
            authorization_id, password
        )

    async def cancel_authorization(self, authorization_id: str) -> None:
        await self.gateway.cancel_authorization(authorization_id)
