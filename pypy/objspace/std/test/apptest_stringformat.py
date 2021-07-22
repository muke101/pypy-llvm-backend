# coding: utf-8
import sys

def test_format_item_dict():
    d = {'i': 23}
    assert 'a23b' == 'a%(i)sb' % d
    assert '23b' == '%(i)sb' % d
    assert 'a23' == 'a%(i)s' % d
    assert '23' == '%(i)s' % d

def test_format_two_items():
    d = {'i': 23, 'j': 42}
    assert 'a23b42c' == 'a%(i)sb%(j)sc' % d
    assert 'a23b23c' == 'a%(i)sb%(i)sc' % d

def test_format_percent_dict():
    d = {}
    assert 'a%b' == 'a%%b' % d

def test_format_empty_key():
    d = {'':42}
    assert '42' == '%()s' % d

def test_format_wrong_char_dict():
    d = {'i': 23}
    raises(ValueError, 'a%(i)Zb'.__mod__, d) 

def test_format_missing():
    d = {'i': 23}
    raises(KeyError, 'a%(x)sb'.__mod__, d) 

def test_format_error():
    d = {}
    assert '' % d == ''
    n = 5
    raises(TypeError, "'' % n")

    class MyMapping(object):
        def __getitem__(self, key):
            py.test.fail('should not be here')
    assert '' % MyMapping() == ''

    class MyMapping2(object):
        def __getitem__(self, key):
            return key
    assert '%(key)s'%MyMapping2() == 'key'
    assert u'%(key)s'%MyMapping2() == u'key'


def test_format_item_string():
    n = 23
    assert 'a23b' == 'a%sb' % n
    assert '23b' == '%sb' % n
    assert 'a23' == 'a%s' % n
    assert '23' == '%s' % n

def test_format_percent_tuple():
    t = ()
    assert 'a%b' == 'a%%b' % t
    assert '%b' == '%%b' % t
    assert 'a%' == 'a%%' % t
    assert '%' == '%%' % t

def test_format_too_much():
    raises(TypeError, '%s%s'.__mod__, ())
    raises(TypeError, '%s%s'.__mod__, (23,))

def test_format_not_enough():
    raises(TypeError, '%s%s'.__mod__, (23,)*3)
    raises(TypeError, '%s%s'.__mod__, (23,)*4)

def test_format_string():
    s = '23'
    assert '23' == '%s' % s
    assert "'23'" == '%r' % s
    raises(TypeError, '%d'.__mod__, s)

def test_format_float():
    f = 23.456
    assert '23' == '%d' % f
    assert '17' == '%x' % f
    assert '23.456' == '%s' % f
    # for 'r' use a float that has an exact decimal rep:
    g = 23.125
    assert '23.125' == '%r' % g
    h = 0.0276
    assert '0.028' == '%.3f' % h    # should work on most platforms...
    big = 1E200
    assert '   inf' == '%6g' % (big * big)

    assert '0.' == '%#.0f' % 0.0

def test_format_int():
    n = 23
    z = 0
    assert '23' == '%d' % n
    assert '17' == '%x' % n
    assert '0x17' == '%#x' % n
    assert '0x0' == '%#x' % z
    assert '23' == '%s' % n
    assert '23' == '%r' % n
    assert ('%d' % (-sys.maxint-1,) == '-' + str(sys.maxint+1)
                                    == '-%d' % (sys.maxint+1,))
    n = 28
    m = 8
    assert '1C' == '%X' % n
    assert '0X1C' == '%#X' % n
    assert '10' == '%o' % m
    assert '010' == '%#o' % m
    assert '-010' == '%#o' % -m
    assert '0' == '%o' % z
    assert '0' == '%#o' % z

    n = 23
    f = 5
    assert '-0x017' == '%#06x' % -n
    assert '' == '%.0o' % z
    assert '0' == '%#.0o' % z
    assert '5' == '%.0o' % f
    assert '05' == '%#.0o' % f
    assert '000' == '%.3o' % z
    assert '000' == '%#.3o' % z
    assert '005' == '%.3o' % f
    assert '005' == '%#.3o' % f
    assert '27' == '%.2o' % n
    assert '027' == '%#.2o' % n

def test_format_long():
    l = 4800000000L
    assert '%d' % l == '4800000000'

    class SubLong(long):
        pass
    sl = SubLong(l)
    assert '%d' % sl == '4800000000'

