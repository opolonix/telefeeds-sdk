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

app = Telefeeds(token="telefeeds_...")


@app.on_message(filters.incoming & filters.text)
async def incoming(client: Client, message: Message) -> None:
    print(client.session_peer_id, message.chat.id, message.text)


app.start()
```

Один объект `Telefeeds` держит один TLS gRPC-канал и создаёт отдельный экземпляр выбранного `pyrogram.Client` для каждой пользовательской сессии. До передачи клиента обработчикам SDK выполняет `get_me()` через ClientHub и заполняет `client.me`. Поэтому peer cache, `access_hash` и вызовы разных аккаунтов не смешиваются.

Входящий gRPC-поток только раскладывает апдейты по очередям сессий. Внутри одной сессии порядок сохраняется, а разные сессии обрабатываются параллельно: медленный обработчик активного чата не останавливает остальные аккаунты.

Kurigram иногда присылает в channel update сокращённые (`min`) профили и штатно делает синхронный `GetChannelDifference` перед вызовом обработчика. Telefeeds отдаёт такой апдейт обработчику сразу, а недостающие профили дополняет в фоне и сохраняет в peer cache. Число фоновых запросов и пауза между повторными дополнениями одного канала задаются через `peer_refresh_concurrency` и `peer_refresh_interval`:

```python
app = Telefeeds(
    token="telefeeds_...",
    peer_refresh_concurrency=4,
    peer_refresh_interval=300.0,
)
```

По умолчанию `fetch_replies=False`, чтобы разбор сообщения не ожидал дополнительный Telegram RPC для исходного сообщения ответа. При необходимости это можно явно изменить через `client_kwargs={"fetch_replies": True}`.

`tl_layer` автоматически берётся из `pyrogram.raw.all.layer`. ClientHub принимает слои 227–229:

```python
app = Telefeeds(token="telefeeds_...", tl_layer=228)
```

## Подписки и переподключение

Параметры `interface` и `close_other` передаются при подписке:

```python
app = Telefeeds(token="telefeeds_...", interface=7, close_other=True)
```

Каналы одного `interface` делят апдейты между собой. Разные интерфейсы получают собственную копию каждого апдейта. `close_other=True` завершает уже открытые каналы этой интеграции и интерфейса.

При временной сетевой ошибке SDK переподключается без ограничения числа попыток. Задержка растёт от `reconnect_initial_delay=0.5` до `reconnect_max_delay=30.0` секунд. Явный отзыв через `close_other` не переподключает старый канал и поднимает `SubscriptionReplacedError`.

Апдейты отдельной сессии можно остановить и вернуть без остановки самой сессии в Telefeeds:

```python
await app.unsubscribe_session(peer_id)
assert not await app.is_session_subscribed(peer_id)

await app.subscribe_session(peer_id)
```

Пауза действует сразу для всех каналов интеграции. Вызовы через эту сессию остаются доступны. День без активной подписки не начисляется, если интеграция не обращалась к сессии через `Invoke`.

В асинхронном приложении:

```python
async with Telefeeds(token="telefeeds_...") as app:
    await app.subscription_task
```

## Вызовы и медиа

В обработчике `client` уже связан с нужной сессией:

```python
await client.send_message("me", "hello")
await client.send_document("me", "archive.zip")
path = await client.download_media(message)
```

Загрузка файлов выполняется частями по 512 КиБ с `cdn_supported=False`, чтобы каждый ответ гарантированно помещался в MTProto-контейнер Bridge.

Вне обработчика клиент можно получить явно:

```python
client = await app.get_client(session_peer_id=123456789)
me = await client.get_me()
```

ClientHub проверяет принадлежность `session_peer_id` интеграции перед каждым `Invoke`. Telegram RPC errors возвращаются как структурированные исключения. Загрузки разбиваются на части, имеют timeout и повтор конкретной части; `cdn_supported=False` устанавливается автоматически.

Ошибки ClientHub доступны как `GatewayError` с независимыми от grpcio полями `code: GatewayErrorCode` и `details`. Низкоуровневые `grpc.aio.AioRpcError` не выходят из SDK. Ожидаемые ошибки регистрации представлены отдельными классами:

```python
from telefeeds import (
    AuthorizationAttemptExpiredError,
    InvalidAuthorizationCodeError,
    InvalidAuthorizationPasswordError,
)

try:
    session = await gateway.complete_password_authorization(authorization_id, password)
except InvalidAuthorizationPasswordError:
    print("Неверный пароль")
except AuthorizationAttemptExpiredError:
    print("Попытка авторизации истекла")
```

Полная иерархия начинается с `AuthorizationError`. Для сырого gRPC-клиента ClientHub передаёт стабильную причину в trailing metadata `telefeeds-error-code`; значения перечислены в `AuthorizationErrorCode` protobuf-контракта.

Низкоуровневый `TelefeedsClient` предоставляет `subscribe()`, `invoke_raw()`, `get_session_snapshots()` и RPC регистрации. Он работает с protobuf-моделями и не требует Pyrogram.

Информацию об интеграции и компактные счётчики можно получить одним дешёвым запросом без обращения к Core и MetricsHub:

```python
snapshot = await app.get_integration_snapshot()
print(snapshot.integration_id, snapshot.name, snapshot.granted_scopes)
print(snapshot.metrics.user_sessions_total)
print(snapshot.metrics.active_connections)
```

Снапшот содержит эффективные значения `default_interface` и `default_close_other`, настройки доступа к пользовательским сессиям, размер proxy pool, тариф, число активных интерфейсов и накопленные дни использования. Управление токенами через публичный интерфейс не предоставляется.

Дешёвый список связанных с интеграцией сессий читается из базы без обращения к Core:

```python
page = await app.list_sessions(page_size=300, updates_enabled=True)
for session in page.sessions:
    print(session.session_peer_id, session.state, session.usage_days)
