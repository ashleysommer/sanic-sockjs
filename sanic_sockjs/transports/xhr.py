from sanic.response import HTTPResponse, StreamingHTTPResponse

from .base import StreamingTransport
from .utils import CACHE_CONTROL, session_cookie, cors_headers, cache_headers


class XHRTransport(StreamingTransport):
    """Long polling derivative transports,
    used for XHRPolling and JSONPolling."""

    maxsize = 0

    async def process(self):
        request = self.request

        if request.method == 'OPTIONS':
            headers = (
                ('Content-Type', "application/javascript; charset=UTF-8"),
                ('Access-Control-Allow-Methods', "OPTIONS, POST"),
            )
            headers += session_cookie(request)
            headers += cors_headers(request.headers)
            headers += cache_headers()
            return HTTPResponse(None, status=204, headers=headers)

        headers = (
            ('Content-Type', "application/javascript; charset=UTF-8"),
            ('Cache-Control', CACHE_CONTROL),
        )
        headers += session_cookie(request)
        headers += cors_headers(request.headers)

        async def stream(_response):
            nonlocal self
            self.response = _response
            await self.handle_session()
        return StreamingHTTPResponse(stream, headers=headers)
