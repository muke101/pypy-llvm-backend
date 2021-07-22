class AppTestMap:
    def test_trivial_map_one_seq(self):
        assert map(lambda x: x+2, [1, 2, 3, 4]) == [3, 4, 5, 6]

    def test_trivial_map_one_seq_2(self):
        assert map(str, [1, 2, 3, 4]) == ['1', '2', '3', '4']

    def test_trivial_map_two_seq(self):
        assert map(lambda x,y: x+y,
                             [1, 2, 3, 4],[1, 2, 3, 4]) == (
                         [2, 4, 6, 8])

    def test_trivial_map_sizes_dont_match_and_should(self):
        raises(TypeError, map, lambda x,y: x+y, [1, 2, 3, 4], [1, 2, 3])

    def test_trivial_map_no_arguments(self):
        raises(TypeError, map)

    def test_trivial_map_no_function_no_seq(self):
        raises(TypeError, map, None)

    def test_trivial_map_no_fuction_one_seq(self):
        assert map(None, [1, 2, 3]) == [1, 2, 3]

    def test_trivial_map_no_function(self):
        assert map(None, [1,2,3], [4,5,6], [7,8], [1]) == (
                         [(1, 4, 7, 1), (2, 5, 8, None), (3, 6, None, None)])

    def test_map_identity1(self):
        a = ['1', 2, 3, 'b', None]
        b = a[:]
        assert map(lambda x: x, a) == a
        assert a == b

    def test_map_None(self):
        a = ['1', 2, 3, 'b', None]
        b = a[:]
        assert map(None, a) == a
        assert a == b

    def test_map_badoperation(self):
        a = ['1', 2, 3, 'b', None]
        raises(TypeError, map, lambda x: x+1, a)

    def test_map_multiply_identity(self):
        a = ['1', 2, 3, 'b', None]
        b = [ 2, 3, 4, 5, 6]
        assert map(None, a, b) == [('1', 2), (2, 3), (3, 4), ('b', 5), (None, 6)]

    def test_map_add(self):
        a = [1, 2, 3, 4]
        b = [0, 1, 1, 1]
        assert map(lambda x, y: x+y, a, b) == [1, 3, 4, 5]

    def test_map_first_item(self):
        a = [1, 2, 3, 4, 5]
        b = []
        assert map(lambda x, y: x, a, b) == a

    def test_map_second_item(self):
        a = []
        b = [1, 2, 3, 4, 5]
        assert map(lambda x, y: y, a, b) == b

    def test_map_iterables(self):
        class A(object):
            def __init__(self, n):
                self.n = n
            def __iter__(self):
                return B(self.n)
        class B(object):
            def __init__(self, n):
                self.n = n
            def next(self):
                self.n -= 1
                if self.n == 0: raise StopIteration
                return self.n
        result = map(None, A(3), A(8))
        # this also checks that B.next() is not called any more after it
        # raised StopIteration once
        assert result == [(2, 7), (1, 6), (None, 5), (None, 4),
                          (None, 3), (None, 2), (None, 1)]


class AppTestZip:
    def test_one_list(self):
        assert zip([1,2,3]) == [(1,), (2,), (3,)]

    def test_three_lists(self):
        assert zip([1,2,3], [1,2], [1,2,3]) == [(1,1,1), (2,2,2)]

    def test_bad_length_hint(self):
        class Foo(object):
            def __length_hint__(self):
                return NotImplemented
            def __iter__(self):
                if False:
                    yield None
        assert zip(Foo()) == []


class AppTestReduce:
    def test_None(self):
        raises(TypeError, reduce, lambda x, y: x+y, [1,2,3], None)

    def test_sum(self):
        assert reduce(lambda x, y: x+y, [1,2,3,4], 0) == 10
        assert reduce(lambda x, y: x+y, [1,2,3,4]) == 10

    def test_minus(self):
        assert reduce(lambda x, y: x-y, [10, 2, 8]) == 0
        assert reduce(lambda x, y: x-y, [2, 8], 10) == 0


class AppTestFilter:
    def test_None(self):
        assert filter(None, ['a', 'b', 1, 0, None]) == ['a', 'b', 1]

    def test_return_type(self):
        txt = "This is a test text"
        assert filter(None, txt) == txt
        tup = ("a", None, 0, [], 1)
        assert filter(None, tup) == ("a", 1)

    def test_function(self):
        assert filter(lambda x: x != "a", "a small text") == " smll text"
        assert filter(lambda x: x < 20, [3, 33, 5, 55]) == [3, 5]

    def test_filter_tuple_calls_getitem(self):
        class T(tuple):
            def __getitem__(self, i):
                return i * 10
        assert filter(lambda x: x != 20, T("abcd")) == (0, 10, 30)


