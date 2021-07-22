"""String formatting routines"""
import math
import sys

from rpython.rlib import jit, rutf8
from rpython.rlib.objectmodel import specialize
from rpython.rlib.rarithmetic import INT_MAX, r_uint
from rpython.rlib.rfloat import DTSF_ALT, formatd
from rpython.rlib.rstring import StringBuilder
from rpython.rlib.unroll import unrolling_iterable
from rpython.tool.sourcetools import func_with_new_name

from pypy.interpreter.error import OperationError, oefmt
from pypy.interpreter.unicodehelper import check_ascii_or_raise


class BaseStringFormatter(object):
    def __init__(self, space, values_w, w_valuedict):
        self.space = space
        self.fmtpos = 0
        self.values_w = values_w
        self.values_pos = 0
        self.w_valuedict = w_valuedict

    def forward(self):
        # move current position forward
        self.fmtpos += 1

    def nextinputvalue(self):
        # return the next value in the tuple of input arguments
        try:
            w_result = self.values_w[self.values_pos]
        except IndexError:
            raise oefmt(self.space.w_TypeError,
                        "not enough arguments for format string")
        else:
            self.values_pos += 1
            return w_result

    def checkconsumed(self):
        if self.values_pos < len(self.values_w) and self.w_valuedict is None:
            raise oefmt(self.space.w_TypeError,
                        "not all arguments converted during string formatting")

    def std_wp_int(self, r, prefix='', keep_zero=False):
        # use self.prec to add some '0' on the left of the number
        if self.prec >= 0:
            if self.prec > 1000:
                raise oefmt(self.space.w_OverflowError,
                            "formatted integer is too long (precision too "
                            "large?)")
            sign = r[0] == '-'
            padding = self.prec - (len(r)-int(sign))
            if padding > 0:
                if sign:
                    r = '-' + '0'*padding + r[1:]
                else:
                    r = '0'*padding + r
            elif self.prec == 0 and r == '0' and not keep_zero:
                r = ''
        self.std_wp_number(r, prefix)

    def fmt_d(self, w_value):
        "int formatting"
        r = int_num_helper(self.space, w_value)
        self.std_wp_int(r)

    def fmt_x(self, w_value):
        "hex formatting"
        r = hex_num_helper(self.space, w_value)
        if self.f_alt:
            prefix = '0x'
        else:
            prefix = ''
        self.std_wp_int(r, prefix)

    def fmt_X(self, w_value):
        "HEX formatting"
        r = hex_num_helper(self.space, w_value)
        if self.f_alt:
            prefix = '0X'
        else:
            prefix = ''
        self.std_wp_int(r.upper(), prefix)

    def fmt_o(self, w_value):
        "oct formatting"
        r = oct_num_helper(self.space, w_value)
        keep_zero = False
        if self.f_alt:
            if r == '0':
                keep_zero = True
            elif r.startswith('-'):
                r = '-0' + r[1:]
            else:
                r = '0' + r
        self.std_wp_int(r, keep_zero=keep_zero)

    fmt_i = fmt_d
    fmt_u = fmt_d

    def fmt_e(self, w_value):
        self.format_float(w_value, 'e')

    def fmt_f(self, w_value):
        self.format_float(w_value, 'f')

    def fmt_g(self, w_value):
        self.format_float(w_value, 'g')

    def fmt_E(self, w_value):
        self.format_float(w_value, 'E')

    def fmt_F(self, w_value):
        self.format_float(w_value, 'F')

    def fmt_G(self, w_value):
        self.format_float(w_value, 'G')

    def format_float(self, w_value, char):
        space = self.space
        x = space.float_w(maybe_float(space, w_value))
        if math.isnan(x):
            if char in 'EFG':
                r = 'NAN'
            else:
                r = 'nan'
        elif math.isinf(x):
            if x < 0:
                if char in 'EFG':
                    r = '-INF'
                else:
                    r = '-inf'
            else:
                if char in 'EFG':
                    r = 'INF'
                else:
                    r = 'inf'
        else:
            prec = self.prec
            if prec < 0:
                prec = 6
            if char in 'fF' and x/1e25 > 1e25:
                char = chr(ord(char) + 1)     # 'f' => 'g'
            flags = 0
            if self.f_alt:
                flags |= DTSF_ALT
            r = formatd(x, char, prec, flags)
        self.std_wp_number(r)

    def std_wp_number(self, r, prefix=''):
        raise NotImplementedError

