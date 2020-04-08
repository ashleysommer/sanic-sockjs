""" iframe-eventsource transport """
from sanic.response import StreamingHTTPResponse
from ..protocol import ENCODING
from .base import StreamingTransport
from .utils import CACHE_CONTROL, session_cookie


class EventsourceTransport(StreamingTransport):
    async def send(self, text):
        blob = "".join(("data: ", text, "\r\n\r\n")).encode(ENCODING)
        await self.response.write(blob)

        self.size += len(blob)
        if self.size > self.maxsize:
            return True
        else:
            return False

    async def process(self):
        headers = (
            ('Content-Type', "text/event-stream"),
            ('Cache-Control', CACHE_CONTROL),
        )
        headers += session_cookie(self.request)

        async def stream(_response):
            nonlocal self
            self.response = _response
            await _response.write(b"\r\n")
            # handle session
            await self.handle_session()
        # open sequence (sockjs protocol)
        return StreamingHTTPResponse(stream, headers=headers)
