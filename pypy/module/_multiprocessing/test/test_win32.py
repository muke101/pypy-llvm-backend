import py
import sys

@py.test.mark.skipif('sys.platform != "win32"')
class AppTestWin32:
    spaceconfig = dict(usemodules=('_multiprocessing', '_cffi_backend',
                                   'signal', '_rawffi', 'binascii'))

    def setup_class(cls):
        # import here since importing _multiprocessing imports multiprocessing
        # (in interp_connection) to get the BufferTooShort exception, which on
        # win32 imports msvcrt which imports via cffi which allocates ccharp
        # that are never released. This trips up the LeakChecker if done in a
        # test function
        cls.w_multiprocessing = cls.space.appexec([],
                                  '(): import multiprocessing as m; return m')

    def test_CreateFile(self):
        from _multiprocessing import win32
        err = raises(WindowsError, win32.CreateFile,
                     "in/valid", 0, 0, 0, 0, 0, 0)
        assert err.value.winerror == 87 # ERROR_INVALID_PARAMETER

    def test_pipe(self):
        from _multiprocessing import win32
        import os
        address = r'\\.\pipe\pypy-test-%s' % (os.getpid())
        openmode = win32.PIPE_ACCESS_INBOUND
        access = win32.GENERIC_WRITE
        obsize, ibsize = 0, 8192
        readhandle = win32.CreateNamedPipe(
            address, openmode,
            win32.PIPE_TYPE_MESSAGE | win32.PIPE_READMODE_MESSAGE |
            win32.PIPE_WAIT,
            1, obsize, ibsize, win32.NMPWAIT_WAIT_FOREVER, win32.NULL
            )
        writehandle = win32.CreateFile(
            address, access, 0, win32.NULL, win32.OPEN_EXISTING, 0, win32.NULL
            )
        win32.SetNamedPipeHandleState(
            writehandle, win32.PIPE_READMODE_MESSAGE, None, None)

        try:
            win32.ConnectNamedPipe(readhandle, win32.NULL)
        except WindowsError as e:
            if e.args[0] != win32.ERROR_PIPE_CONNECTED:
                raise

        timeout = 100
        exc = raises(WindowsError, win32.WaitNamedPipe, address, timeout)
        assert exc.value.winerror == 121 # ERROR_SEM_TIMEOUT

        win32.CloseHandle(readhandle)
        win32.CloseHandle(writehandle)
