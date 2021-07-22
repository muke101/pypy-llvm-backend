import py
from pypy.interpreter.error import OperationError
from pypy.interpreter.module import Module

class TestModule: 
    def test_name(self, space):
        w = space.wrap
        m = Module(space, space.wrap('m'))
        w_m = w(m)
        assert space.eq_w(space.getattr(w_m, w('__name__')), w('m'))

    def test_attr(self, space):
        w = space.wrap
        w_m = w(Module(space, space.wrap('m')))
        self.space.setattr(w_m, w('x'), w(15))
        assert space.eq_w(space.getattr(w_m, w('x')), w(15))
        space.delattr(w_m, w('x'))
        space.raises_w(space.w_AttributeError,
                       space.delattr, w_m, w('x'))

    def test___file__(self, space):
        w = space.wrap
        m = Module(space, space.wrap('m'))
        py.test.raises(OperationError, space.getattr, w(m), w('__file__'))
        m._cleanup_()
        py.test.raises(OperationError, space.getattr, w(m), w('__file__'))
        space.setattr(w(m), w('__file__'), w('m.py'))
        space.getattr(w(m), w('__file__'))   # does not raise
        m._cleanup_()
        py.test.raises(OperationError, space.getattr, w(m), w('__file__'))


class AppTest_ModuleObject: 
    def test_attr(self):
        m = __import__('__builtin__')
        m.x = 15
        assert m.x == 15
        assert getattr(m, 'x') == 15
        setattr(m, 'x', 23)
        assert m.x == 23
        assert getattr(m, 'x') == 23
        del m.x
        raises(AttributeError, getattr, m, 'x')
        m.x = 15
        delattr(m, 'x')
        raises(AttributeError, getattr, m, 'x')
        raises(AttributeError, delattr, m, 'x')
        raises(TypeError, setattr, m, '__dict__', {})

    def test_docstring(self):
        import sys
        foo = type(sys)('foo')
        assert foo.__name__ == 'foo'
        assert foo.__doc__ is None
        bar = type(sys)('bar','docstring')
        assert bar.__doc__ == 'docstring'

    def test___file__(self):
        import sys
        assert not hasattr(sys, '__file__')

    def test_repr(self):
        import sys
        if not hasattr(sys, "pypy_objspaceclass"):
            skip("need PyPy for _pypy_interact")
        r = repr(sys)
        assert r == "<module 'sys' (built-in)>"
        
        import _pypy_interact # known to be in lib_pypy
        r = repr(_pypy_interact)
        assert (r.startswith("<module '_pypy_interact' from ") and
                ('lib_pypy/_pypy_interact.py' in r or
                 r'lib_pypy\\_pypy_interact.py' in r.lower()) and
                r.endswith('>'))
        nofile = type(_pypy_interact)('nofile', 'foo')
        assert repr(nofile) == "<module 'nofile' from ?>"

        m = type(_pypy_interact).__new__(type(_pypy_interact))
        assert repr(m).startswith("<module '?'")

    def test_package(self):
        import sys
        import os

        assert sys.__package__ is None
        assert os.__package__ is None
        assert not hasattr(type(sys)('foo'), '__package__')
