from types import GeneratorType
import tornado.web

def async_yield(f):
    """
    Decorates request handler methods on an AppBaseRequestHandler object such
    that we can use the yield keyword for a bit of code cleanup to make it
    easier to write and use asynchronous calls w/o having to drop into the
    callback function to continue execution.  This makes execution much easier
    to handle as we don't have to attach all method state to self and also
    following the code execution now stays in the same method.

    USAGE
    =====

    class MyHandler(RequestHandler, AsyncYieldMixin):
        @async_yield
        def get(self):
            ... stuff ...
            x = yield http_fetch(
                'http://blah',
                callback=self.yield_cb  # always use this
                )
            print "stuff returned is", x

    TECH NOTES
    ==========

    This is hard coded to be used with AppBaseRequestHandler objects and
    actually just turns the get/post/etc methods into generators and we then
    take advantage of this nature and begin execution with a call to
    self._yield_iter.next() which actually begins execution of the method.
    Then, when yield is encountered with an asynchronous call, we halt
    execution of the method until the our generic callback, self._yield_cb, is
    reached where we save off the results in self._yielded and
    self._yielded_kwargs and then call self._yield_iter.next() again to pick up
    right after the asynchronous call.

    BUT WAIT
    ========

    Q: Doesn't the yield essentially halt (or pause) the execution of the
       handler until the callback returns?
    A: YES. And, I'm ok with that.  This implementation is much more preferable
       than the series of hops we were doing and accomplishes the same thing in
       a much more elegant way.  And, if we need to do true async in multiple
       paths, there's always the original way.

    Q: What if I mix this yield stuff with the tornado async way of doing
       things like in the docs?
    A: Go for it.
    """

    f = tornado.web.asynchronous(f)
    def yielding_asynchronously(self, *a, **ka):
        self._yield_iter = f(self, *a, **ka)
        if type(self._yield_iter) is GeneratorType:
            try: self._yield_iter.next()
            except StopIteration: pass
        else: return self._yield_iter
    return yielding_asynchronously



class AsyncYieldMixin(object):
    """
    Any RequestHandler wishing to use the async_yield wrapper on it's methods
    must extend this mixin.
    """

    def ignored_cb(self, *a, **ka):
        """
        Placeholder callback for when we just don't care what happens to it.
        """
        pass

    def _yield_continue(self, response=None):
        # by sending the response to the generator, we can treat it as a
        # yield expression and do stuff like x= yield async_fun(..)
        # This takes the place of a .next() on the generator.
        try: self._yield_iter.send(response)
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

        """
        if args and ka:
            self._yield_continue((args, ka))
        if ka and not args:
            self._yield_continue(ka)
        elif args and not ka:
            if len(args) == 1:
                # flatten it
                self._yield_continue(args[0])
            else:
                self._yield_continue(args)
        else:
            self._yield_continue()

    ycb = yield_cb # because typing is lame

