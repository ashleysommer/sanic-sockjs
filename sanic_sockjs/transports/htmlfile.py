""" iframe-htmlfile transport """
import re
from sanic import exceptions
from sanic.response import StreamingHTTPResponse
from ..protocol import dumps, ENCODING
from .base import StreamingTransport
from .utils import CACHE_CONTROL, session_cookie, cors_headers


PRELUDE1 = b"""
<!doctype html>
<html><head>
  <meta http-equiv="X-UA-Compatible" content="IE=edge" />
  <meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
</head><body><h2>Don't panic!</h2>
  <script>
    document.domain = document.domain;
    var c = parent."""

PRELUDE2 = b""";
    c.start();
    function p(d) {c.message(d);};
    window.onload = function() {c.stop();};
  </script>"""


class HTMLFileTransport(StreamingTransport):

    maxsize = 131072  # 128K bytes
    check_callback = re.compile(r"^[a-zA-Z0-9_\.]+$")

    async def send(self, text):
        blob = ("<script>\np(%s);\n</script>\r\n" % dumps(text)).encode(ENCODING)
        await self.response.write(blob)

        self.size += len(blob)
        if self.size > self.maxsize:
            return True
        else:
            return False

    async def process(self):
        request = self.request

        try:
            callback = request.query_args.get("c", None)
        except Exception:
            callback = request.args.get("c", None)

        if callback is None:
            await self.session._remote_closed()
            raise exceptions.ServerError('"callback" parameter required')

        elif not self.check_callback.match(callback):
            await self.session._remote_closed()
            raise exceptions.ServerError('invalid "callback" parameter')

        headers = (
            ('Content-Type', "text/html; charset=UTF-8"),
            ('Cache-Control', CACHE_CONTROL),
            ('Connection', "close"),
        )
        headers += session_cookie(request)
        headers += cors_headers(request.headers)

        async def stream(_response):
            nonlocal self
            self.response = _response
            await _response.write(
                b"".join((PRELUDE1, callback.encode("utf-8"), PRELUDE2, b" " * 1024))
            )
            # handle session
            await self.handle_session()
        # open sequence (sockjs protocol)
        return StreamingHTTPResponse(stream, headers=headers)

