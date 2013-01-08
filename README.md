
# DEPRECATED

This project has been pretty much abandoned in favor of splitting out the
useful bits into their own standalone libraries.  This makes testing much
easier and doesn't require people who just want individual bits to satisfy the
requirements for the parts they don't wish to use.

Please see [tornroutes](http://github.com/nod/tornroutes) for the route
decorator.

Async Yields have been deprecated in favor of the superior gen.task that's
included in tornado core now.

CushionDBMixin has been abandoned.  Sorry.


# tornado_addons

This is a collection of addons and accompanying unit tests for the excellent
[Tornado web server](http://www.tornadoweb.org/)

These addons are licensed the same as Tornado under the Apache Licence,
Version 2.0 (http://www.apache.org/licenses/LICENSE-2.0.html).

## Installation

Just place this directory in your python path or run the following:

    sudo python setup.py install

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
            AsyncHTTPClient.fetch( 'http://over/there',
                callback=self.my_async_http_cb )

        def my_async_http_cb(self, fetch_data):
            # do stuff with fetchdata here
            self.write(self.somedata)


Or,  you can wrap your methods with async_yield...

    from tornado_addons.async_yield import async_yield, AsyncYieldMixin

    class SomeHandler(tornado.web.RequestHandler, AsyncYieldMixin):

		@async_yield
		def some_func(self, callback):
			x = yield some_async_call(callback=self.yield_cb)
			callback(x)

        @async_yield
		@tornado.web.asynchronous
        def get(self):
            ycb = self.yield_cb
			retval = yield some_func(ycb)
            somedata = 'xxx'
            fetchdata = yield AsyncHTTPClient.fetch( 'http://over/there',
                                  callback=ycb )
            # do stuff with fetchdata here
            self.write(fetchdata.body if not fetchdata.error else '')


The @async_yield wrapper works for methods bound to a RequestHandler.


### CushionDBMixin

Cushion is a bit of an extraction layer around
[trombi](http://github.com/inoi/trombi), an asynchronous CouchDB driver for
Tornado.

It provides a mixin for RequestHandler that simplifies database access,
especially when used in conjunction with async_yield.

    from tornado.web import RequestHandler
    from tornado_addons.cushion import CushionDBMixin
    from tornado_addons.async_yield import async_yield, AsyncYieldMixin

    class SomeHandler(RequestHandler, CushionDBMixin, AsyncYieldMixin):

        @async_yield
		@tornado.web.asynchronous
        def get(self):
            ycb = self.mycb('get')
            yield self.db_setup('someDB', uri_to_couchdb, ycb)
            x = yield self.db_one('some_key', ycb)
            # ... do stuff wth your data in x now
			self.finish()

