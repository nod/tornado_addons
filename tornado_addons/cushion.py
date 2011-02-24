import logging
import trombi


class CushionException(Exception):
    """
    Generic Cushion Exception
    """
    pass


class CushionDBNotReady(Exception):
    """
    This Exception will be tossed when a database hasn't been connected yet.
    """
    pass


class Cushion(object):
    """
    Captures a pool of db connections here since each account can have their
    own connection.
    """
    _pool = {}
    _server = None

    def __init__(self, uri, user=None, password=None, **ka):
        self._server = trombi.Server(
            uri,
            fetch_args=dict(auth_username=user, auth_password=password),
            **ka)

    def create(self, dbname, callback):
        """
        Attempt to create a database. If it exists, an exception will be
        thrown.
        """
        self._server.create(
            name=dbname,
            callback=callback )

    def exists(self, dbname, callback):
        """
        Attempt to get a connection to the specified database but don't add it
        to our pool if it's there.  You should use open(..) if you intend to
        use the database in the near future.
        """
        if dbname in self:
            # short circuit the whole mess if it's in "us"
            callback(True)
            return

        callback_ = callback

        def cb_(db):
            if db.error: callback_(False)
            else: callback_(True)

        self._server.get(
            name=dbname,
            callback=cb_,
            create=False )

    def open(self, dbname, callback, create=False):
        """
        Open a connection to a specific database instance.  If the database
        doesn't exist, an exception will be thrown unless create=True
        """
        if dbname in self:
            print "found db in self"
            callback(self.get(dbname))
        else:
            print "db NOT FOUND in self"
            def cb_wrapper(db, callback_=callback):
                print "adding DB"
                self._cb_add_db(db)
                callback_(db)
            self._server.get(
                name=dbname,
                callback=cb_wrapper,
                create=create )

    def _cb_add_db(self, db):
        if db.error:
            logging.critical("ERROR WITH COUCHDB "+db.msg)
            raise CushionException(db.msg)
        else:
            logging.info("couchdb initialized "+str(db))
            self._pool[db.name] = db

    def get(self, dbname):
        if not self._pool.has_key(dbname):
            raise CushionDBNotReady(dbname + ' not open yet')
        return self._pool[dbname]

    def ready(self, dbname):
        """
        check that a database is actually connected.
        """
        return dbname in self

    def __contains__(self, dbname):
        return dbname in self._pool

    def one(self, db, _id, cb, **ka):
        """
        Convenience method to fetch one object by id from the specified
        database.

        Parameters
        ==========
        db -> db name as str
        _id -> key of document to fetch as str
        cb -> function ptr to callback
        ka -> keyword arguments
        """
        def _cb(doc):
            cb(doc.raw() if doc else None)
        # note, this is calling the .get method on a trombi Database obj
        self.get(db).get(_id, _cb, **ka)

    def view(self, db, resource, cb, **ka):
        """
        Convenience method to fetch the results of a view from a specific
        database.
        Parameters
        ==========
        db -> db name as str
        resource -> string of the resource 'designDocName/resourceName'
            or '/resourceName' to hit the special view '_alldocs'
        cb -> function ptr to callback
        ka -> keyword arguments
        """
        des, res = resource.split('/')
        # note, this is calling the .view method on a trombi Database obj
        self.get(db).view(des, res, cb, **ka)

    def save(self, db, data, callback=None):
        """saves dict to couchdb"""
        if not callback: callback = self._generic_cb
        # FIXME: should this look for _rev also?
        if '_id' in data: 
            self.get(db).set(data['_id'], data, callback)
        else: 
            self.get(db).set(data, callback)

    def _generic_cb(self, doc):
        if doc.error:
            logging.error("ERROR:" + doc.msg)

    def delete(self, db, data, callback=None):
        """
        Remove doc from database.

        data requires an _id and _rev or an exception is thrown.
        """
        if not callback: callback = self._generic_cb
        if '_id' in data and '_rev' in data:
            self.get(db).delete(data, callback)
        else: raise CushionException(
                "record missing _id and _rev, can't delete"
                )


