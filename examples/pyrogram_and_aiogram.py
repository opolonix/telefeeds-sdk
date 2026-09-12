import asyncio
import os

from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message as BotMessage
from pyrogram import Client, filters
from pyrogram.types import Message as UserMessage

from telefeeds.pyrogram import Telefeeds

telefeeds = Telefeeds(token=os.environ["TELEFEEDS_TOKEN"])
dispatcher = Dispatcher()


@telefeeds.on_message(filters.incoming & filters.text)
async def user_message(client: Client, message: UserMessage) -> None:
    print("user", client.session_peer_id, message.text, flush=True)


@dispatcher.message(Command("ping"))
async def bot_ping(message: BotMessage) -> None:
    await message.answer("pong")


async def main() -> None:
    bot = Bot(token=os.environ["TELEGRAM_BOT_TOKEN"])
    try:
        async with telefeeds:
            assert telefeeds.subscription_task is not None
            await asyncio.gather(
                telefeeds.subscription_task,
                dispatcher.start_polling(bot),
            )
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
