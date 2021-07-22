def test_special_methods():
    class OldStyle:
        pass
    for base in (object, OldStyle,):
        class A(base):
            def __lt__(self, other):
                return "lt"
            def __imul__(self, other):
                return "imul"
            def __sub__(self, other):
                return "sub"
            def __rsub__(self, other):
                return "rsub"
            def __pow__(self, other):
                return "pow"
            def __rpow__(self, other):
                return "rpow"
            def __neg__(self):
                return "neg"
        a = A()
        assert (a < 5) == "lt"
        assert (object() > a) == "lt"
        a1 = a
        a1 *= 4
        assert a1 == "imul"
        assert a - 2 == "sub"
        assert a - object() == "sub"
        assert 2 - a == "rsub"
        assert object() - a == "rsub"
        assert a ** 2 == "pow"
        assert a ** object() == "pow"
        assert 2 ** a == "rpow"
        assert object() ** a == "rpow"
        assert -a == "neg"

        class B(A):
            def __lt__(self, other):
                return "B's lt"
            def __imul__(self, other):
                return "B's imul"
            def __sub__(self, other):
                return "B's sub"
            def __rsub__(self, other):
                return "B's rsub"
            def __pow__(self, other):
                return "B's pow"
            def __rpow__(self, other):
                return "B's rpow"
            def __neg__(self):
                return "B's neg"

        b = B()
        assert (a < b) == "lt"
        assert (b > a) == "lt"
        b1 = b
        b1 *= a
        assert b1 == "B's imul"
        a1 = a
        a1 *= b
        assert a1 == "imul"

        if base is object:
            assert a - b == "B's rsub"
        else:
            assert a - b == "sub"
        assert b - a == "B's sub"
        assert b - b == "B's sub"
        if base is object:
            assert a ** b == "B's rpow"
        else:
            assert a ** b == "pow"
        assert b ** a == "B's pow"
        assert b ** b == "B's pow"
        assert -b == "B's neg"

        class C(B):
            pass
        c = C()
        assert c - 1 == "B's sub"
        assert 1 - c == "B's rsub"
        assert c - b == "B's sub"
        assert b - c == "B's sub"

        assert c ** 1 == "B's pow"
        assert 1 ** c == "B's rpow"
        assert c ** b == "B's pow"
        assert b ** c == "B's pow"

def test_getslice():
    class Sq(object):
        def __getslice__(self, start, stop):
            return (start, stop)
        def __getitem__(self, key):
            return "booh"
        def __len__(self):
            return 100

    sq = Sq()

    assert sq[1:3] == (1,3)
    slice_min, slice_max = sq[:]
    assert slice_min == 0
    assert slice_max >= 2**31-1
    assert sq[1:] == (1, slice_max)
    assert sq[:3] == (0, 3)
    assert sq[:] == (0, slice_max)
    # negative indices
    assert sq[-1:3] == (99, 3)
    assert sq[1:-3] == (1, 97)
    assert sq[-1:-3] == (99, 97)
    # extended slice syntax always uses __getitem__()
    assert sq[::] == "booh"

def test_setslice():
    class Sq(object):
        def __setslice__(self, start, stop, sequence):
            ops.append((start, stop, sequence))
        def __setitem__(self, key, value):
            raise AssertionError(key)
        def __len__(self):
            return 100

    sq = Sq()
    ops = []
    sq[-5:3] = 'hello'
    sq[12:] = 'world'
    sq[:-1] = 'spam'
    sq[:] = 'egg'
    slice_max = ops[-1][1]
    assert slice_max >= 2**31-1

    assert ops == [
        (95, 3,          'hello'),
        (12, slice_max, 'world'),
        (0,  99,         'spam'),
        (0,  slice_max, 'egg'),
        ]

def test_delslice():
    class Sq(object):
        def __delslice__(self, start, stop):
            ops.append((start, stop))
        def __delitem__(self, key):
            raise AssertionError(key)
        def __len__(self):
            return 100

    sq = Sq()
    ops = []
    del sq[5:-3]
    del sq[-12:]
    del sq[:1]
    del sq[:]
    slice_max = ops[-1][1]
    assert slice_max >= 2**31-1

    assert ops == [
        (5,   97),
        (88,  slice_max),
        (0,   1),
        (0,   slice_max),
        ]