class AppTestXRange:
    def test_xrange(self):
        x = xrange(2, 9, 3)
        assert x[1] == 5
        assert len(x) == 3
        assert list(x) == [2, 5, 8]
        # test again, to make sure that xrange() is not its own iterator
        assert list(x) == [2, 5, 8]

    def test_xrange_iter(self):
        x = xrange(2, 9, 3)
        it = iter(x)
        assert iter(it) is it
        assert it.next() == 2
        assert it.next() == 5
        assert it.next() == 8
        raises(StopIteration, it.next)
        # test again, to make sure that xrange() is not its own iterator
        assert iter(x).next() == 2

    def test_xrange_object_with___int__(self):
        class A(object):
            def __int__(self):
                return 5

        assert list(xrange(A())) == [0, 1, 2, 3, 4]
        assert list(xrange(0, A())) == [0, 1, 2, 3, 4]
        assert list(xrange(0, 10, A())) == [0, 5]

    def test_xrange_float(self):
        exc = raises(TypeError, xrange, 0.1, 2.0, 1.1)
        assert "integer" in str(exc.value)

    def test_xrange_long(self):
        import sys
        a = long(10 * sys.maxint)
        raises(OverflowError, xrange, a)
        raises(OverflowError, xrange, 0, a)
        raises(OverflowError, xrange, 0, 1, a)

    def test_xrange_reduce(self):
        x = xrange(2, 9, 3)
        callable, args = x.__reduce__()
        y = callable(*args)
        assert list(y) == list(x)

    def test_xrange_iter_reduce(self):
        x = iter(xrange(2, 9, 3))
        x.next()
        callable, args = x.__reduce__()
        y = callable(*args)
        assert list(y) == list(x)

    def test_xrange_iter_reduce_one(self):
        x = iter(xrange(2, 9))
        x.next()
        callable, args = x.__reduce__()
        y = callable(*args)
        assert list(y) == list(x)

    def test_lib_python_xrange_optimization(self):
        x = xrange(1)
        assert type(reversed(x)) == type(iter(x))

    def test_cpython_issue16029(self):
        import sys
        M = min(sys.maxint, sys.maxsize)
        x = xrange(0, M, M - 1)
        assert x.__reduce__() == (xrange, (0, M, M - 1))
        x = xrange(0, -M, 1 - M)
        assert x.__reduce__() == (xrange, (0, -M - 1, 1 - M))

    def test_cpython_issue16030(self):
        import sys
        M = min(sys.maxint, sys.maxsize)
        x = xrange(0, M, M - 1)
        assert repr(x) == 'xrange(0, %s, %s)' % (M, M - 1)
        x = xrange(0, -M, 1 - M)
        assert repr(x) == 'xrange(0, %s, %s)' % (-M - 1, 1 - M)


class AppTestReversed:
    def test_reversed(self):
        r = reversed("hello")
        assert iter(r) is r
        assert r.next() == "o"
        assert r.next() == "l"
        assert r.next() == "l"
        assert r.next() == "e"
        assert r.next() == "h"
        raises(StopIteration, r.next)
        assert list(reversed(list(reversed("hello")))) == ['h','e','l','l','o']
        raises(TypeError, reversed, reversed("hello"))

    def test_reversed_user_type(self):
        class X(object):
            def __getitem__(self, index):
                return str(index)
            def __len__(self):
                return 5
        assert list(reversed(X())) == ["4", "3", "2", "1", "0"]

    def test_reversed_not_for_mapping(self):
        raises(TypeError, reversed, {})
        raises(TypeError, reversed, {2: 3})
        assert not hasattr(dict, '__reversed__')
        raises(TypeError, reversed, int.__dict__)

    def test_reversed_type_with_no_len(self):
        class X(object):
            def __getitem__(self, key):
                raise ValueError
        raises(TypeError, reversed, X())

    def test_reversed_length_hint(self):
        lst = [1, 2, 3]
        r = reversed(lst)
        assert r.__length_hint__() == 3
        assert next(r) == 3
        assert r.__length_hint__() == 2
        lst.pop()
        assert r.__length_hint__() == 2
        lst.pop()
        assert r.__length_hint__() == 0
        raises(StopIteration, next, r)
        #
        r = reversed(lst)
        assert r.__length_hint__() == 1
        assert next(r) == 1
        assert r.__length_hint__() == 0
        raises(StopIteration, next, r)
        assert r.__length_hint__() == 0


