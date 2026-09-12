from __future__ import annotations

import asyncio
import hashlib
import inspect
import io
import math
import os
from dataclasses import dataclass
from pathlib import Path, PurePath
from typing import Any, BinaryIO

import pyrogram
from pyrogram import raw, utils
from pyrogram.errors import RPCError
from pyrogram.file_id import FileId, FileType, ThumbnailSource

from .session import GrpcSession


@dataclass(slots=True)
class MediaStats:
    uploaded_bytes: int = 0
    downloaded_bytes: int = 0
    requests: int = 0
    retries: int = 0
    cancelled: int = 0


class TelefeedsClientMixin:
    """Overrides Pyrogram transport while preserving the selected client implementation."""

    session_peer_id: int
    session_kind: str
    telefeeds: Any
    session: GrpcSession
    media_stats: MediaStats
    media_part_timeout: float
    media_retries: int

    async def invoke(self, query: Any, *args: Any, **kwargs: Any) -> Any:
        return await super().invoke(query, *args, **kwargs)

    async def get_session(
        self,
        dc_id: int | None = None,
        *,
        is_media: bool = False,
        is_cdn: bool = False,
        temporary: bool = False,
        business_connection_id: str | None = None,
    ) -> GrpcSession:
        if is_cdn:
            raise NotImplementedError(
                "Telegram CDN is disabled; GetFile uses cdn_supported=False"
            )
        return self.session.for_dc(dc_id)

    async def save_file(
        self,
        path: str | PurePath | BinaryIO,
        file_id: int | None = None,
        file_part: int = 0,
        progress: Any = None,
        progress_args: tuple[Any, ...] = (),
    ) -> Any:
        async with self.save_file_semaphore:
            if path is None:
                return None
            close_file = isinstance(path, (str, PurePath))
            if close_file:
                stream = open(path, "rb")  # noqa: ASYNC230, SIM115
            elif not isinstance(path, io.TextIOBase) and all(
                hasattr(path, attribute) for attribute in ("read", "seek", "tell")
            ):
                stream = path
            else:
                raise ValueError(
                    "path must be a file path or a seekable binary file object"
                )

            try:
                stream.seek(0, os.SEEK_END)
                file_size = stream.tell()
                stream.seek(0)
                if file_size <= 0:
                    raise ValueError("file size must be greater than zero")
                limit_mib = 4_000 if self.me and self.me.is_premium else 2_000
                if file_size > limit_mib * 1024 * 1024:
                    raise ValueError(
                        f"files larger than {limit_mib} MiB are not supported"
                    )

                part_size = 512 * 1024
                total_parts = math.ceil(file_size / part_size)
                is_big = file_size > 10 * 1024 * 1024
                missing_part = file_id is not None
                actual_file_id = file_id if file_id is not None else self.rnd_id()
                file_name = Path(str(getattr(stream, "name", "file.bin"))).name

                if missing_part:
                    stream.seek(part_size * file_part)
                    chunk = stream.read(part_size)
                    if not chunk:
                        raise ValueError(f"file part {file_part} is outside the file")
                    request = (
                        raw.functions.upload.SaveBigFilePart(
                            file_id=actual_file_id,
                            file_part=file_part,
                            file_total_parts=total_parts,
                            bytes=chunk,
                        )
                        if is_big
                        else raw.functions.upload.SaveFilePart(
                            file_id=actual_file_id,
                            file_part=file_part,
                            bytes=chunk,
                        )
                    )
                    await self.session.invoke(
                        request,
                        retries=self.media_retries,
                        timeout=self.media_part_timeout,
                    )
                    return None

                checksum = hashlib.md5() if not is_big else None
                part_number = 0
                workers = (
                    max(1, min(4, self.max_concurrent_transmissions)) if is_big else 1
                )
                while part_number < total_parts:
                    batch: list[tuple[int, bytes]] = []
                    for worker_index in range(workers):
                        chunk = stream.read(part_size)
                        if not chunk:
                            break
                        if checksum is not None:
                            checksum.update(chunk)
                        batch.append((part_number, chunk))
                        part_number += 1
                    requests = [
                        (
                            raw.functions.upload.SaveBigFilePart(
                                file_id=actual_file_id,
                                file_part=number,
                                file_total_parts=total_parts,
                                bytes=chunk,
                            )
                            if is_big
                            else raw.functions.upload.SaveFilePart(
                                file_id=actual_file_id,
                                file_part=number,
                                bytes=chunk,
                            )
                        )
                        for number, chunk in batch
                    ]
                    await asyncio.gather(
                        *(
                            self.session.invoke(
                                request,
                                retries=self.media_retries,
                                timeout=self.media_part_timeout,
                            )
                            for request in requests
                        )
                    )
                    if progress is not None:
                        current = min(part_number * part_size, file_size)
                        if inspect.iscoroutinefunction(progress):
                            await progress(current, file_size, *progress_args)
                        else:
                            await asyncio.to_thread(
                                progress, current, file_size, *progress_args
                            )

                if is_big:
                    return raw.types.InputFileBig(
                        id=actual_file_id,
                        parts=total_parts,
                        name=file_name,
                    )
                return raw.types.InputFile(
                    id=actual_file_id,
                    parts=total_parts,
                    name=file_name,
                    md5_checksum=checksum.hexdigest(),
                )
            except (asyncio.CancelledError, pyrogram.StopTransmission):
                self.media_stats.cancelled += 1
                raise
            finally:
                if close_file:
                    stream.close()

    async def get_file(
        self,
        file_id: FileId,
        file_size: int = 0,
        limit: int = 0,
        offset: int = 0,
        progress: Any = None,
        progress_args: tuple[Any, ...] = (),
    ):
        async with self.get_file_semaphore:
            if file_id.file_type == FileType.CHAT_PHOTO:
                if file_id.chat_id > 0:
                    peer = raw.types.InputPeerUser(
                        user_id=file_id.chat_id,
                        access_hash=file_id.chat_access_hash,
                    )
                elif file_id.chat_access_hash == 0:
                    peer = raw.types.InputPeerChat(chat_id=-file_id.chat_id)
                else:
                    peer = raw.types.InputPeerChannel(
                        channel_id=utils.get_channel_id(file_id.chat_id),
                        access_hash=file_id.chat_access_hash,
                    )
                location = raw.types.InputPeerPhotoFileLocation(
                    peer=peer,
                    photo_id=file_id.media_id,
                    big=file_id.thumbnail_source
                    in (
                        ThumbnailSource.CHAT_PHOTO_BIG,
                        ThumbnailSource.CHAT_PHOTO_BIG_LEGACY,
                    ),
                )
            elif file_id.file_type == FileType.PHOTO:
                location = raw.types.InputPhotoFileLocation(
                    id=file_id.media_id,
                    access_hash=file_id.access_hash,
                    file_reference=file_id.file_reference,
                    thumb_size=file_id.thumbnail_size,
                )
            else:
                location = raw.types.InputDocumentFileLocation(
                    id=file_id.media_id,
                    access_hash=file_id.access_hash,
                    file_reference=file_id.file_reference,
                    thumb_size=file_id.thumbnail_size,
                )

            chunk_size = 1024 * 1024
            offset_bytes = abs(offset) * chunk_size
            remaining = abs(limit) or (1 << 31) - 1
            current = 0
            try:
                while current < remaining:
                    request = raw.functions.upload.GetFile(
                        location=location,
                        offset=offset_bytes,
                        limit=chunk_size,
                        precise=False,
                        cdn_supported=False,
                    )
                    response = await self.session.invoke_in_dc(
                        request,
                        file_id.dc_id,
                        retries=self.media_retries,
                        timeout=self.media_part_timeout,
                    )
                    if not isinstance(response, raw.types.upload.File):
                        raise NotImplementedError(
                            "Telegram returned a CDN redirect despite cdn_supported=False"
                        )
                    chunk = response.bytes
                    yield chunk
                    current += 1
                    offset_bytes += len(chunk)
                    if progress is not None:
                        progress_current = (
                            min(offset_bytes, file_size) if file_size else offset_bytes
                        )
                        if inspect.iscoroutinefunction(progress):
                            await progress(progress_current, file_size, *progress_args)
                        else:
                            await asyncio.to_thread(
                                progress,
                                progress_current,
                                file_size,
                                *progress_args,
                            )
                    if len(chunk) < chunk_size:
                        break
            except (asyncio.CancelledError, pyrogram.StopTransmission):
                self.media_stats.cancelled += 1
                raise

    async def download_media(self, message: Any, *args: Any, **kwargs: Any) -> Any:
        try:
            return await super().download_media(message, *args, **kwargs)
        except RPCError as error:
            if type(error).__name__ not in {
                "FileReferenceExpired",
                "FileReferenceEmpty",
            }:
                raise
            chat = getattr(message, "chat", None)
            message_id = getattr(message, "id", None)
            chat_id = getattr(chat, "id", None)
            if chat_id is None or message_id is None:
                raise
            refreshed = await self.get_messages(chat_id, message_id)
            return await super().download_media(refreshed, *args, **kwargs)

    async def connect(self, *args: Any, **kwargs: Any) -> None:
        raise NotImplementedError("Telefeeds owns the Telegram connection")

    async def disconnect(self, *args: Any, **kwargs: Any) -> None:
        raise NotImplementedError("Telefeeds owns the Telegram connection")

    async def start(self, *args: Any, **kwargs: Any) -> None:
        raise NotImplementedError("Telefeeds creates and starts session clients")

    async def stop(self, *args: Any, **kwargs: Any) -> None:
        raise NotImplementedError("stop the parent Telefeeds instance instead")

    async def restart(self, *args: Any, **kwargs: Any) -> None:
        raise NotImplementedError("Telefeeds owns the Telegram connection")

    async def log_out(self, *args: Any, **kwargs: Any) -> None:
        raise NotImplementedError(
            "managed sessions cannot be logged out by SDK clients"
        )

    async def terminate(self, *args: Any, **kwargs: Any) -> None:
        raise NotImplementedError("Telefeeds owns the Telegram connection")

    async def export_session_string(self, *args: Any, **kwargs: Any) -> str:
        raise NotImplementedError("Telefeeds session credentials are not exported")
