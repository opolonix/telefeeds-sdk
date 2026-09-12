# telefeeds-sdk

Python SDK для пользовательских Telegram-сессий, запущенных в Telefeeds. Пакет устанавливается как `telefeeds-sdk`, а импортируется как `telefeeds`.

SDK не устанавливает Pyrogram. Приложение само выбирает пакет, который предоставляет пространство имён `pyrogram`, например Kurigram:

```bash
pip install telefeeds-sdk kurigram
```

## Быстрый старт

```python
from pyrogram import Client, filters
from pyrogram.types import Message
from telefeeds.pyrogram import Telefeeds

app = Telefeeds(token="tfi_...")


@app.on_message(filters.incoming & filters.text)
async def incoming(client: Client, message: Message) -> None:
    print(client.session_peer_id, message.chat.id, message.text)


app.start()
```

Один объект `Telefeeds` держит один TLS gRPC-канал и создаёт отдельный экземпляр выбранного `pyrogram.Client` для каждой пользовательской сессии. Поэтому peer cache, `access_hash` и вызовы разных аккаунтов не смешиваются.

`tl_layer` автоматически берётся из `pyrogram.raw.all.layer`. ClientHub принимает слои 227–229:

```python
app = Telefeeds(token="tfi_...", tl_layer=228)
```

## Подписки и переподключение

Параметры `interface` и `close_other` передаются при подписке:

```python
app = Telefeeds(token="tfi_...", interface=7, close_other=True)
```

Каналы одного `interface` делят апдейты между собой. Разные интерфейсы получают собственную копию каждого апдейта. `close_other=True` завершает уже открытые каналы этой интеграции и интерфейса.

При временной сетевой ошибке SDK переподключается без ограничения числа попыток. Задержка растёт от `reconnect_initial_delay=0.5` до `reconnect_max_delay=30.0` секунд. Явный отзыв через `close_other` не переподключает старый канал и поднимает `SubscriptionReplacedError`.

В асинхронном приложении:

```python
async with Telefeeds(token="tfi_...") as app:
    await app.subscription_task
```

## Вызовы и медиа

В обработчике `client` уже связан с нужной сессией:

```python
await client.send_message("me", "hello")
await client.send_document("me", "archive.zip")
path = await client.download_media(message)
```

Вне обработчика клиент можно получить явно:

```python
client = await app.get_client(session_peer_id=123456789)
me = await client.get_me()
```

ClientHub проверяет принадлежность `session_peer_id` интеграции перед каждым `Invoke`. Telegram RPC errors возвращаются как структурированные исключения. Загрузки разбиваются на части, имеют timeout и повтор конкретной части; `cdn_supported=False` устанавливается автоматически.

Низкоуровневый `TelefeedsClient` предоставляет `subscribe()`, `invoke_raw()`, `get_session_snapshots()` и RPC регистрации по телефону. Он работает с protobuf-моделями и не требует Pyrogram.

## Router и примеры

`Router` группирует обработчики и подключается через `app.include_router(router)`. Доступны штатные фильтры и типы установленного Pyrogram-совместимого пакета.

- [Минимальный Pyrogram-клиент](examples/pyrogram_client.py)
- [Telefeeds и aiogram в одном процессе](examples/pyrogram_and_aiogram.py)

```bash
pip install telefeeds-sdk kurigram aiogram
export TELEFEEDS_TOKEN='tfi_...'
export TELEGRAM_BOT_TOKEN='123456:...'
python examples/pyrogram_and_aiogram.py
```

Контракт gRPC v1 находится в [`telefeeds/proto/telegram/v1/gateway.proto`](src/telefeeds/proto/telegram/v1/gateway.proto). Публичный адрес: `telegram.telefeeds.ru:443`; авторизация передаётся как `authorization: Bearer <token>`.

## Сборка пакета

```bash
python -m build
twine check dist/*
```

Публикация релиза запускается GitHub Actions после создания GitHub Release. Для неё нужен Trusted Publisher проекта `telefeeds-sdk` в PyPI.
