from sanic import exceptions
from sanic.response import HTTPResponse
from ..protocol import loads, ENCODING
from .base import Transport
from .utils import CACHE_CONTROL, session_cookie, cors_headers, cache_headers


class XHRSendTransport(Transport):
    async def process(self):
        request = self.request
        allowed_methods = ('GET', 'POST', 'OPTIONS')
        if request.method not in allowed_methods:
            # TODO: This was previously exceptions.forbidden. Which is right?
            raise exceptions.MethodNotSupported("Method is not allowed", request.method, allowed_methods)

        if self.request.method == 'OPTIONS':
            headers = (
                ('Access-Control-Allow-Methods', "OPTIONS, POST"),
                ('Content-Type', "application/javascript; charset=UTF-8"),
            )
            headers += session_cookie(request)
            headers += cors_headers(request.headers)
            headers += cache_headers()
            return HTTPResponse(None, status=204, headers=headers)

        data = await request.stream.read()
        if not data:
            raise exceptions.ServerError("Payload expected.")

        try:
            messages = loads(data.decode(ENCODING))
        except Exception:
            raise exceptions.ServerError(text="Broken JSON encoding.")

        await self.session._remote_messages(messages)

        headers = (
            ('Content-Type', "text/plain; charset=UTF-8"),
            ('Cache-Control', CACHE_CONTROL),
        )
        headers += session_cookie(request)
        headers += cors_headers(request.headers)

        return HTTPResponse(status=204, headers=headers)
