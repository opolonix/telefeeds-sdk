import asyncio
import os

from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message as BotMessage
from pyrogram import Client, filters
from pyrogram.types import Message as UserMessage

from telefeeds.aiogram import Telefeeds as AiogramTelefeeds
from telefeeds.pyrogram import Telefeeds as PyrogramTelefeeds

user_sessions = PyrogramTelefeeds(token=os.environ["TELEFEEDS_TOKEN"])
bot_api = AiogramTelefeeds(token=os.environ["TELEFEEDS_TOKEN"])
dispatcher = Dispatcher()


@user_sessions.on_message(filters.incoming & filters.text)
async def user_message(client: Client, message: UserMessage) -> None:
    print("user", client.session_peer_id, message.text, flush=True)


@dispatcher.message(Command("ping"))
async def bot_ping(message: BotMessage) -> None:
    await message.answer("pong")


async def main() -> None:
    session_peer_id = int(os.environ["TELEGRAM_BOT_ID"])
    bot = Bot(
        token=f"{session_peer_id}:{'A' * 35}",
        session=bot_api.aiogram_session(session_peer_id),
    )
    async with user_sessions, bot_api:
        assert user_sessions.subscription_task is not None
        try:
            await asyncio.gather(
                user_sessions.subscription_task,
                bot_api.start(dispatcher, session_peer_id, bot=bot),
            )
        finally:
            await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
