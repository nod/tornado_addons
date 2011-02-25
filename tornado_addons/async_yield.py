from types import GeneratorType
import inspect
import tornado.web

class TwasBrillig(object):
    def __init__(self, func, *a, **ka):
        self.func = func
        self.a = a
        self.ka = ka
        self.yielding = None

    def _yield_continue(self, response=None):
        try: self.yielding.send(response)
        except StopIteration: pass

    def yield_cb(self, *args, **ka):
        """
        A generic callback for yielded async calls that just captures all args
        and kwargs then continues execution.

        Notes about retval
        ------------------
        If a single value is returned into the callback, that value is returned
        as the value of a yield expression.

        i.e.: x = yield http.fetch(uri, self.yield_cb)

        The response from the fetch will be returned to x.

        If more than one value is returned, but no kwargs, the retval is the
        args tuple.  If there are kwargs but no args, then retval is kwargs.
        If there are both args and kwargs, retval = (args, kwargs).  If none,
        retval is None.

        It's a little gross but works for a large majority of the cases.

        """

        if args and ka:
            self._yield_continue((args, ka))
        elif ka and not args:
            self._yield_continue(ka)
        elif args and not ka:
            if len(args) == 1:
                # flatten it
                self._yield_continue(args[0])
            else:
                self._yield_continue(args)
        else:
            self._yield_continue()

    def __enter__(self):
        # munge this instance's yield_cb to map to THIS instance of a context
        self.yielding = self.func(*self.a, **self.ka)
        if type(self.yielding) is GeneratorType:
            # the first member of self.a is going to be the instance the
            # function belongs to. attach our yield_cb to that
            self.a[0].add_func_callback(self.func.func_name, self.yield_cb)
        return self.yielding

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type: print exc_type
        self.a[0].rm_func_callback(self.func.func_name)


def async_yield(f):
    f = tornado.web.asynchronous(f)
    def yielding_(*a, **ka):
        with TwasBrillig(f, *a, **ka) as f_:
            if type(f_) is not GeneratorType:
                return f_
            else:
                try:
                    f_.next() # kickstart it
                except StopIteration:
                    print "STOPPED ITERATION"
                    pass
    return yielding_


class AsyncYieldMixin(object):

    def prepare(self):
        self._yield_callbacks = {}
        super(AsyncYieldMixin, self).prepare()

    def add_func_callback(self, _id, cb):
        self._yield_callbacks[_id] = cb

    def rm_func_callback(self, _id):
        del self._yield_callbacks[_id]

    @property
    def mycb(self):
        """
        make a callback
        """
        # return inspect.stack()[1][3]  # <-- calling functions name
        # technically, this just looks up the callback, but eh. whatev
        key = inspect.stack()[1][3]
        cb = self._yield_callbacks[key]
        print "\n....... key",key," cb",cb

        return cb


