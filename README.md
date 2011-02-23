# tornado_addons

Consider this the wicked witch pedaling frantically around Dorothy's house as
it swirls in the air.... (lame jokes over).

This is a collection of addons and accompanying unit tests for the excellent
[Tornado web server](http://www.tornadoweb.org/)

These addons are licensed the same as Tornado under the Apache Licence,
Version 2.0 (http://www.apache.org/licenses/LICENSE-2.0.html).

## Installation

Just place this directory in your python path.

## Testing

Every addon will have a set of accompanying unit tests.  We prefer to run them
via [Nose](http://code.google.com/p/python-nose/).

    cd tornado_addons/
    nosetests

## Usage

The best source of information is the comments in routes.py or async_yield.py.
They're fairly well commented and give a better understanding of the libs.

### routes

Here's a simple example.

    import tornado.web
    from tornado_addons.route import route

    @route('/blah')
    class SomeHandler(tornado.web.RequestHandler):
        pass

    t = tornado.web.Application(route.get_routes(), {'some app': 'settings'}


### Async yields

Here's an example with normal callbacks.

    from tornado.httpclient import AsyncHTTPClient

    @tornado.web.asynchronous
    class SomeHandler(tornado.web.RequestHandler):
        def get(self):
            self.somedata = 'xxx'
            AsyncHTTPClient.fetch(
                'http://over/there',
                callback=self.my_async_http_cb )

        def my_async_http_cb(self, fetch_data):
            # do stuff here....
            self.write(self.somedata)


Or,  you can wrap your methods with async_yield...

    from tornado_addons.async_yield import async_yield, AsyncYieldMixin

    class SomeHandler(tornado.web.RequestHandler, AsyncYieldMixin):
        @async_yield
        def get(self):
            somedata = 'xxx'
            fetchdata = yield AsyncHTTPClient.fetch(
                                  'http://over/there',
                                  callback=self.async_cb )
            self.write(somedata)

The @async_yield wrapper doesn't work for every method with callbacks but it
does cleanup your RequestHandlers quite nicely and really streamlines workflow.


