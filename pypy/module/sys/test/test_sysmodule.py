# -*- coding: iso-8859-1 -*-
import sys

def test_stdin_exists(space):
    space.sys.get('stdin')
    space.sys.get('__stdin__')

def test_stdout_exists(space):
    space.sys.get('stdout')
    space.sys.get('__stdout__')

class AppTestAppSysTests:

    def setup_class(cls):
        cls.w_appdirect = cls.space.wrap(cls.runappdirect)
        cls.w_filesystemenc = cls.space.wrap(sys.getfilesystemencoding())

    def test_sys_in_modules(self):
        import sys
        modules = sys.modules
        assert 'sys' in modules, ( "An entry for sys "
                                        "is not in sys.modules.")
        sys2 = sys.modules['sys']
        assert sys is sys2, "import sys is not sys.modules[sys]."
    def test_builtin_in_modules(self):
        import sys
        modules = sys.modules
        assert '__builtin__' in modules, ( "An entry for __builtin__ "
                                                    "is not in sys.modules.")
        import __builtin__
        builtin2 = sys.modules['__builtin__']
        assert __builtin__ is builtin2, ( "import __builtin__ "
                                            "is not sys.modules[__builtin__].")
    def test_builtin_module_names(self):
        import sys
        names = sys.builtin_module_names
        assert 'sys' in names, (
                        "sys is not listed as a builtin module.")
        assert '__builtin__' in names, (
                        "__builtin__ is not listed as a builtin module.")

    def test_sys_exc_info(self):
        try:
            raise Exception
        except Exception as e:
            import sys
            exc_type,exc_val,tb = sys.exc_info()
        try:
            raise Exception   # 5 lines below the previous one
        except Exception as e2:
            exc_type2,exc_val2,tb2 = sys.exc_info()
        assert exc_type ==Exception
        assert exc_val ==e
        assert exc_type2 ==Exception
        assert exc_val2 ==e2
        assert tb2.tb_lineno - tb.tb_lineno == 5

    def test_dynamic_attributes(self):
        try:
            raise Exception
        except Exception as e:
            import sys
            exc_type = sys.exc_type
            exc_val = sys.exc_value
            tb = sys.exc_traceback
        try:
            raise Exception   # 7 lines below the previous one
        except Exception as e2:
            exc_type2 = sys.exc_type
            exc_val2 = sys.exc_value
            tb2 = sys.exc_traceback
        assert exc_type ==Exception
        assert exc_val ==e
        assert exc_type2 ==Exception
        assert exc_val2 ==e2
        assert tb2.tb_lineno - tb.tb_lineno == 7

    def test_exc_info_normalization(self):
        import sys
        try:
            1/0
        except ZeroDivisionError:
            etype, val, tb = sys.exc_info()
            assert isinstance(val, etype)
        else:
            raise AssertionError("ZeroDivisionError not caught")

    def test_io(self):
        import sys
        assert isinstance(sys.__stdout__, file)
        assert isinstance(sys.__stderr__, file)
        assert isinstance(sys.__stdin__, file)

        #assert sys.__stdin__.name == "<stdin>"
        #assert sys.__stdout__.name == "<stdout>"
        #assert sys.__stderr__.name == "<stderr>"

        if self.appdirect and not isinstance(sys.stdin, file):
            return

        assert isinstance(sys.stdout, file)
        assert isinstance(sys.stderr, file)
        assert isinstance(sys.stdin, file)

    def test_getfilesystemencoding(self):
        import sys
        assert sys.getfilesystemencoding() == self.filesystemenc

    def test_float_info(self):
        import sys
        fi = sys.float_info
        assert isinstance(fi.epsilon, float)
        assert isinstance(fi.dig, int)
        assert isinstance(fi.mant_dig, int)
        assert isinstance(fi.max, float)
        assert isinstance(fi.max_exp, int)
        assert isinstance(fi.max_10_exp, int)
        assert isinstance(fi.min, float)
        assert isinstance(fi.min_exp, int)
        assert isinstance(fi.min_10_exp, int)
        assert isinstance(fi.radix, int)
        assert isinstance(fi.rounds, int)

    def test_long_info(self):
        import sys
        li = sys.long_info
        assert isinstance(li.bits_per_digit, int)
        assert isinstance(li.sizeof_digit, int)

    def test_sys_exit(self):
        import sys
        exc = raises(SystemExit, sys.exit)
        assert exc.value.code is None

        exc = raises(SystemExit, sys.exit, 0)
        assert exc.value.code == 0

        exc = raises(SystemExit, sys.exit, 1)
        assert exc.value.code == 1

        exc = raises(SystemExit, sys.exit, (1, 2, 3))
        assert exc.value.code == (1, 2, 3)


