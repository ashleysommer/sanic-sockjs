import inspect
from distutils.version import LooseVersion
from unittest import mock
try:
    from sanic.compat import Header as MultiDict
except ImportError:
    from sanic.response import CIMultiDict as MultiDict
from sanic import __version__ as sanic_version
from sanic.request import Request
sanic_version = LooseVersion(sanic_version)
sanic_19_6 = LooseVersion("19.6.0")
sentinel = object()
def make_mocked_coro(return_value=sentinel,
                     raise_exception=sentinel):
    """Creates a coroutine mock."""
    async def mock_coro(*args, **kwargs):
        if raise_exception is not sentinel:
            raise raise_exception
        if not inspect.isawaitable(return_value):
            return return_value
        return await return_value

    return mock.Mock(wraps=mock_coro)

def _create_transport(sslcontext=None):
    transport = mock.Mock()

    def get_extra_info(key):
        if key == 'sslcontext':
            return sslcontext
        else:
            return None

    transport.get_extra_info.side_effect = get_extra_info
    return transport

def make_mocked_request(method: str, path: bytes,
                        headers=None, *args,
                        version=(1, 1),
                        closing=False,
                        app=None,
                        writer=sentinel,
                        protocol=sentinel,
                        transport=sentinel,
                        payload=sentinel,
                        sslcontext=None,
                        client_max_size=1024**2,
                        loop=None,
                        stream=False):
    """Creates mocked web.Request testing purposes.
    Useful in unit tests, when spinning full web server is overkill or
    specific conditions and errors are hard to trigger.
    """

    task = mock.Mock()
    if loop is None:
        loop = mock.Mock()
        loop.create_future.return_value = ()

    if version < (1, 1):
        closing = True

    if headers:
        headers = MultiDict(headers)
        raw_hdrs = tuple(
            (k.encode('utf-8'), v.encode('utf-8')) for k, v in headers.items())
    else:
        headers = MultiDict()
        raw_hdrs = ()

    chunked = 'chunked' in headers.get('Transfer-Encoding', '').lower()

    # message = RawRequestMessage(
    #     method, path, version, headers,
    #     raw_hdrs, closing, False, False, chunked, URL(path))
    if app is None:
        app = _create_app_mock()

    if transport is sentinel:
        transport = _create_transport(sslcontext)

    if protocol is sentinel:
        protocol = mock.Mock()
        protocol.transport = transport

    if writer is sentinel:
        writer = mock.Mock()
        writer.write_headers = make_mocked_coro(None)
        writer.write = make_mocked_coro(None)
        writer.write_eof = make_mocked_coro(None)
        writer.drain = make_mocked_coro(None)
        writer.transport = transport

    protocol.transport = transport
    protocol.writer = writer

    if payload is sentinel:
        payload = b""

    if sanic_19_6 > sanic_version:
        req = Request(path, headers, version, method, transport=transport)
        req.app = app
    else:
        req = Request(path, headers, version, method, transport=transport, app=app)
    if stream:
        mock_stream = mock.Mock()
        mock_stream.read = make_mocked_coro(payload)
        req.stream = mock_stream
    else:
        req.body_push(payload)
        req.body_finish()
    # req = Request(message, payload,
    #               protocol, writer, task, loop,
    #               client_max_size=client_max_size)

    return req