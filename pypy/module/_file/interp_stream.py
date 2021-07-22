import py

from rpython.rlib import streamio
from rpython.rlib.streamio import StreamErrors

from pypy.interpreter.error import OperationError, oefmt
from pypy.interpreter.baseobjspace import ObjSpace, W_Root, CannotHaveLock
from pypy.interpreter.typedef import TypeDef
from pypy.interpreter.gateway import interp2app
from pypy.interpreter.streamutil import wrap_streamerror, wrap_oserror_as_ioerror


class W_AbstractStream(W_Root):
    """Base class for interp-level objects that expose streams to app-level"""
    slock = None
    slockowner = None
    # Locking issues:
    # * Multiple threads can access the same W_AbstractStream in
    #   parallel, because many of the streamio calls eventually
    #   release the GIL in some external function call.
    # * Parallel accesses have bad (and crashing) effects on the
    #   internal state of the buffering levels of the stream in
    #   particular.
    # * We can't easily have a lock on each W_AbstractStream because we
    #   can't translate prebuilt lock objects.
    # We are still protected by the GIL, so the easiest is to create
    # the lock on-demand.

    def __init__(self, space, stream):
        self.space = space
        self.stream = stream

    def _try_acquire_lock(self):
        # this function runs with the GIL acquired so there is no race
        # condition in the creation of the lock
        me = self.space.getexecutioncontext()   # used as thread ident
        if self.slockowner is not None:
            if self.slockowner is me:
                return False    # already acquired by the current thread
            if self.slockowner.thread_disappeared:
                self.slockowner = None
                self.slock = None
        try:
            if self.slock is None:
                self.slock = self.space.allocate_lock()
        except CannotHaveLock:
            pass
        else:
            self.slock.acquire(True)
        assert self.slockowner is None
        self.slockowner = me
        return True

    def _release_lock(self):
        self.slockowner = None
        if self.slock is not None:
            self.slock.release()

    def lock(self):
        if not self._try_acquire_lock():
            raise oefmt(self.space.w_RuntimeError, "stream lock already held")

    def unlock(self):
        me = self.space.getexecutioncontext()   # used as thread ident
        if self.slockowner is not me:
            raise oefmt(self.space.w_RuntimeError, "stream lock is not held")
        self._release_lock()

    def _cleanup_(self):
        # remove the lock object, which will be created again as needed at
        # run-time.
        self.slock = None
        assert self.slockowner is None

    def stream_read(self, n):
        """
        An interface for direct interp-level usage of W_AbstractStream,
        e.g. from interp_marshal.py.
        NOTE: this assumes that the stream lock is already acquired.
        Like os.read(), this can return less than n bytes.
        """
        try:
            return self.stream.read(n)
        except StreamErrors as e:
            raise wrap_streamerror(self.space, e)

    def do_write(self, data):
        """
        An interface for direct interp-level usage of W_Stream,
        e.g. from interp_marshal.py.
        NOTE: this assumes that the stream lock is already acquired.
        """
        try:
            self.stream.write(data)
        except StreamErrors as e:
            raise wrap_streamerror(self.space, e)


# ____________________________________________________________

class W_Stream(W_AbstractStream):
    """A class that exposes the raw stream interface to app-level."""
    # this exists for historical reasons, and kept around in case we want
    # to re-expose the raw stream interface to app-level.

for name, argtypes in streamio.STREAM_METHODS.iteritems():
    numargs = len(argtypes)
    argtypes = [typ if typ is not str else 'bytes' for typ in argtypes]
    args = ", ".join(["v%s" % i for i in range(numargs)])
    exec py.code.Source("""
    def %(name)s(self, space, %(args)s):
        acquired = self.try_acquire_lock()
        try:
            try:
                result = self.stream.%(name)s(%(args)s)
            except streamio.StreamError, e:
                raise OperationError(space.w_ValueError,
                                     space.newtext(e.message))
            except OSError, e:
                raise wrap_oserror_as_ioerror(space, e)
        finally:
            if acquired:
                self.release_lock()
        return space.wrap(result)
    %(name)s.unwrap_spec = [W_Stream, ObjSpace] + argtypes
    """ % locals()).compile() in globals()

W_Stream.typedef = TypeDef("Stream",
    lock   = interp2app(W_Stream.lock),
    unlock = interp2app(W_Stream.unlock),
    **dict([(name, interp2app(globals()[name]))
                for name, _ in streamio.STREAM_METHODS.iteritems()]))
