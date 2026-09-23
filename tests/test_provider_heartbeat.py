import asyncio

import grpc
import pytest

from telefeeds._generated import providers_pb2 as proto
from telefeeds._generated import providers_pb2_grpc
from telefeeds.providers import ProviderRegistry


@pytest.mark.asyncio
async def test_provider_answers_ping_and_stops_after_revocation():
    received = []

    class Gateway(providers_pb2_grpc.ProviderGatewayServicer):
        async def Connect(self, frames, context):
            received.append(await anext(frames))
            yield proto.ProviderFrame(kind="ping", request_id="heartbeat-1")
            received.append(await anext(frames))
            await context.abort(grpc.StatusCode.UNAUTHENTICATED, "token revoked")

    server = grpc.aio.server()
    providers_pb2_grpc.add_ProviderGatewayServicer_to_server(Gateway(), server)
    port = server.add_insecure_port("127.0.0.1:0")
    await server.start()
    try:
        async with grpc.aio.insecure_channel(f"127.0.0.1:{port}") as channel:
            await asyncio.wait_for(ProviderRegistry().serve(channel, ()), timeout=5)
        assert [frame.kind for frame in received] == ["hello", "pong"]
        assert received[1].request_id == "heartbeat-1"
    finally:
        await server.stop(0)
