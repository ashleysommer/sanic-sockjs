import asyncio
import json
import random
import logging
import hashlib
import inspect
from functools import partial

from sanic import response
from sanic import exceptions

from .session import SessionManager
from .protocol import IFRAME_HTML
from .transports import handlers
from .transports.utils import CACHE_CONTROL
from .transports.utils import session_cookie
from .transports.utils import cors_headers
from .transports.utils import cache_headers
from .transports.rawwebsocket import RawWebSocketTransport

log = logging.getLogger("sockjs")


def get_manager(name, app):
    return app.config["__sockjs_managers__"][name]


def _gen_endpoint_name():
    return "n" + str(random.randint(1000, 9999))

def teardown_session_manager(session_manager, app, loop):
    loop.run_until_complete(session_manager.clear())

def add_endpoint(
    app,
    handler,
    *,
    name="",
    prefix="/sockjs",
    manager=None,
    disable_transports=(),
    sockjs_cdn="//cdn.jsdelivr.net/npm/sockjs-client@1/dist/sockjs.js",  # noqa
    cookie_needed=True
):

    assert callable(handler), handler
    if not asyncio.iscoroutinefunction(handler) and not inspect.isgeneratorfunction(
        handler
    ):
        handler = asyncio.coroutine(handler)

    if not name:
        name = _gen_endpoint_name()

    # set session manager
    if manager is None:
        manager = SessionManager(name, app, handler)

    if manager.name != name:
        raise ValueError("Session manage must have same name as sockjs route")

    managers = app.config.setdefault("__sockjs_managers__", {})
    if name in managers:
        raise ValueError('SockJS "%s" route already registered' % name)

    managers[name] = manager

    # register routes
    route = SockJSRoute(
        name, manager, sockjs_cdn, handlers, disable_transports, cookie_needed
    )

    app.is_request_stream = True

    if prefix.endswith("/"):
        prefix = prefix[:-1]

    route_name = "sockjs-url-%s-greeting" % name
    app.route(prefix, methods=('GET',), name=route_name, strict_slashes=True)(route.greeting)

    route_name = "sockjs-url-%s" % name
    app.route("%s/" % prefix, methods=('GET',), name=route_name, strict_slashes=True)(route.greeting)

    route_name = "sockjs-%s" % name
    app.route(
        "%s/<server:string>/<sid:string>/<tid:string>" % prefix,
        methods=('GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD', 'OPTIONS'),
        name=route_name,
        strict_slashes=True
    )(route.handler)

    route_name = "sockjs-websocket-%s" % name
    app.websocket(
        "%s/websocket" % prefix, name=route_name
    )(route.websocket)
    route_name = "sockjs-info-%s" % name
    app.route(
        "%s/info" % prefix, methods=('GET','OPTIONS'), name=route_name
    )(route.info)

    route_name = "sockjs-iframe-%s" % name
    app.route(
        "%s/iframe.html" % prefix, methods=('GET',), name=route_name
    )(route.iframe)

    route_name = "sockjs-iframe-ver-%s" % name
    app.route(
        "%s/iframe{version}.html" % prefix, methods=('GET',), name=route_name
    )(route.iframe)

    app.listener('before_server_stop')(partial(teardown_session_manager, manager))

    # start session gc
    manager.start()


class SockJSRoute:
    def __init__(
        self,
        name,
        manager,
        sockjs_cdn,
        handlers,
        disable_transports,
        cookie_needed=True,
    ):
        self.name = name
        self.manager = manager
        self.handlers = handlers
        self.disable_transports = dict((k, 1) for k in disable_transports)
        self.cookie_needed = cookie_needed
        self.iframe_html = (IFRAME_HTML % sockjs_cdn).encode("utf-8")
        self.iframe_html_hxd = hashlib.md5(self.iframe_html).hexdigest()

    async def handler(self, request, server, sid, tid):
        if tid not in self.handlers or tid in self.disable_transports:
            raise exceptions.NotFound("SockJS transport handler not found.")

        create, transport = self.handlers[tid]

        # session
        manager = self.manager
        if not manager.started:
            manager.start()

        if not sid or "." in sid or "." in server:
            raise exceptions.NotFound("SockJS bad route")

        try:
            session = manager.get(sid, create, request=request)
        except KeyError:
            return response.HTTPResponse(None, status=404, headers=session_cookie(request))

        t = transport(manager, session, request)
        try:
            return await t.process()
        except asyncio.CancelledError:
            raise
        except exceptions.SanicException as exc:
            msg = "Server Exception in Transport handler: %s" % str(exc)
            log.exception(msg)
            raise
        except Exception:
            msg = "Exception in transport: %s" % tid
            log.exception(msg)
            if manager.is_acquired(session):
                await manager.release(session)
            raise exceptions.ServerError(msg)
    handler.is_stream = True

    async def websocket(self, request, ws):
        # session
        sid = "%0.9d" % random.randint(1, 2147483647)
        session = self.manager.get(sid, True, request=request)

        transport = RawWebSocketTransport(self.manager, session, request)
        try:
            return await transport.process(ws)
        except asyncio.CancelledError:
            raise
        except exceptions.SanicException as exc:
            return exc

    async def info(self, request):
        resp = response.HTTPResponse(None)
        resp.headers["Content-Type"] = "application/json;charset=UTF-8"
        resp.headers["Cache-Control"] = CACHE_CONTROL
        if request.method == 'OPTIONS':
            resp.status = 204
            resp.headers['Access-Control-Allow-Methods'] = "OPTIONS, GET"
            resp.headers.extend(cors_headers(request.headers))
            resp.headers.extend(cache_headers())
            resp.headers.extend(session_cookie(request))
            return resp
        else:
            resp.headers.extend(cors_headers(request.headers))
            info = {
                "entropy": random.randint(1, 2147483647),
                "websocket": "websocket" not in self.disable_transports,
                "cookie_needed": self.cookie_needed,
                "origins": ["*:*"],
            }
            resp.body = json.dumps(info).encode()
        return resp

    async def iframe(self, request):
        cached = request.headers.get('If-None-Match')
        if cached:
            resp = response.HTTPResponse(status=304)
            resp.headers["Content-Type"] = ""
            resp.headers.extend(cache_headers())
            return resp

        headers = (
            ("Content-Type", "text/html;charset=UTF-8"),
            ("ETag", self.iframe_html_hxd),
        )
        headers += cache_headers()
        return response.HTTPResponse(None, body_bytes=self.iframe_html, headers=headers)

    async def greeting(self, request):
        return response.HTTPResponse(None,
            body_bytes=b"Welcome to SockJS!\n",
            headers=(("Content-Type", "text/plain; charset=UTF-8"),),
        )