def test_format_subclass_with_str():
    class SubInt2(int):
        def __str__(self):
            assert False, "not called"
        def __hex__(self):
            assert False, "not called"
        def __oct__(self):
            assert False, "not called"
        def __int__(self):
            assert False, "not called"
        def __long__(self):
            assert False, "not called"
    sl = SubInt2(123)
    assert '%i' % sl == '123'
    assert '%u' % sl == '123'
    assert '%d' % sl == '123'
    assert '%x' % sl == '7b'
    assert '%X' % sl == '7B'
    assert '%o' % sl == '173'

    skip("the rest of this test is serious nonsense imho, changed "
         "only on 2.7.13, and is different on 3.x anyway.  We could "
         "reproduce it by writing lengthy logic, then get again the "
         "reasonable performance by special-casing the exact type "
         "'long'.  And all for 2.7.13 only.  Let's give up.")

    class SubLong2(long):
        def __str__(self):
            return extra_stuff + 'Xx'
        def __hex__(self):
            return extra_stuff + '0xYy' + extra_tail
        def __oct__(self):
            return extra_stuff + '0Zz' + extra_tail
        def __int__(self):
            assert False, "not called"
        def __long__(self):
            assert False, "not called"
    sl = SubLong2(123)
    for extra_stuff in ['', '-']:
        for extra_tail in ['', 'l', 'L']:
            m = extra_stuff
            x = '%i' % sl
            assert x == m+'Xx'
            assert '%u' % sl == m+'Xx'
            assert '%d' % sl == m+'Xx'
            assert '%x' % sl == m+('Yyl' if extra_tail == 'l' else 'Yy')
            assert '%X' % sl == m+('YYL' if extra_tail == 'l' else 'YY')
            assert '%o' % sl == m+('Zzl' if extra_tail == 'l' else 'Zz')
    extra_stuff = '??'
    raises(ValueError, "'%x' % sl")
    raises(ValueError, "'%X' % sl")
    raises(ValueError, "'%o' % sl")

def test_format_list():
    l = [1,2]
    assert '<[1, 2]>' == '<%s>' % l
    assert '<[1, 2]-[3, 4]>' == '<%s-%s>' % (l, [3,4])

def test_format_tuple():
    t = (1,2)
    assert '<(1, 2)>' == '<%s>' % (t,)
    assert '<(1, 2)-(3, 4)>' == '<%s-%s>' % (t, (3,4))

def test_format_dict():
    # I'll just note that the first of these two completely
    # contradicts what CPython's documentation says:

    #     When the right argument is a dictionary (or other
    #     mapping type), then the formats in the string
    #     \emph{must} include a parenthesised mapping key into
    #     that dictionary inserted immediately after the
    #     \character{\%} character.

    # It is what CPython *does*, however.  All software sucks.

    d = {1:2}
    assert '<{1: 2}>' == '<%s>' % d
    assert '<{1: 2}-{3: 4}>' == '<%s-%s>' % (d, {3:4})

def test_format_wrong_char():
    raises(ValueError, 'a%Zb'.__mod__, ((23,),))
    raises(ValueError, u'a%\ud800b'.__mod__, ((23,),))

def test_incomplete_format():
    raises(ValueError, '%'.__mod__, ((23,),))
    raises((ValueError, TypeError), '%('.__mod__, ({},))

def test_format_char():
    A = 65
    e = 'e'
    assert '%c' % A == 'A'
    assert '%c' % e == 'e'
    raises(OverflowError, '%c'.__mod__, (256,))
    raises(OverflowError, '%c'.__mod__, (-1,))
    raises(OverflowError, u'%c'.__mod__, (sys.maxunicode+1,))
    raises(TypeError, '%c'.__mod__, ("bla",))
    raises(TypeError, '%c'.__mod__, ("",))
    raises(TypeError, '%c'.__mod__, (['c'],))
    surrogate = 0xd800
    assert u'%c' % surrogate == u'\ud800'

def test_broken_unicode():
    raises(UnicodeDecodeError, 'Názov: %s'.__mod__, u'Jerry')

def test___int__():
    class MyInt(object):
        def __init__(self, x):
            self.x = x
        def __int__(self):
            return self.x
    x = MyInt(65)
    assert '%c' % x == 'A'

def test_format_retry_with_long_if_int_fails():
    class IntFails(object):
        def __int__(self):
            raise Exception
        def __long__(self):
            return 0L

    x = "%x" % IntFails()
    assert x == '0'

def test_formatting_huge_precision():
    prec = 2**31
    format_string = "%.{}f".format(prec)
    exc = raises(ValueError, "format_string % 2.34")
    assert str(exc.value) == 'prec too big'
    raises(OverflowError, lambda: u'%.*f' % (prec, 1. / 7))

def test_formatting_huge_width():
    format_string = "%{}f".format(sys.maxsize + 1)
    exc = raises(ValueError, "format_string % 2.34")
    assert str(exc.value) == 'width too big'

def test_wrong_formatchar_error_not_masked_by_not_enough_args():
    with raises(ValueError):
        "%?" % () # not TypeError (which would be due to lack of arguments)
    with raises(ValueError):
        "%?" % {} # not TypeError