def make_formatter_subclass(do_unicode):
    # to build two subclasses of the BaseStringFormatter class,
    # each one getting its own subtle differences and RPython types.

    class StringFormatter(BaseStringFormatter):
        def __init__(self, space, fmt, values_w, w_valuedict):
            BaseStringFormatter.__init__(self, space, values_w, w_valuedict)
            self.fmt = fmt    # always a string, if unicode, utf8 encoded

        def peekchr(self):
            # Return the 'current' character. Note that this returns utf8
            # encoded part, but this is ok since we only need one-character
            # comparisons
            try:
                return self.fmt[self.fmtpos]
            except IndexError:
                raise oefmt(self.space.w_ValueError, "incomplete format")

        # Only shows up if we've already started inlining format(), so just
        # unconditionally unroll this.
        @jit.unroll_safe
        def getmappingkey(self):
            # return the mapping key in a '%(key)s' specifier
            fmt = self.fmt
            i = self.fmtpos + 1   # first character after '('
            i0 = i
            pcount = 1
            while 1:
                try:
                    c = fmt[i]
                except IndexError:
                    space = self.space
                    raise oefmt(space.w_ValueError, "incomplete format key")
                if c == ')':
                    pcount -= 1
                    if pcount == 0:
                        break
                elif c == '(':
                    pcount += 1
                i += 1
            self.fmtpos = i + 1   # first character after ')'
            return fmt[i0:i]

        def getmappingvalue(self, key):
            # return the value corresponding to a key in the input dict
            space = self.space
            if self.w_valuedict is None:
                raise oefmt(space.w_TypeError, "format requires a mapping")
            if do_unicode:
                lgt = rutf8.check_utf8(key, True)
                w_key = space.newutf8(key, lgt)
            else:
                w_key = space.newbytes(key)
            return space.getitem(self.w_valuedict, w_key)

        def parse_fmt(self):
            if self.peekchr() == '(':
                w_value = self.getmappingvalue(self.getmappingkey())
            else:
                w_value = None

            self.peel_flags()

            self.width = self.peel_num('width', sys.maxint)
            if self.width < 0:
                # this can happen:  '%*s' % (-5, "hi")
                self.f_ljust = True
                self.width = -self.width

            if self.peekchr() == '.':
                self.forward()
                self.prec = self.peel_num('prec', INT_MAX)
                if self.prec < 0:
                    self.prec = 0    # this can happen:  '%.*f' % (-5, 3)
            else:
                self.prec = -1

            c = self.peekchr()
            if c == 'h' or c == 'l' or c == 'L':
                self.forward()

            return w_value

        # Same as getmappingkey
        @jit.unroll_safe
        def peel_flags(self):
            self.f_ljust = False
            self.f_sign  = False
            self.f_blank = False
            self.f_alt   = False
            self.f_zero  = False
            while True:
                c = self.peekchr()
                if c == '-':
                    self.f_ljust = True
                elif c == '+':
                    self.f_sign = True
                elif c == ' ':
                    self.f_blank = True
                elif c == '#':
                    self.f_alt = True
                elif c == '0':
                    self.f_zero = True
                else:
                    break
                self.forward()

        # Same as getmappingkey
        @jit.unroll_safe
        def peel_num(self, name, maxval):
            space = self.space
            c = self.peekchr()
            if c == '*':
                self.forward()
                w_value = self.nextinputvalue()
                if name == 'width':
                    return space.int_w(w_value)
                elif name == 'prec':
                    return space.c_int_w(w_value)
                else:
                    assert False
            result = 0
            while True:
                digit = ord(c) - ord('0')
                if not (0 <= digit <= 9):
                    break
                if result > (maxval - digit) / 10:
                    raise oefmt(space.w_ValueError, "%s too big", name)
                result = result * 10 + digit
                self.forward()
                c = self.peekchr()
            return result

        @jit.look_inside_iff(lambda self: jit.isconstant(self.fmt))
        def format(self):
            lgt = len(self.fmt) + 4 * len(self.values_w) + 10
            result = StringBuilder(lgt)
            self.result = result
            while True:
                # fast path: consume as many characters as possible
                fmt = self.fmt
                i = i0 = self.fmtpos
                while i < len(fmt):
                    if fmt[i] == '%':
                        break
                    i += 1
                else:
                    result.append_slice(fmt, i0, len(fmt))
                    break     # end of 'fmt' string
                result.append_slice(fmt, i0, i)
                self.fmtpos = i + 1

                # interpret the next formatter
                w_value = self.parse_fmt()
                c = self.peekchr()
                self.forward()
                if c == '%':
                    self.result.append('%')
                    continue

                # first check whether it's a invalid char, *then* call
                # nextinputvalue, otherwise the error generated by
                # nextinputvalue can cover that of unknown_fmtchar
                for c1 in FORMATTER_CHARS:
                    if c == c1:
                        break
                else:
                    self.unknown_fmtchar()
                if w_value is None:
                    w_value = self.nextinputvalue()

                # dispatch on the formatter
                # (this turns into a switch after translation)
                for c1 in FORMATTER_CHARS:
                    if c == c1:
                        # 'c1' is an annotation constant here,
                        # so this getattr() is ok
                        do_fmt = getattr(self, 'fmt_' + c1)
                        do_fmt(w_value)
                        break

            self.checkconsumed()
            return result.build()

        def unknown_fmtchar(self):
            space = self.space
            if do_unicode:
                cp = rutf8.codepoint_at_pos(self.fmt, self.fmtpos - 1)
                pos = rutf8.codepoints_in_utf8(self.fmt, 0, self.fmtpos - 1)
                w_s = space.newutf8(rutf8.unichr_as_utf8(r_uint(cp),
                                                  allow_surrogates=True), 1)
            else:
                cp = ord(self.fmt[self.fmtpos - 1])
                pos = self.fmtpos - 1
                w_s = space.newbytes(chr(cp))
            raise oefmt(space.w_ValueError,
                        "unsupported format character %R (%s) at index %d",
                        w_s, hex(cp), pos)

        @specialize.arg(2)
        def std_wp(self, r, is_string=False):
            length = len(r)
            if do_unicode and is_string:
                # convert string to unicode using the default encoding
                r = self.space.utf8_w(self.space.newbytes(r))
            prec = self.prec
            if prec == -1 and self.width == 0:
                # fast path
                self.result.append(r)
                return
            if prec >= 0 and prec < length:
                length = prec   # ignore the end of the string if too long
            result = self.result
            padding = self.width - length
            if padding < 0:
                padding = 0
            assert padding >= 0
            if not self.f_ljust and padding > 0:
                result.append_multiple_char(' ', padding)
                # add any padding at the left of 'r'
                padding = 0
            result.append_slice(r, 0, length)       # add 'r' itself
            if padding > 0:
                result.append_multiple_char(' ', padding)
            # add any remaining padding at the right

        def std_wp_number(self, r, prefix=''):
            result = self.result
            if len(prefix) == 0 and len(r) >= self.width:
                # this is strictly a fast path: no prefix, and no padding
                # needed.  It is more efficient code both in the non-jit
                # case (less testing stuff) and in the jit case (uses only
                # result.append(), and no startswith() if not f_sign and
                # not f_blank).
                if self.f_sign and not r.startswith('-'):
                    result.append('+')
                elif self.f_blank and not r.startswith('-'):
                    result.append(' ')
                result.append(r)
                return
            # add a '+' or ' ' sign if necessary
            sign = r.startswith('-')
            if not sign:
                if self.f_sign:
                    r = '+' + r
                    sign = True
                elif self.f_blank:
                    r = ' ' + r
                    sign = True
            # do the padding requested by self.width and the flags,
            # without building yet another RPython string but directly
            # by pushing the pad character into self.result
            padding = self.width - len(r) - len(prefix)
            if padding <= 0:
                padding = 0

            if self.f_ljust:
                padnumber = '<'
            elif self.f_zero:
                padnumber = '0'
            else:
                padnumber = '>'

            assert padding >= 0
            if padnumber == '>':
                result.append_multiple_char(' ', padding)
                # pad with spaces on the left
            if sign:
                result.append(r[0])        # the sign
            result.append(prefix)               # the prefix
            if padnumber == '0':
                result.append_multiple_char('0', padding)
                # pad with zeroes
            result.append_slice(r, int(sign), len(r))
            # the rest of the number
            if padnumber == '<':           # spaces on the right
                result.append_multiple_char(' ', padding)

        def string_formatting(self, w_value):
            space = self.space
            w_impl = space.lookup(w_value, '__str__')
            if w_impl is None:
                raise oefmt(space.w_TypeError,
                            "operand does not support unary str")
            w_result = space.get_and_call_function(w_impl, w_value)
            if space.isinstance_w(w_result, space.w_unicode):
                raise NeedUnicodeFormattingError
            return space.bytes_w(w_result)

        def fmt_s(self, w_value):
            space = self.space
            got_unicode = space.isinstance_w(w_value, space.w_unicode)
            if not do_unicode:
                if got_unicode:
                    # Make sure the format string is ascii encodable
                    check_ascii_or_raise(space, self.fmt)
                    raise NeedUnicodeFormattingError
                s = self.string_formatting(w_value)
            else:
                if not got_unicode:
                    w_value = space.call_function(space.w_unicode, w_value)
                else:
                    from pypy.objspace.std.unicodeobject import unicode_from_object
                    w_value = unicode_from_object(space, w_value)
                s = space.utf8_w(w_value)
            self.std_wp(s, False)

        def fmt_r(self, w_value):
            self.std_wp(self.space.text_w(self.space.repr(w_value)), True)

        def fmt_c(self, w_value):
            self.prec = -1     # just because
            space = self.space
            if space.isinstance_w(w_value, space.w_bytes):
                if do_unicode:
                    w_value = w_value.descr_decode(space, space.newtext('ascii'))
                s = space.bytes_w(w_value)
                if len(s) != 1:
                    raise oefmt(space.w_TypeError, "%c requires int or char")
                self.std_wp(s, True)
            elif space.isinstance_w(w_value, space.w_unicode):
                if not do_unicode:
                    raise NeedUnicodeFormattingError
                ustr = space.utf8_w(w_value)
                if space.len_w(w_value) != 1:
                    raise oefmt(space.w_TypeError, "%c requires int or unichar")
                self.std_wp(ustr, False)
            else:
                n = space.int_w(w_value)
                if do_unicode:
                    try:
                        c = rutf8.unichr_as_utf8(r_uint(n),
                                                 allow_surrogates=True)
                    except rutf8.OutOfRange:
                        raise oefmt(space.w_OverflowError,
                                    "unicode character code out of range")
                    self.std_wp(c, False)
                else:
                    try:
                        s = chr(n)
                    except ValueError:
                        raise oefmt(space.w_OverflowError,
                                    "character code not in range(256)")
                    self.std_wp(s, True)

    return StringFormatter


