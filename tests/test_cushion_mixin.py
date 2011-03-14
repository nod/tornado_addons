
"""
test the CushionDBMixin on RequestHandlers

NOTE - CushionDBMIxin lacks FULL TEST COVERAGE! FIXME
"""

try:
    import trombi
    no_trombi = False
except:
    no_trombi = True

from unittest import skipIf
from random import randint
from ..tornado_addons.cushion import Cushion, CushionException, CushionDBNotReady

baseurl = 'http://localhost:5984'

from ..tornado_addons.async_yield import AsyncYieldMixin
from ..tornado_addons.cushion import CushionDBMixin

import tornado
from random import randint

from tornado.testing import AsyncTestCase


class CushionHandler(CushionDBMixin, AsyncYieldMixin, tornado.web.RequestHandler):
    """
    very basic handler for writing async yield tests on a RequestHandler
    """
    def __init__(self):
        # we need this to avoid RequestHandler's gross __init__ requirements
        pass

    def prepare(self):
        super(CushionHandler,self).prepare()


@skipIf(no_trombi, "not testing Cushion, trombi failed to import")
class CushionMixinTests(AsyncTestCase):

    def setUp(self):
        AsyncTestCase.setUp(self)
        dbname =  'test_db' + str(randint(100, 100000))
        print "WORKING ON", dbname
        self.handler = CushionHandler()
        self.handler.prepare()
        # typically, this would be called in the Handler.prepare()
        self.handler.db_setup(
            dbname, baseurl,
            io_loop=self.io_loop, callback=self.stop, create=True )
        self.wait()

        # create one test record
        print "self.handler.db_default=",self.handler.db_default, CushionDBMixin.db_default
        self.handler.cushion.save(self.handler.db_default, {'fake':'data'}, callback=self.stop)
        rec = self.wait()
        self.record = rec.raw()

    def tearDown(self):
        self.handler.cushion._server.delete(self.handler.db_default, self.stop)
        self.wait()
        del self.handler

    def test_db_one(self):
        self.handler.db_one(self.record['_id'], self.stop)
        rec = self.wait()
        self.assertTrue(self.record['fake'] == rec['fake'])

