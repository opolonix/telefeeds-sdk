from __future__ import annotations

import asyncio
from io import BytesIO
from typing import Any

import grpc
from pyrogram import raw
from pyrogram.errors import RPCError
from pyrogram.raw.core import TLObject

from telefeeds._core import TelefeedsClient, TelegramRPCError


class GrpcSession:
    """Pyrogram Session-compatible adapter backed by one shared gRPC channel."""

    def __init__(
        self,
        gateway: TelefeedsClient,
        session_peer_id: int,
        owner: Any,
        *,
        dc_id: int | None = None,
    ) -> None:
        self.gateway = gateway
        self.session_peer_id = session_peer_id
        self.owner = owner
        self.dc_id = dc_id
        self.is_media = dc_id is not None
        self.is_cdn = False
        self.auth_key = b""

    def for_dc(self, dc_id: int | None) -> GrpcSession:
        if dc_id == self.dc_id:
            return self
        return GrpcSession(
            self.gateway,
            self.session_peer_id,
            self.owner,
            dc_id=dc_id,
        )

    async def invoke(
        self,
        query: Any,
        retries: int = 3,
        timeout: float = 30.0,
        sleep_threshold: float | None = None,
        retry_delay: float = 0.5,
        **kwargs: Any,
    ) -> Any:
        return await self.invoke_in_dc(
            query,
            self.dc_id,
            retries=retries,
            timeout=timeout,
            sleep_threshold=sleep_threshold,
            retry_delay=retry_delay,
        )

    async def invoke_in_dc(
        self,
        query: Any,
        dc_id: int | None,
        *,
        retries: int = 3,
        timeout: float = 30.0,
        sleep_threshold: float | None = None,
        retry_delay: float = 0.5,
    ) -> Any:
        retryable = {
            grpc.StatusCode.ABORTED,
            grpc.StatusCode.DEADLINE_EXCEEDED,
            grpc.StatusCode.RESOURCE_EXHAUSTED,
            grpc.StatusCode.UNAVAILABLE,
        }
        active_dc_id = dc_id
        for attempt in range(retries + 1):
            try:
                body = await self.gateway.invoke_raw(
                    self.session_peer_id,
                    query.write(),
                    dc_id=active_dc_id,
                    tl_layer=self.owner.telefeeds.tl_layer,
                    timeout=timeout,
                )
                response = TLObject.read(BytesIO(body))
                query_name = type(query).__name__
                if query_name in {"SaveFilePart", "SaveBigFilePart"}:
                    self.owner.media_stats.requests += 1
                    self.owner.media_stats.uploaded_bytes += len(query.bytes)
                elif query_name == "GetFile" and isinstance(
                    response, raw.types.upload.File
                ):
                    self.owner.media_stats.requests += 1
                    self.owner.media_stats.downloaded_bytes += len(response.bytes)
                return response
            except TelegramRPCError as error:
                if (
                    error.name == "FILE_MIGRATE"
                    and error.value is not None
                    and attempt < retries
                ):
                    active_dc_id = error.value
                    self.owner.media_stats.retries += 1
                    continue
                if (
                    error.name in {"FLOOD_WAIT", "SLOWMODE_WAIT"}
                    and error.value is not None
                    and sleep_threshold is not None
                    and error.value <= sleep_threshold
                    and attempt < retries
                ):
                    await asyncio.sleep(error.value)
                    continue
                rpc_error = raw.types.RpcError(
                    error_code=error.code,
                    error_message=error.message,
                )
                RPCError.raise_it(rpc_error, type(query))
                raise AssertionError("RPCError.raise_it must raise")
            except grpc.aio.AioRpcError as error:
                if error.code() not in retryable or attempt == retries:
                    raise
                self.owner.media_stats.retries += 1
                await asyncio.sleep(retry_delay * (2**attempt))
            except asyncio.CancelledError:
                if type(query).__name__ in {
                    "SaveFilePart",
                    "SaveBigFilePart",
                    "GetFile",
                }:
                    self.owner.media_stats.cancelled += 1
                raise
        raise AssertionError("retry loop exhausted without returning or raising")

    async def start(self) -> None:
        return None

    async def stop(self) -> None:
        return None
