
"""
Tests the base cushion class. Gets skipped if trombi doesn't import.
"""

try:
    import trombi
    no_trombi = False
except:
    no_trombi = True

from unittest import skipIf
from random import randint
from tornado.testing import AsyncTestCase
from ..tornado_addons.cushion import Cushion, CushionException, CushionDBNotReady

baseurl = 'http://localhost:5984'

@skipIf(no_trombi, "not testing Cushion, trombi failed to import")
class CushionTests(AsyncTestCase):

    def setUp(self):
        AsyncTestCase.setUp(self)

        # now create our test cushion object
        self.cushion = Cushion(baseurl, io_loop=self.io_loop)
        assert isinstance(self.cushion._server, trombi.Server)

        # create a test db
        self.dbname = 'test_db' + str(randint(100, 100000))
        # connect to our database
        # this tests our open(..) method on cushion. I'd rather have it
        # in a separate test, but we need this database and if open fails here,
        # everything else should tank, so setUp is as good a place as any.
        self.cushion.create(self.dbname, self.stop)
        self.wait()
        self.cushion.open(self.dbname, self.stop)
        self.wait()
        # we're after the db has been added
        assert isinstance(self.cushion._pool[self.dbname], trombi.Database)

    def tearDown(self):
        # just blow away our test database using standard trombi fare
        self.cushion._server.delete(self.dbname, self.stop)
        self.wait()

    def test_db_open_with_callback(self):
        # note, this creates and deletes a bogus db
        bogus_db = 'test_db_trash_' + str(randint(10,99))
        self.cushion.create(bogus_db, self.stop)
        self.wait()
        self.cushion.open(bogus_db, self.stop)
        self.wait()
        self.assertTrue(bogus_db in self.cushion)
        self.cushion._server.delete(self.dbname, self.stop)
        self.wait()

    def test_db_not_exists(self):
        # note, this creates and deletes a bogus db
        bogus_db = 'test_db_not_exists_' + str(randint(10,99))
        self.cushion.exists(bogus_db, self.stop)
        is_there = self.wait()
        self.assertTrue( not is_there )

    def test_db_exists(self):
        # note, this creates and deletes a bogus db
        self.cushion.exists(self.dbname, self.stop)
        is_there = self.wait()
        self.assertTrue( is_there )

    def test_db_exists_make_one(self):
        # note, this creates and deletes a bogus db
        bogus_db = 'test_db_exists_' + str(randint(10,99))
        self.cushion.create(bogus_db, self.stop)
        self.wait()
        self.cushion.exists(bogus_db, self.stop)
        is_there = self.wait()
        self.assertTrue( is_there )

    def test_db_get(self):
        # check for a bogus database first
        self.assertRaises(
            CushionDBNotReady,
            self.cushion.get, 'bogus-not-there' )

        # now check for a good one
        self.assertTrue(
            isinstance(
                self.cushion.get(self.dbname),
                trombi.Database
                )
            )

    def test_db_ready(self):
        self.assertTrue( self.cushion.ready(self.dbname) )

    def test_db_shorthand_in(self):
        self.assertTrue( self.dbname in self.cushion )

    def _save_some_data(self, data):
        self.cushion.save( self.dbname, data, self.stop)
        return self.wait()

    def test_save(self):
        data = {'shoesize': 11}
        doc = self._save_some_data(data)
        self.assertTrue( '_id' in doc.raw() )
        self.saving_data = doc.raw()

    def test_delete(self):

        # try to delete bogus data
        try:
            self.cushion.delete(self.dbname, {'bogus':'yep'}, self.stop)
            self.wait()
        except Exception, e:
            self.assertTrue(isinstance(e, CushionException))

        # delete real data
        data = {'shoesize': 11}
        doc = self._save_some_data(data)
        self.cushion.delete(self.dbname, doc.raw(), self.stop)
        retval = self.wait()
        self.assertFalse(retval.error)

    def test_one(self):
        doc = self._save_some_data({'shoes':11, 'hat':'fitted'}).raw()
        self.cushion.one(self.dbname, doc['_id'], self.stop )
        retval = self.wait()
        self.assertEqual(retval['shoes'], doc['shoes'])

    def test_one_fail(self):
        self.cushion.one(self.dbname, 'just_not_there', self.stop )
        self.assertTrue( not self.wait() )

    def test_one_return_type(self):
        doc = self._save_some_data({'shoes':11, 'hat':'fitted'}).raw()
        self.cushion.one(self.dbname, doc['_id'], self.stop )
        retval = self.wait()
        # should be a dict
        self.assertTrue( type({}) == type(retval) )

    def test_view(self):
        # This test does quite a bit.  First, create 4 test records.
        # Then, create a view that will emit those records and insert that into
        # the db.  Finally, call our cushion.view object and compare results.

        self._save_some_data({'foo': 1, 'bar': 'a'})
        self._save_some_data({'foo': 2, 'bar': 'a'})
        self._save_some_data({'foo': 3, 'bar': 'b'})
        self._save_some_data({'foo': 4, 'bar': 'b'})

        fake_map = """ function (doc) { emit(doc['bar'], doc); } """

        # we're going to use python-couchdb's dynamic view loader stuff here
        from couchdb.design import ViewDefinition
        from couchdb.client import Server
        global baseurl
        cdb = Server(baseurl)
        couchdb = cdb[self.dbname]

        view_defn = ViewDefinition(
            'test', 'view',
            map_fun = fake_map,
            language = 'javascript' )
        view_defn.sync(couchdb)

        self.cushion.view(self.dbname, 'test/view', self.stop, key='b')
        records = self.wait()

        self.assertTrue(len(records) == 2)

        # OPTIMIZE: do more to ensure we're getting back what we want