class AppTestSysModulePortedFromCPython:

    def setup_class(cls):
        cls.w_appdirect = cls.space.wrap(cls.runappdirect)

    def test_original_displayhook(self):
        import sys, cStringIO, __builtin__
        savestdout = sys.stdout
        out = cStringIO.StringIO()
        sys.stdout = out

        dh = sys.__displayhook__

        raises(TypeError, dh)
        if hasattr(__builtin__, "_"):
            del __builtin__._

        dh(None)
        assert out.getvalue() == ""
        assert not hasattr(__builtin__, "_")
        dh("hello")
        assert out.getvalue() == "'hello'\n"
        assert __builtin__._ == "hello"

        del sys.stdout
        raises(RuntimeError, dh, 42)

        sys.stdout = savestdout

    def test_lost_displayhook(self):
        import sys
        olddisplayhook = sys.displayhook
        del sys.displayhook
        code = compile("42", "<string>", "single")
        raises(RuntimeError, eval, code)
        sys.displayhook = olddisplayhook

    def test_custom_displayhook(self):
        import sys
        olddisplayhook = sys.displayhook
        def baddisplayhook(obj):
            raise ValueError
        sys.displayhook = baddisplayhook
        code = compile("42", "<string>", "single")
        raises(ValueError, eval, code)
        sys.displayhook = olddisplayhook

    def test_original_excepthook(self):
        import sys, cStringIO
        savestderr = sys.stderr
        err = cStringIO.StringIO()
        sys.stderr = err

        eh = sys.__excepthook__

        raises(TypeError, eh)
        try:
            raise ValueError(42)
        except ValueError as exc:
            eh(*sys.exc_info())

        sys.stderr = savestderr
        assert err.getvalue().endswith("ValueError: 42\n")

    def test_excepthook_failsafe_path(self):
        import traceback
        original_print_exception = traceback.print_exception
        import sys, cStringIO
        savestderr = sys.stderr
        err = cStringIO.StringIO()
        sys.stderr = err
        try:
            traceback.print_exception = "foo"
            eh = sys.__excepthook__
            try:
                raise ValueError(42)
            except ValueError as exc:
                eh(*sys.exc_info())
        finally:
            traceback.print_exception = original_print_exception
            sys.stderr = savestderr

        assert err.getvalue() == "ValueError: 42\n"

    def test_original_excepthook_pypy_encoding(self):
        import sys
        if '__pypy__' not in sys.builtin_module_names:
            skip("only on PyPy")
        savestderr = sys.stderr
        class MyStringIO(object):
            def __init__(self):
                self.output = []
            def write(self, s):
                assert isinstance(s, str)
                self.output.append(s)
            def getvalue(self):
                return ''.join(self.output)

        for input, expectedoutput in [(u"\u013a", "\xe5"),
                                      (u"\u1111", "\\u1111")]:
            err = MyStringIO()
            err.encoding = 'iso-8859-2'
            sys.stderr = err

            eh = sys.__excepthook__
            try:
                raise ValueError(input)
            except ValueError as exc:
                eh(*sys.exc_info())

            sys.stderr = savestderr
            print repr(err.getvalue())
            assert err.getvalue().endswith("ValueError: %s\n" % expectedoutput)

    def test_excepthook_flushes_stdout(self):
        import sys, cStringIO
        savestdout = sys.stdout
        out = cStringIO.StringIO()
        sys.stdout = out

        eh = sys.__excepthook__

        try:
            raise ValueError(42)
        except ValueError as exc:
            print "hello"     # with end-of-line
            eh(*sys.exc_info())
        try:
            raise ValueError(42)
        except ValueError as exc:
            print 123, 456,     # no end-of-line here
            assert sys.stdout.softspace
            eh(*sys.exc_info())
            assert not sys.stdout.softspace

        sys.stdout = savestdout
        assert out.getvalue() == 'hello\n123 456\n'   # with a final \n added

    # FIXME: testing the code for a lost or replaced excepthook in
    # Python/pythonrun.c::PyErr_PrintEx() is tricky.

    def test_exc_clear(self):
        import sys
        raises(TypeError, sys.exc_clear, 42)

        # Verify that exc_info is present and matches exc, then clear it, and
        # check that it worked.
        def clear_check(exc):
            typ, value, traceback = sys.exc_info()
            assert typ is not None
            assert value is exc
            assert traceback is not None

            sys.exc_clear()

            typ, value, traceback = sys.exc_info()
            assert typ is None
            assert value is None
            assert traceback is None

        def clear():
            try:
                raise ValueError(42)
            except ValueError as exc:
                clear_check(exc)

        # Raise an exception and check that it can be cleared
        clear()

        # Verify that a frame currently handling an exception is
        # unaffected by calling exc_clear in a nested frame.
        try:
            raise ValueError(13)
        except ValueError as exc:
            typ1, value1, traceback1 = sys.exc_info()
            clear()
            typ2, value2, traceback2 = sys.exc_info()

            assert typ1 is typ2
            assert value1 is exc
            assert value1 is value2
            assert traceback1 is traceback2

        # Check that an exception can be cleared outside of an except block
        clear_check(exc)

    def test_exit(self):
        import sys
        raises(TypeError, sys.exit, 42, 42)

        # call without argument
        try:
            sys.exit(0)
        except SystemExit as exc:
            assert exc.code == 0
        except:
            raise AssertionError("wrong exception")
        else:
            raise AssertionError("no exception")

        # call with tuple argument with one entry
        # entry will be unpacked
        try:
            sys.exit(42)
        except SystemExit as exc:
            assert exc.code == 42
        except:
            raise AssertionError("wrong exception")
        else:
            raise AssertionError("no exception")

        # call with integer argument
        try:
            sys.exit((42,))
        except SystemExit as exc:
            assert exc.code == 42
        except:
            raise AssertionError("wrong exception")
        else:
            raise AssertionError("no exception")

        # call with string argument
        try:
            sys.exit("exit")
        except SystemExit as exc:
            assert exc.code == "exit"
        except:
            raise AssertionError("wrong exception")
        else:
            raise AssertionError("no exception")

        # call with tuple argument with two entries
        try:
            sys.exit((17, 23))
        except SystemExit as exc:
            assert exc.code == (17, 23)
        except:
            raise AssertionError("wrong exception")
        else:
            raise AssertionError("no exception")

    def test_getdefaultencoding(self):
        import sys
        raises(TypeError, sys.getdefaultencoding, 42)
        # can't check more than the type, as the user might have changed it
        assert isinstance(sys.getdefaultencoding(), str)

    def test_setdefaultencoding(self):
        import sys
        if self.appdirect:
            skip("not worth running appdirect")

        encoding = sys.getdefaultencoding()
        try:
            sys.setdefaultencoding("ascii")
            assert sys.getdefaultencoding() == 'ascii'
            raises(UnicodeDecodeError, unicode, '\x80')

            sys.setdefaultencoding("latin-1")
            assert sys.getdefaultencoding() == 'latin-1'
            assert unicode('\x80') == u'\u0080'

        finally:
            sys.setdefaultencoding(encoding)


    # testing sys.settrace() is done in test_trace.py
    # testing sys.setprofile() is done in test_profile.py

    def test_setcheckinterval(self):
        import sys
        raises(TypeError, sys.setcheckinterval)
        orig = sys.getcheckinterval()
        for n in 0, 100, 120, orig: # orig last to restore starting state
            sys.setcheckinterval(n)
            assert sys.getcheckinterval() == n

    def test_recursionlimit(self):
        import sys
        raises(TypeError, sys.getrecursionlimit, 42)
        oldlimit = sys.getrecursionlimit()
        raises(TypeError, sys.setrecursionlimit)
        raises(ValueError, sys.setrecursionlimit, -42)
        sys.setrecursionlimit(10000)
        assert sys.getrecursionlimit() == 10000
        sys.setrecursionlimit(oldlimit)
        raises(OverflowError, sys.setrecursionlimit, 1<<31)

    def test_getwindowsversion(self):
        import sys
        if hasattr(sys, "getwindowsversion"):
            v = sys.getwindowsversion()
            if '__pypy__' in sys.builtin_module_names:
                assert isinstance(v, tuple)
            assert len(v) == 5
            assert isinstance(v[0], int)
            assert isinstance(v[1], int)
            assert isinstance(v[2], int)
            assert isinstance(v[3], int)
            assert isinstance(v[4], str)

            assert v[0] == v.major
            assert v[1] == v.minor
            assert v[2] == v.build
            assert v[3] == v.platform
            assert v[4] == v.service_pack

            assert isinstance(v.service_pack_minor, int)
            assert isinstance(v.service_pack_major, int)
            assert isinstance(v.suite_mask, int)
            assert isinstance(v.product_type, int)

            # This is how platform.py calls it. Make sure tuple still has 5
            # elements
            maj, min, buildno, plat, csd = sys.getwindowsversion()

    def test_winver(self):
        import sys
        if hasattr(sys, "winver"):
            assert sys.winver == sys.version[:3]

    def test_dllhandle(self):
        import sys
        assert hasattr(sys, 'dllhandle') == (sys.platform == 'win32')

    def test_dlopenflags(self):
        import sys
        if not hasattr(sys, "getdlopenflags"):
            skip('{gs}etdlopenflags is not implemented on this platform')
        raises(TypeError, sys.getdlopenflags, 42)
        oldflags = sys.getdlopenflags()
        raises(TypeError, sys.setdlopenflags)
        sys.setdlopenflags(oldflags+1)
        assert sys.getdlopenflags() == oldflags+1
        sys.setdlopenflags(oldflags)

    def test_refcount(self):
        import sys
        if not hasattr(sys, "getrefcount"):
            skip('Reference counting is not implemented.')

        raises(TypeError, sys.getrefcount)
        c = sys.getrefcount(None)
        n = None
        assert sys.getrefcount(None) == c+1
        del n
        assert sys.getrefcount(None) == c
        if hasattr(sys, "gettotalrefcount"):
            assert isinstance(sys.gettotalrefcount(), int)

    def test_getframe(self):
        import sys
        raises(TypeError, sys._getframe, 42, 42)
        raises(ValueError, sys._getframe, 2000000000)
        assert sys._getframe().f_code.co_name == 'test_getframe'
        #assert (
        #    TestSysModule.test_getframe.im_func.func_code \
        #    is sys._getframe().f_code
        #)

    def test_getframe_in_returned_func(self):
        import sys
        def f():
            return g()
        def g():
            return sys._getframe(0)
        frame = f()
        assert frame.f_code.co_name == 'g'
        assert frame.f_back.f_code.co_name == 'f'
        assert frame.f_back.f_back.f_code.co_name == 'test_getframe_in_returned_func'

    def test_attributes(self):
        import sys
        assert sys.__name__ == 'sys'
        assert isinstance(sys.modules, dict)
        assert isinstance(sys.path, list)
        assert isinstance(sys.api_version, int)
        assert isinstance(sys.argv, list)
        assert sys.byteorder in ("little", "big")
        assert isinstance(sys.builtin_module_names, tuple)
        assert isinstance(sys.copyright, basestring)
        #assert isinstance(sys.exec_prefix, basestring) -- not present!
        #assert isinstance(sys.executable, basestring) -- not present!
        assert isinstance(sys.hexversion, int)
        assert isinstance(sys.maxint, int)
        assert isinstance(sys.maxsize, int)
        assert isinstance(sys.maxunicode, int)
        assert isinstance(sys.platform, basestring)
        #assert isinstance(sys.prefix, basestring) -- not present!
        assert isinstance(sys.version, basestring)
        assert isinstance(sys.warnoptions, list)
        vi = sys.version_info
        if '__pypy__' in sys.builtin_module_names:
            assert isinstance(vi, tuple)
        assert len(vi) == 5
        assert isinstance(vi[0], int)
        assert isinstance(vi[1], int)
        assert isinstance(vi[2], int)
        assert vi[3] in ("alpha", "beta", "candidate", "final")
        assert isinstance(vi[4], int)

    def test_reload_doesnt_override_sys_executable(self):
        import sys
        if not hasattr(sys, 'executable'):    # if not translated
            sys.executable = 'from_test_sysmodule'
        previous = sys.executable
        reload(sys)
        assert sys.executable == previous

    def test_settrace(self):
        import sys
        counts = []
        def trace(x, y, z):
            counts.append(None)

        def x():
            pass
        sys.settrace(trace)
        try:
            x()
            assert sys.gettrace() is trace
        finally:
            sys.settrace(None)
        assert len(counts) == 1

    def test_pypy_attributes(self):
        import sys
        if '__pypy__' not in sys.builtin_module_names:
            skip("only on PyPy")
        assert isinstance(sys.pypy_objspaceclass, str)
        vi = sys.pypy_version_info
        assert isinstance(vi, tuple)
        assert len(vi) == 5
        assert isinstance(vi[0], int)
        assert isinstance(vi[1], int)
        assert isinstance(vi[2], int)
        assert vi[3] in ("alpha", "beta", "candidate", "dev", "final")
        assert isinstance(vi[4], int)

    def test_allattributes(self):
        import sys
        sys.__dict__   # check that we don't crash initializing any attribute

    def test_subversion(self):
        import sys
        if '__pypy__' not in sys.builtin_module_names:
            skip("only on PyPy")
        assert sys.subversion == ('PyPy', '', '')

    def test__mercurial(self):
        import sys, re
        if '__pypy__' not in sys.builtin_module_names:
            skip("only on PyPy")
        project, hgtag, hgid = sys._mercurial
        assert project == 'PyPy'
        # the tag or branch may be anything, including the empty string
        assert isinstance(hgtag, str)
        # the id is either nothing, or an id of 12 hash digits, with a possible
        # suffix of '+' if there are local modifications
        assert hgid == '' or re.match('[0-9a-f]{12}\+?', hgid)
        # the id should also show up in sys.version
        if hgid != '':
            assert hgid in sys.version

    def test_trace_exec_execfile(self):
        import sys
        found = []
        def do_tracing(f, *args):
            print f.f_code.co_filename, f.f_lineno, args
            if f.f_code.co_filename == 'foobar':
                found.append(args[0])
            return do_tracing
        co = compile("execfile('this-file-does-not-exist!')",
                     'foobar', 'exec')
        sys.settrace(do_tracing)
        try:
            exec co in {}
        except IOError:
            pass
        sys.settrace(None)
        assert found == ['call', 'line', 'exception', 'return']

    def test_float_repr_style(self):
        import sys

        # If this ever actually becomes a compilation option this test should
        # be changed.
        assert sys.float_repr_style == "short"

