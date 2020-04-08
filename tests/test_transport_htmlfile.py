from unittest import mock

import pytest
from sanic import request, exceptions

from tests.utils import make_mocked_coro

from sanic_sockjs.transports import htmlfile


@pytest.fixture
def make_transport(make_manager, make_request, make_handler, make_fut):
    def maker(method="GET", path="/", query_params={}):
        handler = make_handler(None)
        manager = make_manager(handler)
        request = make_request(method, path, query_params=query_params)
        #request.app.freeze()
        session = manager.get("TestSessionHtmlFile", create=True, request=request)
        return htmlfile.HTMLFileTransport(manager, session, request)

    return maker


async def test_streaming_send(make_transport):
    trans = make_transport()

    resp = trans.response = mock.Mock()
    resp.write = make_mocked_coro(None)
    stop = await trans.send("text data")
    resp.write.assert_called_with(b'<script>\np("text data");\n</script>\r\n')
    assert not stop
    assert trans.size == len(b'<script>\np("text data");\n</script>\r\n')

    trans.maxsize = 1
    stop = trans.send("text data")
    assert stop


async def test_process(make_transport, make_fut, mocker):
    transp = make_transport(query_params={"c": "calback"})
    transp.handle_session = make_fut(1)
    resp = await transp.process()
    resp.protocol = mocker.Mock()
    resp.protocol.push_data = make_fut(0)
    resp.protocol.drain = make_fut(0)
    await resp.stream()
    assert transp.handle_session.called
    assert resp.status == 200


async def test_process_no_callback(make_transport, make_fut):
    transp = make_transport()
    transp.session = mock.Mock()
    transp.session._remote_closed = make_fut(1)
    with pytest.raises(exceptions.ServerError):
        resp = await transp.process()
    assert transp.session._remote_closed.called


async def test_process_bad_callback(make_transport, make_fut):
    transp = make_transport(query_params={"c": "calback!!!!"})
    transp.session = mock.Mock()
    transp.session._remote_closed = make_fut(1)
    with pytest.raises(exceptions.ServerError):
        resp = await transp.process()
    assert transp.session._remote_closed.called


async def test_session_has_request(make_transport, make_fut):
    transp = make_transport(method="POST")
    transp.session._remote_messages = make_fut(1)
    assert isinstance(transp.session.request, request.Request)