def test_getslice_nolength():
    class Sq(object):
        def __getslice__(self, start, stop):
            return (start, stop)
        def __getitem__(self, key):
            return "booh"

    sq = Sq()

    assert sq[1:3] == (1,3)
    slice_min, slice_max = sq[:]
    assert slice_min == 0
    assert slice_max >= 2**31-1
    assert sq[1:] == (1, slice_max)
    assert sq[:3] == (0, 3)
    assert sq[:] == (0, slice_max)
    # negative indices, but no __len__
    assert sq[-1:3] == (-1, 3)
    assert sq[1:-3] == (1, -3)
    assert sq[-1:-3] == (-1, -3)
    # extended slice syntax always uses __getitem__()
    assert sq[::] == "booh"

def test_ipow():
    x = 2
    x **= 5
    assert x == 32

def test_typechecks():
    class myint(int):
        pass
    class X(object):
        def __nonzero__(self):
            return myint(1)
    raises(TypeError, "not X()")

def test_string_subclass():
    class S(str):
        def __hash__(self):
            return 123
    s = S("abc")
    setattr(s, s, s)
    assert len(s.__dict__) == 1
    # this behavior changed in 2.4
    #assert type(s.__dict__.keys()[0]) is str   # don't store S keys
    #assert s.abc is s
    assert getattr(s,s) is s

def test_notimplemented():
    #import types
    import operator

    def specialmethod(self, other):
        return NotImplemented

    def check(expr, x, y, operator=operator):
        raises(TypeError, expr)

    for metaclass in [type]:   # [type, types.ClassType]:
        for name, expr, iexpr in [
                ('__add__',      'x + y',                   'x += y'),
                ('__sub__',      'x - y',                   'x -= y'),
                ('__mul__',      'x * y',                   'x *= y'),
                ('__truediv__',  'operator.truediv(x, y)',  None),
                ('__floordiv__', 'operator.floordiv(x, y)', None),
                ('__div__',      'x / y',                   'x /= y'),
                ('__mod__',      'x % y',                   'x %= y'),
                ('__divmod__',   'divmod(x, y)',            None),
                ('__pow__',      'x ** y',                  'x **= y'),
                ('__lshift__',   'x << y',                  'x <<= y'),
                ('__rshift__',   'x >> y',                  'x >>= y'),
                ('__and__',      'x & y',                   'x &= y'),
                ('__or__',       'x | y',                   'x |= y'),
                ('__xor__',      'x ^ y',                   'x ^= y'),
                ('__coerce__',   'coerce(x, y)',            None)]:
            if name == '__coerce__':
                rname = name
            else:
                rname = '__r' + name[2:]
            A = metaclass('A', (), {name: specialmethod})
            B = metaclass('B', (), {rname: specialmethod})
            a = A()
            b = B()
            check(expr, a, a)
            check(expr, a, b)
            check(expr, b, a)
            check(expr, b, b)
            check(expr, a, 5)
            check(expr, 5, b)
            if iexpr:
                check(iexpr, a, a)
                check(iexpr, a, b)
                check(iexpr, b, a)
                check(iexpr, b, b)
                check(iexpr, a, 5)
                iname = '__i' + name[2:]
                C = metaclass('C', (), {iname: specialmethod})
                c = C()
                check(iexpr, c, a)
                check(iexpr, c, b)
                check(iexpr, c, 5)

def test_string_results():
    class A(object):
        def __str__(self):
            return answer * 2
        def __repr__(self):
            return answer * 3
        def __hex__(self):
            return answer * 4
        def __oct__(self):
            return answer * 5

    for operate, n in [(str, 2), (repr, 3), (hex, 4), (oct, 5)]:
        answer = "hello"
        assert operate(A()) == "hello" * n
        if operate not in (hex, oct):
            answer = u"world"
            assert operate(A()) == "world" * n
        assert type(operate(A())) is str
        answer = 42
        excinfo = raises(TypeError, operate, A())
        assert "returned non-string (type 'int')" in str(excinfo.value)

def test_missing_getattribute():
    class X(object):
        pass

    class Y(X):
        class __metaclass__(type):
            def mro(cls):
                return [cls, X]

    x = X()
    x.__class__ = Y
    raises(AttributeError, getattr, x, 'a')