class AppTestSysSettracePortedFromCpython(object):
    def test_sys_settrace(self):
        import sys

        class Tracer:
            def __init__(self):
                self.events = []
            def trace(self, frame, event, arg):
                self.events.append((frame.f_lineno, event))
                return self.trace
            def traceWithGenexp(self, frame, event, arg):
                (o for o in [1])
                self.events.append((frame.f_lineno, event))
                return self.trace

        def compare_events(line_offset, events, expected_events):
            events = [(l - line_offset, e) for (l, e) in events]
            assert events == expected_events

        def run_test2(func):
            tracer = Tracer()
            func(tracer.trace)
            sys.settrace(None)
            compare_events(func.func_code.co_firstlineno,
                           tracer.events, func.events)


        def _settrace_and_return(tracefunc):
            sys.settrace(tracefunc)
            sys._getframe().f_back.f_trace = tracefunc
        def settrace_and_return(tracefunc):
            _settrace_and_return(tracefunc)


        def _settrace_and_raise(tracefunc):
            sys.settrace(tracefunc)
            sys._getframe().f_back.f_trace = tracefunc
            raise RuntimeError
        def settrace_and_raise(tracefunc):
            try:
                _settrace_and_raise(tracefunc)
            except RuntimeError as exc:
                pass

        settrace_and_raise.events = [(2, 'exception'),
                                     (3, 'line'),
                                     (4, 'line'),
                                     (4, 'return')]

        settrace_and_return.events = [(1, 'return')]
        run_test2(settrace_and_return)
        run_test2(settrace_and_raise)


