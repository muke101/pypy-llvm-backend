# encoding: utf-8
import py
import sys
from pypy.interpreter.error import OperationError
from pypy.objspace.std import intobject as iobj
from rpython.rlib.rarithmetic import r_uint, is_valid_int, intmask
from rpython.rlib.rbigint import rbigint


class TestW_IntObject:
    def _longshiftresult(self, x):
        """ calculate an overflowing shift """
        n = 1
        l = long(x)
        while 1:
            ires = x << n
            lres = l << n
            if not is_valid_int(ires) or lres != ires:
                return n
            n += 1

    def test_int_w(self):
        assert self.space.int_w(self.space.wrap(42)) == 42

    def test_uint_w(self):
        space = self.space
        assert space.uint_w(space.wrap(42)) == 42
        assert isinstance(space.uint_w(space.wrap(42)), r_uint)
        space.raises_w(space.w_ValueError, space.uint_w, space.wrap(-1))

    def test_bigint_w(self):
        space = self.space
        assert isinstance(space.bigint_w(space.wrap(42)), rbigint)
        assert space.bigint_w(space.wrap(42)).eq(rbigint.fromint(42))

    def test_repr(self):
        x = 1
        f1 = iobj.W_IntObject(x)
        result = f1.descr_repr(self.space)
        assert self.space.unwrap(result) == repr(x)

    def test_str(self):
        x = 12345
        f1 = iobj.W_IntObject(x)
        result = f1.descr_str(self.space)
        assert self.space.unwrap(result) == str(x)

    def test_hash(self):
        x = 42
        f1 = iobj.W_IntObject(x)
        result = f1.descr_hash(self.space)
        assert result.intval == hash(x)

    def test_compare(self):
        import operator
        optab = ['lt', 'le', 'eq', 'ne', 'gt', 'ge']
        for x in (-10, -1, 0, 1, 2, 1000, sys.maxint):
            for y in (-sys.maxint-1, -11, -9, -2, 0, 1, 3, 1111, sys.maxint):
                for op in optab:
                    wx = iobj.W_IntObject(x)
                    wy = iobj.W_IntObject(y)
                    res = getattr(operator, op)(x, y)
                    method = getattr(wx, 'descr_%s' % op)
                    myres = method(self.space, wy)
                    assert self.space.unwrap(myres) == res

    def test_add(self):
        space = self.space
        x = 1
        y = 2
        f1 = iobj.W_IntObject(x)
        f2 = iobj.W_IntObject(y)
        result = f1.descr_add(space, f2)
        assert result.intval == x+y
        x = sys.maxint
        y = 1
        f1 = iobj.W_IntObject(x)
        f2 = iobj.W_IntObject(y)
        v = f1.descr_add(space, f2)
        assert space.isinstance_w(v, space.w_long)
        assert space.bigint_w(v).eq(rbigint.fromlong(x + y))

    def test_sub(self):
        space = self.space
        x = 1
        y = 2
        f1 = iobj.W_IntObject(x)
        f2 = iobj.W_IntObject(y)
        result = f1.descr_sub(space, f2)
        assert result.intval == x-y
        x = sys.maxint
        y = -1
        f1 = iobj.W_IntObject(x)
        f2 = iobj.W_IntObject(y)
        v = f1.descr_sub(space, f2)
        assert space.isinstance_w(v, space.w_long)
        assert space.bigint_w(v).eq(rbigint.fromlong(sys.maxint - -1))

    def test_mul(self):
        space = self.space
        x = 2
        y = 3
        f1 = iobj.W_IntObject(x)
        f2 = iobj.W_IntObject(y)
        result = f1.descr_mul(space, f2)
        assert result.intval == x*y
        x = -sys.maxint-1
        y = -1
        f1 = iobj.W_IntObject(x)
        f2 = iobj.W_IntObject(y)
        v = f1.descr_mul(space, f2)
        assert space.isinstance_w(v, space.w_long)
        assert space.bigint_w(v).eq(rbigint.fromlong(x * y))

    def test_div(self):
        space = self.space
        for i in range(10):
            res = i//3
            f1 = iobj.W_IntObject(i)
            f2 = iobj.W_IntObject(3)
            result = f1.descr_div(space, f2)
            assert result.intval == res
        x = -sys.maxint-1
        y = -1
        f1 = iobj.W_IntObject(x)
        f2 = iobj.W_IntObject(y)
        v = f1.descr_div(space, f2)
        assert space.isinstance_w(v, space.w_long)
        assert space.bigint_w(v).eq(rbigint.fromlong(x / y))

    def test_mod(self):
        x = 1
        y = 2
        f1 = iobj.W_IntObject(x)
        f2 = iobj.W_IntObject(y)
        v = f1.descr_mod(self.space, f2)
        assert v.intval == x % y
        # not that mod cannot overflow

    def test_divmod(self):
        space = self.space
        x = 1
        y = 2
        f1 = iobj.W_IntObject(x)
        f2 = iobj.W_IntObject(y)
        ret = f1.descr_divmod(space, f2)
        v, w = space.unwrap(ret)
        assert (v, w) == divmod(x, y)
        x = -sys.maxint-1
        y = -1
        f1 = iobj.W_IntObject(x)
        f2 = iobj.W_IntObject(y)
        v = f1.descr_divmod(space, f2)
        w_q, w_r = space.fixedview(v, 2)
        assert space.isinstance_w(w_q, space.w_long)
        expected = divmod(x, y)
        assert space.bigint_w(w_q).eq(rbigint.fromlong(expected[0]))
        # no overflow possible
        assert space.unwrap(w_r) == expected[1]

    def test_pow_iii(self):
        x = 10
        y = 2
        z = 13
        f1 = iobj.W_IntObject(x)
        f2 = iobj.W_IntObject(y)
        f3 = iobj.W_IntObject(z)
        v = f1.descr_pow(self.space, f2, f3)
        assert v.intval == pow(x, y, z)
        f1, f2, f3 = [iobj.W_IntObject(i) for i in (10, -1, 42)]
        self.space.raises_w(self.space.w_TypeError,
                            f1.descr_pow, self.space, f2, f3)
        f1, f2, f3 = [iobj.W_IntObject(i) for i in (10, 5, 0)]
        self.space.raises_w(self.space.w_ValueError,
                            f1.descr_pow, self.space, f2, f3)

    def test_pow_iin(self):
        space = self.space
        x = 10
        y = 2
        f1 = iobj.W_IntObject(x)
        f2 = iobj.W_IntObject(y)
        v = f1.descr_pow(space, f2, space.w_None)
        assert v.intval == x ** y
        f1, f2 = [iobj.W_IntObject(i) for i in (10, 20)]
        v = f1.descr_pow(space, f2, space.w_None)
        assert space.isinstance_w(v, space.w_long)
        assert space.bigint_w(v).eq(rbigint.fromlong(pow(10, 20)))

    try:
        from hypothesis import given, strategies, example
    except ImportError:
        pass
    else:
        @given(
           a=strategies.integers(min_value=-sys.maxint-1, max_value=sys.maxint),
           b=strategies.integers(min_value=-sys.maxint-1, max_value=sys.maxint),
           c=strategies.integers(min_value=-sys.maxint-1, max_value=sys.maxint))
        @example(0, 0, -sys.maxint-1)
        @example(0, 1, -sys.maxint-1)
        @example(1, 0, -sys.maxint-1)
        def test_hypot_pow(self, a, b, c):
            if c == 0:
                return
            #
            # "pow(a, b, c)": if b < 0, should get an app-level TypeError.
            # Otherwise, should always work except if c == -maxint-1
            if b < 0:
                expected = TypeError
            elif b > 0 and c == -sys.maxint-1:
                expected = OverflowError
            else:
                expected = pow(a, b, c)

            try:
                result = iobj._pow(self.space, a, b, c)
            except OperationError as e:
                assert ('TypeError: pow() 2nd argument cannot be negative '
                        'when 3rd argument specified' == e.errorstr(self.space))
                result = TypeError
            except OverflowError:
                result = OverflowError
            assert result == expected

        @given(
           a=strategies.integers(min_value=-sys.maxint-1, max_value=sys.maxint),
           b=strategies.integers(min_value=-sys.maxint-1, max_value=sys.maxint))
        def test_hypot_pow_nomod(self, a, b):
            # "a ** b": detect overflows and ValueErrors
            if b < 0:
                expected = ValueError
            elif b > 128 and not (-1 <= a <= 1):
                expected = OverflowError
            else:
                expected = a ** b
                if expected != intmask(expected):
                    expected = OverflowError

            try:
                result = iobj._pow(self.space, a, b, 0)
            except ValueError:
                result = ValueError
            except OverflowError:
                result = OverflowError
            assert result == expected

    def test_neg(self):
        space = self.space
        x = 42
        f1 = iobj.W_IntObject(x)
        v = f1.descr_neg(space)
        assert v.intval == -x
        x = -sys.maxint-1
        f1 = iobj.W_IntObject(x)
        v = f1.descr_neg(space)
        assert space.isinstance_w(v, space.w_long)
        assert space.bigint_w(v).eq(rbigint.fromlong(-x))

    def test_pos(self):
        x = 42
        f1 = iobj.W_IntObject(x)
        v = f1.descr_pos(self.space)
        assert v.intval == +x
        x = -42
        f1 = iobj.W_IntObject(x)
        v = f1.descr_pos(self.space)
        assert v.intval == +x

    def test_abs(self):
        space = self.space
        x = 42
        f1 = iobj.W_IntObject(x)
        v = f1.descr_abs(space)
        assert v.intval == abs(x)
        x = -42
        f1 = iobj.W_IntObject(x)
        v = f1.descr_abs(space)
        assert v.intval == abs(x)
        x = -sys.maxint-1
        f1 = iobj.W_IntObject(x)
        v = f1.descr_abs(space)
        assert space.isinstance_w(v, space.w_long)
        assert space.bigint_w(v).eq(rbigint.fromlong(abs(x)))

    def test_invert(self):
        x = 42
        f1 = iobj.W_IntObject(x)
        v = f1.descr_invert(self.space)
        assert v.intval == ~x

    def test_lshift(self):
        space = self.space
        x = 12345678
        y = 2
        f1 = iobj.W_IntObject(x)
        f2 = iobj.W_IntObject(y)
        v = f1.descr_lshift(space, f2)
        assert v.intval == x << y
        y = self._longshiftresult(x)
        f1 = iobj.W_IntObject(x)
        f2 = iobj.W_IntObject(y)
        v = f1.descr_lshift(space, f2)
        assert space.isinstance_w(v, space.w_long)
        assert space.bigint_w(v).eq(rbigint.fromlong(x << y))

    def test_rshift(self):
        x = 12345678
        y = 2
        f1 = iobj.W_IntObject(x)
        f2 = iobj.W_IntObject(y)
        v = f1.descr_rshift(self.space, f2)
        assert v.intval == x >> y

    def test_and(self):
        x = 12345678
        y = 2
        f1 = iobj.W_IntObject(x)
        f2 = iobj.W_IntObject(y)
        v = f1.descr_and(self.space, f2)
        assert v.intval == x & y

    def test_xor(self):
        x = 12345678
        y = 2
        f1 = iobj.W_IntObject(x)
        f2 = iobj.W_IntObject(y)
        v = f1.descr_xor(self.space, f2)
        assert v.intval == x ^ y

    def test_or(self):
        x = 12345678
        y = 2
        f1 = iobj.W_IntObject(x)
        f2 = iobj.W_IntObject(y)
        v = f1.descr_or(self.space, f2)
        assert v.intval == x | y

    def test_int(self):
        f1 = iobj.W_IntObject(1)
        result = f1.int(self.space)
        assert result == f1

    def test_oct(self):
        x = 012345
        f1 = iobj.W_IntObject(x)
        result = f1.descr_oct(self.space)
        assert self.space.unwrap(result) == oct(x)

    def test_hex(self):
        x = 0x12345
        f1 = iobj.W_IntObject(x)
        result = f1.descr_hex(self.space)
        assert self.space.unwrap(result) == hex(x)


