import random
from pypy import conftest
from pypy.objspace.std import bytearrayobject

class DontAccess(object):
    pass
dont_access = DontAccess()



class AppTestBytesArray:
    def setup_class(cls):
        cls.w_runappdirect = cls.space.wrap(conftest.option.runappdirect)
        def tweak(w_bytearray):
            n = random.randint(-3, 16)
            if n > 0:
                w_bytearray._data = [dont_access] * n + w_bytearray._data
                w_bytearray._offset += n
        cls._old_tweak = [bytearrayobject._tweak_for_tests]
        bytearrayobject._tweak_for_tests = tweak

    def teardown_class(cls):
        [bytearrayobject._tweak_for_tests] = cls._old_tweak

    def test_basics(self):
        b = bytearray()
        assert type(b) is bytearray
        assert b.__class__ is bytearray

    def test_constructor(self):
        assert bytearray() == ""
        assert bytearray('abc') == "abc"
        assert bytearray(['a', 'b', 'c']) == "abc"
        assert bytearray([65, 66, 67]) == "ABC"
        assert bytearray(5) == '\0' * 5
        raises(ValueError, bytearray, ['a', 'bc'])
        raises(ValueError, bytearray, [65, -3])
        raises(TypeError, bytearray, [65.0])
        raises(ValueError, bytearray, -1)

    def test_init_override(self):
        class subclass(bytearray):
            def __init__(self, newarg=1, *args, **kwargs):
                bytearray.__init__(self, *args, **kwargs)
        x = subclass(4, source="abcd")
        assert x == "abcd"

    def test_encoding(self):
        data = u"Hello world\n\u1234\u5678\u9abc\def0\def0"
        for encoding in 'utf8', 'utf16':
            b = bytearray(data, encoding)
            assert b == data.encode(encoding)
        raises(TypeError, bytearray, 9, 'utf8')

    def test_encoding_with_ignore_errors(self):
        data = u"H\u1234"
        b = bytearray(data, "latin1", errors="ignore")
        assert b == "H"

    def test_len(self):
        b = bytearray('test')
        assert len(b) == 4

    def test_nohash(self):
        raises(TypeError, hash, bytearray())

    def test_repr(self):
        assert repr(bytearray()) == "bytearray(b'')"
        assert repr(bytearray('test')) == "bytearray(b'test')"
        assert repr(bytearray("d'oh")) == r'bytearray(b"d\'oh")'
        assert repr(bytearray('d"oh')) == 'bytearray(b\'d"oh\')'
        assert repr(bytearray('d"\'oh')) == 'bytearray(b\'d"\\\'oh\')'
        assert repr(bytearray('d\'"oh')) == 'bytearray(b\'d\\\'"oh\')'

    def test_str(self):
        assert str(bytearray()) == ""
        assert str(bytearray('test')) == "test"
        assert str(bytearray("d'oh")) == "d'oh"

    def test_getitem(self):
        b = bytearray('test')
        assert b[0] == ord('t')
        assert b[2] == ord('s')
        raises(IndexError, b.__getitem__, 4)
        assert b[1:5] == bytearray('est')
        assert b[slice(1,5)] == bytearray('est')
        assert b[1:5:2] == bytearray(b'et')

    def test_arithmetic(self):
        b1 = bytearray('hello ')
        b2 = bytearray('world')
        assert b1 + b2 == bytearray('hello world')
        assert b1 * 2 == bytearray('hello hello ')
        assert b1 * 1 is not b1

        b3 = b1
        b3 *= 3
        assert b3 == 'hello hello hello '
        assert type(b3) == bytearray
        assert b3 is b1

    def test_contains(self):
        assert ord('l') in bytearray('hello')
        assert 'l' in bytearray('hello')
        assert bytearray('ll') in bytearray('hello')
        assert memoryview('ll') in bytearray('hello')

        raises(TypeError, lambda: u'foo' in bytearray('foobar'))

    def test_splitlines(self):
        b = bytearray('1234')
        assert b.splitlines()[0] == b
        assert b.splitlines()[0] is not b

        assert len(bytearray('foo\nbar').splitlines()) == 2
        for item in bytearray('foo\nbar').splitlines():
            assert isinstance(item, bytearray)

    def test_ord(self):
        b = bytearray('\0A\x7f\x80\xff')
        assert ([ord(b[i:i+1]) for i in range(len(b))] ==
                         [0, 65, 127, 128, 255])
        raises(TypeError, ord, bytearray('ll'))
        raises(TypeError, ord, bytearray())

    def test_translate(self):
        b = 'hello'
        ba = bytearray(b)
        rosetta = bytearray(range(0, 256))
        rosetta[ord('o')] = ord('e')

        for table in rosetta, str(rosetta):
            c = ba.translate(table)
            assert ba == bytearray('hello')
            assert c == bytearray('helle')

            c = ba.translate(rosetta, 'l')
            assert c == bytearray('hee')
            assert isinstance(c, bytearray)

    def test_strip(self):
        b = bytearray('mississippi ')

        assert b.strip() == 'mississippi'
        assert b.strip(None) == 'mississippi'

        b = bytearray('mississippi')

        for strip_type in str, memoryview, buffer:
            print 'strip_type', strip_type
            assert b.strip(strip_type('i')) == 'mississipp'
            assert b.strip(strip_type('m')) == 'ississippi'
            assert b.strip(strip_type('pi')) == 'mississ'
            assert b.strip(strip_type('im')) == 'ssissipp'
            assert b.strip(strip_type('pim')) == 'ssiss'
            assert b.strip(strip_type(b)) == ''

    def test_iter(self):
        assert list(bytearray('hello')) == [104, 101, 108, 108, 111]
        assert list(bytearray('hello').__iter__()) == [104, 101, 108, 108, 111]

    def test_compare(self):
        assert bytearray('hello') == bytearray('hello')
        assert bytearray('hello') < bytearray('world')
        assert bytearray('world') > bytearray('hello')

    def test_compare_str(self):
        assert bytearray('hello1') == 'hello1'
        assert not (bytearray('hello1') != 'hello1')
        assert 'hello2' == bytearray('hello2')
        assert not ('hello1' != bytearray('hello1'))
        # unicode is always different
        assert not (bytearray('hello3') == unicode('world'))
        assert bytearray('hello3') != unicode('hello3')
        assert unicode('hello3') != bytearray('world')
        assert unicode('hello4') != bytearray('hello4')
        assert not (bytearray('') == u'')
        assert not (u'' == bytearray(''))
        assert bytearray('') != u''
        assert u'' != bytearray('')

    def test_stringlike_operations(self):
        assert bytearray('hello').islower()
        assert bytearray('HELLO').isupper()
        assert bytearray('hello').isalpha()
        assert not bytearray('hello2').isalpha()
        assert bytearray('hello2').isalnum()
        assert bytearray('1234').isdigit()
        assert bytearray('   ').isspace()
        assert bytearray('Abc').istitle()

        assert bytearray('hello').count('l') == 2
        assert bytearray('hello').count(bytearray('l')) == 2
        assert bytearray('hello').count(memoryview('l')) == 2

        assert bytearray('hello').index('e') == 1
        assert bytearray('hello').rindex('l') == 3
        assert bytearray('hello').index(bytearray('e')) == 1
        assert bytearray('hello').find('l') == 2
        assert bytearray('hello').find('l', -2) == 3
        assert bytearray('hello').rfind('l') == 3


        # these checks used to not raise in pypy but they should
        raises(TypeError, bytearray('hello').index, ord('e'))
        raises(TypeError, bytearray('hello').rindex, ord('e'))
        raises(TypeError, bytearray('hello').find, ord('e'))
        raises(TypeError, bytearray('hello').rfind, ord('e'))

        assert bytearray('hello').startswith('he')
        assert bytearray('hello').startswith(bytearray('he'))
        assert bytearray('hello').startswith(('lo', bytearray('he')))
        assert bytearray('hello').endswith('lo')
        assert bytearray('hello').endswith(bytearray('lo'))
        assert bytearray('hello').endswith((bytearray('lo'), 'he'))

    def test_startswith_too_large(self):
        assert bytearray('ab').startswith(bytearray('b'), 1) is True
        assert bytearray('ab').startswith(bytearray(''), 2) is True
        assert bytearray('ab').startswith(bytearray(''), 3) is False
        assert bytearray('ab').endswith(bytearray('b'), 1) is True
        assert bytearray('ab').endswith(bytearray(''), 2) is True
        assert bytearray('ab').endswith(bytearray(''), 3) is False

    def test_startswith_self(self):
        b = bytearray(b'abcd')
        assert b.startswith(b)

    def test_stringlike_conversions(self):
        # methods that should return bytearray (and not str)
        def check(result, expected):
            assert result == expected
            assert type(result) is bytearray

        check(bytearray('abc').replace('b', bytearray('d')), 'adc')
        check(bytearray('abc').replace('b', 'd'), 'adc')
        check(bytearray('').replace('a', 'ab'), '')

        check(bytearray('abc').upper(), 'ABC')
        check(bytearray('ABC').lower(), 'abc')
        check(bytearray('abc').title(), 'Abc')
        check(bytearray('AbC').swapcase(), 'aBc')
        check(bytearray('abC').capitalize(), 'Abc')

        check(bytearray('abc').ljust(5),  'abc  ')
        check(bytearray('abc').rjust(5),  '  abc')
        check(bytearray('abc').center(5), ' abc ')
        check(bytearray('1').zfill(5), '00001')
        check(bytearray('1\t2').expandtabs(5), '1    2')

        check(bytearray(',').join(['a', bytearray('b')]), 'a,b')
        check(bytearray('abca').lstrip('a'), 'bca')
        check(bytearray('cabc').rstrip('c'), 'cab')
        check(bytearray('abc').lstrip(memoryview('a')), 'bc')
        check(bytearray('abc').rstrip(memoryview('c')), 'ab')
        check(bytearray('aba').strip('a'), 'b')

    def test_xjust_no_mutate(self):
        # a previous regression
        b = bytearray(b'')
        assert b.ljust(1) == bytearray(b' ')
        assert not len(b)

        b2 = b.ljust(0)
        b2 += b' '
        assert not len(b)

        b2 = b.rjust(0)
        b2 += b' '
        assert not len(b)

    def test_split(self):
        # methods that should return a sequence of bytearrays
        def check(result, expected):
            assert result == expected
            assert set(type(x) for x in result) == set([bytearray])

        b = bytearray('mississippi')
        check(b.split('i'), ['m', 'ss', 'ss', 'pp', ''])
        check(b.split(memoryview('i')), ['m', 'ss', 'ss', 'pp', ''])
        check(b.rsplit('i'), ['m', 'ss', 'ss', 'pp', ''])
        check(b.rsplit(memoryview('i')), ['m', 'ss', 'ss', 'pp', ''])
        check(b.rsplit('i', 2), ['mississ', 'pp', ''])

        check(bytearray('foo bar').split(), ['foo', 'bar'])
        check(bytearray('foo bar').split(None), ['foo', 'bar'])

        check(b.partition('ss'), ('mi', 'ss', 'issippi'))
        check(b.partition(memoryview('ss')), ('mi', 'ss', 'issippi'))
        check(b.rpartition('ss'), ('missi', 'ss', 'ippi'))
        check(b.rpartition(memoryview('ss')), ('missi', 'ss', 'ippi'))

    def test_append(self):
        b = bytearray('abc')
        b.append('d')
        b.append(ord('e'))
        assert b == 'abcde'

    def test_insert(self):
        b = bytearray('abc')
        b.insert(0, 'd')
        assert b == bytearray('dabc')

        b.insert(-1, ord('e'))
        assert b == bytearray('dabec')

        b.insert(6, 'f')
        assert b == bytearray('dabecf')

        b.insert(1, 'g')
        assert b == bytearray('dgabecf')

        b.insert(-12, 'h')
        assert b == bytearray('hdgabecf')

        raises(ValueError, b.insert, 1, 'go')
        raises(TypeError, b.insert, 'g', 'o')

    def test_pop(self):
        b = bytearray('world')
        assert b.pop() == ord('d')
        assert b.pop(0) == ord('w')
        assert b.pop(-2) == ord('r')
        raises(IndexError, b.pop, 10)
        raises(IndexError, bytearray().pop)
        assert bytearray('\xff').pop() == 0xff

    def test_remove(self):
        class Indexable:
            def __index__(self):
                return ord('e')

        b = bytearray('hello')
        b.remove(ord('l'))
        assert b == 'helo'
        b.remove(ord('l'))
        assert b == 'heo'
        raises(ValueError, b.remove, ord('l'))
        raises(ValueError, b.remove, 400)
        raises(TypeError, b.remove, u'e')
        raises(TypeError, b.remove, 2.3)
        # remove first and last
        b.remove(ord('o'))
        b.remove(ord('h'))
        assert b == 'e'
        raises(TypeError, b.remove, u'e')
        b.remove(Indexable())
        assert b == ''

    def test_reverse(self):
        b = bytearray('hello')
        b.reverse()
        assert b == bytearray('olleh')

    def test_delitem_from_front(self):
        b = bytearray(b'abcdefghij')
        del b[0]
        del b[0]
        assert len(b) == 8
        assert b == bytearray(b'cdefghij')
        del b[-8]
        del b[-7]
        assert len(b) == 6
        assert b == bytearray(b'efghij')
        del b[:3]
        assert len(b) == 3
        assert b == bytearray(b'hij')

    def test_delitem(self):
        b = bytearray('abc')
        del b[1]
        assert b == bytearray('ac')
        del b[1:1]
        assert b == bytearray('ac')
        del b[:]
        assert b == bytearray()

        b = bytearray('fooble')
        del b[::2]
        assert b == bytearray('obe')

    def test_iadd(self):
        b = b0 = bytearray('abc')
        b += 'def'
        assert b == 'abcdef'
        assert b is b0
        raises(TypeError, b.__iadd__, u"")
        #
        b += bytearray('XX')
        assert b == 'abcdefXX'
        assert b is b0
        #
        b += memoryview('ABC')
        assert b == 'abcdefXXABC'
        assert b is b0

    def test_add(self):
        b1 = bytearray("abc")
        b2 = bytearray("def")

        def check(a, b, expected):
            result = a + b
            assert result == expected
            assert isinstance(result, bytearray)

        check(b1, b2, "abcdef")
        check(b1, "def", "abcdef")
        check("def", b1, "defabc")
        check(b1, memoryview("def"), "abcdef")
        raises(TypeError, lambda: b1 + u"def")
        raises(TypeError, lambda: u"abc" + b2)

    def test_fromhex(self):
        raises(TypeError, bytearray.fromhex, 9)

        assert bytearray.fromhex('') == bytearray()
        assert bytearray.fromhex(u'') == bytearray()

        b = bytearray([0x1a, 0x2b, 0x30])
        assert bytearray.fromhex('1a2B30') == b
        assert bytearray.fromhex(u'1a2B30') == b
        assert bytearray.fromhex(u'  1A 2B  30   ') == b
        assert bytearray.fromhex(u'0000') == '\0\0'

        raises(ValueError, bytearray.fromhex, u'a')
        raises(ValueError, bytearray.fromhex, u'A')
        raises(ValueError, bytearray.fromhex, u'rt')
        raises(ValueError, bytearray.fromhex, u'1a b cd')
        raises(ValueError, bytearray.fromhex, u'\x00')
        raises(ValueError, bytearray.fromhex, u'12   \x00   34')
        raises(UnicodeEncodeError, bytearray.fromhex, u'\u1234')

    def test_extend(self):
        b = bytearray('abc')
        b.extend(bytearray('def'))
        b.extend('ghi')
        assert b == 'abcdefghi'
        b.extend(buffer('jkl'))
        assert b == 'abcdefghijkl'

        b = bytearray('world')
        b.extend([ord(c) for c in 'hello'])
        assert b == bytearray('worldhello')

        b = bytearray('world')
        b.extend(list('hello'))
        assert b == bytearray('worldhello')

        b = bytearray('world')
        b.extend(c for c in 'hello')
        assert b == bytearray('worldhello')

        raises(ValueError, b.extend, ['fish'])
        raises(ValueError, b.extend, [256])
        raises(TypeError, b.extend, object())
        raises(TypeError, b.extend, [object()])
        raises(TypeError, b.extend, u"unicode")

        b = bytearray('abc')
        b.extend(memoryview('def'))
        assert b == bytearray('abcdef')

    def test_extend_calls_len_or_lengthhint(self):
        class BadLen(object):
            def __iter__(self): return iter(range(10))
            def __len__(self): raise RuntimeError('hello')
        b = bytearray()
        raises(RuntimeError, b.extend, BadLen())

    def test_setitem_from_front(self):
        b = bytearray(b'abcdefghij')
        b[:2] = b''
        assert len(b) == 8
        assert b == bytearray(b'cdefghij')
        b[:3] = b'X'
        assert len(b) == 6
        assert b == bytearray(b'Xfghij')
        b[:2] = b'ABC'
        assert len(b) == 7
        assert b == bytearray(b'ABCghij')

    def test_setslice(self):
        b = bytearray('hello')
        b[:] = [ord(c) for c in 'world']
        assert b == bytearray('world')

        b = bytearray('hello world')
        b[::2] = 'bogoff'
        assert b == bytearray('beolg ooflf')

        def set_wrong_size():
            b[::2] = 'foo'
        raises(ValueError, set_wrong_size)

    def test_delitem_slice(self):
        b = bytearray('abcdefghi')
        del b[5:8]
        assert b == 'abcdei'
        del b[:3]
        assert b == 'dei'

        b = bytearray('hello world')
        del b[::2]
        assert b == bytearray('el ol')

    def test_setitem(self):
        b = bytearray('abcdefghi')
        b[1] = 'B'
        assert b == 'aBcdefghi'

    def test_setitem_errmsg(self):
        b = bytearray('abcdefghi')
        e = raises(TypeError, "b[1] = u'B'")
        assert str(e.value).startswith(
            "an integer or string of size 1 is required")
        e = raises(TypeError, "b[1] = None")
        assert str(e.value).startswith(
            "an integer or string of size 1 is required")

    def test_setitem_slice(self):
        b = bytearray('abcdefghi')
        b[0:3] = 'ABC'
        assert b == 'ABCdefghi'
        b[3:3] = '...'
        assert b == 'ABC...defghi'
        b[3:6] = '()'
        assert b == 'ABC()defghi'
        b[6:6] = '<<'
        assert b == 'ABC()d<<efghi'

    def test_buffer(self):
        b = bytearray('abcdefghi')
        buf = buffer(b)
        assert buf[2] == 'c'
        exc = raises(TypeError, "buf[2] = 'D'")
        assert str(exc.value) == "buffer is read-only"
        exc = raises(TypeError, "buf[4:6] = 'EF'")
        assert str(exc.value) == "buffer is read-only"

    def test_decode(self):
        b = bytearray('abcdefghi')
        u = b.decode('utf-8')
        assert isinstance(u, unicode)
        assert u == u'abcdefghi'
        assert b.decode().encode() == b

    def test_int(self):
        assert int(bytearray('-1234')) == -1234

    def test_float(self):
        assert float(bytearray(b'10.4')) == 10.4
        assert float(bytearray('-1.7e-1')) == -1.7e-1
        assert float(bytearray(u'.9e10', 'utf-8')) == .9e10
        import math
        assert math.isnan(float(bytearray('nan')))
        raises(ValueError, float, bytearray('not_a_number'))

    def test_reduce(self):
        assert bytearray('caf\xe9').__reduce__() == (
            bytearray, (u'caf\xe9', 'latin-1'), None)

    def test_setitem_slice_performance(self):
        # because of a complexity bug, this used to take forever on a
        # translated pypy.  On CPython2.6 -A, it takes around 8 seconds.
        if self.runappdirect:
            count = 16*1024*1024
        else:
            count = 1024
        b = bytearray(count)
        for i in range(count):
            b[i:i+1] = 'y'
        assert str(b) == 'y' * count

    def test_partition_return_copy(self):
        b = bytearray(b'foo')
        assert b.partition(b'x')[0] is not b

    def test_split_whitespace(self):
        b = bytearray(b'\x09\x0A\x0B\x0C\x0D\x1C\x1D\x1E\x1F')
        assert b.split() == [b'\x1c\x1d\x1e\x1f']

    def test_dont_force_offset(self):
        def make(x=b'abcdefghij', shift=3):
            b = bytearray(b'?'*shift + x)
            b + b''                       # force 'b'
            del b[:shift]                 # add shift to b._offset
            return b
        assert make(shift=0).__alloc__() == 11
        #
        x = make(shift=3)
        assert x.__alloc__() == 14
        assert memoryview(x)[1] == 'b'
        assert x.__alloc__() == 14
        assert len(x) == 10
        assert x.__alloc__() == 14
        assert x[3] == ord('d')
        assert x[-3] == ord('h')
        assert x.__alloc__() == 14
        assert x[3:-3] == b'defg'
        assert x[-3:3:-1] == b'hgfe'
        assert x.__alloc__() == 14
        assert repr(x) == "bytearray(b'abcdefghij')"
        assert x.__alloc__() == 14
        #
        x = make(shift=3)
        x[3] = ord('D')
        assert x.__alloc__() == 14
        x[4:6] = b'EF'
        assert x.__alloc__() == 14
        x[6:8] = b'G'
        assert x.__alloc__() == 13
        x[-2:4:-2] = b'*/'
        assert x.__alloc__() == 13
        assert x == bytearray(b'abcDE/G*j')
        #
        x = make(b'abcdefghijklmnopqrstuvwxyz', shift=11)
        assert len(x) == 26
        assert x.__alloc__() == 38
        del x[:1]
        assert len(x) == 25
        assert x.__alloc__() == 38
        del x[0:5]
        assert len(x) == 20
        assert x.__alloc__() == 38
        del x[0]
        assert len(x) == 19
        assert x.__alloc__() == 38
        del x[0]                      # too much emptiness, forces now
        assert len(x) == 18
        assert x.__alloc__() == 19
        #
        x = make(b'abcdefghijklmnopqrstuvwxyz', shift=11)
        del x[:9]                     # too much emptiness, forces now
        assert len(x) == 17
        assert x.__alloc__() == 18
        #
        x = make(b'abcdefghijklmnopqrstuvwxyz', shift=11)
        assert x.__alloc__() == 38
        del x[1]
        assert x.__alloc__() == 37      # not forced, but the list shrank
        del x[3:10:2]
        assert x.__alloc__() == 33
        assert x == bytearray(b'acdfhjlmnopqrstuvwxyz')
        #
        x = make(shift=3)
        assert b'f' in x
        assert b'ef' in x
        assert b'efx' not in x
        assert b'very long string longer than the original' not in x
        assert x.__alloc__() == 14
        assert x.find(b'f') == 5
        assert x.rfind(b'f', 2, 11) == 5
        assert x.find(b'fe') == -1
        assert x.index(b'f', 2, 11) == 5
        assert x.__alloc__() == 14

    def test_fromobject___index__(self):
        class WithIndex:
            def __index__(self):
                return 3
        assert bytearray(WithIndex()) == b'\x00\x00\x00'

    def test_fromobject___int__(self):
        class WithInt:
            def __int__(self):
                return 3
        raises(TypeError, bytearray, WithInt())