class AppTestCurrentFrames:
    def test_current_frames(self):
        try:
            import thread
        except ImportError:
            pass
        else:
            skip('This test requires an intepreter without threads')
        import sys

        def f():
            return sys._current_frames()
        frames = f()
        assert frames.keys() == [0]
        assert frames[0].f_code.co_name in ('f', '?')


class AppTestCurrentFramesWithThread(AppTestCurrentFrames):
    spaceconfig = {
        "usemodules": ["time", "thread"],
    }

    def test_current_frames(self):
        import sys
        import time
        import thread

        # XXX workaround for now: to prevent deadlocks, call
        # sys._current_frames() once before starting threads.
        # This is an issue in non-translated versions only.
        sys._current_frames()

        thread_id = thread.get_ident()
        def other_thread():
            #print "thread started"
            lock2.release()
            lock1.acquire()
        lock1 = thread.allocate_lock()
        lock2 = thread.allocate_lock()
        lock1.acquire()
        lock2.acquire()
        thread.start_new_thread(other_thread, ())

        def f():
            lock2.acquire()
            return sys._current_frames()

        frames = f()
        lock1.release()
        thisframe = frames.pop(thread_id)
        assert thisframe.f_code.co_name in ('f', '?')

        assert len(frames) == 1
        _, other_frame = frames.popitem()
        assert other_frame.f_code.co_name in ('other_thread', '?')


