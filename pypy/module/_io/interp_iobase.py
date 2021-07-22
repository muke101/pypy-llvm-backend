from errno import EINTR
from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.error import OperationError, oefmt
from pypy.interpreter.typedef import (
    TypeDef, GetSetProperty, generic_new_descr, descr_get_dict, descr_set_dict,
    make_weakref_descr)
from pypy.interpreter.gateway import interp2app
from rpython.rlib.rstring import StringBuilder
from rpython.rlib import rweakref, rweaklist


DEFAULT_BUFFER_SIZE = 8192

def convert_size(space, w_size):
    if space.is_none(w_size):
        return -1
    else:
        return space.int_w(w_size)

def trap_eintr(space, error):
    # Return True if an EnvironmentError with errno == EINTR is set
    if not error.match(space, space.w_EnvironmentError):
        return False
    try:
        w_value = error.get_w_value(space)
        w_errno = space.getattr(w_value, space.newtext("errno"))
        return space.eq_w(w_errno, space.newint(EINTR))
    except OperationError:
        return False

def unsupported(space, message):
    w_exc = space.getattr(space.getbuiltinmodule('_io'),
                          space.newtext('UnsupportedOperation'))
    return OperationError(w_exc, space.newtext(message))

# May be called with any object
def check_readable_w(space, w_obj):
    if not space.is_true(space.call_method(w_obj, 'readable')):
        raise oefmt(space.w_IOError, "file or stream is not readable")

# May be called with any object
def check_writable_w(space, w_obj):
    if not space.is_true(space.call_method(w_obj, 'writable')):
        raise oefmt(space.w_IOError, "file or stream is not writable")

# May be called with any object
def check_seekable_w(space, w_obj):
    if not space.is_true(space.call_method(w_obj, 'seekable')):
        raise oefmt(space.w_IOError, "file or stream is not seekable")


