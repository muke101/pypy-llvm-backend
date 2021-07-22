import py
from py.test import raises
from pypy.interpreter.error import OperationError
from pypy.tool.pytest.objspace import gettestobjspace

class TestW_StdObjSpace:

    def test_wrap_wrap(self):
        py.test.skip("maybe unskip in the future")
        raises(TypeError,
                          self.space.wrap,
                          self.space.wrap(0))

    def test_str_w_non_str(self):
        raises(OperationError,self.space.str_w,self.space.wrap(None))
        raises(OperationError,self.space.str_w,self.space.wrap(0))

    def test_int_w_non_int(self):
        raises(OperationError,self.space.int_w,self.space.wrap(None))
        raises(OperationError,self.space.int_w,self.space.wrap(""))

    def test_uint_w_non_int(self):
        raises(OperationError,self.space.uint_w,self.space.wrap(None))
        raises(OperationError,self.space.uint_w,self.space.wrap(""))

    def test_sliceindices(self):
        space = self.space
        w_obj = space.appexec([], """():
            class Stuff(object):
                def indices(self, l):
                    return 1,2,3
            return Stuff()
        """)
        w = space.wrap
        w_slice = space.newslice(w(1), w(2), w(1))
        assert space.sliceindices(w_slice, w(3)) == (1,2,1)
        assert space.sliceindices(w_obj, w(3)) == (1,2,3)

    def test_fastpath_isinstance(self):
        from pypy.objspace.std.bytesobject import W_BytesObject
        from pypy.objspace.std.intobject import W_IntObject
        from pypy.objspace.std.iterobject import W_AbstractSeqIterObject
        from pypy.objspace.std.iterobject import W_SeqIterObject

        space = self.space
        assert space._get_interplevel_cls(space.w_bytes) is W_BytesObject
        assert space._get_interplevel_cls(space.w_int) is W_IntObject
        class X(W_BytesObject):
            def __init__(self):
                pass

            typedef = None

        assert space.isinstance_w(X(), space.w_bytes)

        w_sequenceiterator = space.gettypefor(W_SeqIterObject)
        cls = space._get_interplevel_cls(w_sequenceiterator)
        assert cls is W_AbstractSeqIterObject

    def test_wrap_various_unsigned_types(self):
        import sys
        from rpython.rlib.rarithmetic import r_uint
        from rpython.rtyper.lltypesystem import lltype, rffi
        space = self.space
        value = sys.maxint * 2
        x = r_uint(value)
        assert space.eq_w(space.wrap(value), space.wrap(x))
        x = rffi.cast(rffi.UINTPTR_T, r_uint(value))
        assert x > 0
        assert space.eq_w(space.wrap(value), space.wrap(x))
        value = 60000
        x = rffi.cast(rffi.USHORT, r_uint(value))
        assert space.eq_w(space.wrap(value), space.wrap(x))
        value = 200
        x = rffi.cast(rffi.UCHAR, r_uint(value))
        assert space.eq_w(space.wrap(value), space.wrap(x))
