SockJS server based on Asyncio (PEP 3156)
=========================================

.. image :: https://secure.travis-ci.org/ashleysommer/sanic-sockjs.svg
  :target:  https://secure.travis-ci.org/ashleysommer/sanic-sockjs

`sanic_sockjs` is a `SockJS <http://sockjs.org>`_ integration for
`Sanic <https://github.com/huge-success/sanic/>`_.  SockJS interface
is implemented as a `Sanic` route. Its possible to create any number
of different sockjs routes, ie `/sockjs/*` or
`/mycustom-sockjs/*`. You can provide different session implementation
and management for each sockjs route.

Simple Sanic web server is required::

   [server:main]
   use = egg:gunicorn#main
   host = 0.0.0.0
   port = 8080
   worker = sanic.worker.GunicornWorker


Example of sockjs route::

   def main(global_settings, **settings):
       app = Sanic(__main__)
       @app.get('/')
       def index(request):
           ...


       sanic_sockjs.add_endpoint(app, prefix='/sockjs', handler=chatSession)
       app.run("127.0.0.1", 8080)


Client side code::

  <script src="//cdn.jsdelivr.net/npm/sockjs-client@1/dist/sockjs.js"></script>
  <script>
      var sock = new SockJS('http://localhost:8080/sockjs');

      sock.onopen = function() {
        console.log('open');
      };

      sock.onmessage = function(obj) {
        console.log(obj);
      };

      sock.onclose = function() {
        console.log('close');
      };
  </script>


Supported transports
--------------------

* websocket `hybi-10
  <http://tools.ietf.org/html/draft-ietf-hybi-thewebsocketprotocol-10>`_
* `xhr-streaming
  <https://secure.wikimedia.org/wikipedia/en/wiki/XMLHttpRequest#Cross-domain_requests>`_
* `xhr-polling
  <https://secure.wikimedia.org/wikipedia/en/wiki/XMLHttpRequest#Cross-domain_requests>`_
* `iframe-xhr-polling
  <https://developer.mozilla.org/en/DOM/window.postMessage>`_
* iframe-eventsource (`EventSource
  <http://dev.w3.org/html5/eventsource/>`_ used from an `iframe via
  postMessage
  <https://developer.mozilla.org/en/DOM/window.postMessage>`_)
* iframe-htmlfile (`HtmlFile
  <http://cometdaily.com/2007/11/18/ie-activexhtmlfile-transport-part-ii/>`_
  used from an *iframe via postMessage*.
* `jsonp-polling <https://secure.wikimedia.org/wikipedia/en/wiki/JSONP>`_


Requirements
------------

- Python >= 3.6

- Sanic >= 19.3.1 https://github.com/huge-success/sanic


Examples
--------

You can find several `examples` in the sanic_sockjs repository at github.

https://github.com/ashleysommer/sanic-sockjs/tree/master/examples


License
-------

sockjs is offered under the Apache 2 license.
