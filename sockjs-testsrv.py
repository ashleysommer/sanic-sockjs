import asyncio
import logging
from sanic import Sanic

import sanic_sockjs
from sanic_sockjs.transports.eventsource import EventsourceTransport
from sanic_sockjs.transports.htmlfile import HTMLFileTransport
from sanic_sockjs.transports.xhrstreaming import XHRStreamingTransport


async def echoSession(msg, session):
    if msg.type == sanic_sockjs.MSG_MESSAGE:
        session.send(msg.data)


async def closeSessionHander(msg, session):
    if msg.type == sanic_sockjs.MSG_OPEN:
        session.close()


async def broadcastSession(msg, session):
    if msg.type == sanic_sockjs.MSG_OPEN:
        session.manager.broadcast(msg.data)


if __name__ == '__main__':
    """ Sanic-Sockjs tests server """
    loop = asyncio.get_event_loop()
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s %(levelname)s %(message)s')

    HTMLFileTransport.maxsize = 4096
    EventsourceTransport.maxsize = 4096
    XHRStreamingTransport.maxsize = 4096

    app = Sanic(__name__)

    sanic_sockjs.add_endpoint(
        app, echoSession, name='echo', prefix='/echo')
    sanic_sockjs.add_endpoint(
        app, closeSessionHander, name='close', prefix='/close')
    sanic_sockjs.add_endpoint(
        app, broadcastSession, name='broadcast', prefix='/broadcast')
    sanic_sockjs.add_endpoint(
        app, echoSession, name='wsoff', prefix='/disabled_websocket_echo',
        disable_transports=('websocket',))
    sanic_sockjs.add_endpoint(
        app, echoSession, name='cookie', prefix='/cookie_needed_echo',
        cookie_needed=True)

    app.run("127.0.0.1", 8001)
