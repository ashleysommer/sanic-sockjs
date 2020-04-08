from unittest import mock

import pytest
from sanic.response import StreamingHTTPResponse
from sanic import request
from sanic_sockjs import protocol
from sanic_sockjs.transports import base
from tests.utils import make_mocked_coro


@pytest.fixture
def make_transport(make_manager, make_request, make_handler, make_fut):
    def maker(method="GET", path="/", query_params={}):
        handler = make_handler(None)
        manager = make_manager(handler)
        request = make_request(method, path, query_params=query_params)
        #request.app.freeze()
        session = manager.get("TestSessionStreaming", create=True, request=request)
        return base.StreamingTransport(manager, session, request)

    return maker


async def test_transport_ctor(make_request):
    manager = object()
    session = object()
    request = make_request("GET", "/")

    transport = base.Transport(manager, session, request)
    assert transport.manager is manager
    assert transport.session is session
    assert transport.request is request


async def test_streaming_send(make_transport):
    trans = make_transport()

    resp = trans.response = mock.Mock()
    resp.write = make_mocked_coro(None)
    stop = await trans.send("text data")
    assert not stop
    assert trans.size == len(b"text data\n")
    resp.write.assert_called_with(b"text data\n")

    trans.maxsize = 1
    stop = await trans.send("text data")
    assert stop


async def test_handle_session_interrupted(make_transport, make_fut):
    trans = make_transport()
    trans.session.interrupted = True
    trans.send = make_fut(1)
    trans.response = StreamingHTTPResponse(make_fut(0))
    await trans.handle_session()
    trans.send.assert_called_with('c[1002,"Connection interrupted"]')


async def test_handle_session_closing(make_transport, make_fut):
    trans = make_transport()
    trans.send = make_fut(1)
    trans.session.interrupted = False
    trans.session.state = protocol.STATE_CLOSING
    trans.session._remote_closed = make_fut(1)
    trans.response = StreamingHTTPResponse(make_fut(0))
    await trans.handle_session()
    trans.session._remote_closed.assert_called_with()
    trans.send.assert_called_with('c[3000,"Go away!"]')


async def test_handle_session_closed(make_transport, make_fut):
    trans = make_transport()
    trans.send = make_fut(1)
    trans.session.interrupted = False
    trans.session.state = protocol.STATE_CLOSED
    trans.session._remote_closed = make_fut(1)
    trans.response = StreamingHTTPResponse(make_fut(0))
    await trans.handle_session()
    trans.session._remote_closed.assert_called_with()
    trans.send.assert_called_with('c[3000,"Go away!"]')


async def test_session_has_request(make_transport, make_fut):
    transp = make_transport(method="POST")
    transp.session._remote_messages = make_fut(1)
    assert isinstance(transp.session.request, request.Request)
