"""raw websocket transport."""
import asyncio
from asyncio import ensure_future, CancelledError
from websockets import framing, ConnectionClosed

from .base import Transport
from ..exceptions import SessionIsClosed
from ..protocol import FRAME_CLOSE, FRAME_MESSAGE, FRAME_MESSAGE_BLOB, FRAME_HEARTBEAT

class WebSocketHelper(object):
    __slots__ = ('raw_ws',)
    def __init__(self, raw_ws):
        self.raw_ws = raw_ws

    async def send_str(self, data):
        return await self.raw_ws.send(data)

class RawWebSocketTransport(Transport):
    async def server(self, ws, session):
        while True:
            try:
                frame, data = await session._wait(pack=False)
            except SessionIsClosed:
                break

            if frame == FRAME_MESSAGE:
                for text in data:
                    await ws.send_str(text)
            elif frame == FRAME_MESSAGE_BLOB:
                data = data[1:]
                if data.startswith("["):
                    data = data[1:-1]
                await ws.send_str(data)
            elif frame == FRAME_HEARTBEAT:
                await ws.ping()
            elif frame == FRAME_CLOSE:
                try:
                    await ws.close(message="Go away!")
                finally:
                    await session._remote_closed()

    async def client(self, ws, session):
        while True:
            try:
                data = await ws.receive()
            except (ConnectionClosed, CancelledError) as e:
                await session._remote_closed()
                await ws.close(reason="client closed")
                break
            if not data:
                continue
            await self.session._remote_message(data)
            # elif msg.type == framing.OP_CLOSE:
            #     await self.session._remote_close()
            # elif msg.type in (0x100, 0x101): #aiohttp CLOSING and CLOSED
            #     await self.session._remote_closed()
            #     break
            # elif msg.type == framing.OP_PONG:
            #     self.session._tick()

    async def process(self, raw_ws):
        # start websocket connection
        ws = self.ws = WebSocketHelper(raw_ws)

        try:
            await self.manager.acquire(self.session)
        except Exception:  # should use specific exception
            await ws.close(message="Go away!")
            return ws

        server = ensure_future(self.server(ws, self.session))
        client = ensure_future(self.client(ws, self.session))
        try:
            await asyncio.wait((server, client), return_when=asyncio.FIRST_COMPLETED)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            await self.session._remote_close(exc)
        finally:
            await self.manager.release(self.session)
            if not server.done():
                server.cancel()
            if not client.done():
                client.cancel()

        return ws
