# -*- coding: utf-8 -*-

import os
import py
import pytest
import sys
import signal

from rpython.tool.udir import udir
from pypy.tool.pytest.objspace import gettestobjspace
from rpython.translator.c.test.test_extfunc import need_sparse_files
from rpython.rlib import rposix

USEMODULES = ['binascii', 'posix', 'signal', 'struct', 'time']
if os.name != 'nt':
    USEMODULES += ['fcntl']
else:
    # On windows, os.popen uses the subprocess module
    USEMODULES += ['_rawffi', 'thread', 'signal', '_cffi_backend']

def setup_module(mod):
    mod.space = gettestobjspace(usemodules=USEMODULES)
    mod.path = udir.join('posixtestfile.txt')
    mod.path.write("this is a test")
    mod.path2 = udir.join('test_posix2-')
    mod.path3 = udir.join('unlinktestfile.txt')
    mod.path3.write("delete me!")
    pdir = udir.ensure('posixtestdir', dir=True)
    pdir = udir.ensure('posixtestdir', dir=True)
    pdir.join('file1').write("test1")
    os.chmod(str(pdir.join('file1')), 0o600)
    pdir.join('file2').write("test2")
    pdir.join('another_longer_file_name').write("test3")
    mod.pdir = pdir
    if sys.platform == 'darwin':
        # see issue https://bugs.python.org/issue31380
        unicode_dir = udir.ensure('fixc5x9fier.txt', dir=True)
        file_name = 'cafxe9'
    else:
        unicode_dir = udir.ensure('fi\xc5\x9fier.txt', dir=True)
        file_name = 'caf\xe9'
    unicode_dir.join('somefile').write('who cares?')
    unicode_dir.join(file_name).write('who knows?')
    mod.unicode_dir = unicode_dir

    # Initialize sys.filesystemencoding
    # space.call_method(space.getbuiltinmodule('sys'), 'getfilesystemencoding')


GET_POSIX = "(): import %s as m ; return m" % os.name


