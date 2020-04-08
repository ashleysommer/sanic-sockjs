"""websocket transport"""
import asyncio
from asyncio import ensure_future, CancelledError
from websockets import framing, ConnectionClosed
from sanic.websocket import WebSocketProtocol
from sanic import exceptions
from .base import Transport
from ..exceptions import SessionIsClosed
from ..protocol import STATE_CLOSED, FRAME_CLOSE
from ..protocol import loads, close_frame

class WebSocketTransport(Transport):
    async def tx_loop(self, ws, session):
        while True:
            try:
                frame, data = await session._wait()
            except SessionIsClosed:
                break
            try:
                await ws.send(data)
            except OSError:
                pass  # ignore 'cannot write to closed transport'
            if frame == FRAME_CLOSE:
                try:
                    await ws.close()
                finally:
                    await session._remote_closed()

    async def rx_loop(self, ws, session):
        while True:
            try:
                data = await ws.recv()
            except (ConnectionClosed, CancelledError) as e:
                await session._remote_closed()
                await ws.close(reason="client closed")
                break
            if not data:
                continue

            if data.startswith("["):
                data = data[1:-1]

            try:
                text = loads(data)
            except Exception as exc:
                await session._remote_close(exc)
                await session._remote_closed()
                await ws.close(reason="broken json")
                break

            await session._remote_message(text)

            # elif msg.type == framing.OP_CLOSE:
            #     await session._remote_close()
            # elif msg.type in (0x100, 0x101): #aiohttp CLOSING and CLOSED
            #     await session._remote_closed()
            #     break

    async def process(self):
        # start websocket connection
        try:
            p = self.request.transport.get_protocol()
        except:
            raise exceptions.ServerError("Cannot get http protocol from transport")
        if isinstance(p, WebSocketProtocol):
            wsp = p
        else:
            loop = asyncio.get_event_loop()
            app = self.request.app
            wsp = WebSocketProtocol(loop=loop, app=app, request_handler=app.handle_request, error_handler=app.error_handler)
            wsp.transport = self.request.transport
            self.request.transport.set_protocol(wsp)

        ws = self.ws = await wsp.websocket_handshake(self.request)

        # session was interrupted
        if self.session.interrupted:
            await self.ws.send_str(close_frame(1002, "Connection interrupted"))

        elif self.session.state == STATE_CLOSED:
            await self.ws.send_str(close_frame(3000, "Go away!"))

        else:
            try:
                await self.manager.acquire(self.session)
            except Exception:  # should use specific exception
                await self.ws.send_str(close_frame(3000, "Go away!"))
                await ws.close()
                return ws
            server = ensure_future(self.tx_loop(ws, self.session))
            client = ensure_future(self.rx_loop(ws, self.session))
            try:
                await asyncio.wait(
                    (server, client), return_when=asyncio.FIRST_COMPLETED
                )
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
