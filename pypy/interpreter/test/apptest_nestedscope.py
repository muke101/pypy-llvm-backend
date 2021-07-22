from pytest import raises

def test_nested_scope():
    x = 42
    def f(): return x
    assert f() == 42

def test_nested_scope2():
    x = 42
    y = 3
    def f(): return x
    assert f() == 42

def test_nested_scope3():
    x = 42
    def f():
        def g():
            return x
        return g
    assert f()() == 42

def test_nested_scope4():
    def f():
        x = 3
        def g():
            return x
        a = g()
        x = 4
        b = g()
        return (a, b)
    assert f() == (3, 4)

def test_nested_scope_locals():
    def f():
        x = 3
        def g():
            i = x
            return locals()
        return g()
    d = f()
    assert d == {'i':3, 'x':3}

def test_deeply_nested_scope_locals():
    def f():
        x = 3
        def g():
            def h():
                i = x
                return locals()
            return locals(), h()
        return g()
    outer_locals, inner_locals = f()
    assert inner_locals == {'i':3, 'x':3}
    keys = outer_locals.keys()
    keys.sort()
    assert keys == ['h', 'x']

def test_lambda_in_genexpr():
    assert eval('map(apply, (lambda: t for t in range(10)))') == range(10)

def test_cell_repr():
    import re
    from repr import repr as r # Don't shadow builtin repr

    def get_cell():
        x = 42
        def inner():
            return x
        return inner
    x = get_cell().__closure__[0]
    assert re.match(r'<cell at 0x[0-9A-Fa-f]+: int object at 0x[0-9A-Fa-f]+>', repr(x))
    assert re.match(r'<cell at.*\.\.\..*>', r(x))

    def get_cell():
        if False:
            x = 42
        def inner():
            return x
        return inner
    x = get_cell().__closure__[0]
    assert re.match(r'<cell at 0x[0-9A-Fa-f]+: empty>', repr(x))

def test_cell_contents():
    def f(x):
        def f(y):
            return x + y
        return f

    g = f(10)
    assert g.func_closure[0].cell_contents == 10

def test_empty_cell_contents():

    def f():
        def f(y):
            return x + y
        return f
        x = 1

    g = f()
    with raises(ValueError):
        g.func_closure[0].cell_contents

def test_compare_cells():
    def f(n):
        if n:
            x = 42
        def f(y):
            return x + y
        return f

    g0 = f(0).func_closure[0]
    g1 = f(1).func_closure[0]
    assert cmp(g0, g1) == -1

def test_leaking_class_locals():
    def f(x):
        class X:
            x = 12
            def f(self):
                return x
            locals()
        return X
    assert f(1).x == 12

def test_nested_scope_locals_mutating_cellvars():
    def f():
        x = 12
        def m():
            locals()
            x
            locals()
            return x
        return m
    assert f()() == 12