class NeedUnicodeFormattingError(Exception):
    pass

StringFormatter = make_formatter_subclass(do_unicode=False)
UnicodeFormatter = make_formatter_subclass(do_unicode=True)
UnicodeFormatter.__name__ = 'UnicodeFormatter'


# an "unrolling" list of all the known format characters,
# collected from which fmt_X() functions are defined in the class
FORMATTER_CHARS = unrolling_iterable(
    [_name[-1] for _name in dir(StringFormatter)
               if len(_name) == 5 and _name.startswith('fmt_')])

def format(space, w_fmt, values_w, w_valuedict, do_unicode):
    "Entry point"
    if not do_unicode:
        fmt = space.bytes_w(w_fmt)
        formatter = StringFormatter(space, fmt, values_w, w_valuedict)
        try:
            result = formatter.format()
        except NeedUnicodeFormattingError:
            # fall through to the unicode case
            pass
        else:
            return space.newbytes(result)
    fmt = space.utf8_w(w_fmt)
    formatter = UnicodeFormatter(space, fmt, values_w, w_valuedict)
    result = formatter.format()
    # this can force strings, not sure if it's a problem or not
    lgt = rutf8.codepoints_in_utf8(result)
    return space.newutf8(result, lgt)

def mod_format(space, w_format, w_values, do_unicode=False):
    if space.isinstance_w(w_values, space.w_tuple):
        values_w = space.fixedview(w_values)
        return format(space, w_format, values_w, None, do_unicode)
    else:
        # we check directly for dict to avoid obscure checking
        # in simplest case
        if space.isinstance_w(w_values, space.w_dict) or \
           (space.lookup(w_values, '__getitem__') and
           not space.isinstance_w(w_values, space.w_basestring)):
            return format(space, w_format, [w_values], w_values, do_unicode)
        else:
            return format(space, w_format, [w_values], None, do_unicode)