class AppTestInt(object):
    def test_hash(self):
        assert hash(-1) == (-1).__hash__() == -2
        assert hash(-2) == (-2).__hash__() == -2

    def test_conjugate(self):
        assert (1).conjugate() == 1
        assert (-1).conjugate() == -1

        class I(int):
            pass
        assert I(1).conjugate() == 1

        class I(int):
            def __pos__(self):
                return 42
        assert I(1).conjugate() == 1

    def test_inplace(self):
        a = 1
        a += 1
        assert a == 2
        a -= 1
        assert a == 1

    def test_trunc(self):
        import math
        assert math.trunc(1) == 1
        assert math.trunc(-1) == -1

    def test_int_callable(self):
        assert 43 == int(43)

    def test_numerator_denominator(self):
        assert (1).numerator == 1
        assert (1).denominator == 1
        assert (42).numerator == 42
        assert (42).denominator == 1

    def test_int_string(self):
        assert 42 == int("42")
        assert 10000000000 == long("10000000000")

    def test_int_unicode(self):
        assert 42 == int(unicode('42'))

    def test_int_float(self):
        assert 4 == int(4.2)

    def test_int_str_repr(self):
        assert "42" == str(42)
        assert "42" == repr(42)
        raises(ValueError, int, '0x2A')

    def test_int_two_param(self):
        assert 42 == int('0x2A', 0)
        assert 42 == int('2A', 16)
        assert 42 == int('42', 10)
        raises(TypeError, int, 1, 10)
        raises(TypeError, int, '5', '9')

    def test_int_largenums(self):
        import sys
        for x in [-sys.maxint-1, -1, sys.maxint]:
            y = int(str(x))
            assert y == x
            assert type(y) is int

    def test_shift_zeros(self):
        assert (1 << 0) == 1
        assert (1 >> 0) == 1

    def test_overflow(self):
        import sys
        n = sys.maxint + 1
        assert isinstance(n, long)

    def test_pow(self):
        assert pow(2, -10) == 1/1024.

    def test_int_w_long_arg(self):
        assert int(10000000000) == 10000000000L
        assert int("10000000000") == 10000000000l
        raises(ValueError, int, "10000000000JUNK")
        raises(ValueError, int, "10000000000JUNK", 10)

    def test_int_subclass_ctr(self):
        import sys
        class j(int):
            pass
        assert j(100) == 100
        assert isinstance(j(100),j)
        assert j(100L) == 100
        assert j("100") == 100
        assert j("100",2) == 4
        assert isinstance(j("100",2),j)
        raises(OverflowError,j,sys.maxint+1)
        raises(OverflowError,j,str(sys.maxint+1))

    def test_int_subclass_ops(self):
        import sys
        class j(int):
            def __add__(self, other):
                return "add."
            def __iadd__(self, other):
                return "iadd."
            def __sub__(self, other):
                return "sub."
            def __isub__(self, other):
                return "isub."
            def __mul__(self, other):
                return "mul."
            def __imul__(self, other):
                return "imul."
            def __lshift__(self, other):
                return "lshift."
            def __ilshift__(self, other):
                return "ilshift."
        assert j(100) +  5   == "add."
        assert j(100) +  str == "add."
        assert j(100) -  5   == "sub."
        assert j(100) -  str == "sub."
        assert j(100) *  5   == "mul."
        assert j(100) *  str == "mul."
        assert j(100) << 5   == "lshift."
        assert j(100) << str == "lshift."
        assert (5 +  j(100),  type(5 +  j(100))) == (     105, int)
        assert (5 -  j(100),  type(5 -  j(100))) == (     -95, int)
        assert (5 *  j(100),  type(5 *  j(100))) == (     500, int)
        assert (5 << j(100),  type(5 << j(100))) == (5 << 100, long)
        assert (j(100) >> 2,  type(j(100) >> 2)) == (      25, int)

    def test_int_subclass_int(self):
        class j(int):
            def __int__(self):
                return value
            def __repr__(self):
                return '<instance of j>'
        class subint(int):
            pass
        class sublong(long):
            pass
        value = 42L
        assert int(j()) == 42
        value = 4200000000000000000000000000000000L
        assert int(j()) == 4200000000000000000000000000000000L
        value = subint(42)
        assert int(j()) == 42 and type(int(j())) is subint
        value = sublong(4200000000000000000000000000000000L)
        assert (int(j()) == 4200000000000000000000000000000000L
                and type(int(j())) is sublong)
        value = 42.0
        raises(TypeError, int, j())
        value = "foo"
        raises(TypeError, int, j())

    def test_special_int(self):
        class a(object):
            def __int__(self):
                self.ar = True
                return None
        inst = a()
        raises(TypeError, int, inst)
        assert inst.ar == True

        class b(object):
            pass
        raises((AttributeError,TypeError), int, b())

    def test_special_long(self):
        class a(object):
            def __long__(self):
                self.ar = True
                return None
        inst = a()
        raises(TypeError, long, inst)
        assert inst.ar == True

        class b(object):
            pass
        raises((AttributeError,TypeError), long, b())

    def test_just_trunc(self):
        class myint(object):
            def __trunc__(self):
                return 42
        assert int(myint()) == 42

    def test_override___int__(self):
        class myint(int):
            def __int__(self):
                return 42
        assert int(myint(21)) == 42
        class myotherint(int):
            pass
        assert int(myotherint(21)) == 21

    def test_trunc_returns_non_int(self):
        class Integral(object):
            def __int__(self):
                return 42
        class TruncReturnsNonInt(object):
            def __trunc__(self):
                return Integral()
        assert int(TruncReturnsNonInt()) == 42

    def test_trunc_returns_int_subclass(self):
        class Classic:
            pass
        for base in object, Classic:
            class TruncReturnsNonInt(base):
                def __trunc__(self):
                    return True
            n = int(TruncReturnsNonInt())
            assert n == 1
            assert type(n) is bool

    def test_int_before_string(self):
        class Integral(str):
            def __int__(self):
                return 42
        assert int(Integral('abc')) == 42

    def test_getnewargs(self):
        assert  0 .__getnewargs__() == (0,)

    def test_cmp(self):
        skip("This is a 'wont fix' case")
        # We don't have __cmp__, we consistently have __eq__ & the others
        # instead.  In CPython some types have __cmp__ and some types have
        # __eq__ & the others.
        assert 1 .__cmp__
        assert int .__cmp__

    def test_bit_length(self):
        for val, bits in [
            (0, 0),
            (1, 1),
            (10, 4),
            (150, 8),
            (-1, 1),
            (-2, 2),
            (-3, 2),
            (-4, 3),
            (-10, 4),
            (-150, 8),
        ]:
            assert val.bit_length() == bits

    def test_bit_length_max(self):
        import sys
        val = -sys.maxint-1
        bits = 32 if val == -2147483648 else 64
        assert val.bit_length() == bits

    def test_int_real(self):
        class A(int): pass
        b = A(5).real
        assert type(b) is int

    def test_int_error_msg(self):
        e = raises(TypeError, int, [])
        assert str(e.value) == (
            "int() argument must be a string or a number, not 'list'")

    def test_invalid_literal_message(self):
        import sys
        if '__pypy__' not in sys.builtin_module_names:
            skip('PyPy 2.x/CPython 3.4 only')
        for value in b'  1j ', u'  1٢٣٤j ':
            try:
                int(value)
            except ValueError as e:
                assert repr(value) in str(e)
            else:
                assert False, value

    def test_coerce(self):
        assert 3 .__coerce__(4) == (3, 4)
        assert 3 .__coerce__(4L) == NotImplemented

    def test_fake_int_as_base(self):
        class MyInt(object):
            def __init__(self, x):
                self.x = x
            def __int__(self):
                return self.x

        base = MyInt(24)
        assert int('10', base) == 24

    def test_truediv(self):
        import operator
        x = 1000000
        a = x / 2
        assert a == 500000
        a = operator.truediv(x, 2)
        assert a == 500000.0

        x = 63050394783186940
        a = x / 7
        assert a == 9007199254740991
        a = operator.truediv(x, 7)
        assert a == 9007199254740991.0

    def test_truediv_future(self):
        ns = dict(x=63050394783186940)
        exec("from __future__ import division; import operator; "
             "a = x / 7; b = operator.truediv(x, 7)", ns)
        assert ns['a'] == 9007199254740991.0
        assert ns['b'] == 9007199254740991.0

    def test_int_of_bool(self):
        x = int(False)
        assert x == 0
        assert type(x) is int
        assert str(x) == "0"

    def test_binop_overflow(self):
        x = int(2)
        assert x.__lshift__(128) == 680564733841876926926749214863536422912L

    def test_rbinop_overflow(self):
        x = int(321)
        assert x.__rlshift__(333) == 1422567365923326114875084456308921708325401211889530744784729710809598337369906606315292749899759616L

    def test_some_rops(self):
        import sys
        x = int(-sys.maxint)
        assert x.__rsub__(2) == (2 + sys.maxint)

    def test_error_message_wrong_self(self):
        unboundmeth = int.__str__
        e = raises(TypeError, unboundmeth, "!")
        assert "int" in str(e.value)
        if hasattr(unboundmeth, 'im_func'):
            e = raises(TypeError, unboundmeth.im_func, "!")
            assert "'int'" in str(e.value)


class AppTestIntShortcut(AppTestInt):
    spaceconfig = {"objspace.std.intshortcut": True}

    def test_inplace(self):
        # ensure other inplace ops still work
        l = []
        l += xrange(5)
        assert l == list(range(5))
        a = 8.5
        a -= .5
        assert a == 8
