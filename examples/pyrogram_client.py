import os

from pyrogram import Client, filters
from pyrogram.types import Message

from telefeeds.pyrogram import Telefeeds

app = Telefeeds(token=os.environ["TELEFEEDS_TOKEN"])


@app.on_message(filters.incoming & filters.text)
async def incoming(client: Client, message: Message) -> None:
    print(client.session_peer_id, message.chat.id, message.text, flush=True)


if __name__ == "__main__":
    app.start()