```

Следующая страница запрашивается с `page_token=page.next_page_token`. Размер страницы — от 1 до 1000, по умолчанию 300.

`SessionSnapshot.usage_days` содержит число UTC-дней использования сессии текущей интеграцией, а `last_usage_at` — начало последнего начисленного UTC-дня.

Для будущей повторной привязки уже существующей сессии контракт содержит `begin_existing_session_authorization()` и `complete_existing_session_authorization()`. Ответ сообщает способ подтверждения через `authorization_kind` и `code_provider`: Telegram Gateway или Telegram-бот, ссылку для получения кода и необходимость её открыть. Провайдеры пока не включены, поэтому эти два RPC возвращают gRPC `UNIMPLEMENTED`.

Одновременно интеграция может держать до трёх незавершённых авторизаций. Попытка автоматически закрывается через час или немедленно через `await app.cancel_authorization(authorization_id)`.

## Router и примеры

`Router` группирует обработчики и подключается через `app.include_router(router)`. Доступны штатные фильтры и типы установленного Pyrogram-совместимого пакета.

- [Минимальный Pyrogram-клиент](examples/pyrogram_client.py)
- [Telefeeds и aiogram в одном процессе](examples/pyrogram_and_aiogram.py)
- [Регистрация пользовательского аккаунта](examples/register_account.py)

```bash
pip install telefeeds-sdk kurigram aiogram
export TELEFEEDS_TOKEN='telefeeds_...'
export TELEGRAM_BOT_TOKEN='123456:...'
python examples/pyrogram_and_aiogram.py
```

Для регистрации интеграции должен быть разрешён доступ к пользовательским сессиям:

```bash
export TELEFEEDS_TOKEN='telefeeds_...'
python examples/register_account.py
```

Контракт gRPC v1 находится в [`telefeeds/proto/telegram/v1/gateway.proto`](src/telefeeds/proto/telegram/v1/gateway.proto). Публичный адрес: `telegram.telefeeds.ru:443`; авторизация передаётся как `authorization: Bearer <token>`.

## Сборка пакета

```bash
python -m build
twine check dist/*
```

Публикация релиза запускается GitHub Actions после создания GitHub Release. Для неё нужен Trusted Publisher проекта `telefeeds-sdk` в PyPI.
# Наборы аудитории и CSV-выгрузки (SDK 0.3.0)

Зарегистрируйте обработчики до запуска клиента. Интеграцию нужно связать с ботом
в интерфейсе Telefeeds. Каталог запрашивается один раз на логический `interface`,
а не на каждое соединение. Ответы разных интерфейсов появляются независимо.
`client.gateway.providers.ttl = 600` задаёт срок кэша каталога (0–3600 секунд).

```python
from pydantic import BaseModel, Field
from telefeeds import BackStream
from telefeeds.pyrogram import Telefeeds

client = Telefeeds("YOUR_INTEGRATION_TOKEN", interface=1)

async def count_active(bot_id: int):
    return await repository.count_active(bot_id)

@client.make_set("active_clients", title="Активные пользователи",
                 summary="Пользователи, активные в сервисе", count_call=count_active)
async def active_clients(bot_id: int, stream: BackStream):
    async for user in repository.active_clients(bot_id):
        await stream.push(user_id=user.telegram_id,
                          username=user.username, lang_code=user.lang_code)

class ClientRow(BaseModel):
    name: str = Field(title="Имя пользователя")

async def revision(bot_id: int):
    return await repository.dataset_revision(bot_id)

@client.make_dataset("clients", title="Клиенты", headers=ClientRow,
                     revision_call=revision)
async def clients(bot_id: int, stream: BackStream, offset: int = 0):
    async for index, user in repository.clients_at_offset(bot_id, offset):
        await stream.push(ClientRow(name=user.name), offset=index)
```

`repository` — ваш источник данных. `username` и `lang_code` необязательны.
`await stream.push` обязателен: он обеспечивает обратное давление, не накапливая
всё множество в памяти. Пакет содержит до 500 строк и примерно 240 КБ;
шлюз принимает не более 256 КиБ JSON за пакет. Следующий пакет разрешается
после передачи предыдущего потребителю. Таймаут отсутствия ответа — 30 секунд,
общая продолжительность выгрузки — не более часа. `count_call` ожидается до
двух секунд, ошибка счётчика не скрывает сам набор.

Возобновление CSV требует стабильного порядка, непрерывных нулевых offsets и
`revision_call`, возвращающего неизменную версию данных. Изменившаяся версия
запрещает продолжение. Состояние живёт в Redis час; строки и CSV в Telefeeds
не сохраняются. Браузер скачивает оставшуюся часть отдельным CSV с заголовками;
для цельного файла нужно начать загрузку заново. Смещение означает переданные
сервером строки, а не подтверждение записи файла браузером.

Для обычного доступа к Telegram бот использует тот же SDK (`Invoke` и апдейты),
но разрешения «Присылать апдейты» и «Разрешить взаимодействие с API» включаются
отдельно на связи интеграция—бот. По умолчанию оба выключены. Каталоги не
включают эти разрешения автоматически. Прямое MTProto-соединение поддерживает
сервер Telefeeds; SDK подключается к gRPC.
