from __future__ import annotations

import asyncio
from collections.abc import Sequence

from aiogram import Bot, Dispatcher
from aiogram.types import Update

from telefeeds._core.client import TelefeedsClient

from .session import TelefeedsAiogramSession


class Telefeeds(TelefeedsClient):
    """Telefeeds client with an aiogram-native session and update runner."""

    def aiogram_session(self, session_peer_id: int) -> TelefeedsAiogramSession:
        return TelefeedsAiogramSession(self, session_peer_id)

    async def start(
        self,
        dispatcher: Dispatcher,
        session_peer_id: int,
        *,
        bot: Bot | None = None,
        allowed_updates: Sequence[str] = (),
    ) -> None:
        await self.open()
        managed_bot = bot is None
        if bot is None:
            bot = Bot(
                token=f"{session_peer_id}:{'A' * 35}",
                session=self.aiogram_session(session_peer_id),
            )
        try:
            async for body in self.subscribe_bot_api(
                session_peer_id,
                allowed_updates=allowed_updates,
            ):
                update = Update.model_validate_json(body, context={"bot": bot})
                await dispatcher.feed_update(bot, update)
        finally:
            if managed_bot:
                await bot.session.close()

    def run(
        self,
        dispatcher: Dispatcher,
        session_peer_id: int,
        *,
        bot: Bot | None = None,
        allowed_updates: Sequence[str] = (),
    ) -> None:
        asyncio.run(
            self.start(
                dispatcher,
                session_peer_id,
                bot=bot,
                allowed_updates=allowed_updates,
            )
        )
