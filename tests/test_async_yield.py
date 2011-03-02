
from ..tornado_addons.async_yield import async_yield, AsyncYieldMixin

import tornado
from random import randint

from tornado.testing import AsyncTestCase


class AYHandler(AsyncYieldMixin, tornado.web.RequestHandler):
    """
    very basic handler for writing async yield tests on a RequestHandler
    """

    def __init__(self):
        """
        fake this to make it easier to instantiate
        """
        self.application = tornado.web.Application([], {})

    def prepare(self):
        super(AYHandler, self).prepare()

    def async_assign(self, newdata, callback):
        """
        totally contrived async function
        """
        self.test_ioloop.add_callback(lambda: callback(newdata))

    @async_yield
    def embedded_async(self, callback):
        xx = yield self.async_assign('me', self.mycb('embedded_async'))
        callback(xx)

    @async_yield
    def some_async_func(self, ioloop, val, callback):
        self.test_ioloop = ioloop # we have to fake this for tests
        results = yield self.async_assign(val, self.mycb('some_async_func'))
        callback(results)

    @async_yield
    def call_other_async(self, ioloop, val, callback):
        cb = self.mycb('call_other_async')
        self.test_ioloop = ioloop # we have to fake this for tests
        yield self.embedded_async(cb)
        results = yield self.async_assign(val, cb)
        callback(results)


class AYHandlerTests(AsyncTestCase):

    def setUp(self):
        AsyncTestCase.setUp(self)
        self.handler = AYHandler()
        self.handler.prepare()

    def tearDown(self):
        del self.handler

    def test_async_func(self):
        self.handler.some_async_func(self.io_loop, 'xyzzy', self.stop)
        retval = self.wait()
        self.assertTrue('xyzzy' == retval)

    def test_async_func_return_more(self):
        self.handler.some_async_func(self.io_loop, [1,2,3], self.stop)
        retval = self.wait()
        self.assertTrue(len(retval) == 3 and retval[1] == 2)

    def test_call_other_async_yield(self):
        self.handler.call_other_async(self.io_loop, [1,2,3], self.stop)
        retval = self.wait()
        self.assertTrue(len(retval) == 3 and retval[1] == 2)
        
