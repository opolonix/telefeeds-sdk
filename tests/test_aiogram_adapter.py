import asyncio
from collections.abc import AsyncIterator
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiogram import Bot
from aiogram.methods import GetMe

from telefeeds._core.errors import (
    GatewayError,
    GatewayErrorCode,
    SubscriptionReplacedError,
)
from telefeeds.aiogram import Telefeeds


@pytest.mark.asyncio
async def test_aiogram_session_routes_method_through_bot_api_protocol() -> None:
    client = Telefeeds(token="integration-token", secure=False)
    calls: list[tuple[int, str, dict[str, object], dict[str, str]]] = []

    async def invoke(
        session_peer_id: int,
        method: str,
        parameters: dict[str, object],
        *,
        files: dict[str, str] | None = None,
        timeout: float | None = None,
    ) -> bytes:
        calls.append((session_peer_id, method, parameters, files or {}))
        return b'{"ok":true,"result":{"id":42,"is_bot":true,"first_name":"Telefeeds"}}'

    client.invoke_bot_api = invoke  # type: ignore[method-assign]
    session = client.aiogram_session(42)
    bot = Bot(token=f"42:{'A' * 35}", session=session)
    result = await session.make_request(bot, GetMe())

    assert result.id == 42
    assert calls == [(42, "getMe", {}, {})]


@pytest.mark.asyncio
async def test_bot_api_subscription_selects_single_bot() -> None:
    client = Telefeeds(token="integration-token", secure=False)

    async def updates() -> AsyncIterator[bytes]:
        yield b'{"update_id":1}'

    client.subscribe_bot_api = lambda *args, **kwargs: updates()  # type: ignore[method-assign]
    received = [body async for body in client.subscribe_bot_api(42)]
    assert received == [b'{"update_id":1}']


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "disconnect",
    [
        GatewayError(GatewayErrorCode.UNAVAILABLE, "server restarting"),
        GatewayError(GatewayErrorCode.CANCELLED, "transport interrupted"),
        None,
    ],
)
async def test_aiogram_reconnects_after_server_disconnect(
    caplog, disconnect: GatewayError | None
) -> None:
    client = Telefeeds(
        token="integration-token",
        secure=False,
        reconnect_initial_delay=0.001,
        reconnect_max_delay=0.002,
    )
    client.open = AsyncMock(return_value=client)  # type: ignore[method-assign]
    delivered = asyncio.Event()
    feed_update = AsyncMock(side_effect=lambda *args: delivered.set())
    dispatcher = SimpleNamespace(feed_update=feed_update)
    attempts = 0

    async def updates() -> AsyncIterator[bytes]:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            if disconnect is not None:
                raise disconnect
            return
        yield b'{"update_id":1}'
        await asyncio.Future()

    client.subscribe_bot_api = lambda *args, **kwargs: updates()  # type: ignore[method-assign]
    task = asyncio.create_task(client.start(dispatcher, 42))  # type: ignore[arg-type]
    try:
        await asyncio.wait_for(delivered.wait(), timeout=1)
        assert attempts == 2
        assert not task.done()
        assert "reconnecting" in caplog.text
    finally:
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task


@pytest.mark.asyncio
async def test_aiogram_retries_initial_connection(caplog) -> None:
    client = Telefeeds(
        token="integration-token",
        secure=False,
        reconnect_initial_delay=0.001,
        reconnect_max_delay=0.002,
    )
    client.open = AsyncMock(side_effect=[TimeoutError(), None])  # type: ignore[method-assign]
    subscribed = asyncio.Event()

    async def updates() -> AsyncIterator[bytes]:
        subscribed.set()
        await asyncio.Future()
        yield b'{"update_id":1}'

    client.subscribe_bot_api = lambda *args, **kwargs: updates()  # type: ignore[method-assign]
    dispatcher = SimpleNamespace(feed_update=AsyncMock())
    task = asyncio.create_task(client.start(dispatcher, 42))  # type: ignore[arg-type]
    try:
        await asyncio.wait_for(subscribed.wait(), timeout=1)
        assert client.open.await_count == 2
        assert "server is unavailable" in caplog.text
    finally:
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (GatewayError(GatewayErrorCode.UNAUTHENTICATED, "bad token"), GatewayError),
        (
            GatewayError(
                GatewayErrorCode.CANCELLED,
                "channel was replaced by close_other",
            ),
            SubscriptionReplacedError,
        ),
    ],
)
async def test_aiogram_does_not_retry_fatal_subscription_errors(
    error: GatewayError,
    expected: type[Exception],
) -> None:
    client = Telefeeds(token="integration-token", secure=False)
    client.open = AsyncMock(return_value=client)  # type: ignore[method-assign]
    attempts = 0

    async def updates() -> AsyncIterator[bytes]:
        nonlocal attempts
        attempts += 1
        raise error
        yield b'{"update_id":1}'

    client.subscribe_bot_api = lambda *args, **kwargs: updates()  # type: ignore[method-assign]
    dispatcher = SimpleNamespace(feed_update=AsyncMock())
    with pytest.raises(expected):
        await client.start(dispatcher, 42)  # type: ignore[arg-type]
    assert attempts == 1
