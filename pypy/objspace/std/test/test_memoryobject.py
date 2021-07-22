class AppTestMemoryView:
    def test_basic(self):
        v = memoryview(b"abc")
        assert v.tobytes() == b"abc"
        assert len(v) == 3
        assert list(v) == ['a', 'b', 'c']
        assert v.tolist() == [97, 98, 99]
        assert v[1] == "b"
        assert v[-1] == "c"
        exc = raises(TypeError, "v[1] = b'x'")
        assert str(exc.value) == "cannot modify read-only memory"
        assert v.readonly is True
        w = v[1:234]
        assert isinstance(w, memoryview)
        assert len(w) == 2
        exc = raises(NotImplementedError, "v[0:2:2]")
        assert str(exc.value) == ""

    def test_rw(self):
        data = bytearray(b'abcefg')
        v = memoryview(data)
        assert v.readonly is False
        v[0] = 'z'
        assert data == bytearray(eval("b'zbcefg'"))
        v[1:4] = '123'
        assert data == bytearray(eval("b'z123fg'"))
        v[0:3] = v[2:5]
        assert data == bytearray(eval("b'23f3fg'"))
        exc = raises(ValueError, "v[2] = 'spam'")
        assert str(exc.value) in ("cannot modify size of memoryview object",
                                  "string must be of size 1")
        exc = raises(NotImplementedError, "v[0:2:2] = 'spam'")
        assert str(exc.value) == ""

    def test_memoryview_attrs(self):
        v = memoryview(b"a"*100)
        assert v.format == "B"
        assert v.itemsize == 1
        assert v.shape == (100,)
        assert v.ndim == 1
        assert v.strides == (1,)

    def test_suboffsets(self):
        v = memoryview(b"a"*100)
        assert v.suboffsets == None
        v = memoryview(buffer("a"*100, 2))
        assert v.shape == (98,)
        assert v.suboffsets == None

    def test_compare(self):
        assert memoryview(b"abc") == b"abc"
        assert memoryview(b"abc") == bytearray(b"abc")
        assert memoryview(b"abc") != 3
        assert not memoryview("abc") == u"abc"
        assert memoryview("abc") != u"abc"
        assert not u"abc" == memoryview("abc")
        assert u"abc" != memoryview("abc")

    def test_pypy_raw_address_base(self):
        import sys
        if '__pypy__' not in sys.modules:
            skip('PyPy-only test')
        a = memoryview(b"foobar")._pypy_raw_address()
        assert a != 0
        b = memoryview(bytearray(b"foobar"))._pypy_raw_address()
        assert b != 0
