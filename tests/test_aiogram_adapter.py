from collections.abc import AsyncIterator

import pytest
from aiogram import Bot
from aiogram.methods import GetMe

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
