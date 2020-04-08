import asyncio

import pytest
from multidict import CIMultiDict

from sanic_sockjs import protocol
from sanic import exceptions
from sanic import response

async def test_info(make_route, make_request):
    route = make_route()
    request = make_request("GET", "/sm/")

    response = await route.info(request)
    info = protocol.loads(response.body.decode("utf-8"))

    assert info["websocket"]
    assert info["cookie_needed"]


async def test_info_entropy(make_route, make_request):
    route = make_route()
    request = make_request("GET", "/sm/")

    response = await route.info(request)
    entropy1 = protocol.loads(response.body.decode("utf-8"))["entropy"]

    response = await route.info(request)
    entropy2 = protocol.loads(response.body.decode("utf-8"))["entropy"]

    assert entropy1 != entropy2


async def test_info_options(make_route, make_request):
    route = make_route()
    request = make_request("OPTIONS", "/sm/")
    response = await route.info(request)

    assert response.status == 204

    headers = response.headers
    assert "Access-Control-Max-Age" in headers
    assert "Cache-Control" in headers
    assert "Expires" in headers
    assert "Set-Cookie" in headers
    assert "access-control-allow-credentials" in headers
    assert "access-control-allow-origin" in headers


async def test_greeting(make_route, make_request):
    route = make_route()
    request = make_request("GET", "/sm/")
    response = await route.greeting(request)

    assert response.body == b"Welcome to SockJS!\n"


async def test_iframe(make_route, make_request):
    route = make_route()
    request = make_request("GET", "/sm/")

    response = await route.iframe(request)
    text = """<!DOCTYPE html>
<html>
<head>
<meta http-equiv="X-UA-Compatible" content="IE=edge" />
<meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
  <script src="http:sockjs-cdn"></script>
  <script>
    document.domain = document.domain;
    SockJS.bootstrap_iframe();
  </script>
</head>
<body>
  <h2>Don't panic!</h2>
  <p>This is a SockJS hidden iframe. It's used for cross domain magic.</p>
</body>
</html>"""

    assert response.body.decode("utf-8") == text
    assert "ETag" in response.headers


async def test_iframe_cache(make_route, make_request):
    route = make_route()
    request = make_request(
        "GET", "/sm/", headers=CIMultiDict({"IF-NONE-MATCH": "test"})
    )
    response = await route.iframe(request)

    assert response.status == 304


async def test_handler_unknown_transport(make_route, make_request):
    route = make_route()
    request = make_request("GET", "/sm/000/test1/unknown")

    with pytest.raises(exceptions.NotFound):
        res = await route.handler(request, "000", "test1", "unknown")



async def test_handler_empty_session(make_route, make_request):
    route = make_route()
    request = make_request("GET", "/sm/000//websocket")
    with pytest.raises(exceptions.NotFound):
        res = await route.handler(request, "000", "", "websocket")



async def test_handler_bad_session_id(make_route, make_request):
    route = make_route()
    request = make_request("GET","/sm/000/test.1/websocket")
    with pytest.raises(exceptions.NotFound):
        res = await route.handler(request, "000", "test.1", "websocket")

async def test_handler_bad_server_id(make_route, make_request):
    route = make_route()
    request = make_request("GET", "/sm/test.1/test/websocket")
    with pytest.raises(exceptions.NotFound):
        res = await route.handler(request, "test.1", "test", "websocket")


async def test_new_session_before_read(make_route, make_request):
    route = make_route()
    request = make_request("GET", "/sm/000/s1/xhr_send")
    res = await route.handler(request, "000", "s1", "xhr_send")
    assert isinstance(res, response.HTTPResponse)
    assert res.status == 404
    assert res.headers.get('Set-Cookie', False)

async def _test_transport(make_route, make_request):
    route = make_route()
    request = make_request("GET", "/sm/000/s1/xhr")

    params = []

    class Transport:
        def __init__(self, manager, session, request):
            params.append((manager, session, request))

        def process(self):
            return response.text(None, 200)

    route = make_route(handlers={"test": (True, Transport)})
    res = await route.handler(request, "000", "s1", "xhr")
    assert isinstance(res, response.HTTPResponse)
    assert res.status is 200
    assert params[0] == (route.manager, route.manager["s1"], request)


async def test_fail_transport(make_route, make_request):
    request = make_request("GET", "/sm/000/session/test")

    params = []

    class Transport:
        def __init__(self, manager, session, request):
            params.append((manager, session, request))

        def process(self):
            raise Exception("Error")

    route = make_route(handlers={"test": (True, Transport)})
    with pytest.raises(exceptions.ServerError):
        res = await route.handler(request, "000", "session", "test")


async def test_release_session_for_failed_transport(make_route, make_request):
    request = make_request("GET", "/sm/000/s1/test")

    class Transport:
        def __init__(self, manager, session, request):
            self.manager = manager
            self.session = session

        async def process(self):
            await self.manager.acquire(self.session)
            raise Exception("Error")

    route = make_route(handlers={"test": (True, Transport)})
    with pytest.raises(exceptions.ServerError):
        res = await route.handler(request, "000", "s1", "test")

    s1 = route.manager["s1"]
    assert not route.manager.is_acquired(s1)


async def test_raw_websocket(make_route, make_request, mocker):
    wst = mocker.patch("sanic_sockjs.route.RawWebSocketTransport")
    loop = asyncio.get_event_loop()
    wst.return_value.process.return_value = loop.create_future()
    wst.return_value.process.return_value.set_result(response.text(None, 200))

    raw_ws = mocker.Mock()
    route = make_route()
    request = make_request("GET", "/sm/", headers=CIMultiDict({}))
    res = await route.websocket(request, raw_ws)

    assert isinstance(res, response.HTTPResponse)
    assert res.status is 200
    assert wst.called
    assert wst.return_value.process.called


async def _test_raw_websocket_fail(make_route, make_request):
    route = make_route()
    request = make_request("GET", "/sm/")
    with pytest.raises(exceptions.NotFound):
        res = await route.websocket(request)

