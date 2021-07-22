from pypy.interpreter.pycode import PyCode
from pypy.interpreter import gateway
from pypy.interpreter.astcompiler import consts
import py

class TestCode:
    def test_code_eq_corner_cases(self):
        space = self.space
        def make_code_with_const(w_obj):
            return PyCode(space, 0, 0, 1, 0, '', [w_obj], [], [], '', '', 0, '', [], [], False)
        def cmp_code_consts(w_obj1, w_obj2):
            w_code1 = make_code_with_const(w_obj1)
            w_code2 = make_code_with_const(w_obj2)

            # code objects in co_consts are compared by identity
            # (we never share them in the bytecode compiler, it happens
            # extremely rarely and is not useful anyway)

            res1 = space.is_true(space.eq(w_code1, w_code2))
            res2 = space.is_true(space.eq(w_code2, w_code1))
            if res1:
                # if the code objects are equal, the hash should be the same
                h1 = space.int_w(w_code1.descr_code__hash__())
                h2 = space.int_w(w_code2.descr_code__hash__())
                assert h1 == h2

            # check reflexivity
            assert res1 == res2


            # wrapping as code doesn't change the result
            w_codecode1 = make_code_with_const(w_code1)
            w_codecode2 = make_code_with_const(w_code2)
            assert space.is_true(space.eq(w_codecode1, w_codecode2)) == res1

            # check that tupleization doesn't change the result
            if not space.isinstance_w(w_obj1, space.w_tuple):
                res3 = cmp_code_consts(space.newtuple([space.w_None, w_obj1]),
                                       space.newtuple([space.w_None, w_obj2]))
                assert res3 == res1
            return res1

        assert cmp_code_consts(space.w_None, space.w_None)

        # floats
        assert not cmp_code_consts(space.newfloat(0.0), space.newfloat(-0.0))
        assert cmp_code_consts(space.newfloat(float('nan')), space.newfloat(float('nan')))

        # complex
        assert not cmp_code_consts(space.newcomplex(0.0, 0.0), space.newcomplex(0.0, -0.0))
        assert not cmp_code_consts(space.newcomplex(0.0, 0.0), space.newcomplex(-0.0, 0.0))
        assert not cmp_code_consts(space.newcomplex(0.0, 0.0), space.newcomplex(-0.0, -0.0))
        assert not cmp_code_consts(space.newcomplex(-0.0, 0.0), space.newcomplex(0.0, -0.0))
        assert not cmp_code_consts(space.newcomplex(-0.0, 0.0), space.newcomplex(-0.0, -0.0))
        assert not cmp_code_consts(space.newcomplex(0.0, -0.0), space.newcomplex(-0.0, -0.0))

        # code objects: we compare them by identity, PyPy doesn't share them ever