class AppTestSysExcInfoDirect:

    def setup_method(self, meth):
        self.checking = not self.runappdirect
        if self.checking:
            self.seen = []
            from pypy.module.sys import vm
            def exc_info_with_tb(*args):
                self.seen.append("n")     # not optimized
                return self.old[0](*args)
            def exc_info_without_tb(*args):
                self.seen.append("y")     # optimized
                return self.old[1](*args)
            self.old = [vm.exc_info_with_tb, vm.exc_info_without_tb]
            vm.exc_info_with_tb = exc_info_with_tb
            vm.exc_info_without_tb = exc_info_without_tb
            #
            from rpython.rlib import jit
            self.old2 = [jit.we_are_jitted]
            jit.we_are_jitted = lambda: True

    def teardown_method(self, meth):
        if self.checking:
            from pypy.module.sys import vm
            from rpython.rlib import jit
            vm.exc_info_with_tb = self.old[0]
            vm.exc_info_without_tb = self.old[1]
            jit.we_are_jitted = self.old2[0]
            #
            assert ''.join(self.seen) == meth.expected

    def test_returns_none(self):
        import sys
        assert sys.exc_info() == (None, None, None)
        assert sys.exc_info()[0] is None
        assert sys.exc_info()[1] is None
        assert sys.exc_info()[2] is None
        assert sys.exc_info()[:2] == (None, None)
        assert sys.exc_info()[:3] == (None, None, None)
        assert sys.exc_info()[0:2] == (None, None)
        assert sys.exc_info()[2:4] == (None,)
    test_returns_none.expected = 'nnnnnnnn'

    def test_returns_subscr(self):
        import sys
        e = KeyError("boom")
        try:
            raise e
        except:
            assert sys.exc_info()[0] is KeyError  # y
            assert sys.exc_info()[1] is e         # y
            assert sys.exc_info()[2] is not None  # n
            assert sys.exc_info()[-3] is KeyError # y
            assert sys.exc_info()[-2] is e        # y
            assert sys.exc_info()[-1] is not None # n
    test_returns_subscr.expected = 'yynyyn'

    def test_returns_slice_2(self):
        import sys
        e = KeyError("boom")
        try:
            raise e
        except:
            foo = sys.exc_info()                  # n
            assert sys.exc_info()[:0] == ()       # y
            assert sys.exc_info()[:1] == foo[:1]  # y
            assert sys.exc_info()[:2] == foo[:2]  # y
            assert sys.exc_info()[:3] == foo      # n
            assert sys.exc_info()[:4] == foo      # n
            assert sys.exc_info()[:-1] == foo[:2] # y
            assert sys.exc_info()[:-2] == foo[:1] # y
            assert sys.exc_info()[:-3] == ()      # y
    test_returns_slice_2.expected = 'nyyynnyyy'

    def test_returns_slice_3(self):
        import sys
        e = KeyError("boom")
        try:
            raise e
        except:
            foo = sys.exc_info()                   # n
            assert sys.exc_info()[2:2] == ()       # y
            assert sys.exc_info()[0:1] == foo[:1]  # y
            assert sys.exc_info()[1:2] == foo[1:2] # y
            assert sys.exc_info()[0:3] == foo      # n
            assert sys.exc_info()[2:4] == foo[2:]  # n
            assert sys.exc_info()[0:-1] == foo[:2] # y
            assert sys.exc_info()[0:-2] == foo[:1] # y
            assert sys.exc_info()[5:-3] == ()      # y
    test_returns_slice_3.expected = 'nyyynnyyy'

    def test_strange_invocation(self):
        import sys
        e = KeyError("boom")
        try:
            raise e
        except:
            a = []; k = {}
            assert sys.exc_info(*a)[:0] == ()
            assert sys.exc_info(**k)[:0] == ()
    test_strange_invocation.expected = 'nn'

    def test_call_in_subfunction(self):
        import sys
        def g():
            # this case is not optimized, because we need to search the
            # frame chain.  it's probably not worth the complications
            return sys.exc_info()[1]
        e = KeyError("boom")
        try:
            raise e
        except:
            assert g() is e
    test_call_in_subfunction.expected = 'n'
