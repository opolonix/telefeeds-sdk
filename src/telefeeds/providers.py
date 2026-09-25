"""Bounded reverse RPC for integration audience sets and datasets."""

from __future__ import annotations

import asyncio
import inspect
import json
import logging
import math
import re
from dataclasses import dataclass
from typing import Callable

import grpc
from pydantic import BaseModel

from telefeeds._generated import providers_pb2 as proto
from telefeeds._generated import providers_pb2_grpc

log = logging.getLogger(__name__)


class BackStream:
    def __init__(
        self,
        request_id: str,
        send: Callable,
        credit: asyncio.Semaphore,
        *,
        headers: type[BaseModel] | None,
        offset: int,
        source_revision: str = "",
        export_id: str = "",
    ):
        self.request_id = request_id
        self.send = send
        self.credit = credit
        self.headers = headers
        self.offset = offset
        self.source_revision = source_revision
        self.export_id = export_id
        self.progress_percent: float | None = None
        self.rows: list[dict] = []
        self.bytes = 0

    async def push(
        self,
        row: BaseModel | None = None,
        *,
        user_id: int | None = None,
        username: str | None = None,
        lang_code: str | None = None,
        offset: int | None = None,
        progress_percent: float | None = None,
    ) -> None:
        if progress_percent is not None and (
            isinstance(progress_percent, bool)
            or not isinstance(progress_percent, (int, float))
            or not math.isfinite(progress_percent)
            or not 0 <= progress_percent <= 100
        ):
            raise ValueError("progress_percent must be between 0 and 100")
        if self.headers is not None:
            if row is None or not isinstance(row, self.headers):
                raise TypeError("dataset row must match its headers model")
            if offset != self.offset:
                raise ValueError(
                    "dataset offsets must be contiguous, starting at requested offset"
                )
            value = row.model_dump(mode="json")
        else:
            if (
                isinstance(user_id, bool)
                or not isinstance(user_id, int)
                or user_id <= 0
            ):
                raise ValueError("user_id must be a positive Telegram user id")
            value = {"user_id": user_id, "username": username, "lang_code": lang_code}
        size = len(json.dumps(value, ensure_ascii=False).encode("utf-8"))
        if size > 240_000:
            raise ValueError("a row must not exceed 240 KB")
        if self.rows and (self.bytes + size > 240_000 or len(self.rows) >= 500):
            await self.flush()
        self.rows.append(value)
        self.bytes += size
        self.offset += 1
        if progress_percent is not None:
            self.progress_percent = progress_percent

    async def flush(self) -> None:
        if not self.rows:
            return
        await self.credit.acquire()
        await self.send(
            proto.ProviderFrame(
                request_id=self.request_id,
                kind="chunk",
                data=json.dumps(
                    {
                        "rows": self.rows,
                        "next_offset": self.offset,
                        "source_revision": self.source_revision,
                        "progress_percent": self.progress_percent,
                    },
                    ensure_ascii=False,
                ),
            )
        )
        self.rows = []
        self.bytes = 0


@dataclass
class Provider:
    handler: Callable
    title: str
    summary: str
    count_call: Callable | None
    headers: type[BaseModel] | None
    revision_call: Callable | None