class AppTestPosix:
    spaceconfig = {'usemodules': USEMODULES}

    def setup_class(cls):
        space = cls.space
        cls.w_runappdirect = space.wrap(cls.runappdirect)
        cls.w_posix = space.appexec([], GET_POSIX)
        cls.w_path = space.wrap(str(path))
        cls.w_path2 = space.wrap(str(path2))
        cls.w_path3 = space.wrap(str(path3))
        cls.w_pdir = space.wrap(str(pdir))
        cls.w_plat = space.wrap(sys.platform)
        try:
            cls.w_unicode_dir = space.wrap(
                str(unicode_dir).decode(sys.getfilesystemencoding()))
        except UnicodeDecodeError:
            # filesystem encoding is not good enough
            cls.w_unicode_dir = space.w_None
        if hasattr(os, 'getuid'):
            cls.w_getuid = space.wrap(os.getuid())
            cls.w_geteuid = space.wrap(os.geteuid())
        if hasattr(os, 'getgid'):
            cls.w_getgid = space.wrap(os.getgid())
        if hasattr(os, 'getgroups'):
            cls.w_getgroups = space.newlist([space.wrap(e) for e in os.getgroups()])
        if hasattr(os, 'getpgid'):
            cls.w_getpgid = space.wrap(os.getpgid(os.getpid()))
        if hasattr(os, 'getsid'):
            cls.w_getsid0 = space.wrap(os.getsid(0))
        if hasattr(os, 'sysconf'):
            sysconf_name = os.sysconf_names.keys()[0]
            cls.w_sysconf_name = space.wrap(sysconf_name)
            cls.w_sysconf_value = space.wrap(os.sysconf_names[sysconf_name])
            cls.w_sysconf_result = space.wrap(os.sysconf(sysconf_name))
        if hasattr(os, 'confstr'):
            confstr_name = os.confstr_names.keys()[0]
            cls.w_confstr_name = space.wrap(confstr_name)
            cls.w_confstr_value = space.wrap(os.confstr_names[confstr_name])
            cls.w_confstr_result = space.wrap(os.confstr(confstr_name))
        cls.w_SIGABRT = space.wrap(signal.SIGABRT)
        cls.w_python = space.wrap(sys.executable)
        cls.w_platform = space.wrap(sys.platform)
        if hasattr(os, 'major'):
            cls.w_expected_major_12345 = space.wrap(os.major(12345))
            cls.w_expected_minor_12345 = space.wrap(os.minor(12345))
        cls.w_udir = space.wrap(str(udir))

    def setup_method(self, meth):
        if getattr(meth, 'need_sparse_files', False):
            if sys.maxsize < 2**32 and not self.runappdirect:
                # this fails because it uses ll2ctypes to call the posix
                # functions like 'open' and 'lseek', whereas a real compiled
                # C program would macro-define them to their longlong versions
                pytest.skip("emulation of files can't use "
                             "larger-than-long offsets")
            need_sparse_files()

    def test_posix_is_pypy_s(self):
        assert hasattr(self.posix, '_statfields')

    def test_some_posix_basic_operation(self):
        path = self.path
        posix = self.posix
        fd = posix.open(path, posix.O_RDONLY, 0o777)
        fd2 = posix.dup(fd)
        assert not posix.isatty(fd2)
        s = posix.read(fd, 1)
        assert s == b't'
        posix.lseek(fd, 5, 0)
        s = posix.read(fd, 1)
        assert s == b'i'
        st = posix.fstat(fd)
        posix.close(fd2)
        posix.close(fd)

        import sys, stat
        assert st[0] == st.st_mode
        assert st[1] == st.st_ino
        assert st[2] == st.st_dev
        assert st[3] == st.st_nlink
        assert st[4] == st.st_uid
        assert st[5] == st.st_gid
        assert st[6] == st.st_size
        assert st[7] == int(st.st_atime)   # in complete corner cases, rounding
        assert st[8] == int(st.st_mtime)   # here could maybe get the wrong
        assert st[9] == int(st.st_ctime)   # integer...

        assert stat.S_IMODE(st.st_mode) & stat.S_IRUSR
        assert stat.S_IMODE(st.st_mode) & stat.S_IWUSR
        if not sys.platform.startswith('win'):
            assert not (stat.S_IMODE(st.st_mode) & stat.S_IXUSR)

        assert st.st_size == 14
        assert st.st_nlink == 1

        assert not hasattr(st, 'nsec_atime')

        if sys.platform.startswith('linux'):
            assert isinstance(st.st_atime, float)
            assert isinstance(st.st_mtime, float)
            assert isinstance(st.st_ctime, float)
            assert hasattr(st, 'st_rdev')

    def test_stat_float_times(self):
        path = self.path
        posix = self.posix
        current = posix.stat_float_times()
        assert current is True
        try:
            posix.stat_float_times(True)
            st = posix.stat(path)
            assert isinstance(st.st_mtime, float)
            assert st[7] == int(st.st_atime)
            assert posix.stat_float_times(-1) is True

            posix.stat_float_times(False)
            st = posix.stat(path)
            assert isinstance(st.st_mtime, (int, long))
            assert st[7] == st.st_atime
            assert posix.stat_float_times(-1) is False

        finally:
            posix.stat_float_times(current)


    def test_stat_result(self):
        st = self.posix.stat_result((0, 0, 0, 0, 0, 0, 0, 41, 42.1, 43))
        assert st.st_atime == 41
        assert st.st_mtime == 42.1
        assert st.st_ctime == 43
        assert repr(st).startswith(self.posix.__name__ + '.stat_result')

    def test_stat_lstat(self):
        import stat
        st = self.posix.stat(".")
        assert stat.S_ISDIR(st.st_mode)
        st = self.posix.stat(b".")
        assert stat.S_ISDIR(st.st_mode)
        st = self.posix.lstat(".")
        assert stat.S_ISDIR(st.st_mode)

    def test_stat_exception(self):
        import sys
        import errno
        for fn in [self.posix.stat, self.posix.lstat]:
            with raises(OSError) as exc:
                fn("nonexistentdir/nonexistentfile")
            assert exc.value.errno == errno.ENOENT
            assert exc.value.filename == "nonexistentdir/nonexistentfile"

    if hasattr(__import__(os.name), "statvfs"):
        def test_statvfs(self):
            st = self.posix.statvfs(".")
            assert isinstance(st, self.posix.statvfs_result)
            for field in [
                'f_bsize', 'f_frsize', 'f_blocks', 'f_bfree', 'f_bavail',
                'f_files', 'f_ffree', 'f_favail', 'f_flag', 'f_namemax',
            ]:
                assert hasattr(st, field)

    def test_pickle(self):
        import pickle, os
        st = self.posix.stat(os.curdir)
        # print type(st).__module__
        s = pickle.dumps(st)
        # print repr(s)
        new = pickle.loads(s)
        assert new == st
        assert type(new) is type(st)

    def test_open_exception(self):
        posix = self.posix
        try:
            posix.open('qowieuqwoeiu', 0, 0)
        except OSError as e:
            assert e.filename == 'qowieuqwoeiu'
        else:
            assert 0

    def test_filename_exception(self):
        for fname in ['unlink', 'remove',
                      'chdir', 'mkdir', 'rmdir',
                      'listdir', 'readlink',
                      'chroot']:
            if hasattr(self.posix, fname):
                func = getattr(self.posix, fname)
                try:
                    func('qowieuqw/oeiu')
                except OSError as e:
                    assert e.filename == 'qowieuqw/oeiu'
                else:
                    assert 0

    def test_chmod_exception(self):
        try:
            self.posix.chmod('qowieuqw/oeiu', 0)
        except OSError as e:
            assert e.filename == 'qowieuqw/oeiu'
        else:
            assert 0

    def test_chown_exception(self):
        if hasattr(self.posix, 'chown'):
            try:
                self.posix.chown('qowieuqw/oeiu', 0, 0)
            except OSError as e:
                assert e.filename == 'qowieuqw/oeiu'
            else:
                assert 0

    def test_utime_exception(self):
        for arg in [None, (0, 0)]:
            try:
                self.posix.utime('qowieuqw/oeiu', arg)
            except OSError as e:
                assert e.filename == 'qowieuqw/oeiu'
            else:
                assert 0

    def test_functions_raise_error(self):
        import sys
        def ex(func, *args):
            try:
                func(*args)
            except OSError:
                pass
            else:
                raise AssertionError("%s(%s) did not raise" %(
                                     func.__name__,
                                     ", ".join([str(x) for x in args])))
        UNUSEDFD = 123123
        ex(self.posix.open, "qweqwe", 0, 0)
        ex(self.posix.lseek, UNUSEDFD, 123, 0)
        #apparently not posix-required: ex(self.posix.isatty, UNUSEDFD)
        ex(self.posix.read, UNUSEDFD, 123)
        ex(self.posix.write, UNUSEDFD, b"x")
        ex(self.posix.close, UNUSEDFD)
        #UMPF cpython raises IOError ex(self.posix.ftruncate, UNUSEDFD, 123)
        if sys.platform == 'win32' and self.runappdirect:
            # XXX kills the host interpreter untranslated
            ex(self.posix.fstat, UNUSEDFD)
            ex(self.posix.stat, "qweqwehello")
            # how can getcwd() raise?
            ex(self.posix.dup, UNUSEDFD)

    def test_fdopen(self):
        import errno
        path = self.path
        posix = self.posix
        fd = posix.open(path, posix.O_RDONLY, 0777)
        f = posix.fdopen(fd, "r")
        f.close()

        # There used to be code here to ensure that fcntl is not faked
        # but we can't do that cleanly any more
        try:
            fid = posix.fdopen(fd)
            fid.read(10)
        except (IOError, OSError) as e:
            assert e.errno == errno.EBADF
        else:
            assert False, "using result of fdopen(fd) on closed file must raise"

    def test_fdopen_hackedbuiltins(self):
        "Same test, with __builtins__.file removed"
        _file = __builtins__.file
        __builtins__.file = None
        try:
            path = self.path
            posix = self.posix
            fd = posix.open(path, posix.O_RDONLY, 0777)
            f = posix.fdopen(fd, "r")
            f.close()
        finally:
            __builtins__.file = _file

    def test_fdopen_directory(self):
        import errno
        os = self.posix
        try:
            fd = os.open('.', os.O_RDONLY)
        except OSError as e:
            assert e.errno == errno.EACCES
            skip("system cannot open directories")
        with raises(IOError) as exc:
            os.fdopen(fd, 'r')
        assert exc.value.errno == errno.EISDIR

    def test_fdopen_keeps_fd_open_on_errors(self):
        path = self.path
        posix = self.posix
        fd = posix.open(path, posix.O_RDONLY)
        # compatability issue - using Visual Studio 10 and above no
        # longer raises on fid creation, only when _using_ fid
        # win32 python2 raises IOError on flush(), win32 python3 raises OSError
        try:
            fid = posix.fdopen(fd, 'w')
            fid.write('abc')
            fid.flush()
        except  (OSError, IOError) as e:
            assert e.errno in (9, 22)
        else:
            assert False, "expected OSError"
        posix.close(fd)  # fd should not be closed

    def test_getcwd(self):
        assert isinstance(self.posix.getcwd(), str)
        assert isinstance(self.posix.getcwdu(), unicode)
        assert self.posix.getcwd() == self.posix.getcwdu()

    def test_listdir(self):
        pdir = self.pdir
        posix = self.posix
        result = posix.listdir(pdir)
        result.sort()
        assert result == ['another_longer_file_name',
                          'file1',
                          'file2']

    def test_listdir_unicode(self):
        import sys
        unicode_dir = self.unicode_dir
        if unicode_dir is None:
            skip("encoding not good enough")
        posix = self.posix
        result = posix.listdir(unicode_dir)
        typed_result = [(type(x), x) for x in result]
        assert (unicode, u'somefile') in typed_result
        file_system_encoding = sys.getfilesystemencoding()
        try:
            u = "caf\xe9".decode(file_system_encoding)
        except UnicodeDecodeError:
            # Could not decode, listdir returned the byte string
            if sys.platform != 'darwin':
                assert (str, "caf\xe9") in typed_result
            else:
                # if the test is being run in an utf-8 encoded macOS
                # the posix.listdir function is returning the name of
                # the file properly.
                # This test should be run in multiple macOS platforms to
                # be sure that is working as expected.
                if file_system_encoding.lower() == 'utf-8':
                    assert (unicode, 'cafxe9') in typed_result
                else:
                    # darwin 'normalized' it
                    assert (unicode, 'caf%E9') in typed_result
        else:
            assert (unicode, u) in typed_result
        assert posix.access(b'caf\xe9', posix.R_OK) is False
        assert posix.access('caf\udcc0', posix.R_OK) is False
        assert posix.access(b'caf\xc3', posix.R_OK) is False

    def test_access(self):
        pdir = self.pdir + '/file1'
        posix = self.posix

        assert posix.access(pdir, posix.R_OK) is True
        assert posix.access(pdir, posix.W_OK) is True
        import sys
        if sys.platform != "win32":
            assert posix.access(pdir, posix.X_OK) is False

    def test_unlink(self):
        os = self.posix
        path = self.path3
        with open(path, 'wb'):
            pass
        os.unlink(path)

    def test_times(self):
        """
        posix.times() should return a five-tuple giving float-representations
        (seconds, effectively) of the four fields from the underlying struct
        tms and the return value.
        """
        result = self.posix.times()
        assert isinstance(result, tuple)
        assert len(result) == 5
        for value in result:
            assert isinstance(value, float)

    def test_strerror(self):
        assert isinstance(self.posix.strerror(0), str)
        assert isinstance(self.posix.strerror(1), str)

    if hasattr(__import__(os.name), "fork"):
        def test_fork(self):
            os = self.posix
            pid = os.fork()
            if pid == 0:   # child
                os._exit(4)
            pid1, status1 = os.waitpid(pid, 0)
            assert pid1 == pid
            assert os.WIFEXITED(status1)
            assert os.WEXITSTATUS(status1) == 4
        pass # <- please, inspect.getsource(), don't crash


    if hasattr(__import__(os.name), "openpty"):
        def test_openpty(self):
            os = self.posix
            master_fd, slave_fd = os.openpty()
            assert isinstance(master_fd, int)
            assert isinstance(slave_fd, int)
            os.write(slave_fd, b'x\n')
            data = os.read(master_fd, 100)
            assert data.startswith(b'x')
            os.close(master_fd)
            os.close(slave_fd)

    if hasattr(__import__(os.name), "forkpty"):
        def test_forkpty(self):
            import sys
            if 'freebsd' in sys.platform:
                skip("hangs indifinitly on FreeBSD (also on CPython).")
            os = self.posix
            childpid, master_fd = os.forkpty()
            assert isinstance(childpid, int)
            assert isinstance(master_fd, int)
            if childpid == 0:
                data = os.read(0, 100)
                if data.startswith(b'abc'):
                    os._exit(42)
                else:
                    os._exit(43)
            os.write(master_fd, b'abc\n')
            _, status = os.waitpid(childpid, 0)
            assert status >> 8 == 42

    def test_popen(self):
        os = self.posix
        for i in range(5):
            stream = os.popen('echo 1')
            res = stream.read()
            assert res == '1\n'
            assert stream.close() is None

    def test_popen_with(self):
        os = self.posix
        stream = os.popen('echo 1')
        with stream as fp:
            res = fp.read()
            assert res == '1\n'

    def test_popen_child_fds(self):
        os = self.posix
        with open('/'.join([self.pdir, 'file1']), 'r') as fd:
            with self.posix.popen('%s -c "import os; print os.read(%d, 10)" 2>&1' % (self.python, fd.fileno())) as stream:
                res = stream.read()
                if self.plat == 'win32':
                    assert '\nOSError: [Errno 9]' in res
                else:
                    assert res == 'test1\n'
    if sys.platform == "win32":
        # using startfile in app_startfile creates global state
        test_popen.dont_track_allocations = True
        test_popen_with.dont_track_allocations = True
        test_popen_child_fds.dont_track_allocations = True


    if hasattr(__import__(os.name), '_getfullpathname'):
        def test__getfullpathname(self):
            # nt specific
            posix = self.posix
            sysdrv = posix.environ.get("SystemDrive", "C:")
            # just see if it does anything
            path = sysdrv + 'hubber'
            assert '\\' in posix._getfullpathname(path)

    def test_utime(self):
        os = self.posix
        from os.path import join
        # XXX utimes & float support
        path = join(self.pdir, "test_utime.txt")
        fh = open(path, "w")
        fh.write(b"x")
        fh.close()
        from time import time, sleep
        t0 = time()
        sleep(1.1)
        os.utime(path, None)
        assert os.stat(path).st_atime > t0
        os.utime(path, (int(t0), int(t0)))
        assert int(os.stat(path).st_atime) == int(t0)

    def test_utime_raises(self):
        os = self.posix
        import errno
        with raises(TypeError):
            os.utime('xxx', 3)
        with raises(OSError) as exc:
            os.utime('somefilewhichihopewouldneverappearhere', None)
        assert exc.value.errno == errno.ENOENT

    for name in rposix.WAIT_MACROS:
        if hasattr(os, name):
            values = [0, 1, 127, 128, 255]
            code = py.code.Source("""
            def test_wstar(self):
                os = self.posix
                %s
            """ % "\n    ".join(["assert os.%s(%d) == %d" % (name, value,
                             getattr(os, name)(value)) for value in values]))
            d = {}
            exec code.compile() in d
            locals()['test_' + name] = d['test_wstar']

    if hasattr(os, 'WIFSIGNALED'):
        def test_wifsignaled(self):
            os = self.posix
            assert os.WIFSIGNALED(0) == False
            assert os.WIFSIGNALED(1) == True

    if hasattr(os, 'uname'):
        def test_os_uname(self):
            os = self.posix
            res = os.uname()
            assert len(res) == 5
            for i in res:
                assert isinstance(i, str)
            assert isinstance(res, tuple)

    if hasattr(os, 'getuid'):
        def test_os_getuid(self):
            os = self.posix
            assert os.getuid() == self.getuid
            assert os.geteuid() == self.geteuid

    if hasattr(os, 'setuid'):
        @py.test.mark.skipif("sys.version_info < (2, 7, 4)")
        def test_os_setuid_error(self):
            os = self.posix
            with raises(OverflowError):
                os.setuid(-2)
            with raises(OverflowError):
                os.setuid(2**32)
            with raises(OSError):
                os.setuid(-1)

    if hasattr(os, 'getgid'):
        def test_os_getgid(self):
            os = self.posix
            assert os.getgid() == self.getgid

    if hasattr(os, 'getgroups'):
        def test_os_getgroups(self):
            os = self.posix
            assert os.getgroups() == self.getgroups

    if hasattr(os, 'setgroups'):
        def test_os_setgroups(self):
            os = self.posix
            with raises(TypeError):
                os.setgroups([2, 5, "hello"])
            try:
                os.setgroups(os.getgroups())
            except OSError:
                pass

    if hasattr(os, 'initgroups'):
        def test_os_initgroups(self):
            os = self.posix
            with raises(OSError):
                os.initgroups("crW2hTQC", 100)

    if hasattr(os, 'tcgetpgrp'):
        def test_os_tcgetpgrp(self):
            os = self.posix
            with raises(OSError):
                os.tcgetpgrp(9999)

    if hasattr(os, 'tcsetpgrp'):
        def test_os_tcsetpgrp(self):
            os = self.posix
            with raises(OSError):
                os.tcsetpgrp(9999, 1)

    if hasattr(os, 'getpgid'):
        def test_os_getpgid(self):
            os = self.posix
            assert os.getpgid(os.getpid()) == self.getpgid
            with raises(OSError):
                os.getpgid(1234567)

    if hasattr(os, 'setgid'):
        @pytest.mark.skipif("sys.version_info < (2, 7, 4)")
        def test_os_setgid_error(self):
            os = self.posix
            with raises(OverflowError):
                os.setgid(-2)
            with raises(OverflowError):
                os.setgid(2**32)
            with raises(OSError):
                os.setgid(-1)
            with raises(OSError):
                os.setgid(-1L)
            with raises(OSError):
                os.setgid(2**32-1)

    if hasattr(os, 'getsid'):
        def test_os_getsid(self):
            os = self.posix
            assert os.getsid(0) == self.getsid0
            with raises(OSError):
                os.getsid(-100000)

    if hasattr(os, 'getresuid'):
        def test_os_getresuid(self):
            os = self.posix
            res = os.getresuid()
            assert len(res) == 3

    if hasattr(os, 'getresgid'):
        def test_os_getresgid(self):
            os = self.posix
            res = os.getresgid()
            assert len(res) == 3

    if hasattr(os, 'setresuid'):
        def test_os_setresuid(self):
            os = self.posix
            a, b, c = os.getresuid()
            os.setresuid(a, b, c)

    if hasattr(os, 'setresgid'):
        def test_os_setresgid(self):
            os = self.posix
            a, b, c = os.getresgid()
            os.setresgid(a, b, c)

    if hasattr(os, 'sysconf'):
        def test_os_sysconf(self):
            os = self.posix
            assert os.sysconf(self.sysconf_value) == self.sysconf_result
            assert os.sysconf(self.sysconf_name) == self.sysconf_result
            assert os.sysconf_names[self.sysconf_name] == self.sysconf_value

        def test_os_sysconf_error(self):
            os = self.posix
            with raises(ValueError):
                os.sysconf("!@#$%!#$!@#")

    if hasattr(os, 'fpathconf'):
        def test_os_fpathconf(self):
            os = self.posix
            assert os.fpathconf(1, "PC_PIPE_BUF") >= 128
            with raises(OSError):
                os.fpathconf(-1, "PC_PIPE_BUF")
            with raises(ValueError):
                os.fpathconf(1, "##")

    if hasattr(os, 'pathconf'):
        def test_os_pathconf(self):
            os = self.posix
            assert os.pathconf("/tmp", "PC_NAME_MAX") >= 31
            # Linux: the following gets 'No such file or directory'
            with raises(OSError):
                os.pathconf("", "PC_PIPE_BUF")
            with raises(ValueError):
                os.pathconf("/tmp", "##")

    if hasattr(os, 'confstr'):
        def test_os_confstr(self):
            os = self.posix
            assert os.confstr(self.confstr_value) == self.confstr_result
            assert os.confstr(self.confstr_name) == self.confstr_result
            assert os.confstr_names[self.confstr_name] == self.confstr_value

        def test_os_confstr_error(self):
            os = self.posix
            with raises(ValueError):
                os.confstr("!@#$%!#$!@#")

    if hasattr(os, 'wait'):
        def test_os_wait(self):
            os = self.posix
            exit_status = 0x33

            if not hasattr(os, "fork"):
                skip("Need fork() to test wait()")
            if hasattr(os, "waitpid") and hasattr(os, "WNOHANG"):
                try:
                    while os.waitpid(-1, os.WNOHANG)[0]:
                        pass
                except OSError:  # until we get "No child processes", hopefully
                    pass
            child = os.fork()
            if child == 0: # in child
                os._exit(exit_status)
            else:
                pid, status = os.wait()
                assert child == pid
                assert os.WIFEXITED(status)
                assert os.WEXITSTATUS(status) == exit_status

    if hasattr(os, 'getloadavg'):
        def test_os_getloadavg(self):
            os = self.posix
            l0, l1, l2 = os.getloadavg()
            assert type(l0) is float and l0 >= 0.0
            assert type(l1) is float and l0 >= 0.0
            assert type(l2) is float and l0 >= 0.0

    if hasattr(os, 'major'):
        def test_major_minor(self):
            os = self.posix
            assert os.major(12345) == self.expected_major_12345
            assert os.minor(12345) == self.expected_minor_12345
            assert os.makedev(self.expected_major_12345,
                              self.expected_minor_12345) == 12345
            with raises((ValueError, OverflowError)):
                os.major(-1)

    if hasattr(os, 'fsync'):
        def test_fsync(self):
            os = self.posix
            f = open(self.path2, "w")
            try:
                fd = f.fileno()
                os.fsync(fd)
                os.fsync(long(fd))
                os.fsync(f)     # <- should also work with a file, or anything
            finally:            #    with a fileno() method
                f.close()
            try:
                # May not raise anything with a buggy libc (or eatmydata)
                os.fsync(fd)
            except OSError:
                pass
            with raises(ValueError):
                os.fsync(-1)

    if hasattr(os, 'fdatasync'):
        def test_fdatasync(self):
            os = self.posix
            f = open(self.path2, "w")
            try:
                fd = f.fileno()
                os.fdatasync(fd)
            finally:
                f.close()
            try:
                # May not raise anything with a buggy libc (or eatmydata)
                os.fdatasync(fd)
            except OSError:
                pass
            with raises(ValueError):
                os.fdatasync(-1)

    if hasattr(os, 'fchdir'):
        def test_fchdir(self):
            os = self.posix
            localdir = os.getcwd()
            os.mkdir(self.path2 + 'fchdir')
            for func in [os.fchdir, os.chdir]:
                fd = os.open(self.path2 + 'fchdir', os.O_RDONLY)
                try:
                    os.fchdir(fd)
                    mypath = os.getcwd()
                finally:
                    os.chdir(localdir)
            with raises(ValueError):
                os.fchdir(-1)

    def test_largefile(self):
        os = self.posix
        fd = os.open(self.path2 + 'test_largefile',
                     os.O_RDWR | os.O_CREAT, 0666)
        os.ftruncate(fd, 10000000000L)
        res = os.lseek(fd, 9900000000L, 0)
        assert res == 9900000000L
        res = os.lseek(fd, -5000000000L, 1)
        assert res == 4900000000L
        res = os.lseek(fd, -5200000000L, 2)
        assert res == 4800000000L
        os.close(fd)

        st = os.stat(self.path2 + 'test_largefile')
        assert st.st_size == 10000000000L
    test_largefile.need_sparse_files = True

    def test_write_buffer(self):
        os = self.posix
        fd = os.open(self.path2 + 'test_write_buffer', os.O_RDWR | os.O_CREAT, 0666)
        def writeall(s):
            while s:
                count = os.write(fd, s)
                assert count > 0
                s = s[count:]
        writeall(b'hello, ')
        writeall(buffer('world!\n'))
        res = os.lseek(fd, 0, 0)
        assert res == 0
        data = b''
        while True:
            s = os.read(fd, 100)
            if not s:
                break
            data += s
        assert data == b'hello, world!\n'
        os.close(fd)

    def test_write_unicode(self):
        os = self.posix
        fd = os.open(self.path2 + 'test_write_unicode',
                     os.O_RDWR | os.O_CREAT, 0666)
        os.write(fd, u'X')
        with raises(UnicodeEncodeError):
            os.write(fd, u'\xe9')
        os.lseek(fd, 0, 0)
        data = os.read(fd, 2)
        assert data == 'X'
        os.close(fd)

    if hasattr(__import__(os.name), "fork"):
        def test_abort(self):
            os = self.posix
            pid = os.fork()
            if pid == 0:
                os.abort()
            pid1, status1 = os.waitpid(pid, 0)
            assert pid1 == pid
            assert os.WIFSIGNALED(status1)
            assert os.WTERMSIG(status1) == self.SIGABRT
        pass # <- please, inspect.getsource(), don't crash

    def test_closerange(self):
        os = self.posix
        if not hasattr(os, 'closerange'):
            skip("missing os.closerange()")
        fds = [os.open(self.path + str(i), os.O_CREAT|os.O_WRONLY, 0777)
               for i in range(15)]
        fds.sort()
        start = fds.pop()
        stop = start + 1
        while len(fds) > 3 and fds[-1] == start - 1:
            start = fds.pop()
        os.closerange(start, stop)
        for fd in fds:
            os.close(fd)     # should not have been closed
        if self.platform == 'win32' and self.runappdirect:
            # XXX kills the host interpreter untranslated
            for fd in range(start, stop):
                with raises(OSError):
                    os.fstat(fd)   # should have been closed

    if hasattr(os, 'chown'):
        def test_chown(self):
            os = self.posix
            os.unlink(self.path)
            with raises(OSError):
                os.chown(self.path, os.getuid(), os.getgid())
            f = open(self.path, "w")
            f.write("this is a test")
            f.close()
            os.chown(self.path, os.getuid(), os.getgid())

    if hasattr(os, 'lchown'):
        def test_lchown(self):
            os = self.posix
            os.unlink(self.path)
            with raises(OSError):
                os.lchown(self.path, os.getuid(), os.getgid())
            os.symlink('foobar', self.path)
            os.lchown(self.path, os.getuid(), os.getgid())

    if hasattr(os, 'fchown'):
        def test_fchown(self):
            os = self.posix
            f = open(self.path, "w")
            os.fchown(f.fileno(), os.getuid(), os.getgid())
            f.close()

    if hasattr(os, 'chmod'):
        def test_chmod(self):
            import sys
            os = self.posix
            os.unlink(self.path)
            with raises(OSError):
                os.chmod(self.path, 0600)
            f = open(self.path, "w")
            f.write("this is a test")
            f.close()
            if sys.platform == 'win32':
                os.chmod(self.path, 0400)
                assert (os.stat(self.path).st_mode & 0600) == 0400
                os.chmod(self.path, 0700)
            else:
                os.chmod(self.path, 0200)
                assert (os.stat(self.path).st_mode & 0777) == 0200
                os.chmod(self.path, 0700)
            os.unlink(self.path)

    if hasattr(os, 'fchmod'):
        def test_fchmod(self):
            os = self.posix
            f = open(self.path, "w")
            os.fchmod(f.fileno(), 0200)
            assert (os.fstat(f.fileno()).st_mode & 0777) == 0200
            f.close()
            assert (os.stat(self.path).st_mode & 0777) == 0200
            os.unlink(self.path)

    if hasattr(os, 'mkfifo'):
        def test_mkfifo(self):
            os = self.posix
            os.mkfifo(self.path2 + 'test_mkfifo', 0666)
            st = os.lstat(self.path2 + 'test_mkfifo')
            import stat
            assert stat.S_ISFIFO(st.st_mode)

    if hasattr(os, 'mknod'):
        def test_mknod(self):
            import stat
            os = self.posix
            # os.mknod() may require root priviledges to work at all
            try:
                # not very useful: os.mknod() without specifying 'mode'
                os.mknod(self.path2 + 'test_mknod-1')
            except OSError as e:
                skip("os.mknod(): got %r" % (e,))
            st = os.lstat(self.path2 + 'test_mknod-1')
            assert stat.S_ISREG(st.st_mode)
            # os.mknod() with S_IFIFO
            os.mknod(self.path2 + 'test_mknod-2', 0600 | stat.S_IFIFO)
            st = os.lstat(self.path2 + 'test_mknod-2')
            assert stat.S_ISFIFO(st.st_mode)

        def test_mknod_with_ifchr(self):
            # os.mknod() with S_IFCHR
            # -- usually requires root priviledges --
            os = self.posix
            if hasattr(os.lstat('.'), 'st_rdev'):
                import stat
                try:
                    os.mknod(self.path2 + 'test_mknod-3', 0600 | stat.S_IFCHR,
                             0x105)
                except OSError as e:
                    skip("os.mknod() with S_IFCHR: got %r" % (e,))
                else:
                    st = os.lstat(self.path2 + 'test_mknod-3')
                    assert stat.S_ISCHR(st.st_mode)
                    assert st.st_rdev == 0x105

    if hasattr(os, 'nice') and hasattr(os, 'fork') and hasattr(os, 'waitpid'):
        def test_nice(self):
            os = self.posix
            myprio = os.nice(0)
            #
            pid = os.fork()
            if pid == 0:    # in the child
                res = os.nice(3)
                os._exit(res)
            #
            pid1, status1 = os.waitpid(pid, 0)
            assert pid1 == pid
            assert os.WIFEXITED(status1)
            expected = min(myprio + 3, 19)
            assert os.WEXITSTATUS(status1) == expected

    if hasattr(os, 'symlink'):
        def test_symlink(self):
            posix = self.posix
            unicode_dir = self.unicode_dir
            if unicode_dir is None:
                skip("encoding not good enough")
            dest = u"%s/file.txt" % unicode_dir
            posix.symlink(u"%s/somefile" % unicode_dir, dest)
            with open(dest) as f:
                data = f.read()
                assert data == "who cares?"

    try:
        os.getlogin()
    except (AttributeError, OSError):
        pass
    else:
        def test_getlogin(self):
            assert isinstance(self.posix.getlogin(), str)
            # How else could we test that getlogin is properly
            # working?

    def test_tmpfile(self):
        os = self.posix
        f = os.tmpfile()
        f.write("xxx")
        f.flush()
        f.seek(0, 0)
        assert isinstance(f, file)
        assert f.read() == 'xxx'

    def test_tmpnam(self):
        import stat, os
        s1 = os.tmpnam()
        s2 = os.tmpnam()
        assert s1 != s2
        def isdir(s):
            try:
                return stat.S_ISDIR(os.stat(s).st_mode)
            except OSError:
                return -1
        assert isdir(s1) == -1
        assert isdir(s2) == -1
        assert isdir(os.path.dirname(s1)) == 1
        assert isdir(os.path.dirname(s2)) == 1

    def test_tempnam(self):
        import stat, os
        for dir in [None, self.udir]:
            for prefix in [None, 'foobar']:
                s1 = os.tempnam(dir, prefix)
                s2 = os.tempnam(dir, prefix)
                assert s1 != s2
                def isdir(s):
                    try:
                        return stat.S_ISDIR(os.stat(s).st_mode)
                    except OSError:
                        return -1
                assert isdir(s1) == -1
                assert isdir(s2) == -1
                assert isdir(os.path.dirname(s1)) == 1
                assert isdir(os.path.dirname(s2)) == 1
                if dir:
                    assert os.path.dirname(s1) == dir
                    assert os.path.dirname(s2) == dir
                assert os.path.basename(s1).startswith(prefix or 'tmp')
                assert os.path.basename(s2).startswith(prefix or 'tmp')

    def test_tmpnam_warning(self):
        import warnings, os
        #
        def f_tmpnam_warning(): os.tmpnam()    # a single line
        #
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            f_tmpnam_warning()
            assert len(w) == 1
            assert issubclass(w[-1].category, RuntimeWarning)
            assert "potential security risk" in str(w[-1].message)
            # check that the warning points to the call to os.tmpnam(),
            # not to some code inside app_posix.py
            assert w[-1].lineno == f_tmpnam_warning.func_code.co_firstlineno

    def test_has_kill(self):
        os = self.posix
        assert hasattr(os, 'kill')

    def test_pipe_flush(self):
        os = self.posix
        ffd, gfd = os.pipe()
        f = os.fdopen(ffd, 'r')
        g = os.fdopen(gfd, 'w')
        g.write('he')
        g.flush()
        x = f.read(1)
        assert x == 'h'
        f.flush()
        x = f.read(1)
        assert x == 'e'

    def test_urandom(self):
        os = self.posix
        s = os.urandom(5)
        assert isinstance(s, bytes)
        assert len(s) == 5
        for x in range(50):
            if s != os.urandom(5):
                break
        else:
            assert False, "urandom() always returns the same string"
            # Or very unlucky

    if hasattr(os, 'startfile'):
        def test_startfile(self):
            if not self.runappdirect:
                skip("should not try to import cffi at app-level")
            startfile = self.posix.startfile
            for t1 in [str, unicode]:
                for t2 in [str, unicode]:
                    with raises(WindowsError) as e:
                        startfile(t1("\\"), t2("close"))
                    assert e.value.args[0] == 1155
                    assert e.value.args[1] == (
                        "No application is associated with the "
                        "specified file for this operation")
                    if len(e.value.args) > 2:
                        assert e.value.args[2] == t1("\\")
            #
            with raises(WindowsError) as e:
                startfile("\\foo\\bar\\baz")
            assert e.value.args[0] == 2
            assert e.value.args[1] == (
                "The system cannot find the file specified")
            if len(e.value.args) > 2:
                assert e.value.args[2] == "\\foo\\bar\\baz"

    @pytest.mark.skipif("sys.platform != 'win32'")
    def test_rename(self):
        os = self.posix
        fname = self.path2 + 'rename.txt'
        with open(fname, "w") as f:
            f.write("this is a rename test")
        str_name = str(self.pdir) + '/test_rename.txt'
        os.rename(fname, str_name)
        with open(str_name) as f:
            assert f.read() == 'this is a rename test'
        os.rename(str_name, fname)
        unicode_name = str(self.udir) + u'/test\u03be.txt'
        os.rename(fname, unicode_name)
        with open(unicode_name) as f:
            assert f.read() == 'this is a rename test'
        os.rename(unicode_name, fname)