def test_width():
    a = 'a'
    assert "%3s" % a == '  a'
    assert "%-3s"% a == 'a  '

def test_prec_cornercase():
    z = 0
    assert "%.0x" % z == ''
    assert "%.x" % z == ''
    assert "%.0d" % z == ''
    assert "%.i" % z == ''
    assert "%.0o" % z == ''
    assert "%.o" % z == ''

def test_prec_string():
    a = 'a'
    abcde = 'abcde'
    assert "%.3s"% a ==     'a'
    assert "%.3s"% abcde == 'abc'

def test_prec_width_string():
    a = 'a'
    abcde = 'abcde'
    assert "%5.3s" % a ==     '    a'
    assert "%5.3s" % abcde == '  abc'
    assert "%-5.3s"% a ==     'a    '
    assert "%-5.3s"% abcde == 'abc  '

def test_zero_pad():
    one = 1
    ttf = 2.25
    assert "%02d" % one ==   "01"
    assert "%05d" % one ==   "00001"
    assert "%-05d" % one ==  "1    "
    assert "%04f" % ttf == "2.250000"
    assert "%05g" % ttf == "02.25"
    assert "%-05g" % ttf =="2.25 "
    assert "%05s" % ttf == " 2.25"

def test_star_width():
    f = 5
    assert "%*s" %( f, 'abc') ==  '  abc'
    assert "%*s" %(-f, 'abc') ==  'abc  '
    assert "%-*s"%( f, 'abc') ==  'abc  '
    assert "%-*s"%(-f, 'abc') ==  'abc  '

def test_star_prec():
    t = 3
    assert "%.*s"%( t, 'abc') ==  'abc'
    assert "%.*s"%( t, 'abcde') ==  'abc'
    assert "%.*s"%(-t, 'abc') ==  ''

def test_star_width_prec():
    f = 5
    assert "%*.*s"%( f, 3, 'abc') ==    '  abc'
    assert "%*.*s"%( f, 3, 'abcde') ==  '  abc'
    assert "%*.*s"%(-f, 3, 'abcde') ==  'abc  '

def test_long_format():
    def f(fmt, x):
        return fmt % x
    assert '%.70f' % 2.0 == '2.' + '0' * 70
    assert '%.110g' % 2.0 == '2'

def test_subnormal():
    inf = 1e300 * 1e300
    assert "%f" % (inf,) == 'inf'
    assert "%E" % (inf,) == 'INF'
    assert "%f" % (-inf,) == '-inf'
    assert "%F" % (-inf,) == '-INF'
    nan = inf / inf
    assert "%f" % (nan,) == 'nan'
    assert "%f" % (-nan,) == 'nan'
    assert "%E" % (nan,) == 'NAN'
    assert "%F" % (nan,) == 'NAN'
    assert "%G" % (nan,) == 'NAN'

def test_unicode_convert():
    u = u"x"
    assert isinstance("%s" % u, unicode)

def test_unicode_nonascii():
    """
    Interpolating a unicode string with non-ascii characters in it into
    a string format should decode the format string as ascii and return
    unicode.
    """
    u = u'\x80'
    result = "%s" % u
    assert isinstance(result, unicode)
    assert result == u

def test_unicode_d():
    t = 3
    assert u"%.1d" % t == '3'

def test_unicode_overflow():
    skip("nicely passes on top of CPython but requires > 2GB of RAM")
    raises((OverflowError, MemoryError), 'u"%.*d" % (sys.maxint, 1)')

def test_unicode_format_a():
    ten = 10L
    assert u'%x' % ten == 'a'

def test_long_no_overflow():
    big = 0x1234567890987654321
    assert "%x" % big == "1234567890987654321"

def test_missing_cases():
    big = -123456789012345678901234567890
    assert '%032d' % big == '-0123456789012345678901234567890'

def test_invalid_char():
    f = 4
    raises(ValueError, 'u"%\u1234" % (f,)')

def test_formatting_huge_precision_u():
    prec = 2**31
    format_string = u"%.{}f".format(prec)
    exc = raises(ValueError, "format_string % 2.34")
    assert str(exc.value) == 'prec too big'
    raises(OverflowError, lambda: u'%.*f' % (prec, 1. / 7))

def test_formatting_huge_width_u():
    format_string = u"%{}f".format(sys.maxsize + 1)
    exc = raises(ValueError, "format_string % 2.34")
    assert str(exc.value) == 'width too big'

def test_unicode_error_position():
    with raises(ValueError) as info:
        u"\xe4\xe4\xe4%?" % {}
    assert str(info.value) == "unsupported format character u'?' (0x3f) at index 4"
    with raises(ValueError) as info:
        u"\xe4\xe4\xe4%\xe4" % {}
    assert str(info.value) == "unsupported format character u'\\xe4' (0xe4) at index 4"