class W_IOBase(W_Root):
    def __init__(self, space, add_to_autoflusher=True):
        # XXX: IOBase thinks it has to maintain its own internal state in
        # `__IOBase_closed` and call flush() by itself, but it is redundant
        # with whatever behaviour a non-trivial derived class will implement.
        self.space = space
        self.w_dict = space.newdict(instance=True)
        self.__IOBase_closed = False
        if add_to_autoflusher:
            get_autoflusher(space).add(self)
        if self.needs_to_finalize:
            self.register_finalizer(space)

    def getdict(self, space):
        return self.w_dict

    def _closed(self, space):
        # This gets the derived attribute, which is *not* __IOBase_closed
        # in most cases!
        w_closed = space.findattr(self, space.newtext('closed'))
        if w_closed is not None and space.is_true(w_closed):
            return True
        return False

    def _finalize_(self):
        space = self.space
        w_closed = space.findattr(self, space.newtext('closed'))
        try:
            # If `closed` doesn't exist or can't be evaluated as bool, then
            # the object is probably in an unusable state, so ignore.
            if w_closed is not None and not space.is_true(w_closed):
                space.call_method(self, "close")
        except OperationError:
            # Silencing I/O errors is bad, but printing spurious tracebacks is
            # equally as bad, and potentially more frequent (because of
            # shutdown issues).
            pass
    needs_to_finalize = True

    def _CLOSED(self):
        # Use this macro whenever you want to check the internal `closed`
        # status of the IOBase object rather than the virtual `closed`
        # attribute as returned by whatever subclass.
        return self.__IOBase_closed

    def _unsupportedoperation(self, space, message):
        raise unsupported(space, message)

    def _check_closed(self, space, message=None):
        if message is None:
            message = "I/O operation on closed file"
        if self._closed(space):
            raise OperationError(
                space.w_ValueError, space.newtext(message))

    def check_closed_w(self, space):
        self._check_closed(space)

    def closed_get_w(self, space):
        return space.newbool(self.__IOBase_closed)

    def close_w(self, space):
        if self._CLOSED():
            return
        try:
            space.call_method(self, "flush")
        finally:
            self.__IOBase_closed = True

    def flush_w(self, space):
        if self._CLOSED():
            raise oefmt(space.w_ValueError, "I/O operation on closed file")

    def seek_w(self, space, w_offset, w_whence=None):
        self._unsupportedoperation(space, "seek")

    def tell_w(self, space):
        return space.call_method(self, "seek", space.newint(0), space.newint(1))

    def truncate_w(self, space, w_size=None):
        self._unsupportedoperation(space, "truncate")

    def fileno_w(self, space):
        self._unsupportedoperation(space, "fileno")

    def enter_w(self, space):
        self._check_closed(space)
        return self

    def exit_w(self, space, __args__):
        space.call_method(self, "close")

    def iter_w(self, space):
        self._check_closed(space)
        return self

    def next_w(self, space):
        w_line = space.call_method(self, "readline")
        if space.len_w(w_line) == 0:
            raise OperationError(space.w_StopIteration, space.w_None)
        return w_line

    def isatty_w(self, space):
        self._check_closed(space)
        return space.w_False

    def readable_w(self, space):
        return space.w_False

    def writable_w(self, space):
        return space.w_False

    def seekable_w(self, space):
        return space.w_False

    # ______________________________________________________________

    def readline_w(self, space, w_limit=None):
        # For backwards compatibility, a (slowish) readline().
        limit = convert_size(space, w_limit)

        has_peek = space.findattr(self, space.newtext("peek"))

        builder = StringBuilder()
        size = 0

        while limit < 0 or size < limit:
            nreadahead = 1

            if has_peek:
                try:
                    w_readahead = space.call_method(self, "peek", space.newint(1))
                except OperationError as e:
                    if trap_eintr(space, e):
                        continue
                    raise
                if not space.isinstance_w(w_readahead, space.w_bytes):
                    raise oefmt(space.w_IOError,
                                "peek() should have returned a bytes object, "
                                "not '%T'", w_readahead)
                length = space.len_w(w_readahead)
                if length > 0:
                    n = 0
                    buf = space.bytes_w(w_readahead)
                    if limit >= 0:
                        while True:
                            if n >= length or n >= limit:
                                break
                            n += 1
                            if buf[n-1] == '\n':
                                break
                    else:
                        while True:
                            if n >= length:
                                break
                            n += 1
                            if buf[n-1] == '\n':
                                break
                    nreadahead = n

            try:
                w_read = space.call_method(self, "read", space.newint(nreadahead))
            except OperationError as e:
                if trap_eintr(space, e):
                    continue
                raise
            if not space.isinstance_w(w_read, space.w_bytes):
                raise oefmt(space.w_IOError,
                            "peek() should have returned a bytes object, not "
                            "'%T'", w_read)
            read = space.bytes_w(w_read)
            if not read:
                break

            size += len(read)
            builder.append(read)

            if read[-1] == '\n':
                break

        return space.newbytes(builder.build())

    def readlines_w(self, space, w_hint=None):
        hint = convert_size(space, w_hint)
        if hint <= 0:
            return space.newlist(space.unpackiterable(self))

        length = 0
        lines_w = []
        w_iterator = space.iter(self)
        while 1:
            try:
                w_line = space.next(w_iterator)
            except OperationError as e:
                if not e.match(space, space.w_StopIteration):
                    raise
                break
            lines_w.append(w_line)
            length += space.len_w(w_line)
            if length > hint:
                break
        return space.newlist(lines_w)

    def writelines_w(self, space, w_lines):
        self._check_closed(space)

        w_iterator = space.iter(w_lines)

        while True:
            try:
                w_line = space.next(w_iterator)
            except OperationError as e:
                if not e.match(space, space.w_StopIteration):
                    raise
                break  # done
            while True:
                try:
                    space.call_method(self, "write", w_line)
                except OperationError as e:
                    if trap_eintr(space, e):
                        continue
                    raise
                else:
                    break

    @staticmethod
    def output_slice(space, rwbuffer, target_pos, data):
        if target_pos + len(data) > rwbuffer.getlength():
            raise oefmt(space.w_RuntimeError,
                        "target buffer has shrunk during operation")
        rwbuffer.setslice(target_pos, data)


