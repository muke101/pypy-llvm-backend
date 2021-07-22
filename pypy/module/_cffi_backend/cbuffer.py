from pypy.interpreter.error import oefmt, OperationError
from pypy.interpreter.gateway import unwrap_spec, interp2app
from pypy.interpreter.typedef import TypeDef, make_weakref_descr
from pypy.module._cffi_backend import cdataobj, ctypeptr, ctypearray
from pypy.module._cffi_backend import ctypestruct
from pypy.objspace.std.bufferobject import W_Buffer
from pypy.interpreter.buffer import SimpleView

from rpython.rlib.buffer import LLBuffer


# Override the typedef to narrow down the interface that's exposed to app-level

class MiniBuffer(W_Buffer):
    def __init__(self, buffer, keepalive=None):
        W_Buffer.__init__(self, buffer)
        self.keepalive = keepalive

    def descr_setitem(self, space, w_index, w_obj):
        try:
            W_Buffer.descr_setitem(self, space, w_index, w_obj)
        except OperationError as e:
            if e.match(space, space.w_TypeError):
                e.w_type = space.w_ValueError
            raise

    def _comparison_helper(self, space, w_other, mode):
        if space.isinstance_w(w_other, space.w_unicode):
            return space.w_NotImplemented
        try:
            other_buf = space.readbuf_w(w_other)
        except OperationError as e:
            if e.async(space):
                raise
            return space.w_NotImplemented
        my_buf = self.buf
        my_len = len(my_buf)
        other_len = len(other_buf)
        if other_len != my_len:
            if mode == 'E':
                return space.w_False
            if mode == 'N':
                return space.w_True
        cmp = _memcmp(my_buf, other_buf, min(my_len, other_len))
        if cmp == 0:
            if my_len < other_len:
                cmp = -1
            elif my_len > other_len:
                cmp = 1

        if   mode == 'L': res = cmp <  0
        elif mode == 'l': res = cmp <= 0
        elif mode == 'E': res = cmp == 0
        elif mode == 'N': res = cmp != 0
        elif mode == 'G': res = cmp >  0
        elif mode == 'g': res = cmp >= 0
        else: raise AssertionError

        return space.newbool(res)

    def descr_eq(self, space, w_other):
        return self._comparison_helper(space, w_other, 'E')
    def descr_ne(self, space, w_other):
        return self._comparison_helper(space, w_other, 'N')
    def descr_lt(self, space, w_other):
        return self._comparison_helper(space, w_other, 'L')
    def descr_le(self, space, w_other):
        return self._comparison_helper(space, w_other, 'l')
    def descr_gt(self, space, w_other):
        return self._comparison_helper(space, w_other, 'G')
    def descr_ge(self, space, w_other):
        return self._comparison_helper(space, w_other, 'g')

def _memcmp(buf1, buf2, length):
    # XXX very slow
    for i in range(length):
        if buf1[i] < buf2[i]:
            return -1
        if buf1[i] > buf2[i]:
            return 1
    return 0

@unwrap_spec(w_cdata=cdataobj.W_CData, size=int)
def MiniBuffer___new__(space, w_subtype, w_cdata, size=-1):
    ctype = w_cdata.ctype
    if isinstance(ctype, ctypeptr.W_CTypePointer):
        if size < 0:
            structobj = w_cdata.get_structobj()
            if (structobj is not None and
                isinstance(structobj.ctype, ctypestruct.W_CTypeStructOrUnion)):
                size = structobj._sizeof()
            if size < 0:
                size = ctype.ctitem.size
    elif isinstance(ctype, ctypearray.W_CTypeArray):
        if size < 0:
            size = w_cdata._sizeof()
    else:
        raise oefmt(space.w_TypeError,
                    "expected a pointer or array cdata, got '%s'", ctype.name)
    if size < 0:
        raise oefmt(space.w_TypeError,
                    "don't know the size pointed to by '%s'", ctype.name)
    ptr = w_cdata.unsafe_escaping_ptr()    # w_cdata kept alive by MiniBuffer()
    return MiniBuffer(LLBuffer(ptr, size), w_cdata)

MiniBuffer.typedef = TypeDef(
    "_cffi_backend.buffer",
    __new__ = interp2app(MiniBuffer___new__),
    __len__ = interp2app(MiniBuffer.descr_len),
    __getitem__ = interp2app(MiniBuffer.descr_getitem),
    __setitem__ = interp2app(MiniBuffer.descr_setitem),
    __eq__ = interp2app(MiniBuffer.descr_eq),
    __ne__ = interp2app(MiniBuffer.descr_ne),
    __lt__ = interp2app(MiniBuffer.descr_lt),
    __le__ = interp2app(MiniBuffer.descr_le),
    __gt__ = interp2app(MiniBuffer.descr_gt),
    __ge__ = interp2app(MiniBuffer.descr_ge),
    __weakref__ = make_weakref_descr(MiniBuffer),
    __str__ = interp2app(MiniBuffer.descr_str),
    __doc__ = """ffi.buffer(cdata[, byte_size]):
Return a read-write buffer object that references the raw C data
pointed to by the given 'cdata'.  The 'cdata' must be a pointer or an
array.  Can be passed to functions expecting a buffer, or directly
manipulated with:

    buf[:]          get a copy of it in a regular string, or
    buf[idx]        as a single character
    buf[:] = ...
    buf[idx] = ...  change the content
""",
    )
MiniBuffer.typedef.acceptable_as_base_class = False
