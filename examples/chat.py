import os
import logging
from sanic import Sanic
from sanic.response import HTTPResponse
import sanic_sockjs

CHAT_FILE = open(
    os.path.join(os.path.dirname(__file__), 'chat.html'), 'rb').read()


async def chat_msg_handler(msg, session):
    if msg.type == sanic_sockjs.MSG_OPEN:
        session.manager.broadcast("Someone joined.")
    elif msg.type == sanic_sockjs.MSG_MESSAGE:
        session.manager.broadcast(msg.data)
    elif msg.type == sanic_sockjs.MSG_CLOSED:
        session.manager.broadcast("Someone left.")

app = Sanic(__name__)

@app.get('/')
async def index(request):
    return HTTPResponse(None, body_bytes=CHAT_FILE, content_type="text/html")


if __name__ == '__main__':
    """Simple sockjs chat."""
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s %(levelname)s %(message)s')

    sanic_sockjs.add_endpoint(app, chat_msg_handler, name='chat', prefix='/sockjs/')

    app.run("127.0.0.1", 8002)
