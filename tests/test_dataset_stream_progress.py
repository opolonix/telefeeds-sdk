import asyncio
import json

import pytest
from pydantic import BaseModel

from telefeeds.providers import BackStream


class Row(BaseModel):
    name: str


@pytest.mark.asyncio
async def test_dataset_stream_exposes_export_id_and_progress():
    frames = []

    async def send(frame):
        frames.append(frame)

    stream = BackStream(
        "request", send, asyncio.Semaphore(1),
        headers=Row, offset=0, export_id="export-uuid",
    )
    assert stream.export_id == "export-uuid"
    await stream.push(Row(name="Ada"), offset=0, progress_percent=40)
    await stream.flush()
    data = json.loads(frames[0].data)
    assert data["next_offset"] == 1
    assert data["progress_percent"] == 40
