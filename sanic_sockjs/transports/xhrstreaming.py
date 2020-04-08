from sanic.response import HTTPResponse, StreamingHTTPResponse


from .base import StreamingTransport
from .utils import CACHE_CONTROL, session_cookie, cors_headers, cache_headers


class XHRStreamingTransport(StreamingTransport):

    maxsize = 131072  # 128K bytes
    open_seq = b"h" * 2048 + b"\n"

    async def process(self):
        request = self.request
        headers = (
            ('Connection', request.headers.get('Connection', "close")),
            ('Content-Type', "application/javascript; charset=UTF-8"),
            ('Cache-Control', CACHE_CONTROL),
        )

        headers += session_cookie(request)
        headers += cors_headers(request.headers)

        if request.method == 'OPTIONS':
            headers += (('Access-Control-Allow-Methods', "OPTIONS, POST"),)
            headers += cache_headers()
            return HTTPResponse(None, status=204, headers=headers)

        async def stream(_response):
            nonlocal self
            self.response = _response
            await _response.write(self.open_seq)
            # event loop
            await self.handle_session()
        # open sequence (sockjs protocol)
        return StreamingHTTPResponse(stream, headers=headers)
        #resp.force_close()
