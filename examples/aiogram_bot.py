import os

from aiogram import Dispatcher
from aiogram.filters import Command
from aiogram.types import Message

from telefeeds.aiogram import Telefeeds

telefeeds = Telefeeds(token=os.environ["TELEFEEDS_TOKEN"])
dispatcher = Dispatcher()


@dispatcher.message(Command("ping"))
async def ping(message: Message) -> None:
    await message.answer("pong")


if __name__ == "__main__":
    telefeeds.run(dispatcher, session_peer_id=int(os.environ["TELEGRAM_BOT_ID"]))
