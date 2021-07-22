# -*- encoding: utf-8 -*-
import py
import sys
try:
    from hypothesis import given, strategies, settings, example
    HAS_HYPOTHESIS = True
except ImportError:
    HAS_HYPOTHESIS = False
    
from rpython.rlib import rutf8
from pypy.interpreter.error import OperationError


class TestUnicodeObject:
    def test_comparison_warning(self):
        warnings = []
        def my_warn(msg, warningscls):
            warnings.append(msg)
            prev_warn(msg, warningscls)
        space = self.space
        prev_warn = space.warn
        try:
            space.warn = my_warn
            space.appexec([], """():
                chr(128) == unichr(128)
                chr(128) != unichr(128)
                chr(127) == unichr(127) # no warnings
            """)
        finally:
            space.warn = prev_warn
        assert len(warnings) == 2

    def test_listview_ascii(self):
        w_str = self.space.newutf8('abcd', 4)
        assert self.space.listview_ascii(w_str) == list("abcd")

    def test_new_shortcut(self):
        space = self.space
        w_uni = self.space.newutf8('abcd', 4)
        w_new = space.call_method(
                space.w_unicode, "__new__", space.w_unicode, w_uni)
        assert w_new is w_uni

    def test_fast_iter(self):
        space = self.space
        w_uni = space.newutf8(u"aä".encode("utf-8"), 2)
        old_index_storage = w_uni._index_storage
        w_iter = space.iter(w_uni)
        w_char1 = w_iter.descr_next(space)
        w_char2 = w_iter.descr_next(space)
        py.test.raises(OperationError, w_iter.descr_next, space)
        assert w_uni._index_storage is old_index_storage
        assert space.eq_w(w_char1, w_uni._getitem_result(space, 0))
        assert space.eq_w(w_char2, w_uni._getitem_result(space, 1))


    if HAS_HYPOTHESIS:
        @given(strategies.text(), strategies.integers(min_value=0, max_value=10),
                                  strategies.integers(min_value=-1, max_value=10))
        def test_hypo_index_find(self, u, start, len1):
            if start + len1 < 0:
                return   # skip this case
            v = u[start : start + len1]
            space = self.space
            w_u = space.newutf8(u.encode('utf8'), len(u))
            w_v = space.newutf8(v.encode('utf8'), len(v))
            expected = u.find(v, start, start + len1)
            try:
                w_index = space.call_method(w_u, 'index', w_v,
                                            space.newint(start),
                                            space.newint(start + len1))
            except OperationError as e:
                if not e.match(space, space.w_ValueError):
                    raise
                assert expected == -1
            else:
                assert space.int_w(w_index) == expected >= 0

            w_index = space.call_method(w_u, 'find', w_v,
                                        space.newint(start),
                                        space.newint(start + len1))
            assert space.int_w(w_index) == expected

            rexpected = u.rfind(v, start, start + len1)
            try:
                w_index = space.call_method(w_u, 'rindex', w_v,
                                            space.newint(start),
                                            space.newint(start + len1))
            except OperationError as e:
                if not e.match(space, space.w_ValueError):
                    raise
                assert rexpected == -1
            else:
                assert space.int_w(w_index) == rexpected >= 0

            w_index = space.call_method(w_u, 'rfind', w_v,
                                        space.newint(start),
                                        space.newint(start + len1))
            assert space.int_w(w_index) == rexpected

            expected = u.startswith(v, start)
            w_res = space.call_method(w_u, 'startswith', w_v,
                                      space.newint(start))
            assert w_res is space.newbool(expected)

            expected = u.startswith(v, start, start + len1)
            w_res = space.call_method(w_u, 'startswith', w_v,
                                      space.newint(start),
                                      space.newint(start + len1))
            assert w_res is space.newbool(expected)

            expected = u.endswith(v, start)
            w_res = space.call_method(w_u, 'endswith', w_v,
                                      space.newint(start))
            assert w_res is space.newbool(expected)

            expected = u.endswith(v, start, start + len1)
            w_res = space.call_method(w_u, 'endswith', w_v,
                                      space.newint(start),
                                      space.newint(start + len1))
            assert w_res is space.newbool(expected)


        @given(u=strategies.text(),
               start=strategies.integers(min_value=0, max_value=10),
               len1=strategies.integers(min_value=-1, max_value=10))
        def test_hypo_index_find(self, u, start, len1):
            space = self.space
            if start + len1 < 0:
                return   # skip this case
            v = u[start : start + len1]
            w_u = space.wrap(u)
            w_v = space.wrap(v)
            expected = u.find(v, start, start + len1)
            try:
                w_index = space.call_method(w_u, 'index', w_v,
                                            space.newint(start),
                                            space.newint(start + len1))
            except OperationError as e:
                if not e.match(space, space.w_ValueError):
                    raise
                assert expected == -1
            else:
                assert space.int_w(w_index) == expected >= 0

            w_index = space.call_method(w_u, 'find', w_v,
                                        space.newint(start),
                                        space.newint(start + len1))
            assert space.int_w(w_index) == expected

            rexpected = u.rfind(v, start, start + len1)
            try:
                w_index = space.call_method(w_u, 'rindex', w_v,
                                            space.newint(start),
                                            space.newint(start + len1))
            except OperationError as e:
                if not e.match(space, space.w_ValueError):
                    raise
                assert rexpected == -1
            else:
                assert space.int_w(w_index) == rexpected >= 0

            w_index = space.call_method(w_u, 'rfind', w_v,
                                        space.newint(start),
                                        space.newint(start + len1))
            assert space.int_w(w_index) == rexpected

            expected = u.startswith(v, start)
            w_res = space.call_method(w_u, 'startswith', w_v,
                                      space.newint(start))
            assert w_res is space.newbool(expected)

            expected = u.startswith(v, start, start + len1)
            w_res = space.call_method(w_u, 'startswith', w_v,
                                      space.newint(start),
                                      space.newint(start + len1))
            assert w_res is space.newbool(expected)

            expected = u.endswith(v, start)
            w_res = space.call_method(w_u, 'endswith', w_v,
                                      space.newint(start))
            assert w_res is space.newbool(expected)

            expected = u.endswith(v, start, start + len1)
            w_res = space.call_method(w_u, 'endswith', w_v,
                                      space.newint(start),
                                      space.newint(start + len1))
            assert w_res is space.newbool(expected)

    def test_getitem_constant_index_jit(self):
        # test it directly, to prevent only seeing bugs in jitted code
        space = self.space
        u = u"äöabc"
        w_u = self.space.wrap(u)
        for i in range(-len(u), len(u)):
            assert w_u._getitem_result_constant_index_jit(space, i)._utf8 == u[i].encode("utf-8")
        with py.test.raises(OperationError):
            w_u._getitem_result_constant_index_jit(space, len(u))
        with py.test.raises(OperationError):
            w_u._getitem_result_constant_index_jit(space, -len(u) - 1)

    def test_getslice_constant_index_jit(self):
        space = self.space
        u = u"äöabcéééß"
        w_u = self.space.wrap(u)
        for start in range(0, 4):
            for end in range(start, len(u)):
                assert w_u._unicode_sliced_constant_index_jit(space, start, end)._utf8 == u[start: end].encode("utf-8")