class AppTestEnvironment(object):
    def setup_class(cls):
        cls.w_path = space.wrap(str(path))
        cls.w_posix = space.appexec([], GET_POSIX)
        cls.w_python = space.wrap(sys.executable)

    def test_environ(self):
        import sys, os
        environ = os.environ
        if not environ:
            skip('environ not filled in for untranslated tests')
        for k, v in environ.items():
            assert type(k) is str
            assert type(v) is str
        name = next(iter(environ))
        assert environ[name] is not None
        del environ[name]
        with raises(KeyError):
            environ[name]

    @pytest.mark.dont_track_allocations('putenv intentionally keeps strings alive')
    def test_environ_nonascii(self):
        import sys, os
        name, value = 'PYPY_TEST_日本', 'foobar日本'
        os.environ[name] = value
        assert os.environ[name] == value
        assert os.getenv(name) == value
        del os.environ[name]
        assert os.environ.get(name) is None
        assert os.getenv(name) is None

    if hasattr(__import__(os.name), "unsetenv"):
        def test_unsetenv_nonexisting(self):
            os = self.posix
            os.unsetenv("XYZABC") #does not raise
            try:
                os.environ["ABCABC"]
            except KeyError:
                pass
            else:
                raise AssertionError("did not raise KeyError")
            os.environ["ABCABC"] = "1"
            assert os.environ["ABCABC"] == "1"
            os.unsetenv("ABCABC")
            cmd = ('%s -c "import os, sys; '
                   'sys.exit(int(\'ABCABC\' in os.environ))" '
                   % self.python)
            res = os.system(cmd)
            assert res == 0

    def test_putenv_invalid_name(self):
        import os, sys
        if sys.platform.startswith('win'):
            os.putenv("=hidden", "foo")
            raises(ValueError, os.putenv, "foo=bar", "xxx")
        else:
            raises(ValueError, os.putenv, "=foo", "xxx")