class CushionDBMixin(object):

    db_default = ''
    cushion = None

    def db_ignored_cb(self, *a, **ka):
        """
        do as much nothing as possible
        """
        pass

    def db_setup(self, dbname, uri, callback, **kwa):
        print "DB_SETUP", dbname, uri, callback, kwa
        self.db_default = dbname
        if not self.cushion:
            self.cushion = Cushion(uri, io_loop=kwa.get('io_loop'))
        self.cushion.open(
            dbname,
            callback=callback,
            create=kwa.get('create')  )

    def _db_cb_get(self, callback, ignore_cb):
        # we should never have a callback AND ignore_cb
        # and we should have at least one
        assert(not callback and ignore_cb)
        assert(callback or not ignore_cb)
        if ignore_cb: callback_ = self.db_ignored_cb
        elif not callback:
            if not hasattr(self, 'yield_cb'):
                raise Exception(
                    "default callbacks must extend AsyncYieldMixin" )
            callback_ = self.yield_cb
        else: callback_ = callback
        return callback_


    def db_save(self, data, db=None, callback=None, ignore_cb=False):
        # default to the account database
        if not db: db = self.db_default

        callback = self._db_cb_get(callback, ignore_cb)

        cush = self.cushion
        # if the db's not open, we're going to open the db with the callback
        # being the same way we were called
        if db not in cush: # db's not ready...
            cush.open( db, lambda *a: self.db_save(data, db, callback))
        else:
            cush.save(db, data, callback)


    def db_delete(self, obj, db=None, callback=None, ignore_cb=False):
        if not db: db = self.db_default

        callback = self._db_cb_get(callback, ignore_cb)

        cush = self.cushion
        if db not in cush: # db's not ready...
            # open the db then call ourselves once it's ready to go
            cush.open(
                db,
                lambda *a: self.db_delete(
                            obj,
                            db,
                            callback=callback,
                            ignore_cb=ignore_cb )
                )
        else: cush.delete(db, obj, callback)


    def db_one(self, key, db=None, callback=None, **kwargs):
        """
        Retrieve a particular document from couchdb.

        If no callback is specified, this will assume self.yield_cb.  This
        means, for convenience, this can be called like the following:

          x = yield self.db_one(dbname, key)

        Parameters:
        db <-   name of the db to hit.  If this db isn't in our cushion, we'll
                block until we get that connection.
        key <-  the key of our document, a string.
        callback <- None or a function to call upon completion.
        **  any other remaining kwargs will be passed through to cushion's .one
            call, which passes them to trombi.
        """
        logging.debug("------------- couch 1 -------------")

        # default to the account db
        if not db: db = self.db_default

        if not callback:
            # for convenience, if no callback is passed in, we'll assume an
            # async_yield situation.
            callback = self.yield_cb

        cush = self.cushion
        # if the db's not open, we're going to open the db with the callback
        # being the same way we were called
        if db not in cush: # db's not ready...
            cush.open(
                db,
                lambda *a: self.db_one(key, db, callback=callback, **kwargs)
                )
        else: cush.one(db, key, callback, **kwargs)


    def db_view(self, resource, db=None, callback=None, **kwargs):
        """
        see comments for db_one
        """
        logging.debug("------------- couch * -------------")

        # default to the account db
        if not db: db = self.db_default

        if not callback:
            # for convenience, if no callback is passed in, we'll assume an
            # async_yield situation.
            callback = self.yield_cb
        cush = self.cushion
        # if the db's not open, we're going to open the db with the callback
        # being the same way we were called
        if db not in cush: # db's not ready...
            # open the db then call ourselves once it's ready to go
            cush.open(
                db,
                lambda *a: self.db_view(
                    resource, db, callback=callback, **kwargs )
                )
        else:
            cush.view(db, resource, callback, **kwargs)



