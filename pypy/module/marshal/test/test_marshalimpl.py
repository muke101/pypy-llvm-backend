from pypy.module.marshal import interp_marshal
from pypy.interpreter.error import OperationError
import sys


class AppTestMarshalMore:
    spaceconfig = dict(usemodules=('array',))

    def test_long_0(self):
        import marshal
        z = 0L
        z1 = marshal.loads(marshal.dumps(z))
        assert z == z1
        assert type(z1) is long

    def test_unmarshal_int64(self):
        # test that we can unmarshal 64-bit ints on 32-bit platforms
        # (of course we only test that if we're running on such a
        # platform :-)
        import marshal
        z = marshal.loads('I\x00\xe4\x0bT\x02\x00\x00\x00')
        assert z == 10000000000
        z = marshal.loads('I\x00\x1c\xf4\xab\xfd\xff\xff\xff')
        assert z == -10000000000
        z = marshal.loads('I\x88\x87\x86\x85\x84\x83\x82\x01')
        assert z == 108793946209421192
        z = marshal.loads('I\xd8\xd8\xd9\xda\xdb\xdc\xcd\xfe')
        assert z == -0x0132232425262728

    def test_buffer(self):
        import marshal
        z = marshal.loads(buffer('i\x02\x00\x00\x00???'))
        assert z == 2

    def test_marshal_buffer_object(self):
        import marshal
        s = marshal.dumps(buffer('foobar'))
        t = marshal.loads(s)
        assert type(t) is str and t == 'foobar'

    def test_marshal_bufferlike_object(self):
        import marshal, array
        s = marshal.dumps(array.array('c', 'asd'))
        t = marshal.loads(s)
        assert type(t) is str and t == 'asd'
        exc = raises(ValueError, marshal.dumps, memoryview('asd'))
        assert str(exc.value) == "unmarshallable object"

    def test_unmarshal_evil_long(self):
        import marshal
        raises(ValueError, marshal.loads, 'l\x02\x00\x00\x00\x00\x00\x00\x00')
        z = marshal.loads('I\x00\xe4\x0bT\x02\x00\x00\x00')
        assert z == 10000000000
        z = marshal.loads('I\x00\x1c\xf4\xab\xfd\xff\xff\xff')
        assert z == -10000000000


class AppTestMarshalSmallLong(AppTestMarshalMore):
    spaceconfig = dict(usemodules=('array',),
                       **{"objspace.std.withsmalllong": True})


def test_long_more(space):
    import marshal, struct

    class FakeM:
        # NOTE: marshal is platform independent, running this test must assume
        # that self.seen gets values from the endianess of the marshal module.
        # (which is little endian!)
        def __init__(self):
            self.seen = []
        def start(self, code):
            self.seen.append(code)
        def put_int(self, value):
            self.seen.append(struct.pack("<i", value))
        def put_short(self, value):
            self.seen.append(struct.pack("<h", value))

    def _marshal_check(x):
        expected = marshal.dumps(long(x))
        w_obj = space.wraplong(x)
        m = FakeM()
        interp_marshal.marshal(space, w_obj, m)
        assert ''.join(m.seen) == expected
        #
        u = interp_marshal.StringUnmarshaller(space, space.wrap(expected))
        w_long = u.load_w_obj()
        assert space.eq_w(w_long, w_obj)

    for sign in [1L, -1L]:
        for i in range(100):
            _marshal_check(sign * ((1L << i) - 1L))
            _marshal_check(sign * (1L << i))