class AppTestCodeIntrospection:
    def setup_class(cls):
        filename = __file__
        if filename[-3:] != '.py':
            filename = filename[:-1]

        cls.w_file = cls.space.wrap(filename)

    def test_attributes(self):
        def f(): pass
        def g(x, *y, **z): "docstring"
        assert hasattr(f.func_code, 'co_code')
        assert hasattr(g.func_code, 'co_code')

        testcases = [
            (f.func_code, {'co_name': 'f',
                           'co_names': (),
                           'co_varnames': (),
                           'co_argcount': 0,
                           'co_consts': (None,)
                           }),
            (g.func_code, {'co_name': 'g',
                           'co_names': (),
                           'co_varnames': ('x', 'y', 'z'),
                           'co_argcount': 1,
                           'co_consts': ("docstring", None),
                           }),
            ]

        import sys
        if hasattr(sys, 'pypy_objspaceclass'): 
            testcases += [
                (abs.func_code, {'co_name': 'abs',
                                 'co_varnames': ('val',),
                                 'co_argcount': 1,
                                 'co_flags': 0,
                                 'co_consts': ("abs(number) -> number\n\nReturn the absolute value of the argument.",),
                                 }),
                (object.__init__.im_func.func_code,
                                {#'co_name': '__init__',   XXX getting descr__init__
                                 'co_varnames': ('obj', 'args', 'keywords'),
                                 'co_argcount': 1,
                                 'co_flags': 0x000C,  # VARARGS|VARKEYWORDS
                                 }),
                ]

        # in PyPy, built-in functions have code objects
        # that emulate some attributes
        for code, expected in testcases:
            assert hasattr(code, '__class__')
            assert not hasattr(code,'__dict__')
            for key, value in expected.items():
                assert getattr(code, key) == value

    def test_co_names(self):
        src = '''if 1:
        def foo():
            pass

        g = 3

        def f(x, y):
            z = x + y
            foo(g)
'''
        d = {}
        exec src in d

        assert list(sorted(d['f'].func_code.co_names)) == ['foo', 'g']

    def test_code(self):
        import sys
        try: 
            import new
        except ImportError: 
            skip("could not import new module")
        codestr = "global c\na = 1\nb = 2\nc = a + b\n"
        ccode = compile(codestr, '<string>', 'exec')
        co = new.code(ccode.co_argcount,
                      ccode.co_nlocals,
                      ccode.co_stacksize,
                      ccode.co_flags,
                      ccode.co_code,
                      ccode.co_consts,
                      ccode.co_names,
                      ccode.co_varnames,
                      ccode.co_filename,
                      ccode.co_name,
                      ccode.co_firstlineno,
                      ccode.co_lnotab,
                      ccode.co_freevars,
                      ccode.co_cellvars)
        d = {}
        exec co in d
        assert d['c'] == 3
        # test backwards-compatibility version with no freevars or cellvars
        co = new.code(ccode.co_argcount,
                      ccode.co_nlocals,
                      ccode.co_stacksize,
                      ccode.co_flags,
                      ccode.co_code,
                      ccode.co_consts,
                      ccode.co_names,
                      ccode.co_varnames,
                      ccode.co_filename,
                      ccode.co_name,
                      ccode.co_firstlineno,
                      ccode.co_lnotab)
        d = {}
        exec co in d
        assert d['c'] == 3
        def f(x):
            y = 1
        ccode = f.func_code
        raises(ValueError, new.code,
              -ccode.co_argcount,
              ccode.co_nlocals,
              ccode.co_stacksize,
              ccode.co_flags,
              ccode.co_code,
              ccode.co_consts,
              ccode.co_names,
              ccode.co_varnames,
              ccode.co_filename,
              ccode.co_name,
              ccode.co_firstlineno,
              ccode.co_lnotab)
        raises(ValueError, new.code,
              ccode.co_argcount,
              -ccode.co_nlocals,
              ccode.co_stacksize,
              ccode.co_flags,
              ccode.co_code,
              ccode.co_consts,
              ccode.co_names,
              ccode.co_varnames,
              ccode.co_filename,
              ccode.co_name,
              ccode.co_firstlineno,
              ccode.co_lnotab)

    def test_hash(self):
        d1 = {}
        exec "def f(): pass" in d1
        d2 = {}
        exec "def f(): pass" in d2
        assert d1['f'].func_code == d2['f'].func_code
        assert hash(d1['f'].func_code) == hash(d2['f'].func_code)

    def test_repr(self):
        def f():
            xxx
        res = repr(f.func_code)
        expected = ["<code object f",
                    self.file,
                    'line']
        for i in expected:
            assert i in res

    def test_code_extra(self):
        exec """if 1:
        def f():
            "docstring"
            'stuff'
            56
"""

        # check for new flag, CO_NOFREE
        assert f.func_code.co_flags & 0x40

        exec """if 1:
        def f(x):
            def g(y):
                return x+y
            return g
"""

        # CO_NESTED
        assert f(4).func_code.co_flags & 0x10
        assert f.func_code.co_flags & 0x10 == 0
