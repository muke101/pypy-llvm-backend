import py
from pypy import conftest
from pypy.interpreter import gateway
from rpython.rlib.jit import non_virtual_ref, vref_None

class AppTestSlow:
    spaceconfig = dict(usemodules=['itertools'])

    def setup_class(cls):
        if py.test.config.option.runappdirect:
            filename = __file__
        else:
            filename = gateway.__file__

        if filename[-3:] != '.py':
            filename = filename[:-1]

        cls.w_file = cls.space.wrap(filename)

    def test_inspect(self):
        if not hasattr(len, 'func_code'):
            skip("Cannot run this test if builtins have no func_code")
        import inspect
        args, varargs, varkw = inspect.getargs(len.func_code)
        assert args == ['obj']
        assert varargs is None
        assert varkw is None

def _attach_helpers(space):
    from pypy.interpreter import pytraceback
    def hide_top_frame(space, w_frame):
        w_last = None
        while w_frame.f_backref():
            w_last = w_frame
            w_frame = w_frame.f_backref()
        assert w_last
        w_saved = w_last.f_backref()
        w_last.f_backref = vref_None
        return w_saved

    def restore_top_frame(space, w_frame, w_saved):
        while w_frame.f_backref():
            w_frame = w_frame.f_backref()
        w_frame.f_backref = non_virtual_ref(w_saved)

    def read_exc_type(space, w_frame):
        if w_frame.last_exception is None:
            return space.w_None
        else:
            return w_frame.last_exception.w_type

    from pypy.interpreter import gateway

    hide_gw = gateway.interp2app(hide_top_frame)
    space.setitem(space.builtin.w_dict,
                  space.wrap('hide_top_frame'),
                  space.wrap(hide_gw))
    restore_gw = gateway.interp2app(restore_top_frame)
    space.setitem(space.builtin.w_dict,
                  space.wrap('restore_top_frame'),
                  space.wrap(restore_gw))

    read_exc_type_gw = gateway.interp2app(read_exc_type)
    space.setitem(space.builtin.w_dict,
                  space.wrap('read_exc_type'),
                  space.wrap(read_exc_type_gw))

def _detach_helpers(space):
    space.delitem(space.builtin.w_dict,
                  space.wrap('hide_top_frame'))
    space.delitem(space.builtin.w_dict,
                  space.wrap('restore_top_frame'))