W_IOBase.typedef = TypeDef(
    '_io._IOBase',
    __new__ = generic_new_descr(W_IOBase),
    __enter__ = interp2app(W_IOBase.enter_w),
    __exit__ = interp2app(W_IOBase.exit_w),
    __iter__ = interp2app(W_IOBase.iter_w),
    next = interp2app(W_IOBase.next_w),
    close = interp2app(W_IOBase.close_w),
    flush = interp2app(W_IOBase.flush_w),
    seek = interp2app(W_IOBase.seek_w),
    tell = interp2app(W_IOBase.tell_w),
    truncate = interp2app(W_IOBase.truncate_w),
    fileno = interp2app(W_IOBase.fileno_w),
    isatty = interp2app(W_IOBase.isatty_w),
    readable = interp2app(W_IOBase.readable_w),
    writable = interp2app(W_IOBase.writable_w),
    seekable = interp2app(W_IOBase.seekable_w),

    _checkReadable = interp2app(check_readable_w),
    _checkWritable = interp2app(check_writable_w),
    _checkSeekable = interp2app(check_seekable_w),
    _checkClosed = interp2app(W_IOBase.check_closed_w),
    closed = GetSetProperty(W_IOBase.closed_get_w),
    __dict__ = GetSetProperty(descr_get_dict, descr_set_dict, cls=W_IOBase),
    __weakref__ = make_weakref_descr(W_IOBase),

    readline = interp2app(W_IOBase.readline_w),
    readlines = interp2app(W_IOBase.readlines_w),
    writelines = interp2app(W_IOBase.writelines_w),
)

class W_RawIOBase(W_IOBase):
    # ________________________________________________________________
    # Abstract read methods, based on readinto()

    def read_w(self, space, w_size=None):
        size = convert_size(space, w_size)
        if size < 0:
            return space.call_method(self, "readall")

        w_buffer = space.call_function(space.w_bytearray, w_size)
        w_length = space.call_method(self, "readinto", w_buffer)
        if space.is_w(w_length, space.w_None):
            return w_length
        space.delslice(w_buffer, w_length, space.len(w_buffer))
        return space.str(w_buffer)

    def readall_w(self, space):
        builder = StringBuilder()
        while True:
            try:
                w_data = space.call_method(self, "read",
                                           space.newint(DEFAULT_BUFFER_SIZE))
            except OperationError as e:
                if trap_eintr(space, e):
                    continue
                raise
            if space.is_w(w_data, space.w_None):
                if not builder.getlength():
                    return w_data
                break

            if not space.isinstance_w(w_data, space.w_bytes):
                raise oefmt(space.w_TypeError, "read() should return bytes")
            data = space.bytes_w(w_data)
            if not data:
                break
            builder.append(data)
        return space.newbytes(builder.build())

W_RawIOBase.typedef = TypeDef(
    '_io._RawIOBase', W_IOBase.typedef,
    __new__ = generic_new_descr(W_RawIOBase),

    read = interp2app(W_RawIOBase.read_w),
    readall = interp2app(W_RawIOBase.readall_w),
)


# ------------------------------------------------------------
# functions to make sure that all streams are flushed on exit
# ------------------------------------------------------------


class AutoFlusher(rweaklist.RWeakListMixin):
    def __init__(self, space):
        self.initialize()

    def add(self, w_iobase):
        if rweakref.has_weakref_support():
            self.add_handle(w_iobase)
        #else:
        #   no support for weakrefs, so ignore and we
        #   will not get autoflushing

    def flush_all(self, space):
        while True:
            handles = self.get_all_handles()
            self.initialize()  # reset the state here
            progress = False
            for wr in handles:
                w_iobase = wr()
                if w_iobase is None:
                    continue
                progress = True
                try:
                    space.call_method(w_iobase, 'flush')
                except OperationError:
                    # Silencing all errors is bad, but getting randomly
                    # interrupted here is equally as bad, and potentially
                    # more frequent (because of shutdown issues).
                    pass
            if not progress:
                break

def get_autoflusher(space):
    return space.fromcache(AutoFlusher)
