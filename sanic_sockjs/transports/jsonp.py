"""jsonp transport"""
import re
from urllib.parse import unquote_plus
from sanic import exceptions
from sanic.response import StreamingHTTPResponse, HTTPResponse

from .base import StreamingTransport
from .utils import CACHE_CONTROL, session_cookie, cors_headers
from ..protocol import dumps, loads, ENCODING


class JSONPolling(StreamingTransport):

    check_callback = re.compile(r"^[a-zA-Z0-9_\.]+$")
    callback = ""

    async def send(self, text):
        data = "/**/%s(%s);\r\n" % (self.callback, dumps(text))
        await self.response.write(data.encode(ENCODING))
        return True

    async def process(self):
        session = self.session
        request = self.request
        meth = request.method

        if request.method == 'GET':
            try:
                callback = self.callback = request.query_args.get("c")
            except Exception:
                callback = self.callback = request.args.get("c", None)

            if not callback:
                await self.session._remote_closed()
                raise exceptions.ServerError('"callback" parameter required')

            elif not self.check_callback.match(callback):
                await self.session._remote_closed()
                raise exceptions.ServerError('invalid "callback" parameter')

            headers = (
                ('Content-Type', "application/javascript; charset=UTF-8"),
                ('Cache-Control', CACHE_CONTROL),
            )
            headers += session_cookie(request)
            headers += cors_headers(request.headers)

            async def stream(_response):
                nonlocal self
                self.response = _response
                # handle session
                await self.handle_session()

            # open sequence (sockjs protocol)
            return StreamingHTTPResponse(stream, headers=headers)

        elif request.method == 'POST':
            data = await request.stream.read()

            ctype = request.content_type.lower()
            if ctype == "application/x-www-form-urlencoded":
                if not data.startswith(b"d="):
                    raise exceptions.ServerError("Payload expected.")

                data = unquote_plus(data[2:].decode(ENCODING))
            else:
                data = data.decode(ENCODING)

            if not data:
                raise exceptions.ServerError("Payload expected.")

            try:
                messages = loads(data)
            except Exception:
                raise exceptions.ServerError("Broken JSON encoding.")

            await session._remote_messages(messages)

            headers = (
                ('Content-Type', "text/html;charset=UTF-8"),
                ('Cache-Control', CACHE_CONTROL),
            )
            headers += session_cookie(request)
            return HTTPResponse(None, body_bytes=b"ok", headers=headers)
        else:
            raise exceptions.MethodNotSupported("No support for such method: %s" % meth, meth, ('GET','POST'))