class AppTestPosixUnicode:
    def setup_class(cls):
        if sys.platform == 'win32':
            py.test.skip("Posix-only tests")
        if cls.runappdirect:
            # Can't change encoding
            try:
                u"ą".encode(sys.getfilesystemencoding())
            except UnicodeEncodeError:
                py.test.skip("encoding not good enough")
        else:
            cls.save_fs_encoding = cls.space.sys.filesystemencoding
            cls.space.sys.filesystemencoding = "utf-8"

    def teardown_class(cls):
        try:
            cls.space.sys.filesystemencoding = cls.save_fs_encoding
        except AttributeError:
            pass

    def test_stat_unicode(self):
        # test that passing unicode would not raise UnicodeDecodeError
        import posix
        try:
            posix.stat(u"ą")
        except OSError:
            pass

    def test_open_unicode(self):
        # Ensure passing unicode doesn't raise UnicodeEncodeError
        import posix
        try:
            posix.open(u"ą", posix.O_WRONLY)
        except OSError:
            pass

    def test_remove_unicode(self):
        # See 2 above ;)
        import posix
        try:
            posix.remove(u"ą")
        except OSError:
            pass


class AppTestUnicodeFilename:
    def setup_class(cls):
        ufilename = (unicode(udir.join('test_unicode_filename_')) +
                     u'\u65e5\u672c.txt') # "Japan"
        try:
            f = file(ufilename, 'w')
        except UnicodeEncodeError:
            pytest.skip("encoding not good enough")
        f.write("test")
        f.close()
        cls.space = space
        cls.w_filename = space.wrap(ufilename)
        cls.w_posix = space.appexec([], GET_POSIX)

    def test_open(self):
        fd = self.posix.open(self.filename, self.posix.O_RDONLY)
        try:
            content = self.posix.read(fd, 50)
        finally:
            self.posix.close(fd)
        assert content == b"test"


from pypy import pypydir
class TestPexpect(object):
    # XXX replace with AppExpectTest class as soon as possible
    def setup_class(cls):
        try:
            import pexpect
        except ImportError:
            py.test.skip("pexpect not found")

    def _spawn(self, *args, **kwds):
        import pexpect
        kwds.setdefault('timeout', 600)
        print 'SPAWN:', args, kwds
        child = pexpect.spawn(*args, **kwds)
        child.logfile = sys.stdout
        return child

    def spawn(self, argv):
        py_py = py.path.local(pypydir).join('bin', 'pyinteractive.py')
        return self._spawn(sys.executable, [str(py_py)] + argv)

    def test_ttyname(self):
        source = py.code.Source("""
        import os, sys
        assert os.ttyname(sys.stdin.fileno())
        print 'ok!'
        """)
        f = udir.join("test_ttyname.py")
        f.write(source)
        child = self.spawn([str(f)])
        child.expect('ok!')