class AppTestInterpObjectPickling:
    pytestmark = py.test.mark.skipif("config.option.runappdirect")
    spaceconfig = {
        "usemodules": ["struct", "binascii"]
    }

    def setup_class(cls):
        _attach_helpers(cls.space)

    def teardown_class(cls):
        _detach_helpers(cls.space)

    def test_pickle_code(self):
        def f():
            return 42
        import pickle
        code = f.func_code
        pckl = pickle.dumps(code)
        result = pickle.loads(pckl)
        assert code == result

    def test_pickle_global_func(self):
        import new
        mod = new.module('mod')
        import sys
        sys.modules['mod'] = mod
        try:
            def func():
                return 42
            mod.__dict__['func'] = func
            func.__module__ = 'mod'
            import pickle
            pckl = pickle.dumps(func)
            result = pickle.loads(pckl)
            assert func is result
        finally:
            del sys.modules['mod']

    def test_pickle_not_imported_module(self):
        import new
        mod = new.module('mod')
        mod.__dict__['a'] = 1
        import pickle
        pckl = pickle.dumps(mod)
        result = pickle.loads(pckl)
        assert mod.__name__ == result.__name__
        assert mod.__dict__ == result.__dict__

    def test_pickle_builtin_func(self):
        import pickle
        pckl = pickle.dumps(map)
        result = pickle.loads(pckl)
        assert map is result

    def test_pickle_non_top_reachable_func(self):
        def func():
            return 42
        global a
        a = 42
        del globals()['test_pickle_non_top_reachable_func']
        import pickle
        pckl   = pickle.dumps(func)
        result = pickle.loads(pckl)
        assert func.func_name     == result.func_name
        assert func.func_closure  == result.func_closure
        assert func.func_code     == result.func_code
        assert func.func_defaults == result.func_defaults
        assert func.func_dict     == result.func_dict
        assert func.func_doc      == result.func_doc
        assert func.func_globals  == result.func_globals

    def test_pickle_cell(self):
        def g():
            x = [42]
            def f():
                x[0] += 1
                return x
            return f.func_closure[0]
        import pickle
        cell = g()
        pckl = pickle.dumps(cell)
        result = pickle.loads(pckl)
        assert cell == result
        assert not (cell != result)

    def test_pickle_frame(self):
        #import sys
        # avoid creating a closure for now
        def f():
            try:
                raise Exception()
            except:
                import sys
                exc_type, exc, tb = sys.exc_info()
                return tb.tb_frame
        import pickle
        f1     = f()
        saved = hide_top_frame(f1)
        pckl   = pickle.dumps(f1)
        restore_top_frame(f1, saved)
        f2     = pickle.loads(pckl)

        assert type(f1) is type(f2)
        assert dir(f1) == dir(f2)
        assert f1.__doc__ == f2.__doc__
        assert f2.f_back is None # because we pruned it
        assert f1.f_builtins is f2.f_builtins
        assert f1.f_code == f2.f_code
        assert f1.f_exc_traceback is f2.f_exc_traceback
        assert f1.f_exc_type is f2.f_exc_type
        assert f1.f_exc_value is f2.f_exc_value
        assert f1.f_lasti == f2.f_lasti
        assert f1.f_lineno == f2.f_lineno
        assert f1.f_restricted is f2.f_restricted
        assert f1.f_trace is f2.f_trace

    def test_pickle_frame_with_exc(self):
        #import sys
        # avoid creating a closure for now
        self = None
        def f():
            try:
                raise ValueError
            except:
                import sys, pickle
                f = sys._getframe()
                saved = hide_top_frame(f)
                pckl = pickle.dumps(f)
                restore_top_frame(f, saved)
                return pckl

        import pickle
        pckl   = f()
        f2     = pickle.loads(pckl)

        assert read_exc_type(f2) is ValueError

    def test_pickle_frame_clos(self):
        # similar to above, therefore skipping the asserts.
        # we just want to see that the closure works
        import sys # this is the difference!
        def f():
            try:
                raise Exception()
            except:
                exc_type, exc, tb = sys.exc_info()
                return tb.tb_frame
        import pickle
        f1     = f()
        saved = hide_top_frame(f1)
        pckl   = pickle.dumps(f1)
        restore_top_frame(f1, saved)
        f2     = pickle.loads(pckl)

    def test_frame_setstate_crash(self):
        import sys
        raises(ValueError, sys._getframe().__setstate__, [])

    def test_pickle_traceback(self):
        def f():
            try:
                raise Exception()
            except:
                from sys import exc_info
                exc_type, exc, tb = exc_info()
                return tb
        import pickle
        tb     = f()
        saved = hide_top_frame(tb.tb_frame)
        pckl   = pickle.dumps(tb)
        result = pickle.loads(pckl)

        assert type(tb) is type(result)
        assert tb.tb_lasti == result.tb_lasti
        assert tb.tb_lineno == result.tb_lineno
        assert tb.tb_next == result.tb_next

        restore_top_frame(tb.tb_frame, saved)

    def test_pickle_module(self):
        import pickle
        mod    = pickle
        pckl   = pickle.dumps(mod)
        result = pickle.loads(pckl)
        assert mod is result

    def test_pickle_moduledict(self):
        import pickle
        moddict  = pickle.__dict__
        pckl     = pickle.dumps(moddict)
        result   = pickle.loads(pckl)
        assert moddict is result

    def test_pickle_bltins_module(self):
        import pickle
        mod  = __builtins__
        pckl     = pickle.dumps(mod)
        result   = pickle.loads(pckl)
        assert mod is result

    def test_pickle_buffer(self):
        skip("Can't pickle buffer objects on top of CPython either.  "
             "Do we really need it?")
        import pickle
        a = buffer('ABCDEF')
        pckl     = pickle.dumps(a)
        result   = pickle.loads(pckl)
        assert a == result

    def test_pickle_complex(self):
        import pickle
        a = complex(1.23,4.567)
        pckl     = pickle.dumps(a)
        result   = pickle.loads(pckl)
        assert a == result

    def test_pickle_method(self):
        class myclass(object):
            def f(self):
                return 42
            def __reduce__(self):
                return (myclass, ())
        import pickle, sys, new
        myclass.__module__ = 'mod'
        myclass_inst = myclass()
        mod = new.module('mod')
        mod.myclass = myclass
        sys.modules['mod'] = mod
        try:
            method   = myclass_inst.f
            pckl     = pickle.dumps(method)
            result   = pickle.loads(pckl)
            # we cannot compare the objects, because the method will be a fresh one
            assert method() == result()
        finally:
            del sys.modules['mod']

    def test_pickle_staticmethod(self):
        class myclass(object):
            def f():
                return 42
            f = staticmethod(f)
        import pickle
        method   = myclass.f
        pckl     = pickle.dumps(method)
        result   = pickle.loads(pckl)
        assert method() == result()

    def test_pickle_classmethod(self):
        class myclass(object):
            def f(cls):
                return cls
            f = classmethod(f)
        import pickle, sys, new
        myclass.__module__ = 'mod'
        mod = new.module('mod')
        mod.myclass = myclass
        sys.modules['mod'] = mod
        try:
            method   = myclass.f
            pckl     = pickle.dumps(method)
            result   = pickle.loads(pckl)
            assert method() == result()
        finally:
            del sys.modules['mod']

    def test_pickle_sequenceiter(self):
        '''
        In PyPy there is no distinction here between listiterator and
        tupleiterator that is why you will find no test_pickle_listiter nor
        test_pickle_tupleiter here, just this test.
        '''
        import pickle
        liter  = iter([3,9,6,12,15,17,19,111])
        liter.next()
        pckl   = pickle.dumps(liter)
        result = pickle.loads(pckl)
        liter.next()
        result.next()
        assert type(liter) is type(result)
        raises(TypeError, len, liter)
        assert list(liter) == list(result)

    def test_pickle_reversesequenceiter(self):
        import pickle
        liter  = reversed([3,9,6,12,15,17,19,111])
        liter.next()
        pckl   = pickle.dumps(liter)
        result = pickle.loads(pckl)
        liter.next()
        result.next()
        assert type(liter) is type(result)
        raises(TypeError, len, liter)
        assert list(liter) == list(result)

    def test_pickle_reversesequenceiter_stopped(self):
        import pickle
        iter = reversed([])
        raises(StopIteration, next, iter)
        pckl   = pickle.dumps(iter)
        result = pickle.loads(pckl)
        raises(StopIteration, next, result)

    # This test used to be marked xfail and it tried to test for the past
    # support of pickling dictiter objects.
    def test_pickle_dictiter(self):
        import pickle
        tdict = {'2':2, '3':3, '5':5}
        diter  = iter(tdict)
        diter.next()
        raises(TypeError, pickle.dumps, diter)

    def test_pickle_reversed(self):
        import pickle
        r = reversed(tuple(range(10)))
        r.next()
        r.next()
        pickled = pickle.dumps(r)
        result = pickle.loads(pickled)
        result.next()
        r.next()
        assert type(r) is type(result)
        assert list(r) == list(result)

    def test_pickle_reversed_stopped(self):
        import pickle
        class IE(object):
            def __len__(self):
                return 1
            def __getitem__(self, i):
                raise IndexError
        for it in (), IE():
            iter = reversed(it)
            raises(StopIteration, next, iter)
            pckl   = pickle.dumps(iter)
            result = pickle.loads(pckl)
            raises(StopIteration, next, result)

    def test_pickle_enum(self):
        import pickle
        e = enumerate(range(100, 106))
        e.next()
        e.next()
        pckl   = pickle.dumps(e)
        result = pickle.loads(pckl)
        res = e.next()
        assert res == (2, 102)
        res = result.next()
        assert res == (2, 102)
        assert type(e) is type(result)
        res = list(e)
        assert res == [(3, 103), (4, 104), (5, 105)]
        res = list(result)
        assert res == [(3, 103), (4, 104), (5, 105)]

    def test_pickle_xrangeiter(self):
        import pickle
        riter  = iter(xrange(5))
        riter.next()
        riter.next()
        pckl   = pickle.dumps(riter)
        result = pickle.loads(pckl)
        assert type(riter) is type(result)
        assert list(result) == [2,3,4]

    def test_pickle_generator(self):
        import new
        mod = new.module('mod')
        import sys
        sys.modules['mod'] = mod
        try:
            def giveme(n):
                x = 0
                while x < n:
                    yield x
                    x += 1
            import pickle
            mod.giveme = giveme
            giveme.__module__ = mod
            g1   = mod.giveme(10)
            #g1.next()
            #g1.next()
            pckl = pickle.dumps(g1)
            g2   = pickle.loads(pckl)
            assert list(g1) == list(g2)
        finally:
            del sys.modules['mod']

    def test_pickle_generator_blk(self):
        # same as above but with the generator inside a block
        import new
        mod = new.module('mod')
        import sys
        sys.modules['mod'] = mod
        try:
            def giveme(n):
                x = 0
                while x < n:
                    yield x
                    x += 1
            import pickle
            mod.giveme = giveme
            giveme.__module__ = mod
            g1   = mod.giveme(10)
            g1.next()
            g1.next()
            pckl = pickle.dumps(g1)
            g2   = pickle.loads(pckl)
            assert list(g1) == list(g2)
        finally:
            del sys.modules['mod']

    def test_pickle_builtin_method(self):
        import pickle

        a_list = [1]
        meth1 = a_list.append
        pckl = pickle.dumps(meth1)
        meth2 = pickle.loads(pckl)
        meth1(1)
        meth2(2)
        assert a_list == [1, 1]
        assert meth2.im_self == [1, 2]

        unbound_meth = list.append
        unbound_meth2 = pickle.loads(pickle.dumps(unbound_meth))
        l = []
        unbound_meth2(l, 1)
        assert l == [1]

    def test_pickle_submodule(self):
        import pickle
        import sys, new

        mod = new.module('pack.mod')
        sys.modules['pack.mod'] = mod
        pack = new.module('pack')
        pack.mod = mod
        sys.modules['pack'] = pack

        import pack.mod
        pckl   = pickle.dumps(pack.mod)
        result = pickle.loads(pckl)
        assert pack.mod is result


    def test_pickle_generator_crash(self):
        import pickle

        def f():
            yield 0

        x = f()
        x.next()
        try:
            x.next()
        except StopIteration:
            y = pickle.loads(pickle.dumps(x))
        assert 'finished' in y.__name__
        assert 'finished' in repr(y)
        assert y.gi_code is None