class AppTestUnicodeStringStdOnly:
    def test_compares(self):
        assert u'a' == 'a'
        assert 'a' == u'a'
        assert not u'a' == 'b'
        assert not 'a'  == u'b'
        assert u'a' != 'b'
        assert 'a'  != u'b'
        assert not (u'a' == 5)
        assert u'a' != 5
        assert u'a' < 5 or u'a' > 5

        s = chr(128)
        u = unichr(128)
        assert not s == u # UnicodeWarning
        assert s != u
        assert not u == s
        assert u != s


class AppTestUnicodeString:
    spaceconfig = dict(usemodules=('unicodedata',))

    def test_addition(self):
        def check(a, b):
            assert a == b
            assert type(a) == type(b)
        check(u'a' + 'b', u'ab')
        check('a' + u'b', u'ab')

    def test_getitem(self):
        assert u'abc'[2] == 'c'
        raises(IndexError, u'abc'.__getitem__, 15)
        assert u'g\u0105\u015b\u0107'[2] == u'\u015b'

    def test_join(self):
        def check(a, b):
            assert a == b
            assert type(a) == type(b)
        check(', '.join([u'a']), u'a')
        check(', '.join(['a', u'b']), u'a, b')
        check(u', '.join(['a', 'b']), u'a, b')
        try:
            u''.join([u'a', 2, 3])
        except TypeError as e:
            assert 'sequence item 1' in str(e)
        else:
            raise Exception("DID NOT RAISE")

    if sys.version_info >= (2,3):
        def test_contains_ex(self):
            assert u'' in 'abc'
            assert u'bc' in 'abc'
            assert 'bc' in 'abc'
        pass   # workaround for inspect.py bug in some Python 2.4s

    def test_contains(self):
        assert u'a' in 'abc'
        assert 'a' in u'abc'
        raises(UnicodeDecodeError, "u'\xe2' in 'g\xe2teau'")

    def test_splitlines(self):
        assert u''.splitlines() == []
        assert u''.splitlines(1) == []
        assert u'\n'.splitlines() == [u'']
        assert u'a'.splitlines() == [u'a']
        assert u'one\ntwo'.splitlines() == [u'one', u'two']
        assert u'\ntwo\nthree'.splitlines() == [u'', u'two', u'three']
        assert u'\n\n'.splitlines() == [u'', u'']
        assert u'a\nb\nc'.splitlines(1) == [u'a\n', u'b\n', u'c']
        assert u'\na\nb\n'.splitlines(1) == [u'\n', u'a\n', u'b\n']
        assert ((u'a' + '\xc2\x85'.decode('utf8') + u'b\n').splitlines() ==
                ['a', 'b'])

    def test_zfill(self):
        assert u'123'.zfill(2) == u'123'
        assert u'123'.zfill(3) == u'123'
        assert u'123'.zfill(4) == u'0123'
        assert u'123'.zfill(6) == u'000123'
        assert u'+123'.zfill(2) == u'+123'
        assert u'+123'.zfill(3) == u'+123'
        assert u'+123'.zfill(4) == u'+123'
        assert u'+123'.zfill(5) == u'+0123'
        assert u'+123'.zfill(6) == u'+00123'
        assert u'-123'.zfill(3) == u'-123'
        assert u'-123'.zfill(4) == u'-123'
        assert u'-123'.zfill(5) == u'-0123'
        assert u''.zfill(3) == u'000'
        assert u'34'.zfill(1) == u'34'
        assert u'34'.zfill(4) == u'0034'

    def test_split(self):
        assert u"".split() == []
        assert u"".split(u'x') == ['']
        assert u" ".split() == []
        assert u"a".split() == [u'a']
        assert u"a".split(u"a", 1) == [u'', u'']
        assert u" ".split(u" ", 1) == [u'', u'']
        assert u"aa".split(u"a", 2) == [u'', u'', u'']
        assert u" a ".split() == [u'a']
        assert u"a b c".split() == [u'a',u'b',u'c']
        assert u'this is the split function'.split() == [u'this', u'is', u'the', u'split', u'function']
        assert u'a|b|c|d'.split(u'|') == [u'a', u'b', u'c', u'd']
        assert 'a|b|c|d'.split(u'|') == [u'a', u'b', u'c', u'd']
        assert u'a|b|c|d'.split('|') == [u'a', u'b', u'c', u'd']
        assert u'a|b|c|d'.split(u'|', 2) == [u'a', u'b', u'c|d']
        assert u'a b c d'.split(None, 1) == [u'a', u'b c d']
        assert u'a b c d'.split(None, 2) == [u'a', u'b', u'c d']
        assert u'a b c d'.split(None, 3) == [u'a', u'b', u'c', u'd']
        assert u'a b c d'.split(None, 4) == [u'a', u'b', u'c', u'd']
        assert u'a b c d'.split(None, 0) == [u'a b c d']
        assert u'a  b  c  d'.split(None, 2) == [u'a', u'b', u'c  d']
        assert u'a b c d '.split() == [u'a', u'b', u'c', u'd']
        assert u'a//b//c//d'.split(u'//') == [u'a', u'b', u'c', u'd']
        assert u'endcase test'.split(u'test') == [u'endcase ', u'']
        raises(ValueError, u'abc'.split, '')
        raises(ValueError, u'abc'.split, u'')
        raises(ValueError, 'abc'.split, u'')
        assert u'   a b c d'.split(None, 0) == [u'a b c d']
        assert u'a\nb\u1680c'.split() == [u'a', u'b', u'c']

    def test_rsplit(self):
        assert u"".rsplit() == []
        assert u" ".rsplit() == []
        assert u"a".rsplit() == [u'a']
        assert u"a".rsplit(u"a", 1) == [u'', u'']
        assert u" ".rsplit(u" ", 1) == [u'', u'']
        assert u"aa".rsplit(u"a", 2) == [u'', u'', u'']
        assert u" a ".rsplit() == [u'a']
        assert u"a b c".rsplit() == [u'a',u'b',u'c']
        assert u'this is the rsplit function'.rsplit() == [u'this', u'is', u'the', u'rsplit', u'function']
        assert u'a|b|c|d'.rsplit(u'|') == [u'a', u'b', u'c', u'd']
        assert u'a|b|c|d'.rsplit('|') == [u'a', u'b', u'c', u'd']
        assert 'a|b|c|d'.rsplit(u'|') == [u'a', u'b', u'c', u'd']
        assert u'a|b|c|d'.rsplit(u'|', 2) == [u'a|b', u'c', u'd']
        assert u'a b c d'.rsplit(None, 1) == [u'a b c', u'd']
        assert u'a b c d'.rsplit(None, 2) == [u'a b', u'c', u'd']
        assert u'a b c d'.rsplit(None, 3) == [u'a', u'b', u'c', u'd']
        assert u'a b c d'.rsplit(None, 4) == [u'a', u'b', u'c', u'd']
        assert u'a b c d'.rsplit(None, 0) == [u'a b c d']
        assert u'a  b  c  d'.rsplit(None, 2) == [u'a  b', u'c', u'd']
        assert u'a b c d '.rsplit() == [u'a', u'b', u'c', u'd']
        assert u'a//b//c//d'.rsplit(u'//') == [u'a', u'b', u'c', u'd']
        assert u'endcase test'.rsplit(u'test') == [u'endcase ', u'']
        raises(ValueError, u'abc'.rsplit, u'')
        raises(ValueError, u'abc'.rsplit, '')
        raises(ValueError, 'abc'.rsplit, u'')
        assert u'  a b c  '.rsplit(None, 0) == [u'  a b c']
        assert u''.rsplit('aaa') == [u'']
        assert u'a\nb\u1680c'.rsplit() == [u'a', u'b', u'c']

    def test_rsplit_bug(self):
        assert u'Vestur- og Mið'.rsplit() == [u'Vestur-', u'og', u'Mið']

    def test_split_rsplit_str_unicode(self):
        x = 'abc'.split(u'b')
        assert x == [u'a', u'c']
        assert map(type, x) == [unicode, unicode]
        x = 'abc'.rsplit(u'b')
        assert x == [u'a', u'c']
        assert map(type, x) == [unicode, unicode]
        x = 'abc'.split(u'\u4321')
        assert x == [u'abc']
        assert map(type, x) == [unicode]
        x = 'abc'.rsplit(u'\u4321')
        assert x == [u'abc']
        assert map(type, x) == [unicode]
        raises(UnicodeDecodeError, '\x80'.split, u'a')
        raises(UnicodeDecodeError, '\x80'.split, u'')
        raises(UnicodeDecodeError, '\x80'.rsplit, u'a')
        raises(UnicodeDecodeError, '\x80'.rsplit, u'')

    def test_center(self):
        s=u"a b"
        assert s.center(0) == u"a b"
        assert s.center(1) == u"a b"
        assert s.center(2) == u"a b"
        assert s.center(3) == u"a b"
        assert s.center(4) == u"a b "
        assert s.center(5) == u" a b "
        assert s.center(6) == u" a b  "
        assert s.center(7) == u"  a b  "
        assert s.center(8) == u"  a b   "
        assert s.center(9) == u"   a b   "
        assert u'abc'.center(10) == u'   abc    '
        assert u'abc'.center(6) == u' abc  '
        assert u'abc'.center(3) == u'abc'
        assert u'abc'.center(2) == u'abc'
        assert u'abc'.center(5, u'*') == u'*abc*'    # Python 2.4
        assert u'abc'.center(5, '*') == u'*abc*'     # Python 2.4
        raises(TypeError, u'abc'.center, 4, u'cba')

    def test_title(self):
        assert u"brown fox".title() == u"Brown Fox"
        assert u"!brown fox".title() == u"!Brown Fox"
        assert u"bROWN fOX".title() == u"Brown Fox"
        assert u"Brown Fox".title() == u"Brown Fox"
        assert u"bro!wn fox".title() == u"Bro!Wn Fox"
        assert u"brow\u4321n fox".title() == u"Brow\u4321N Fox"
        assert u'\ud800'.title() == u'\ud800'
        assert (unichr(0x345) + u'abc').title() == u'\u0399Abc'
        assert (unichr(0x345) + u'ABC').title() == u'\u0399Abc'

    def test_istitle(self):
        assert u"".istitle() == False
        assert u"!".istitle() == False
        assert u"!!".istitle() == False
        assert u"brown fox".istitle() == False
        assert u"!brown fox".istitle() == False
        assert u"bROWN fOX".istitle() == False
        assert u"Brown Fox".istitle() == True
        assert u"bro!wn fox".istitle() == False
        assert u"Bro!wn fox".istitle() == False
        assert u"!brown Fox".istitle() == False
        assert u"!Brown Fox".istitle() == True
        assert u"Brow&&&&N Fox".istitle() == True
        assert u"!Brow&&&&n Fox".istitle() == False
        assert u'\u1FFc'.istitle()
        assert u'Greek \u1FFcitlecases ...'.istitle()

    def test_islower_isupper_with_titlecase(self):
        # \u01c5 is a char which is neither lowercase nor uppercase, but
        # titlecase
        assert not u'\u01c5abc'.islower()
        assert not u'\u01c5ABC'.isupper()

    def test_lower_upper(self):
        assert u'a'.lower() == u'a'
        assert u'A'.lower() == u'a'
        assert u'\u0105'.lower() == u'\u0105'
        assert u'\u0104'.lower() == u'\u0105'
        assert u'\ud800'.lower() == u'\ud800'
        assert u'a'.upper() == u'A'
        assert u'A'.upper() == u'A'
        assert u'\u0105'.upper() == u'\u0104'
        assert u'\u0104'.upper() == u'\u0104'
        assert u'\ud800'.upper() == u'\ud800'

    def test_capitalize(self):
        assert u"brown fox".capitalize() == u"Brown fox"
        assert u' hello '.capitalize() == u' hello '
        assert u'Hello '.capitalize() == u'Hello '
        assert u'hello '.capitalize() == u'Hello '
        assert u'aaaa'.capitalize() == u'Aaaa'
        assert u'AaAa'.capitalize() == u'Aaaa'
        # check that titlecased chars are lowered correctly
        # \u1ffc is the titlecased char
        assert (u'\u1ff3\u1ff3\u1ffc\u1ffc'.capitalize() ==
                u'\u1ffc\u1ff3\u1ff3\u1ff3')
        # check with cased non-letter chars
        assert (u'\u24c5\u24ce\u24c9\u24bd\u24c4\u24c3'.capitalize() ==
                u'\u24c5\u24e8\u24e3\u24d7\u24de\u24dd')
        assert (u'\u24df\u24e8\u24e3\u24d7\u24de\u24dd'.capitalize() ==
                u'\u24c5\u24e8\u24e3\u24d7\u24de\u24dd')
        assert u'\u2160\u2161\u2162'.capitalize() == u'\u2160\u2171\u2172'
        assert u'\u2170\u2171\u2172'.capitalize() == u'\u2160\u2171\u2172'
        # check with Ll chars with no upper - nothing changes here
        assert (u'\u019b\u1d00\u1d86\u0221\u1fb7'.capitalize() ==
                u'\u019b\u1d00\u1d86\u0221\u1fb7')
        assert u'\ud800'.capitalize() == u'\ud800'
        assert u'xx\ud800'.capitalize() == u'Xx\ud800'

    def test_rjust(self):
        s = u"abc"
        assert s.rjust(2) == s
        assert s.rjust(3) == s
        assert s.rjust(4) == u" " + s
        assert s.rjust(5) == u"  " + s
        assert u'abc'.rjust(10) == u'       abc'
        assert u'abc'.rjust(6) == u'   abc'
        assert u'abc'.rjust(3) == u'abc'
        assert u'abc'.rjust(2) == u'abc'
        assert u'abc'.rjust(5, u'*') == u'**abc'    # Python 2.4
        assert u'abc'.rjust(5, '*') == u'**abc'     # Python 2.4
        raises(TypeError, u'abc'.rjust, 5, u'xx')

    def test_ljust(self):
        s = u"abc"
        assert s.ljust(2) == s
        assert s.ljust(3) == s
        assert s.ljust(4) == s + u" "
        assert s.ljust(5) == s + u"  "
        assert u'abc'.ljust(10) == u'abc       '
        assert u'abc'.ljust(6) == u'abc   '
        assert u'abc'.ljust(3) == u'abc'
        assert u'abc'.ljust(2) == u'abc'
        assert u'abc'.ljust(5, u'*') == u'abc**'    # Python 2.4
        assert u'abc'.ljust(5, '*') == u'abc**'     # Python 2.4
        raises(TypeError, u'abc'.ljust, 6, u'')

    def test_replace(self):
        assert u'one!two!three!'.replace(u'!', '@', 1) == u'one@two!three!'
        assert u'one!two!three!'.replace('!', u'') == u'onetwothree'
        assert u'one!two!three!'.replace(u'!', u'@', 2) == u'one@two@three!'
        assert u'one!two!three!'.replace('!', '@', 3) == u'one@two@three@'
        assert u'one!two!three!'.replace(u'!', '@', 4) == u'one@two@three@'
        assert u'one!two!three!'.replace('!', u'@', 0) == u'one!two!three!'
        assert u'one!two!three!'.replace(u'!', u'@') == u'one@two@three@'
        assert u'one!two!three!'.replace('x', '@') == u'one!two!three!'
        assert u'one!two!three!'.replace(u'x', '@', 2) == u'one!two!three!'
        assert u'abc'.replace('', u'-') == u'-a-b-c-'
        assert u'\u1234'.replace(u'', '-') == u'-\u1234-'
        assert u'\u0234\u5678'.replace('', u'-') == u'-\u0234-\u5678-'
        assert u'\u0234\u5678'.replace('', u'-', 0) == u'\u0234\u5678'
        assert u'\u0234\u5678'.replace('', u'-', 1) == u'-\u0234\u5678'
        assert u'\u0234\u5678'.replace('', u'-', 2) == u'-\u0234-\u5678'
        assert u'\u0234\u5678'.replace('', u'-', 3) == u'-\u0234-\u5678-'
        assert u'\u0234\u5678'.replace('', u'-', 4) == u'-\u0234-\u5678-'
        assert u'\u0234\u5678'.replace('', u'-', 700) == u'-\u0234-\u5678-'
        assert u'\u0234\u5678'.replace('', u'-', -1) == u'-\u0234-\u5678-'
        assert u'\u0234\u5678'.replace('', u'-', -42) == u'-\u0234-\u5678-'
        assert u'abc'.replace(u'', u'-', 3) == u'-a-b-c'
        assert u'abc'.replace('', '-', 0) == u'abc'
        assert u''.replace(u'', '') == u''
        assert u''.replace('', u'a') == u'a'
        assert u'abc'.replace(u'ab', u'--', 0) == u'abc'
        assert u'abc'.replace('xy', '--') == u'abc'
        assert u'123'.replace(u'123', '') == u''
        assert u'123123'.replace('123', u'') == u''
        assert u'123x123'.replace(u'123', u'') == u'x'

    def test_replace_buffer(self):
        assert u'one!two!three'.replace(buffer('!'), buffer('@')) == u'one@two@three'

    def test_replace_overflow(self):
        import sys
        if sys.maxint > 2**31-1:
            skip("Wrong platform")
        s = u"a" * (2**16)
        raises(OverflowError, s.replace, u"", s)

    def test_strip(self):
        s = u" a b "
        assert s.strip() == u"a b"
        assert s.rstrip() == u" a b"
        assert s.lstrip() == u"a b "
        assert u'xyzzyhelloxyzzy'.strip(u'xyz') == u'hello'
        assert u'xyzzyhelloxyzzy'.lstrip('xyz') == u'helloxyzzy'
        assert u'xyzzyhelloxyzzy'.rstrip(u'xyz') == u'xyzzyhello'
        exc = raises(TypeError, s.strip, buffer(' '))
        assert str(exc.value) == 'strip arg must be None, unicode or str'
        exc = raises(TypeError, s.rstrip, buffer(' '))
        assert str(exc.value) == 'rstrip arg must be None, unicode or str'
        exc = raises(TypeError, s.lstrip, buffer(' '))
        assert str(exc.value) == 'lstrip arg must be None, unicode or str'

    def test_strip_str_unicode(self):
        x = "--abc--".strip(u"-")
        assert (x, type(x)) == (u"abc", unicode)
        x = "--abc--".lstrip(u"-")
        assert (x, type(x)) == (u"abc--", unicode)
        x = "--abc--".rstrip(u"-")
        assert (x, type(x)) == (u"--abc", unicode)
        raises(UnicodeDecodeError, "\x80".strip, u"")
        raises(UnicodeDecodeError, "\x80".lstrip, u"")
        raises(UnicodeDecodeError, "\x80".rstrip, u"")

    def test_long_from_unicode(self):
        assert long(u'12345678901234567890') == 12345678901234567890
        assert int(u'12345678901234567890') == 12345678901234567890
        assert long(u'123', 7) == 66

    def test_int_from_unicode(self):
        assert int(u'12345') == 12345

    def test_float_from_unicode(self):
        assert float(u'123.456e89') == float('123.456e89')

    def test_repr_16bits(self):
        # this used to fail when run on a CPython host with 16-bit unicodes
        s = repr(u'\U00101234')
        assert s == "u'\\U00101234'"

    def test_repr(self):
        for ustr in [u"", u"a", u"'", u"\'", u"\"", u"\t", u"\\", u'',
                     u'a', u'"', u'\'', u'\"', u'\t', u'\\', u"'''\"",
                     unichr(19), unichr(2), u'\u1234', u'\U00101234']:
            assert eval(repr(ustr)) == ustr

    def test_getnewargs(self):
        class X(unicode):
            pass
        x = X(u"foo\u1234")
        a = x.__getnewargs__()
        assert a == (u"foo\u1234",)
        assert type(a[0]) is unicode

    def test_call_unicode(self):
        assert unicode() == u''
        assert unicode(None) == u'None'
        assert unicode(123) == u'123'
        assert unicode([2, 3]) == u'[2, 3]'
        class U(unicode):
            pass
        assert unicode(U()).__class__ is unicode
        assert U(u'test') == u'test'
        assert U(u'test').__class__ is U

    def test_call_unicode_2(self):
        class X(object):
            def __unicode__(self):
                return u'x'
        raises(TypeError, unicode, X(), 'ascii')

    def test_startswith(self):
        assert u'ab'.startswith(u'ab') is True
        assert u'ab'.startswith(u'a') is True
        assert u'ab'.startswith(u'') is True
        assert u'x'.startswith(u'a') is False
        assert u'x'.startswith(u'x') is True
        assert u''.startswith(u'') is True
        assert u''.startswith(u'a') is False
        assert u'x'.startswith(u'xx') is False
        assert u'y'.startswith(u'xx') is False
        assert u'\u1234\u5678\u4321'.startswith(u'\u1234') is True
        assert u'\u1234\u5678\u4321'.startswith(u'\u1234\u4321') is False
        assert u'\u1234'.startswith(u'', 1, 0) is True

    def test_startswith_more(self):
        assert u'ab'.startswith(u'a', 0) is True
        assert u'ab'.startswith(u'a', 1) is False
        assert u'ab'.startswith(u'b', 1) is True
        assert u'abc'.startswith(u'bc', 1, 2) is False
        assert u'abc'.startswith(u'c', -1, 4) is True

    def test_startswith_too_large(self):
        assert u'ab'.startswith(u'b', 1) is True
        assert u'ab'.startswith(u'', 2) is True
        assert u'ab'.startswith(u'', 3) is True   # not False
        assert u'ab'.endswith(u'b', 1) is True
        assert u'ab'.endswith(u'', 2) is True
        assert u'ab'.endswith(u'', 3) is True   # not False

    def test_startswith_tuples(self):
        assert u'hello'.startswith((u'he', u'ha'))
        assert not u'hello'.startswith((u'lo', u'llo'))
        assert u'hello'.startswith((u'hellox', u'hello'))
        assert not u'hello'.startswith(())
        assert u'helloworld'.startswith((u'hellowo', u'rld', u'lowo'), 3)
        assert not u'helloworld'.startswith((u'hellowo', u'ello', u'rld'), 3)
        assert u'hello'.startswith((u'lo', u'he'), 0, -1)
        assert not u'hello'.startswith((u'he', u'hel'), 0, 1)
        assert u'hello'.startswith((u'he', u'hel'), 0, 2)
        raises(TypeError, u'hello'.startswith, (42,))

    def test_startswith_endswith_convert(self):
        assert 'hello'.startswith((u'he\u1111', u'he'))
        assert not 'hello'.startswith((u'lo\u1111', u'llo'))
        assert 'hello'.startswith((u'hellox\u1111', u'hello'))
        assert not 'hello'.startswith((u'lo', u'he\u1111'), 0, -1)
        assert not 'hello'.endswith((u'he\u1111', u'he'))
        assert 'hello'.endswith((u'\u1111lo', u'llo'))
        assert 'hello'.endswith((u'\u1111hellox', u'hello'))

    def test_endswith(self):
        assert u'ab'.endswith(u'ab') is True
        assert u'ab'.endswith(u'b') is True
        assert u'ab'.endswith(u'') is True
        assert u'x'.endswith(u'a') is False
        assert u'x'.endswith(u'x') is True
        assert u''.endswith(u'') is True
        assert u''.endswith(u'a') is False
        assert u'x'.endswith(u'xx') is False
        assert u'y'.endswith(u'xx') is False

    def test_endswith_more(self):
        assert u'abc'.endswith(u'ab', 0, 2) is True
        assert u'abc'.endswith(u'bc', 1) is True
        assert u'abc'.endswith(u'bc', 2) is False
        assert u'abc'.endswith(u'b', -3, -1) is True

    def test_endswith_tuple(self):
        assert not u'hello'.endswith((u'he', u'ha'))
        assert u'hello'.endswith((u'lo', u'llo'))
        assert u'hello'.endswith((u'hellox', u'hello'))
        assert not u'hello'.endswith(())
        assert u'helloworld'.endswith((u'hellowo', u'rld', u'lowo'), 3)
        assert not u'helloworld'.endswith((u'hellowo', u'ello', u'rld'), 3, -1)
        assert u'hello'.endswith((u'hell', u'ell'), 0, -1)
        assert not u'hello'.endswith((u'he', u'hel'), 0, 1)
        assert u'hello'.endswith((u'he', u'hell'), 0, 4)
        raises(TypeError, u'hello'.endswith, (42,))

    def test_expandtabs(self):
        assert u'abc\rab\tdef\ng\thi'.expandtabs() ==    u'abc\rab      def\ng       hi'
        assert u'abc\rab\tdef\ng\thi'.expandtabs(8) ==   u'abc\rab      def\ng       hi'
        assert u'abc\rab\tdef\ng\thi'.expandtabs(4) ==   u'abc\rab  def\ng   hi'
        assert u'abc\r\nab\tdef\ng\thi'.expandtabs(4) == u'abc\r\nab  def\ng   hi'
        assert u'abc\rab\tdef\ng\thi'.expandtabs() ==    u'abc\rab      def\ng       hi'
        assert u'abc\rab\tdef\ng\thi'.expandtabs(8) ==   u'abc\rab      def\ng       hi'
        assert u'abc\r\nab\r\ndef\ng\r\nhi'.expandtabs(4) == u'abc\r\nab\r\ndef\ng\r\nhi'

        s = u'xy\t'
        assert s.expandtabs() =='xy      '

        s = u'\txy\t'
        assert s.expandtabs() =='        xy      '
        assert s.expandtabs(1) ==' xy '
        assert s.expandtabs(2) =='  xy  '
        assert s.expandtabs(3) =='   xy '

        assert u'xy'.expandtabs() =='xy'
        assert u''.expandtabs() ==''

    def test_expandtabs_overflows_gracefully(self):
        import sys
        if sys.maxint > (1 << 32):
            skip("Wrong platform")
        raises((OverflowError, MemoryError), u't\tt\t'.expandtabs, sys.maxint)

    def test_expandtabs_0(self):
        assert u'x\ty'.expandtabs(0) == u'xy'
        assert u'x\ty'.expandtabs(-42) == u'xy'

    def test_translate(self):
        assert u'bbbc' == u'abababc'.translate({ord('a'):None})
        assert u'iiic' == u'abababc'.translate({ord('a'):None, ord('b'):ord('i')})
        assert u'iiix' == u'abababc'.translate({ord('a'):None, ord('b'):ord('i'), ord('c'):u'x'})
        assert u'<i><i><i>c' == u'abababc'.translate({ord('a'):None, ord('b'):u'<i>'})
        assert u'c' == u'abababc'.translate({ord('a'):None, ord('b'):u''})
        assert u'xyyx' == u'xzx'.translate({ord('z'):u'yy'})
        assert u'abcd' == u'ab\0d'.translate(u'c')
        assert u'abcd' == u'abcd'.translate(u'')

        raises(TypeError, u'hello'.translate)
        raises(TypeError, u'abababc'.translate, {ord('a'):''})
        raises(TypeError, u'x'.translate, {ord('x'):0x110000})

    def test_unicode_from_encoded_object(self):
        assert unicode('x', 'utf-8') == u'x'
        assert unicode('x', 'utf-8', 'strict') == u'x'

    def test_unicode_startswith_tuple(self):
        assert u'xxx'.startswith(('x', 'y', 'z'), 0)
        assert u'xxx'.endswith(('x', 'y', 'z'), 0)

    def test_missing_cases(self):
        # some random cases, which are discovered to not be tested during annotation
        assert u'xxx'[1:1] == u''

    # these tests test lots of encodings, so they really belong to the _codecs
    # module. however, they test useful unicode methods too
    # they are stolen from CPython's unit tests

    def test_codecs_utf7(self):
        utfTests = [
            (u'A\u2262\u0391.', 'A+ImIDkQ.'),             # RFC2152 example
            (u'Hi Mom -\u263a-!', 'Hi Mom -+Jjo--!'),     # RFC2152 example
            (u'\u65E5\u672C\u8A9E', '+ZeVnLIqe-'),        # RFC2152 example
            (u'Item 3 is \u00a31.', 'Item 3 is +AKM-1.'), # RFC2152 example
            (u'+', '+-'),
            (u'+-', '+--'),
            (u'+?', '+-?'),
            (u'\?', '+AFw?'),
            (u'+?', '+-?'),
            (ur'\\?', '+AFwAXA?'),
            (ur'\\\?', '+AFwAXABc?'),
            (ur'++--', '+-+---'),
        ]

        for (x, y) in utfTests:
            assert x.encode('utf-7') == y

        # surrogates are supported
        assert unicode('+3ADYAA-', 'utf-7') == u'\udc00\ud800'

        assert unicode('+AB', 'utf-7', 'replace') == u'\ufffd'

    def test_codecs_utf8(self):
        assert u''.encode('utf-8') == ''
        assert u'\u20ac'.encode('utf-8') == '\xe2\x82\xac'
        assert u'\ud800\udc02'.encode('utf-8') == '\xf0\x90\x80\x82'
        assert u'\ud84d\udc56'.encode('utf-8') == '\xf0\xa3\x91\x96'
        assert u'\ud800\udc02'.encode('uTf-8') == '\xf0\x90\x80\x82'
        assert u'\ud84d\udc56'.encode('Utf8') == '\xf0\xa3\x91\x96'
        assert u'\ud800'.encode('utf-8') == '\xed\xa0\x80'
        assert u'\udc00'.encode('utf-8') == '\xed\xb0\x80'
        assert (u'\ud800\udc02'*1000).encode('utf-8') == '\xf0\x90\x80\x82'*1000
        assert (
            u'\u6b63\u78ba\u306b\u8a00\u3046\u3068\u7ffb\u8a33\u306f'
            u'\u3055\u308c\u3066\u3044\u307e\u305b\u3093\u3002\u4e00'
            u'\u90e8\u306f\u30c9\u30a4\u30c4\u8a9e\u3067\u3059\u304c'
            u'\u3001\u3042\u3068\u306f\u3067\u305f\u3089\u3081\u3067'
            u'\u3059\u3002\u5b9f\u969b\u306b\u306f\u300cWenn ist das'
            u' Nunstuck git und'.encode('utf-8') == 
            '\xe6\xad\xa3\xe7\xa2\xba\xe3\x81\xab\xe8\xa8\x80\xe3\x81'
            '\x86\xe3\x81\xa8\xe7\xbf\xbb\xe8\xa8\xb3\xe3\x81\xaf\xe3'
            '\x81\x95\xe3\x82\x8c\xe3\x81\xa6\xe3\x81\x84\xe3\x81\xbe'
            '\xe3\x81\x9b\xe3\x82\x93\xe3\x80\x82\xe4\xb8\x80\xe9\x83'
            '\xa8\xe3\x81\xaf\xe3\x83\x89\xe3\x82\xa4\xe3\x83\x84\xe8'
            '\xaa\x9e\xe3\x81\xa7\xe3\x81\x99\xe3\x81\x8c\xe3\x80\x81'
            '\xe3\x81\x82\xe3\x81\xa8\xe3\x81\xaf\xe3\x81\xa7\xe3\x81'
            '\x9f\xe3\x82\x89\xe3\x82\x81\xe3\x81\xa7\xe3\x81\x99\xe3'
            '\x80\x82\xe5\xae\x9f\xe9\x9a\x9b\xe3\x81\xab\xe3\x81\xaf'
            '\xe3\x80\x8cWenn ist das Nunstuck git und'
        )

        # UTF-8 specific decoding tests
        assert unicode('\xf0\xa3\x91\x96', 'utf-8') == u'\U00023456' 
        assert unicode('\xf0\x90\x80\x82', 'utf-8') == u'\U00010002' 
        assert unicode('\xe2\x82\xac', 'utf-8') == u'\u20ac' 

    def test_codecs_errors(self):
        # Error handling (encoding)
        raises(UnicodeError, u'Andr\202 x'.encode, 'ascii')
        raises(UnicodeError, u'Andr\202 x'.encode, 'ascii','strict')
        assert u'Andr\202 x'.encode('ascii','ignore') == "Andr x"
        assert u'Andr\202 x'.encode('ascii','replace') == "Andr? x"

        # Error handling (decoding)
        raises(UnicodeError, unicode, 'Andr\202 x', 'ascii')
        raises(UnicodeError, unicode, 'Andr\202 x', 'ascii','strict')
        assert unicode('Andr\202 x','ascii','ignore') == u"Andr x"
        assert unicode('Andr\202 x','ascii','replace') == u'Andr\uFFFD x'

        # Error handling (unknown character names)
        assert "\\N{foo}xx".decode("unicode-escape", "ignore") == u"xx"

        # Error handling (truncated escape sequence)
        raises(UnicodeError, "\\".decode, "unicode-escape")

        raises(UnicodeError, "\xc2".decode, "utf-8")
        assert '\xe1\x80'.decode('utf-8', 'replace') == u"\ufffd"

    def test_repr_bug(self):
        assert (repr(u'\U00090418\u027d\U000582b9\u54c3\U000fcb6e') == 
                "u'\\U00090418\\u027d\\U000582b9\\u54c3\\U000fcb6e'")
        assert (repr(u'\n') == 
                "u'\\n'")


    def test_partition(self):
        assert (u'this is the par', u'ti', u'tion method') == \
            u'this is the partition method'.partition(u'ti')

        # from raymond's original specification
        S = u'http://www.python.org'
        assert (u'http', u'://', u'www.python.org') == S.partition(u'://')
        assert (u'http://www.python.org', u'', u'') == S.partition(u'?')
        assert (u'', u'http://', u'www.python.org') == S.partition(u'http://')
        assert (u'http://www.python.', u'org', u'') == S.partition(u'org')

        raises(ValueError, S.partition, u'')
        raises(TypeError, S.partition, None)

    def test_rpartition(self):
        assert (u'this is the rparti', u'ti', u'on method') == \
            u'this is the rpartition method'.rpartition(u'ti')

        # from raymond's original specification
        S = u'http://www.python.org'
        assert (u'http', u'://', u'www.python.org') == S.rpartition(u'://')
        assert (u'', u'', u'http://www.python.org') == S.rpartition(u'?')
        assert (u'', u'http://', u'www.python.org') == S.rpartition(u'http://')
        assert (u'http://www.python.', u'org', u'') == S.rpartition(u'org')

        raises(ValueError, S.rpartition, u'')
        raises(TypeError, S.rpartition, None)

    def test_partition_str_unicode(self):
        x = 'abbbd'.rpartition(u'bb')
        assert x == (u'ab', u'bb', u'd')
        assert map(type, x) == [unicode, unicode, unicode]
        raises(UnicodeDecodeError, '\x80'.partition, u'')
        raises(UnicodeDecodeError, '\x80'.rpartition, u'')

    def test_mul(self):
        zero = 0
        assert type(u'' * zero) == type(zero * u'') == unicode
        assert u'' * zero == zero * u'' == u''
        assert u'x' * zero == zero * u'x' == u''
        assert type(u'x' * zero) == type(zero * u'x') == unicode
        assert u'123' * zero == zero * u'123' == u''
        assert type(u'123' * zero) == type(zero * u'123') == unicode
        for i in range(10):
            u = u'123' * i
            assert len(u) == 3*i
            for j in range(0, i, 3):
                assert u[j+0] == u'1'
                assert u[j+1] == u'2'
                assert u[j+2] == u'3'
            assert u'123' * i == i * u'123'

    def test_index(self):
        assert u"rrarrrrrrrrra".index(u'a', 4, None) == 12
        assert u"rrarrrrrrrrra".index(u'a', None, 6) == 2
        assert u"\u1234\u4321\u5678".index(u'\u5678', 1) == 2

    def test_rindex(self):
        from sys import maxint
        assert u'abcdefghiabc'.rindex(u'') == 12
        assert u'abcdefghiabc'.rindex(u'def') == 3
        assert u'abcdefghiabc'.rindex(u'abc') == 9
        assert u'abcdefghiabc'.rindex(u'abc', 0, -1) == 0
        assert u'abcdefghiabc'.rindex(u'abc', -4*maxint, 4*maxint) == 9
        assert u'rrarrrrrrrrra'.rindex(u'a', 4, None) == 12
        assert u"\u1234\u5678".rindex(u'\u5678') == 1

        raises(ValueError, u'abcdefghiabc'.rindex, u'hib')
        raises(ValueError, u'defghiabc'.rindex, u'def', 1)
        raises(ValueError, u'defghiabc'.rindex, u'abc', 0, -1)
        raises(ValueError, u'abcdefghi'.rindex, u'ghi', 0, 8)
        raises(ValueError, u'abcdefghi'.rindex, u'ghi', 0, -1)
        raises(TypeError, u'abcdefghijklmn'.rindex, u'abc', 0, 0.0)
        raises(TypeError, u'abcdefghijklmn'.rindex, u'abc', -10.0, 30)

    def test_rfind(self):
        assert u'abcdefghiabc'.rfind(u'abc') == 9
        assert u'abcdefghiabc'.rfind(u'') == 12
        assert u'abcdefghiabc'.rfind(u'abcd') == 0
        assert u'abcdefghiabc'.rfind(u'abcz') == -1
        assert u"\u1234\u5678".rfind(u'\u5678') == 1

    def test_rfind_corner_case(self):
        assert u'abc'.rfind('', 4) == -1

    def test_find_index_str_unicode(self):
        assert u'abcdefghiabc'.find(u'bc') == 1
        assert u'ab\u0105b\u0107'.find('b', 2) == 3
        assert u'ab\u0105b\u0107'.find('b', 0, 1) == -1
        assert 'abcdefghiabc'.rfind(u'abc') == 9
        raises(UnicodeDecodeError, '\x80'.find, u'')
        raises(UnicodeDecodeError, '\x80'.rfind, u'')
        assert 'abcdefghiabc'.index(u'bc') == 1
        assert 'abcdefghiabc'.rindex(u'abc') == 9
        raises(UnicodeDecodeError, '\x80'.index, u'')
        raises(UnicodeDecodeError, '\x80'.rindex, u'')
        assert u"\u1234\u5678".find(u'\u5678') == 1

    def test_count_unicode(self):
        assert u'aaa'.count('', 10) == 0
        assert u'aaa'.count('', 3) == 1
        assert u"".count(u"x") ==0
        assert u"".count(u"") ==1
        assert u"Python".count(u"") ==7
        assert u"ab aaba".count(u"ab") ==2
        assert u'aaa'.count(u'a') == 3
        assert u'aaa'.count(u'b') == 0
        assert u'aaa'.count(u'a', -1) == 1
        assert u'aaa'.count(u'a', -10) == 3
        assert u'aaa'.count(u'a', 0, -1) == 2
        assert u'aaa'.count(u'a', 0, -10) == 0
        assert u'ababa'.count(u'aba') == 1

    def test_count_str_unicode(self):
        assert 'aaa'.count(u'a') == 3
        assert 'aaa'.count(u'b') == 0
        assert 'aaa'.count(u'a', -1) == 1
        assert 'aaa'.count(u'a', -10) == 3
        assert 'aaa'.count(u'a', 0, -1) == 2
        assert 'aaa'.count(u'a', 0, -10) == 0
        assert 'ababa'.count(u'aba') == 1
        raises(UnicodeDecodeError, '\x80'.count, u'')

    def test_swapcase(self):
        assert u'\xe4\xc4\xdf'.swapcase() == u'\xc4\xe4\xdf'
        assert u'\ud800'.swapcase() == u'\ud800'

    def test_buffer(self):
        buf = buffer(u'XY')
        assert str(buf) in ['X\x00Y\x00',
                            '\x00X\x00Y',
                            'X\x00\x00\x00Y\x00\x00\x00',
                            '\x00\x00\x00X\x00\x00\x00Y']

    def test_call_special_methods(self):
        # xxx not completely clear if these are implementation details or not
        assert 'abc'.__add__(u'def') == u'abcdef'
        assert u'abc'.__add__(u'def') == u'abcdef'
        assert u'abc'.__add__('def') == u'abcdef'
        assert u'abc'.__rmod__(u'%s') == u'abc'
        ret = u'abc'.__rmod__('%s')
        raises(AttributeError, "u'abc'.__radd__(u'def')")

    def test_str_unicode_concat_overrides(self):
        "Test from Jython about being bug-compatible with CPython."

        def check(value, expected):
            assert type(value) == type(expected)
            assert value == expected

        def _test_concat(t1, t2):
            tprecedent = str
            if issubclass(t1, unicode) or issubclass(t2, unicode):
                tprecedent = unicode

            class SubclassB(t2):
                def __add__(self, other):
                    return SubclassB(t2(self) + t2(other))
            check(SubclassB('py') + SubclassB('thon'), SubclassB('python'))
            check(t1('python') + SubclassB('3'), tprecedent('python3'))
            check(SubclassB('py') + t1('py'), SubclassB('pypy'))

            class SubclassC(t2):
                def __radd__(self, other):
                    return SubclassC(t2(other) + t2(self))
            check(SubclassC('stack') + SubclassC('less'), t2('stackless'))
            check(t1('iron') + SubclassC('python'), SubclassC('ironpython'))
            check(SubclassC('tiny') + t1('py'), tprecedent('tinypy'))

            class SubclassD(t2):
                def __add__(self, other):
                    return SubclassD(t2(self) + t2(other))

                def __radd__(self, other):
                    return SubclassD(t2(other) + t2(self))
            check(SubclassD('di') + SubclassD('ct'), SubclassD('dict'))
            check(t1('list') + SubclassD(' comp'), SubclassD('list comp'))
            check(SubclassD('dun') + t1('der'), SubclassD('dunder'))

        _test_concat(str, str)
        _test_concat(unicode, unicode)
        # the following two cases are really there to emulate a CPython bug.
        _test_concat(str, unicode)   # uses hack in add__String_Unicode()
        _test_concat(unicode, str)   # uses hack in descroperation.binop_impl()

    def test_returns_subclass(self):
        class X(unicode):
            pass

        class Y(object):
            def __unicode__(self):
                return X("stuff")

        assert unicode(Y()).__class__ is X

    def test_getslice(self):
        assert u'123456'.__getslice__(1, 5) == u'2345'
        s = u"\u0105b\u0107"
        assert s[:] == u"\u0105b\u0107"
        assert s[1:] == u"b\u0107"
        assert s[:2] == u"\u0105b"
        assert s[1:2] == u"b"
        assert s[-2:] == u"b\u0107"
        assert s[:-1] == u"\u0105b"
        assert s[-2:2] == u"b"
        assert s[1:-1] == u"b"
        assert s[-2:-1] == u"b"

    def test_getitem_slice(self):
        assert u'123456'.__getitem__(slice(1, 5)) == u'2345'
        s = u"\u0105b\u0107"
        assert s[slice(3)] == u"\u0105b\u0107"
        assert s[slice(1, 3)] == u"b\u0107"
        assert s[slice(2)] == u"\u0105b"
        assert s[slice(1,2)] == u"b"
        assert s[slice(-2,3)] == u"b\u0107"
        assert s[slice(-1)] == u"\u0105b"
        assert s[slice(-2,2)] == u"b"
        assert s[slice(1,-1)] == u"b"
        assert s[slice(-2,-1)] == u"b"
        assert u"abcde"[::2] == u"ace"
        assert u"\u0105\u0106\u0107abcd"[::2] == u"\u0105\u0107bd"

    def test_no_len_on_str_iter(self):
        iterable = u"hello"
        raises(TypeError, len, iter(iterable))

    def test_encode_raw_unicode_escape(self):
        u = unicode('\\', 'raw_unicode_escape')
        assert u == u'\\'

    def test_decode_from_buffer(self):
        buf = buffer('character buffers are decoded to unicode')
        u = unicode(buf, 'utf-8', 'strict')
        assert u == u'character buffers are decoded to unicode'

    def test_unicode_conversion_with__unicode__(self):
        class A(unicode):
            def __unicode__(self):
                return "foo"
        class B(unicode):
            pass
        a = A('bar')
        assert a == 'bar'
        assert unicode(a) == 'foo'
        b = B('bar')
        assert b == 'bar'
        assert unicode(b) == 'bar'

    def test_unicode_conversion_with__str__(self):
        # new-style classes
        class A(object):
            def __str__(self):
                return u'\u1234'
        s = unicode(A())
        assert type(s) is unicode
        assert s == u'\u1234'
        # with old-style classes, it's different, but it should work as well
        class A:
            def __str__(self):
                return u'\u1234'
        s = unicode(A())
        assert type(s) is unicode
        assert s == u'\u1234'

    def test_formatting_unicode__str__(self):
        class A:
            def __init__(self, num):
                self.num = num
            def __str__(self):
                return unichr(self.num)

        s = '%s' % A(111)    # this is ASCII
        assert type(s) is unicode
        assert s == chr(111)

        s = '%s' % A(0x1234)    # this is not ASCII
        assert type(s) is unicode
        assert s == u'\u1234'

        # now the same with a new-style class...
        class A(object):
            def __init__(self, num):
                self.num = num
            def __str__(self):
                return unichr(self.num)

        s = '%s' % A(111)    # this is ASCII
        assert type(s) is unicode
        assert s == chr(111)

        s = '%s' % A(0x1234)    # this is not ASCII
        assert type(s) is unicode
        assert s == u'\u1234'

    def test_formatting_unicode__str__2(self):
        class A:
            def __str__(self):
                return u'baz'

        class B:
            def __str__(self):
                return 'foo'

            def __unicode__(self):
                return u'bar'

        a = A()
        b = B()
        s = '%s %s' % (a, b)
        assert s == u'baz bar'

        skip("but this case here is completely insane")
        s = '%s %s' % (b, a)
        assert s == u'foo baz'

    def test_formatting_unicode__str__3(self):
        # "bah" is all I can say
        class X(object):
            def __repr__(self):
                return u'\u1234'
        '%s' % X()
        #
        class X(object):
            def __str__(self):
                return u'\u1234'
        '%s' % X()

    def test_format_repeat(self):
        assert format(u"abc", u"z<5") == u"abczz"
        assert format(u"abc", u"\u2007<5") == u"abc\u2007\u2007"
        # raises UnicodeEncodeError, like CPython does
        raises(UnicodeEncodeError, format, 123, u"\u2007<5")

    def test_formatting_char(self):
        for num in range(0x80,0x100):
            uchar = unichr(num)
            print num
            assert uchar == u"%c" % num   # works only with ints
            assert uchar == u"%c" % uchar # and unicode chars
            # the implicit decoding should fail for non-ascii chars
            raises(UnicodeDecodeError, u"%c".__mod__, chr(num))
            raises(UnicodeDecodeError, u"%s".__mod__, chr(num))

    def test_str_subclass(self):
        class Foo9(str):
            def __unicode__(self):
                return u"world"
        assert unicode(Foo9("hello")) == u"world"

    def test_class_with_both_str_and_unicode(self):
        class A(object):
            def __str__(self):
                return 'foo'

            def __unicode__(self):
                return u'bar'

        assert unicode(A()) == u'bar'

        class A:
            def __str__(self):
                return 'foo'

            def __unicode__(self):
                return u'bar'

        assert unicode(A()) == u'bar'

    def test_format_unicode_subclass(self):
        class U(unicode):
            def __unicode__(self):
                return u'__unicode__ overridden'
        u = U(u'xxx')
        assert repr("%s" % u) == "u'__unicode__ overridden'"
        assert repr("{}".format(u)) == "'__unicode__ overridden'"

    def test_format_c_overflow(self):
        import sys
        raises(OverflowError, u'{0:c}'.format, -1)
        raises(OverflowError, u'{0:c}'.format, sys.maxunicode + 1)

    def test_replace_with_buffer(self):
        assert u'abc'.replace(buffer('b'), buffer('e')) == u'aec'
        assert u'abc'.replace(buffer('b'), u'e') == u'aec'
        assert u'abc'.replace(u'b', buffer('e')) == u'aec'

    def test_unicode_subclass(self):
        class S(unicode):
            pass

        a = S(u'hello \u1234')
        b = unicode(a)
        assert type(b) is unicode
        assert b == u'hello \u1234'

        assert u'%s' % S(u'mar\xe7') == u'mar\xe7'

    def test_isdecimal(self):
        assert u'0'.isdecimal()
        assert not u''.isdecimal()
        assert not u'a'.isdecimal()
        assert not u'\u2460'.isdecimal() # CIRCLED DIGIT ONE

    def test_isnumeric(self):
        assert u'0'.isnumeric()
        assert not u''.isnumeric()
        assert not u'a'.isnumeric()
        assert u'\u2460'.isnumeric() # CIRCLED DIGIT ONE

    def test_replace_str_unicode(self):
        res = 'one!two!three!'.replace(u'!', u'@', 1)
        assert res == u'one@two!three!'
        assert type(res) == unicode
        raises(UnicodeDecodeError, '\x80'.replace, 'a', u'b')
        raises(UnicodeDecodeError, '\x80'.replace, u'a', 'b')

    def test_join_subclass(self):
        class UnicodeSubclass(unicode):
            pass
        class StrSubclass(str):
            pass

        s1 = UnicodeSubclass(u'a')
        assert u''.join([s1]) is not s1
        s2 = StrSubclass(u'a')
        assert u''.join([s2]) is not s2

    def test_encoding_and_errors_cant_be_none(self):
        raises(TypeError, "''.decode(None)")
        raises(TypeError, "u''.encode(None)")
        raises(TypeError, "unicode('', encoding=None)")
        raises(TypeError, 'u"".encode("utf-8", None)')

    def test_unicode_constructor_misc(self):
        x = u'foo'
        x += u'bar'
        assert unicode(x) is x
        #
        class U(unicode):
            def __unicode__(self):
                return u'BOK'
        u = U(x)
        assert unicode(u) == u'BOK'
        #
        class U2(unicode):
            pass
        z = U2(u'foobaz')
        assert type(unicode(z)) is unicode
        assert unicode(z) == u'foobaz'
        #
        assert unicode(encoding='supposedly_the_encoding') == u''
        assert unicode(errors='supposedly_the_error') == u''
        e = raises(TypeError, unicode, u'', 'supposedly_the_encoding')
        assert str(e.value) == 'decoding Unicode is not supported'
        e = raises(TypeError, unicode, u'', errors='supposedly_the_error')
        assert str(e.value) == 'decoding Unicode is not supported'
        e = raises(TypeError, unicode, u, 'supposedly_the_encoding')
        assert str(e.value) == 'decoding Unicode is not supported'
        e = raises(TypeError, unicode, z, 'supposedly_the_encoding')
        assert str(e.value) == 'decoding Unicode is not supported'

    def test_newlist_utf8_non_ascii(self):
        'ä'.split("\n")[0] # does not crash
