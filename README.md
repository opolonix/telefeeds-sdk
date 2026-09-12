# telefeeds-sdk

`telefeeds-sdk` connects Python applications to Telegram user sessions running in Telefeeds. The distribution is installed as `telefeeds-sdk` and imported as `telefeeds`.

The SDK deliberately does not depend on Pyrogram. Install the implementation that should provide the `pyrogram` namespace in your application:

```bash
pip install telefeeds-sdk kurigram
```

You can use another compatible distribution instead of Kurigram. `telefeeds.pyrogram` imports its `pyrogram.Client`, raw TL classes, filters and parsers at runtime, so the SDK does not install or replace the client's chosen implementation.

Build and validate release artifacts with `python -m build` and `twine check dist/*`. They can then be uploaded with `twine upload dist/*` or through a PyPI trusted-publishing workflow.

## Pyrogram interface

```python
from telefeeds.pyrogram import Telefeeds
from pyrogram import Client, filters
from pyrogram.types import Message

app = Telefeeds(token="tfi_...")


@app.on_message(filters.text)
async def handle_message(client: Client, message: Message) -> None:
    print(client.session_peer_id, message.chat.id, message.text)
    await message.reply("received")


app.start()
```

`start()` blocks in synchronous code and keeps the update stream alive. In an existing event loop, use the asynchronous lifecycle:

```python
async with Telefeeds(token="tfi_...") as app:
    await app.subscription_task
```

One `Telefeeds` object owns one TLS gRPC channel and any number of lightweight session clients. A separate dynamic subclass and in-memory peer storage are used for each `(session_kind, session_peer_id)`. Methods such as `send_message()`, `get_messages()` and raw `invoke()` therefore resolve peers in the correct account. Direct connection, logout and session export methods raise `NotImplementedError`, because Telefeeds owns the MTProto connection and credentials.

To use a custom client class from the installed Pyrogram-compatible package:

```python
class MyClient(Client):
    pass


app = Telefeeds(token="tfi_...", default_client=MyClient)
```

The generated runtime class inherits `MyClient`; the SDK only replaces its session transport.

## Routers and filters

```python
from telefeeds.pyrogram import Router
from pyrogram import filters

messages = Router(name="messages")


@messages.on_message(filters.private & filters.text)
async def private_text(client, message):
    print(message.text)


app.include_router(messages)
```

Routers use Pyrogram handler and filter objects. A custom filter can attach data directly to the parsed update; the same object is passed to the handler:

```python
from pyrogram.filters import create


async def load_context(filter_object, client, message):
    message.telefeeds_context = {"session_peer_id": client.session_peer_id}
    return True


context_filter = create(load_context, "ContextFilter")


@messages.on_message(context_filter)
async def with_context(client, message):
    print(message.telefeeds_context)
```

All event decorators exposed by the installed implementation can be represented by a regular handler through `add_handler()`. The SDK includes decorators for message, edited/deleted message, callback query, status, inline, poll, member, story, reaction, business, raw update and lifecycle handlers.

## Selecting and invoking a session

Inside a handler, the `client` already belongs to the session that produced the update. Outside handlers:

```python
client = await app.get_client(session_peer_id=123456789)
await client.send_message("me", "hello")

result = await app.invoke(
    123456789,
    pyrogram.raw.functions.users.GetFullUser(
        id=await client.resolve_peer("username")
    ),
)
```

ClientHub checks the access token's integration against `session_peer_id` before forwarding every call. Supplying a session owned by another integration returns gRPC `PERMISSION_DENIED`.

## Media

Normal Pyrogram methods work for uploads and downloads:

```python
await client.send_document("me", "archive.zip")
path = await client.download_media(message)
```

Uploads use 512 KiB parts and up to four concurrent requests for large files. Downloads use 1 MiB parts. Every `upload.GetFile` is sent with `cdn_supported=False`. The SDK applies a deadline and bounded retries to each part; cancellation of the calling asyncio task cancels the current gRPC calls. Pyrogram's `FILE_PART_X_MISSING` flow re-sends only the named part. `FILE_MIGRATE_X` switches the file DC without creating a new public channel. If `FILE_REFERENCE_EXPIRED` is returned while downloading an original `Message`, the SDK fetches that message once and retries with its refreshed reference. A bare file ID cannot be refreshed because it has no source chat/message address.

ClientHub additionally enforces concurrent media limits per access token and per session, applies queue backpressure and reports transferred bytes in session snapshots. Client-side counters are available as `client.media_stats`.

## Session registration

```python
from telefeeds import AuthorizationState, TelefeedsClient

async with TelefeedsClient("tfi_...") as gateway:
    challenge = await gateway.begin_phone_authorization("+995...")
    result = await gateway.complete_phone_authorization(
        challenge.authorization_id,
        input("Telegram code: "),
    )

    if result.state == AuthorizationState.PASSWORD_REQUIRED:
        session = await gateway.complete_password_authorization(
            challenge.authorization_id,
            input("2FA password: "),
        )
    else:
        session = result.session

    print(session.session_peer_id, session.state)
```

The integration's API ID, API hash, device identity and active proxy are managed by ClientHub. Successful authorization automatically imports the session into Core.

## Snapshots and raw transport

```python
snapshots = await app.get_session_snapshots()
for snapshot in snapshots:
    print(snapshot.session_peer_id, snapshot.alive, snapshot.media_upload_bytes)
```

The framework-independent client accepts serialized TL directly:

```python
body = await gateway.invoke_raw(session_peer_id, request.write(), dc_id=4)
```

Telegram RPC failures raise `TelegramRPCError` with `code`, normalized `name`, numeric `value` and `caused_by`. The Pyrogram adapter converts them into the concrete error class supplied by the installed package, including `FilePartMissing`, `FileMigrate` and `FileReferenceExpired`. Gateway and transport failures remain distinct from Telegram RPC errors.

## API versioning

The bundled contract is available at `telefeeds/proto/telegram/v1/gateway.proto`. Its package is `telefeeds.telegram.v1`. Compatible fields and RPCs are added to v1; incompatible changes use a new protobuf package version. The current public endpoint is `telegram.telefeeds.ru:443`, and every RPC sends `authorization: Bearer <integration_access_token>` over TLS.
