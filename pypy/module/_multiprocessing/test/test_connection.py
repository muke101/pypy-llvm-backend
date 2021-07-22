import py
import sys
from pypy.interpreter.gateway import interp2app, W_Root

class TestImport:
    def test_simple(self):
        from pypy.module._multiprocessing import interp_connection
        from pypy.module._multiprocessing import interp_semaphore

class AppTestBufferTooShort:
    spaceconfig = {'usemodules': ['_multiprocessing', 'thread', 'signal',
                                  'itertools', 'select', 'struct', 'binascii']}
    if sys.platform == 'win32':
        spaceconfig['usemodules'].append('_rawffi')
        spaceconfig['usemodules'].append('_cffi_backend')
    else:
        spaceconfig['usemodules'].append('fcntl')


    def setup_class(cls):
        if cls.runappdirect:
            def raiseBufferTooShort(self, data):
                import multiprocessing
                raise multiprocessing.BufferTooShort(data)
            cls.w_raiseBufferTooShort = raiseBufferTooShort
        else:
            from pypy.module._multiprocessing import interp_connection
            def raiseBufferTooShort(space, w_data):
                raise interp_connection.BufferTooShort(space, w_data)
            cls.w_raiseBufferTooShort = cls.space.wrap(
                interp2app(raiseBufferTooShort))

    def test_exception(self):
        import multiprocessing
        try:
            self.raiseBufferTooShort("data")
        except multiprocessing.BufferTooShort as e:
            assert isinstance(e, multiprocessing.ProcessError)
            assert e.args == ("data",)

    if sys.platform == "win32":
        test_exception.dont_track_allocations = True

class BaseConnectionTest(object):
    def test_connection(self):
        import sys
        # if not translated, for win32
        if not hasattr(sys, 'executable'):
            sys.executable = 'from test_connection.py'
        rhandle, whandle = self.make_pair()

        whandle.send_bytes("abc")
        assert rhandle.recv_bytes(100) == "abc"

        obj = [1, 2.0, "hello"]
        whandle.send(obj)
        obj2 = rhandle.recv()
        assert obj == obj2

    if sys.platform == "win32":
        test_connection.dont_track_allocations = True

    def test_poll(self):
        import sys
        # if not translated, for win32
        if not hasattr(sys, 'executable'):
            sys.executable = 'from test_connection.py'
        rhandle, whandle = self.make_pair()

        assert rhandle.poll() == False
        assert rhandle.poll(1) == False
        whandle.send(1)
        import time; time.sleep(0.1)  # give it time to arrive :-)
        assert rhandle.poll() == True
        assert rhandle.poll(None) == True
        assert rhandle.recv() == 1
        assert rhandle.poll() == False
        raises(IOError, whandle.poll)

    def test_read_into(self):
        import array, multiprocessing
        import sys
        # if not translated, for win32
        if not hasattr(sys, 'executable'):
            sys.executable = 'from test_connection.py'
        rhandle, whandle = self.make_pair()

        obj = [1, 2.0, "hello"]
        whandle.send(obj)
        buffer = array.array('b', [0]*10)
        raises(multiprocessing.BufferTooShort, rhandle.recv_bytes_into, buffer)
        assert rhandle.readable

class AppTestWinpipeConnection(BaseConnectionTest):
    spaceconfig = {
        "usemodules": [
            '_multiprocessing', 'thread', 'signal', 'struct', 'array',
            'itertools', '_socket', 'binascii',
        ]
    }
    if sys.platform == 'win32':
        spaceconfig['usemodules'].append('_rawffi')
        spaceconfig['usemodules'].append('_cffi_backend')

    def setup_class(cls):
        if sys.platform != "win32":
            py.test.skip("win32 only")

        if not cls.runappdirect:
            space = cls.space
            # stubs for some modules,
            # just for multiprocessing to import correctly on Windows
            w_modules = space.sys.get('modules')
            space.setitem(w_modules, space.wrap('msvcrt'), space.sys)
        else:
            import _multiprocessing

    def w_make_pair(self):
        import multiprocessing

        return multiprocessing.Pipe(duplex=False)


class AppTestSocketConnection(BaseConnectionTest):
    spaceconfig = {
        "usemodules": [
            '_multiprocessing', 'thread', 'signal', 'struct', 'array',
            'itertools', '_socket', 'binascii', 'select' ]
    }
    if sys.platform == 'win32':
        spaceconfig['usemodules'].append('_rawffi')
        spaceconfig['usemodules'].append('_cffi_backend')
    else:
        spaceconfig['usemodules'].append('fcntl')

    def setup_class(cls):
        cls.w_connections = cls.space.newlist([])

    def w_socketpair(self):
        "A socket.socketpair() that works on Windows"
        import errno
        import socket

        serverSocket = socket.socket()
        serverSocket.bind(('127.0.0.1', 0))
        serverSocket.listen(1)

        client = socket.socket()
        client.setblocking(False)
        try:
            client.connect(('127.0.0.1', serverSocket.getsockname()[1]))
        except socket.error as e:
            assert e.args[0] in (errno.EINPROGRESS, errno.EWOULDBLOCK)
        server, addr = serverSocket.accept()

        # keep sockets alive during the test
        self.connections.append(server)
        self.connections.append(client)

        return server.fileno(), client.fileno()

    def w_make_pair(self):
        import _multiprocessing

        fd1, fd2 = self.socketpair()
        rhandle = _multiprocessing.Connection(fd1, writable=False)
        whandle = _multiprocessing.Connection(fd2, readable=False)
        self.connections.append(rhandle)
        self.connections.append(whandle)
        return rhandle, whandle

    def teardown_method(self, func):
        # Work hard to close all sockets and connections now!
        # since the fd is probably already closed, another unrelated
        # part of the program will probably reuse it;
        # And any object forgotten here will close it on destruction...
        try:
            w_connections = self.w_connections
        except AttributeError:
            return
        space = self.space
        for c in space.unpackiterable(w_connections):
            if isinstance(c, W_Root):
                space.call_method(c, "close")
            else:
                c.close()
        space.delslice(w_connections, space.wrap(0), space.wrap(100))

    def test_bad_fd(self):
        import _multiprocessing

        raises(IOError, _multiprocessing.Connection, -1)
        raises(IOError, _multiprocessing.Connection, -15)

    def test_byte_order(self):
        import socket
        if not 'fromfd' in dir(socket):
            skip('No fromfd in socket')
        # The exact format of net strings (length in network byte
        # order) is important for interoperation with others
        # implementations.
        rhandle, whandle = self.make_pair()
        whandle.send_bytes("abc")
        whandle.send_bytes("defg")
        sock = socket.fromfd(rhandle.fileno(),
                             socket.AF_INET, socket.SOCK_STREAM)
        data1 = sock.recv(7)
        assert data1 == '\x00\x00\x00\x03abc'
        data2 = sock.recv(8)
        assert data2 == '\x00\x00\x00\x04defg'

    def test_repr(self):
        import _multiprocessing, os
        fd = os.dup(1)     # closed by Connection.__del__
        c = _multiprocessing.Connection(fd)
        assert repr(c) == '<read-write Connection, handle %d>' % fd
        if hasattr(_multiprocessing, 'PipeConnection'):
            fd = os.dup(1)     # closed by PipeConnection.__del__
            c = _multiprocessing.PipeConnection(fd)
            assert repr(c) == '<read-write PipeConnection, handle %d>' % fd
