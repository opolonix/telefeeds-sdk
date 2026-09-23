from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any, cast

from aiogram.client.bot import Bot
from aiogram.client.session.base import BaseSession
from aiogram.methods import TelegramMethod
from aiogram.methods.base import TelegramType

from telefeeds._core.client import TelefeedsClient


class TelefeedsAiogramSession(BaseSession):
    """aiogram transport backed by Telefeeds gRPC instead of HTTP Bot API."""

    def __init__(self, client: TelefeedsClient, session_peer_id: int) -> None:
        super().__init__()
        if session_peer_id <= 0:
            raise ValueError("session_peer_id must be positive")
        self.client = client
        self.session_peer_id = session_peer_id

    async def close(self) -> None:
        return None

    async def make_request(
        self,
        bot: Bot,
        method: TelegramMethod[TelegramType],
        timeout: int | None = None,
    ) -> TelegramType:
        files: dict[str, Any] = {}
        parameters = {
            name: prepared
            for name, value in method.model_dump(warnings=False).items()
            if (prepared := self.prepare_value(value, bot=bot, files=files, _dumps_json=False))
            is not None
        }
        uploaded: dict[str, str] = {}
        for name, file in files.items():
            uploaded[name] = await self.client.upload_bot_api_file(
                self.session_peer_id,
                file.filename or name,
                file.read(bot),
                timeout=timeout,
            )
        content = await self.client.invoke_bot_api(
            self.session_peer_id,
            method.__api_method__,
            parameters,
            files=uploaded,
            timeout=timeout,
        )
        response = self.check_response(
            bot=bot,
            method=method,
            status_code=200,
            content=content.decode(),
        )
        return cast(TelegramType, response.result)

    async def stream_content(
        self,
        url: str,
        headers: dict[str, Any] | None = None,
        timeout: int = 30,
        chunk_size: int = 65_536,
        raise_for_status: bool = True,
    ) -> AsyncGenerator[bytes, None]:
        file_id = url.rsplit("/", 1)[-1]
        async for chunk in self.client.download_bot_api_file(
            self.session_peer_id,
            telegram_file_id=file_id,
        ):
            yield chunk
