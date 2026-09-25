from __future__ import annotations

import asyncio
import logging
from collections.abc import Sequence
from contextlib import aclosing

from aiogram import Bot, Dispatcher
from aiogram.types import Update

from telefeeds._core.client import TelefeedsClient
from telefeeds._core.errors import (
    GatewayError,
    GatewayErrorCode,
    SubscriptionReplacedError,
)

from .session import TelefeedsAiogramSession

log = logging.getLogger(__name__)

RETRYABLE_SUBSCRIPTION_CODES = {
    GatewayErrorCode.ABORTED,
    GatewayErrorCode.CANCELLED,
    GatewayErrorCode.DEADLINE_EXCEEDED,
    GatewayErrorCode.INTERNAL,
    GatewayErrorCode.RESOURCE_EXHAUSTED,
    GatewayErrorCode.UNAVAILABLE,
    GatewayErrorCode.UNKNOWN,
}


class Telefeeds(TelefeedsClient):
    """Telefeeds client with an aiogram-native session and update runner."""

    def __init__(
        self,
        token: str,
        endpoint: str = "telegram.telefeeds.ru:443",
        *,
        secure: bool = True,
        root_certificates: bytes | None = None,
        default_timeout: float = 30.0,
        max_message_bytes: int = 16 * 1024 * 1024,
        reconnect_initial_delay: float = 0.5,
        reconnect_max_delay: float = 30.0,
    ) -> None:
        super().__init__(
            token,
            endpoint,
            secure=secure,
            root_certificates=root_certificates,
            default_timeout=default_timeout,
            max_message_bytes=max_message_bytes,
        )
        if reconnect_initial_delay <= 0:
            raise ValueError("reconnect_initial_delay must be greater than zero")
        if reconnect_max_delay < reconnect_initial_delay:
            raise ValueError(
                "reconnect_max_delay must be greater than or equal to "
                "reconnect_initial_delay"
            )
        self.reconnect_initial_delay = reconnect_initial_delay
        self.reconnect_max_delay = reconnect_max_delay

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
        managed_bot = bot is None
        if bot is None:
            bot = Bot(
                token=f"{session_peer_id}:{'A' * 35}",
                session=self.aiogram_session(session_peer_id),
            )
        try:
            reconnect_delay = self.reconnect_initial_delay
            while True:
                try:
                    await self.open()
                except TimeoutError:
                    log.warning(
                        "Telefeeds server is unavailable; reconnecting in %.1fs",
                        reconnect_delay,
                    )
                except GatewayError as error:
                    if error.code not in RETRYABLE_SUBSCRIPTION_CODES:
                        raise
                    reconnect_delay = max(
                        reconnect_delay,
                        error.retry_after or 0,
                    )
                    log.warning(
                        "Telefeeds server is unavailable (%s); reconnecting in %.1fs",
                        error.code.value,
                        reconnect_delay,
                    )
                else:
                    async with aclosing(
                        self.subscribe_bot_api(
                            session_peer_id,
                            allowed_updates=allowed_updates,
                        )
                    ) as updates:
                        while True:
                            try:
                                body = await anext(updates)
                            except StopAsyncIteration:
                                log.warning(
                                    "Telefeeds update stream ended; "
                                    "reconnecting in %.1fs",
                                    reconnect_delay,
                                )
                                break
                            except GatewayError as error:
                                if (
                                    error.code == GatewayErrorCode.CANCELLED
                                    and error.details
                                    == "channel was replaced by close_other"
                                ):
                                    raise SubscriptionReplacedError(
                                        "update subscription was replaced by a close_other connection"
                                    ) from error
                                if error.code not in RETRYABLE_SUBSCRIPTION_CODES:
                                    raise
                                reconnect_delay = max(
                                    reconnect_delay,
                                    error.retry_after or 0,
                                )
                                log.warning(
                                    "Telefeeds update stream disconnected (%s); "
                                    "reconnecting in %.1fs",
                                    error.code.value,
                                    reconnect_delay,
                                )
                                break
                            update = Update.model_validate_json(
                                body, context={"bot": bot}
                            )
                            await dispatcher.feed_update(bot, update)
                            reconnect_delay = self.reconnect_initial_delay
                await asyncio.sleep(reconnect_delay)
                reconnect_delay = min(
                    reconnect_delay * 2,
                    self.reconnect_max_delay,
                )
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