class AppTestApply:
    def test_apply(self):
        def f(*args, **kw):
            return args, kw
        args = (1,3)
        kw = {'a': 1, 'b': 4}
        assert apply(f) == ((), {})
        assert apply(f, args) == (args, {})
        assert apply(f, args, kw) == (args, kw)


class AppTestAllAny:
    """
    These are copied directly and replicated from the Python 2.5 source code.
    """

    def test_all(self):

        class TestFailingBool(object):
            def __nonzero__(self):
                raise RuntimeError
        class TestFailingIter(object):
            def __iter__(self):
                raise RuntimeError

        assert all([2, 4, 6]) == True
        assert all([2, None, 6]) == False
        raises(RuntimeError, all, [2, TestFailingBool(), 6])
        raises(RuntimeError, all, TestFailingIter())
        raises(TypeError, all, 10)               # Non-iterable
        raises(TypeError, all)                   # No args
        raises(TypeError, all, [2, 4, 6], [])    # Too many args
        assert all([]) == True                   # Empty iterator
        S = [50, 60]
        assert all([x > 42 for x in S]) == True
        S = [50, 40, 60]
        assert all([x > 42 for x in S]) == False

    def test_any(self):

        class TestFailingBool(object):
            def __nonzero__(self):
                raise RuntimeError
        class TestFailingIter(object):
            def __iter__(self):
                raise RuntimeError

        assert any([None, None, None]) == False
        assert any([None, 4, None]) == True
        raises(RuntimeError, any, [None, TestFailingBool(), 6])
        raises(RuntimeError, all, TestFailingIter())
        raises(TypeError, any, 10)               # Non-iterable
        raises(TypeError, any)                   # No args
        raises(TypeError, any, [2, 4, 6], [])    # Too many args
        assert any([]) == False                  # Empty iterator
        S = [40, 60, 30]
        assert any([x > 42 for x in S]) == True
        S = [10, 20, 30]
        assert any([x > 42 for x in S]) == False


class AppTestMinMax:
    def test_min(self):
        assert min(1, 2) == 1
        assert min(1, 2, key=lambda x: -x) == 2
        assert min([1, 2, 3]) == 1
        raises(TypeError, min, 1, 2, bar=2)
        raises(TypeError, min, 1, 2, key=lambda x: x, bar=2)
        assert type(min(1, 1.0)) is int
        assert type(min(1.0, 1)) is float
        assert type(min(1, 1.0, 1L)) is int
        assert type(min(1.0, 1L, 1)) is float
        assert type(min(1L, 1, 1.0)) is long

    def test_max(self):
        assert max(1, 2) == 2
        assert max(1, 2, key=lambda x: -x) == 1
        assert max([1, 2, 3]) == 3
        raises(TypeError, max, 1, 2, bar=2)
        raises(TypeError, max, 1, 2, key=lambda x: x, bar=2)
        assert type(max(1, 1.0)) is int
        assert type(max(1.0, 1)) is float
        assert type(max(1, 1.0, 1L)) is int
        assert type(max(1.0, 1L, 1)) is float
        assert type(max(1L, 1, 1.0)) is long

    def test_max_list_and_key(self):
        assert max(["100", "50", "30", "-200"], key=int) == "100"
        assert max("100", "50", "30", "-200", key=int) == "100"


try:
    from hypothesis import given, strategies, example
except ImportError:
    pass
else:
    @given(lst=strategies.lists(strategies.integers()))
    def test_map_hypothesis(space, lst):
        print lst
        w_lst = space.appexec([space.wrap(lst[:])], """(lst):
            def change(n):
                if n & 3 == 1:
                    lst.pop(0)
                elif n & 3 == 2:
                    lst.append(100)
                return n * 2
            return map(change, lst)
        """)
        expected = []
        i = 0
        while i < len(lst):
            n = lst[i]
            if n & 3 == 1:
                lst.pop(0)
            elif n & 3 == 2:
                lst.append(100)
            expected.append(n * 2)
            i += 1
        assert space.unwrap(w_lst) == expected