def test_silly_but_consistent_order():
    # incomparable objects sort by type name :-/
    class A(object):
        pass
    class zz(object):
        pass
    assert A() < zz()
    assert zz() > A()
    # if in doubt, CPython sorts numbers before non-numbers
    assert 0 < ()
    assert 0L < ()
    assert 0.0 < ()
    assert 0j < ()
    assert 0 < []
    assert 0L < []
    assert 0.0 < []
    assert 0j < []
    assert 0 < A()
    assert 0L < A()
    assert 0.0 < A()
    assert 0j < A()
    assert 0 < zz()
    assert 0L < zz()
    assert 0.0 < zz()
    assert 0j < zz()
    # what if the type name is the same... whatever, but
    # be consistent
    a1 = A()
    a2 = A()
    class A(object): pass
    a3 = A()
    a4 = A()
    assert (a1 < a3) == (a1 < a4) == (a2 < a3) == (a2 < a4)

def test_setattrweakref():
    skip("fails, works in cpython")
    # The issue is that in CPython, none of the built-in types have
    # a __weakref__ descriptor, even if their instances are weakrefable.
    # Should we emulate this?
    class P(object):
        pass

    setattr(P, "__weakref__", 0)

def test_subclass_addition():
    # the __radd__ is never called (compare with the next test)
    l = []
    class A(object):
        def __add__(self, other):
            l.append(self.__class__)
            l.append(other.__class__)
            return 123
        def __radd__(self, other):
            # should never be called!
            return 456
    class B(A):
        pass
    res1 = A() + B()
    res2 = B() + A()
    assert res1 == res2 == 123
    assert l == [A, B, B, A]

def test_subclass_comparison():
    # the __eq__ *is* called with reversed arguments
    l = []
    class A(object):
        def __eq__(self, other):
            l.append(self.__class__)
            l.append(other.__class__)
            return False

        def __lt__(self, other):
            l.append(self.__class__)
            l.append(other.__class__)
            return False

    class B(A):
        pass

    A() == B()
    A() < B()
    B() < A()
    assert l == [B, A, A, B, B, A]

def test_subclass_comparison_more():
    # similarly, __gt__(b,a) is called instead of __lt__(a,b)
    l = []
    class A(object):
        def __lt__(self, other):
            l.append(self.__class__)
            l.append(other.__class__)
            return '<'
        def __gt__(self, other):
            l.append(self.__class__)
            l.append(other.__class__)
            return '>'
    class B(A):
        pass
    res1 = A() < B()
    res2 = B() < A()
    assert res1 == '>' and res2 == '<'
    assert l == [B, A, B, A]

def test_rich_comparison():
    # Old-style
    class A:
        def __init__(self, a):
            self.a = a
        def __eq__(self, other):
            return self.a == other.a
    class B:
        def __init__(self, a):
            self.a = a
    # New-style
    class C(object):
        def __init__(self, a):
            self.a = a
        def __eq__(self, other):
            return self.a == other.a
    class D(object):
        def __init__(self, a):
            self.a = a

    assert A(1) == B(1)
    assert B(1) == A(1)
    assert A(1) == C(1)
    assert C(1) == A(1)
    assert A(1) == D(1)
    assert D(1) == A(1)
    assert C(1) == D(1)
    assert D(1) == C(1)
    assert not(A(1) == B(2))
    assert not(B(1) == A(2))
    assert not(A(1) == C(2))
    assert not(C(1) == A(2))
    assert not(A(1) == D(2))
    assert not(D(1) == A(2))
    assert not(C(1) == D(2))
    assert not(D(1) == C(2))

def test_partial_ordering():
    class A(object):
        def __lt__(self, other):
            return self
    a1 = A()
    a2 = A()
    assert (a1 < a2) is a1
    assert (a1 > a2) is a2