# ____________________________________________________________
# Formatting helpers

def maybe_int(space, w_value):
    # make sure that w_value is a wrapped integer
    return space.int(w_value)

def maybe_float(space, w_value):
    # make sure that w_value is a wrapped float
    return space.float(w_value)

def format_num_helper_generator(fmt, digits):
    def format_num_helper(space, w_value):
        if (not space.isinstance_w(w_value, space.w_int) and
            not space.isinstance_w(w_value, space.w_long)):
          try:
            w_value = maybe_int(space, w_value)
          except OperationError:
            try:
                w_value = space.long(w_value)
            except OperationError as operr:
                if operr.match(space, space.w_TypeError):
                    raise oefmt(
                        space.w_TypeError,
                        "%s format: a number is required, not %T", fmt, w_value)
                else:
                    raise
        try:
            value = space.int_w(w_value)
            return fmt % (value,)
        except OperationError as operr:
            if not operr.match(space, space.w_OverflowError):
                raise
            num = space.bigint_w(w_value)
            return num.format(digits)
    return func_with_new_name(format_num_helper,
                              'base%d_num_helper' % len(digits))

int_num_helper = format_num_helper_generator('%d', '0123456789')
oct_num_helper = format_num_helper_generator('%o', '01234567')
hex_num_helper = format_num_helper_generator('%x', '0123456789abcdef')