class AppTestGeneratorCloning:

    def setup_class(cls):
        try:
            cls.space.appexec([], """():
                def f(): yield 42
                f().__reduce__()
            """)
        except TypeError as e:
            if 'pickle generator' not in str(e):
                raise
            py.test.skip("Frames can't be __reduce__()-ed")

    def test_deepcopy_generator(self):
        import copy

        def f(n):
            for i in range(n):
                yield 42 + i
        g = f(4)
        g2 = copy.deepcopy(g)
        res = g.next()
        assert res == 42
        res = g2.next()
        assert res == 42
        g3 = copy.deepcopy(g)
        res = g.next()
        assert res == 43
        res = g2.next()
        assert res == 43
        res = g3.next()
        assert res == 43

    def test_shallowcopy_generator(self):
        """Note: shallow copies of generators are often confusing.
        To start with, 'for' loops have an iterator that will not
        be copied, and so create tons of confusion.
        """
        import copy

        def f(n):
            while n > 0:
                yield 42 + n
                n -= 1
        g = f(2)
        g2 = copy.copy(g)
        res = g.next()
        assert res == 44
        res = g2.next()
        assert res == 44
        g3 = copy.copy(g)
        res = g.next()
        assert res == 43
        res = g2.next()
        assert res == 43
        res = g3.next()
        assert res == 43
        g4 = copy.copy(g2)
        for i in range(2):
            raises(StopIteration, g.next)
            raises(StopIteration, g2.next)
            raises(StopIteration, g3.next)
            raises(StopIteration, g4.next)