def test_eq_order():
    class A(object):
        def __eq__(self, other): return self.__class__.__name__+':A.eq'
        def __ne__(self, other): return self.__class__.__name__+':A.ne'
        def __lt__(self, other): return self.__class__.__name__+':A.lt'
        def __le__(self, other): return self.__class__.__name__+':A.le'
        def __gt__(self, other): return self.__class__.__name__+':A.gt'
        def __ge__(self, other): return self.__class__.__name__+':A.ge'
    class B(object):
        def __eq__(self, other): return self.__class__.__name__+':B.eq'
        def __ne__(self, other): return self.__class__.__name__+':B.ne'
        def __lt__(self, other): return self.__class__.__name__+':B.lt'
        def __le__(self, other): return self.__class__.__name__+':B.le'
        def __gt__(self, other): return self.__class__.__name__+':B.gt'
        def __ge__(self, other): return self.__class__.__name__+':B.ge'
    #
    assert (A() == B()) == 'A:A.eq'
    assert (A() != B()) == 'A:A.ne'
    assert (A() <  B()) == 'A:A.lt'
    assert (A() <= B()) == 'A:A.le'
    assert (A() >  B()) == 'A:A.gt'
    assert (A() >= B()) == 'A:A.ge'
    #
    assert (B() == A()) == 'B:B.eq'
    assert (B() != A()) == 'B:B.ne'
    assert (B() <  A()) == 'B:B.lt'
    assert (B() <= A()) == 'B:B.le'
    assert (B() >  A()) == 'B:B.gt'
    assert (B() >= A()) == 'B:B.ge'
    #
    class C(A):
        def __eq__(self, other): return self.__class__.__name__+':C.eq'
        def __ne__(self, other): return self.__class__.__name__+':C.ne'
        def __lt__(self, other): return self.__class__.__name__+':C.lt'
        def __le__(self, other): return self.__class__.__name__+':C.le'
        def __gt__(self, other): return self.__class__.__name__+':C.gt'
        def __ge__(self, other): return self.__class__.__name__+':C.ge'
    #
    assert (A() == C()) == 'C:C.eq'
    assert (A() != C()) == 'C:C.ne'
    assert (A() <  C()) == 'C:C.gt'
    assert (A() <= C()) == 'C:C.ge'
    assert (A() >  C()) == 'C:C.lt'
    assert (A() >= C()) == 'C:C.le'
    #
    assert (C() == A()) == 'C:C.eq'
    assert (C() != A()) == 'C:C.ne'
    assert (C() <  A()) == 'C:C.lt'
    assert (C() <= A()) == 'C:C.le'
    assert (C() >  A()) == 'C:C.gt'
    assert (C() >= A()) == 'C:C.ge'
    #
    class D(A):
        pass
    #
    assert (A() == D()) == 'D:A.eq'
    assert (A() != D()) == 'D:A.ne'
    assert (A() <  D()) == 'D:A.gt'
    assert (A() <= D()) == 'D:A.ge'
    assert (A() >  D()) == 'D:A.lt'
    assert (A() >= D()) == 'D:A.le'
    #
    assert (D() == A()) == 'D:A.eq'
    assert (D() != A()) == 'D:A.ne'
    assert (D() <  A()) == 'D:A.lt'
    assert (D() <= A()) == 'D:A.le'
    assert (D() >  A()) == 'D:A.gt'
    assert (D() >= A()) == 'D:A.ge'

def test_addition():
    # Old-style
    class A:
        def __init__(self, a):
            self.a = a
        def __add__(self, other):
            return self.a + other.a
        __radd__ = __add__
    class B:
        def __init__(self, a):
            self.a = a
    # New-style
    class C(object):
        def __init__(self, a):
            self.a = a
        def __add__(self, other):
            return self.a + other.a
        __radd__ = __add__
    class D(object):
        def __init__(self, a):
            self.a = a

    assert A(1) + B(2) == 3
    assert B(1) + A(2) == 3
    assert A(1) + C(2) == 3
    assert C(1) + A(2) == 3
    assert A(1) + D(2) == 3
    assert D(1) + A(2) == 3
    assert C(1) + D(2) == 3
    assert D(1) + C(2) == 3

def test_mod_failure():
    try:
        [] % 3
    except TypeError as e:
        assert '%' in str(e)
    else:
        assert False, "did not raise"

def test_invalid_iterator():
    class x(object):
        def __iter__(self):
            return self
    raises(TypeError, iter, x())

def test_attribute_error():
    class classmethodonly(classmethod):
        def __get__(self, instance, type):
            if instance is not None:
                raise AttributeError("Must be called on a class, not an instance.")
            return super(classmethodonly, self).__get__(instance, type)

    class A(object):
        @classmethodonly
        def a(cls):
            return 3

    raises(AttributeError, lambda: A().a)

def test_delete_descriptor():
    class Prop(object):
        def __get__(self, obj, cls):
            return 42
        def __delete__(self, obj):
            obj.deleted = True
    class C(object):
        x = Prop()
    obj = C()
    del obj.x
    assert obj.deleted

def test_non_callable():
    meth = classmethod(1).__get__(1)
    raises(TypeError, meth)

def test_isinstance_and_issubclass():
    class Meta(type):
        def __instancecheck__(cls, instance):
            if cls is A:
                return True
            return False
        def __subclasscheck__(cls, sub):
            if cls is B:
                return True
            return False
    class A:
        __metaclass__ = Meta
    class B(A):
        pass
    a = A()
    b = B()
    assert isinstance(a, A) # "shortcut" does not go through metaclass
    assert not isinstance(a, B)
    assert isinstance(b, A)
    assert isinstance(b, B) # "shortcut" does not go through metaclass
    assert isinstance(4, A)
    assert not issubclass(A, A)
    assert not issubclass(B, A)
    assert issubclass(A, B)
    assert issubclass(B, B)
    assert issubclass(23, B)