class ProviderRegistry:
    def __init__(self):
        self.sets: dict[str, Provider] = {}
        self.datasets: dict[str, Provider] = {}
        self.interface_id = 0
        self.ttl = 600

    def register(
        self,
        collection: dict,
        key: str,
        *,
        title: str | None,
        summary: str,
        count_call: Callable | None,
        headers: type[BaseModel] | None,
        revision_call: Callable | None,
    ):
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", key) or key in collection:
            raise ValueError("provider key is invalid or already registered")

        def decorate(handler):
            if not inspect.iscoroutinefunction(handler):
                raise TypeError("provider handler must be async")
            collection[key] = Provider(
                handler,
                title or summary or key,
                summary,
                count_call,
                headers,
                revision_call,
            )
            return handler

        return decorate

    def make_set(
        self,
        key: str,
        *,
        title: str | None = None,
        summary: str = "",
        count_call: Callable | None = None,
    ):
        return self.register(
            self.sets,
            key,
            title=title,
            summary=summary,
            count_call=count_call,
            headers=None,
            revision_call=None,
        )

    def make_dataset(
        self,
        key: str,
        *,
        headers: type[BaseModel],
        title: str | None = None,
        summary: str = "",
        revision_call: Callable | None = None,
    ):
        return self.register(
            self.datasets,
            key,
            title=title,
            summary=summary,
            count_call=None,
            headers=headers,
            revision_call=revision_call,
        )

    async def handle(
        self, frame: proto.ProviderFrame, send: Callable, credit: asyncio.Semaphore
    ) -> None:
        try:
            request = json.loads(frame.data)
            operation = request["operation"]
            collection = (
                self.sets
                if operation in ("discover_sets", "read_set")
                else self.datasets
            )
            bot_id = int(request["bot_id"])
            if operation.startswith("discover_"):
                entries = {}
                counts = {
                    key: asyncio.create_task(provider.count_call(bot_id))
                    for key, provider in collection.items()
                    if provider.count_call
                }
                try:
                    if counts:
                        await asyncio.wait(counts.values(), timeout=2)
                finally:
                    for task in counts.values():
                        if not task.done():
                            task.cancel()
                    if counts:
                        await asyncio.gather(*counts.values(), return_exceptions=True)
                for key, provider in collection.items():
                    quantity = None
                    if provider.count_call:
                        try:
                            task = counts[key]
                            if task.cancelled():
                                log.warning("count_call timed out for %s", key)
                            else:
                                quantity = task.result()
                            if quantity is not None and (
                                isinstance(quantity, bool)
                                or not isinstance(quantity, int)
                                or quantity < 0
                            ):
                                raise ValueError(
                                    "count_call must return a non-negative integer or None"
                                )
                        except Exception:
                            log.exception(
                                "count_call failed for %s; quantity omitted", key
                            )
                            quantity = None
                    entries[key] = {
                        "title": provider.title,
                        "summary": provider.summary,
                        "quantity": quantity,
                    }
                    if provider.headers:
                        entries[key]["columns"] = [
                            {"key": key, "title": field.title or key}
                            for key, field in provider.headers.model_fields.items()
                        ]
                        entries[key]["schema"] = provider.headers.model_json_schema()
                        entries[key]["resumable"] = provider.revision_call is not None
                await send(
                    proto.ProviderFrame(
                        request_id=frame.request_id,
                        kind="catalog",
                        data=json.dumps(
                            {
                                "ttl": self.ttl,
                                "sets"
                                if operation == "discover_sets"
                                else "datasets": entries,
                            },
                            ensure_ascii=False,
                        ),
                    )
                )
                return
            provider = collection[request["key"]]
            offset = int(request.get("offset", 0))
            revision = (
                str(await provider.revision_call(bot_id))
                if provider.revision_call
                else ""
            )
            if offset and (not revision or revision != request.get("source_revision")):
                raise ValueError("source revision changed or resuming is not supported")
            stream = BackStream(
                frame.request_id,
                send,
                credit,
                headers=provider.headers,
                offset=offset,
                source_revision=revision,
                export_id=str(request.get("export_id") or ""),
            )
            kwargs = {"offset": offset} if provider.headers else {}
            if request.get("args"):
                raise ValueError("provider inputs are not supported yet")
            await provider.handler(bot_id, stream, **kwargs)
            await stream.flush()
            await credit.acquire()
            await send(
                proto.ProviderFrame(
                    request_id=frame.request_id,
                    kind="completed",
                    data=json.dumps(
                        {"next_offset": stream.offset, "source_revision": revision}
                    ),
                )
            )
        except asyncio.CancelledError:
            raise
        except Exception as error:
            log.exception("Provider request failed")
            await credit.acquire()
            await send(
                proto.ProviderFrame(
                    request_id=frame.request_id,
                    kind="error",
                    data=json.dumps(
                        {
                            "code": type(error).__name__,
                            "message": "Provider execution failed; see integration logs",
                        }
                    ),
                )
            )

    async def serve(self, channel: grpc.aio.Channel, metadata: tuple) -> None:
        stub = providers_pb2_grpc.ProviderGatewayStub(channel)
        while True:
            tasks: dict[str, tuple[asyncio.Task, asyncio.Semaphore]] = {}
            outgoing: asyncio.Queue = asyncio.Queue(maxsize=2)

            async def frames():
                yield proto.ProviderFrame(kind="hello", interface_id=self.interface_id)
                while True:
                    yield await outgoing.get()

            call = stub.Connect(frames(), metadata=metadata)
            try:
                async for frame in call:
                    if frame.kind == "ping":
                        await outgoing.put(proto.ProviderFrame(
                            kind="pong", request_id=frame.request_id,
                            interface_id=self.interface_id,
                        ))
                    elif frame.kind == "request":
                        if len(tasks) >= 32:
                            await outgoing.put(
                                proto.ProviderFrame(
                                    request_id=frame.request_id,
                                    kind="error",
                                    data='{"code":"RESOURCE_EXHAUSTED","message":"Provider is busy"}',
                                )
                            )
                            continue
                        credit = asyncio.Semaphore(1)
                        tasks[frame.request_id] = (
                            asyncio.create_task(
                                self.handle(frame, outgoing.put, credit)
                            ),
                            credit,
                        )
                    elif frame.kind == "credit" and frame.request_id in tasks:
                        tasks[frame.request_id][1].release()
                    elif frame.kind == "cancel" and frame.request_id in tasks:
                        task, credit = tasks.pop(frame.request_id)
                        task.cancel()
                        await asyncio.gather(task, return_exceptions=True)
            except grpc.aio.AioRpcError as error:
                log.warning("Provider connection lost: %s", error.code().name)
                if error.code() in (
                    grpc.StatusCode.UNAUTHENTICATED,
                    grpc.StatusCode.PERMISSION_DENIED,
                ):
                    return
            finally:
                call.cancel()
                for task, credit in tasks.values():
                    task.cancel()
                await asyncio.gather(
                    *(task for task, credit in tasks.values()), return_exceptions=True
                )
            await asyncio.sleep(2)
