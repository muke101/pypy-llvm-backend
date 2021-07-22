import _io

def test_init():
    raises(TypeError, _io.BytesIO, u"12345")
    buf = "1234567890"
    b = _io.BytesIO(buf)
    assert b.getvalue() == buf
    b = _io.BytesIO(None)
    assert b.getvalue() == ""
    b.__init__(buf * 2)
    assert b.getvalue() == buf * 2
    b.__init__(buf)
    assert b.getvalue() == buf

def test_init_kwargs():

    buf = "1234567890"
    b = _io.BytesIO(initial_bytes=buf)
    assert b.read() == buf
    raises(TypeError, _io.BytesIO, buf, foo=None)

def test_capabilities():
    f = _io.BytesIO()
    assert f.readable()
    assert f.writable()
    assert f.seekable()
    f.close()
    raises(ValueError, f.readable)
    raises(ValueError, f.writable)
    raises(ValueError, f.seekable)

def test_write():
    f = _io.BytesIO()
    assert f.write("") == 0
    assert f.write("hello") == 5
    exc = raises(TypeError, f.write, u"lo")
    assert str(exc.value) == "'unicode' does not have the buffer interface"
    import gc; gc.collect()
    assert f.getvalue() == "hello"
    f.close()

def test_read():
    f = _io.BytesIO("hello")
    assert f.read() == "hello"
    import gc; gc.collect()
    assert f.read(8192) == ""
    f.close()

def test_seek():
    f = _io.BytesIO("hello")
    assert f.tell() == 0
    assert f.seek(-1, 2) == 4
    assert f.tell() == 4
    assert f.seek(0) == 0

def test_truncate():
    f = _io.BytesIO()
    f.write("hello")
    assert f.truncate(0) == 0
    assert f.tell() == 5
    f.seek(0)
    f.write("hello")
    f.seek(3)
    assert f.truncate() == 3
    assert f.getvalue() == "hel"
    assert f.truncate(2) == 2
    assert f.tell() == 3

def test_setstate():
    # state is (content, position, __dict__)
    f = _io.BytesIO("hello")
    content, pos, __dict__ = f.__getstate__()
    assert (content, pos) == ("hello", 0)
    assert __dict__ is None or __dict__ == {}
    f.__setstate__(("world", 3, {"a": 1}))
    assert f.getvalue() == "world"
    assert f.read() == "ld"
    assert f.a == 1
    assert f.__getstate__() == ("world", 5, {"a": 1})
    raises(TypeError, f.__setstate__, ("", 0))
    f.close()
    raises(ValueError, f.__getstate__)
    raises(ValueError, f.__setstate__, ("world", 3, {"a": 1}))

def test_readinto():

    b = _io.BytesIO("hello")
    a1 = bytearray('t')
    a2 = bytearray('testing')
    assert b.readinto(a1) == 1
    assert b.readinto(a2) == 4
    exc = raises(TypeError, b.readinto, u"hello")
    assert str(exc.value) == "cannot use unicode as modifiable buffer"
    exc = raises(TypeError, b.readinto, buffer(b"hello"))
    assert str(exc.value) == "must be read-write buffer, not buffer"
    exc = raises(TypeError, b.readinto, buffer(bytearray("hello")))
    assert str(exc.value) == "must be read-write buffer, not buffer"
    exc = raises(TypeError, b.readinto, memoryview(b"hello"))
    assert str(exc.value) == "must be read-write buffer, not memoryview"
    b.close()
    assert a1 == "h"
    assert a2 == "elloing"
    raises(ValueError, b.readinto, bytearray("hello"))

def test_readline():
    f = _io.BytesIO(b'abc\ndef\nxyzzy\nfoo\x00bar\nanother line')
    assert f.readline() == b'abc\n'
    assert f.readline(10) == b'def\n'
    assert f.readline(2) == b'xy'
    assert f.readline(4) == b'zzy\n'
    assert f.readline() == b'foo\x00bar\n'
    assert f.readline(None) == b'another line'
    raises(TypeError, f.readline, 5.3)

def test_overread():
    f = _io.BytesIO(b'abc')
    assert f.readline(10) == b'abc'