def test_issubclass_and_method():
    class Meta(type):
        def __subclasscheck__(cls, sub):
            if sub is Dict:
                return True
    class A:
        __metaclass__ = Meta
        def method(self):
            return 42
    class Dict:
        method = A.method
    assert Dict().method() == 42

def test_truth_of_long():
    class X(object):
        def __len__(self): return 1L
        __nonzero__ = __len__
    raises(TypeError, bool, X())  # must return bool or int, not long
    del X.__nonzero__
    assert X()

def test_len_overflow():
    import sys
    class X(object):
        def __len__(self):
            return sys.maxsize + 1
    raises(OverflowError, len, X())
    raises(OverflowError, bool, X())

def test_len_underflow():
    import sys
    class X(object):
        def __len__(self):
            return -1
    raises(ValueError, len, X())
    raises(ValueError, bool, X())
    class Y(object):
        def __len__(self):
            return -1L
    raises(ValueError, len, Y())
    raises(ValueError, bool, Y())

def test_len_custom__int__():
    class X(object):
        def __init__(self, x):
            self.x = x
        def __len__(self):
            return self.x
        def __int__(self):
            return self.x

    l = len(X(3.0))
    assert l == 3 and type(l) is int
    assert X(3.0)
    assert not X(0.0)
    l = len(X(X(2)))
    assert l == 2 and type(l) is int
    assert X(X(2))
    assert not X(X(0))

def test_bool___contains__():
    class X(object):
        def __contains__(self, item):
            if item == 'foo':
                return 42
            else:
                return 'hello world'
    x = X()
    res = 'foo' in x
    assert res is True
    res = 'bar' in x
    assert res is True
    #
    class MyError(Exception):
        pass
    class CannotConvertToBool(object):
        def __nonzero__(self):
            raise MyError
    class X(object):
        def __contains__(self, item):
            return CannotConvertToBool()
    x = X()
    raises(MyError, "'foo' in x")

def test___cmp___fake_int():
    class MyInt(object):
        def __init__(self, x):
            self.x = x
        def __int__(self):
            return self.x
    class X(object):
        def __cmp__(self, other):
            return MyInt(0)

    assert X() == 'hello'

def test_sequence_rmul_overrides():
    class oops(object):
        def __rmul__(self, other):
            return 42
        def __index__(self):
            return 3
    assert '2' * oops() == 42
    assert [2] * oops() == 42
    assert (2,) * oops() == 42
    assert u'2' * oops() == 42
    assert bytearray('2') * oops() == 42
    assert 1000 * oops() == 42
    assert '2'.__mul__(oops()) == '222'
    x = '2'
    x *= oops()
    assert x == 42
    x = [2]
    x *= oops()
    assert x == 42

def test_sequence_rmul_overrides_oldstyle():
    class oops:
        def __rmul__(self, other):
            return 42
        def __index__(self):
            return 3
    assert '2' * oops() == 42
    assert [2] * oops() == 42
    assert (2,) * oops() == 42
    assert u'2' * oops() == 42
    assert bytearray('2') * oops() == 42
    assert 1000 * oops() == 42
    assert '2'.__mul__(oops()) == '222'

def test_sequence_radd_overrides():
    class A1(list):
        pass
    class A2(list):
        def __radd__(self, other):
            return 42
    assert [2] + A1([3]) == [2, 3]
    assert type([2] + A1([3])) is list
    assert [2] + A2([3]) == 42
    x = "2"
    x += A2([3])
    assert x == 42
    x = [2]
    x += A2([3])
    assert x == 42

def test_data_descriptor_without_delete():
    class D(object):
        def __set__(self, x, y):
            pass
    class A(object):
        d = D()
    raises(AttributeError, "del A().d")

def test_data_descriptor_without_set():
    class D(object):
        def __delete__(self, x):
            pass
    class A(object):
        d = D()
    raises(AttributeError, "A().d = 5")

def test_not_subscriptable_error_gives_keys():
    d = {'key1': {'key2': {'key3': None}}}
    excinfo = raises(TypeError, "d['key1']['key2']['key3']['key4']['key5']")
    assert "key4" in str(excinfo.value)
