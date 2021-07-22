from rpython.rlib import jit, rutf8
from rpython.rlib.objectmodel import we_are_translated, not_rpython
from rpython.rlib.rstring import StringBuilder, UnicodeBuilder
from rpython.rlib.rutf8 import MAXUNICODE

from pypy.interpreter.error import OperationError, oefmt
from pypy.interpreter.gateway import interp2app, unwrap_spec, WrappedDefault
from pypy.interpreter import unicodehelper


class VersionTag(object):
    pass


class CodecState(object):
    _immutable_fields_ = ["version?"]

    def __init__(self, space):
        self.codec_search_path = []
        self.codec_search_cache = {}
        self.codec_error_registry = {}
        self.codec_need_encodings = True
        self.decode_error_handler = self.make_decode_errorhandler(space)
        self.encode_error_handler = self.make_encode_errorhandler(space)

        self.unicodedata_handler = None
        self.modified()

    def _make_errorhandler(self, space, decode):
        def call_errorhandler(errors, encoding, reason, input, startpos,
                              endpos):
            """Generic wrapper for calling into error handlers.

            Note that error handler receives and returns position into
            the unicode characters, not into the position of utf8 bytes,
            so it needs to be converted by the codec

            Returns (unicode_or_none, str_or_none, newpos) as error
            handlers may return unicode or on Python 3, bytes.
            """
            w_errorhandler = lookup_error(space, errors)
            if decode:
                w_cls = space.w_UnicodeDecodeError
                w_input = space.newbytes(input)
                length = len(input)
            else:
                w_cls = space.w_UnicodeEncodeError
                length = rutf8.check_utf8(input, allow_surrogates=True)
                w_input = space.newutf8(input, length)
            w_exc =  space.call_function(
                w_cls,
                space.newtext(encoding),
                w_input,
                space.newint(startpos),
                space.newint(endpos),
                space.newtext(reason))
            w_res = space.call_function(w_errorhandler, w_exc)
            if (not space.isinstance_w(w_res, space.w_tuple)
                or space.len_w(w_res) != 2
                or not space.isinstance_w(
                                 space.getitem(w_res, space.newint(0)),
                                 space.w_unicode)):
                raise oefmt(space.w_TypeError,
                            "%s error handler must return (unicode, int) "
                            "tuple, not %R",
                            "decoding" if decode else "encoding", w_res)
            w_replace, w_newpos = space.fixedview(w_res, 2)
            newpos = space.int_w(w_newpos)
            if newpos < 0:
                newpos = length + newpos
            if newpos < 0 or newpos > length:
                raise oefmt(space.w_IndexError,
                            "position %d from error handler out of bounds",
                            newpos)
            w_replace = space.convert_to_w_unicode(w_replace)
            return w_replace._utf8, newpos
        return call_errorhandler

    def make_decode_errorhandler(self, space):
        return self._make_errorhandler(space, True)

    def make_encode_errorhandler(self, space):
        return self._make_errorhandler(space, False)

    def get_unicodedata_handler(self, space):
        if self.unicodedata_handler:
            return self.unicodedata_handler
        try:
            w_unicodedata = space.getbuiltinmodule("unicodedata")
            w_getcode = space.getattr(w_unicodedata, space.newtext("_get_code"))
        except OperationError:
            return None
        else:
            self.unicodedata_handler = UnicodeData_Handler(space, w_getcode)
            return self.unicodedata_handler

    def modified(self):
        self.version = VersionTag()

    def get_codec_from_cache(self, key):
        return self._get_codec_with_version(key, self.version)

    @jit.elidable
    def _get_codec_with_version(self, key, version):
        return self.codec_search_cache.get(key, None)

    def _cleanup_(self):
        assert not self.codec_search_path


def register_codec(space, w_search_function):
    """register(search_function)

    Register a codec search function. Search functions are expected to take
    one argument, the encoding name in all lower case letters, and return
    a tuple of functions (encoder, decoder, stream_reader, stream_writer).
    """
    state = space.fromcache(CodecState)
    if space.is_true(space.callable(w_search_function)):
        state.codec_search_path.append(w_search_function)
    else:
        raise oefmt(space.w_TypeError, "argument must be callable")


@unwrap_spec(encoding='text')
def lookup_codec(space, encoding):
    """lookup(encoding) -> (encoder, decoder, stream_reader, stream_writer)
    Looks up a codec tuple in the Python codec registry and returns
    a tuple of functions.
    """
    assert not (space.config.translating and not we_are_translated()), \
        "lookup_codec() should not be called during translation"
    state = space.fromcache(CodecState)
    normalized_encoding = encoding.replace(" ", "-").lower()
    w_result = state.get_codec_from_cache(normalized_encoding)
    if w_result is not None:
        return w_result
    return _lookup_codec_loop(space, encoding, normalized_encoding)


def _lookup_codec_loop(space, encoding, normalized_encoding):
    state = space.fromcache(CodecState)
    if state.codec_need_encodings:
        w_import = space.getattr(space.builtin, space.newtext("__import__"))
        # registers new codecs
        space.call_function(w_import, space.newtext("encodings"))
        state.codec_need_encodings = False
        if len(state.codec_search_path) == 0:
            raise oefmt(space.w_LookupError,
                        "no codec search functions registered: can't find "
                        "encoding")
    for w_search in state.codec_search_path:
        w_result = space.call_function(w_search,
                                       space.newtext(normalized_encoding))
        if not space.is_w(w_result, space.w_None):
            if not (space.isinstance_w(w_result, space.w_tuple) and
                    space.len_w(w_result) == 4):
                raise oefmt(space.w_TypeError,
                            "codec search functions must return 4-tuples")
            else:
                state.codec_search_cache[normalized_encoding] = w_result
                state.modified()
                return w_result
    raise oefmt(space.w_LookupError, "unknown encoding: %s", encoding)

# ____________________________________________________________
# Register standard error handlers

def check_exception(space, w_exc):
    try:
        w_start = space.getattr(w_exc, space.newtext('start'))
        w_end = space.getattr(w_exc, space.newtext('end'))
        w_obj = space.getattr(w_exc, space.newtext('object'))
    except OperationError as e:
        if not e.match(space, space.w_AttributeError):
            raise
        raise oefmt(space.w_TypeError, "wrong exception")

    delta = space.int_w(w_end) - space.int_w(w_start)
    if delta < 0 or not (space.isinstance_w(w_obj, space.w_bytes) or
                         space.isinstance_w(w_obj, space.w_unicode)):
        raise oefmt(space.w_TypeError, "wrong exception")

def strict_errors(space, w_exc):
    check_exception(space, w_exc)
    if space.isinstance_w(w_exc, space.w_BaseException):
        raise OperationError(space.type(w_exc), w_exc)
    else:
        raise oefmt(space.w_TypeError, "codec must pass exception instance")

def ignore_errors(space, w_exc):
    check_exception(space, w_exc)
    w_end = space.getattr(w_exc, space.newtext('end'))
    return space.newtuple([space.newutf8('', 0), w_end])

REPLACEMENT = u'\ufffd'.encode('utf8')

def replace_errors(space, w_exc):
    check_exception(space, w_exc)
    w_start = space.getattr(w_exc, space.newtext('start'))
    w_end = space.getattr(w_exc, space.newtext('end'))
    size = space.int_w(w_end) - space.int_w(w_start)
    if space.isinstance_w(w_exc, space.w_UnicodeEncodeError):
        text = '?' * size
        return space.newtuple([space.newutf8(text, size), w_end])
    elif space.isinstance_w(w_exc, space.w_UnicodeDecodeError):
        text = REPLACEMENT
        return space.newtuple([space.newutf8(text, 1), w_end])
    elif space.isinstance_w(w_exc, space.w_UnicodeTranslateError):
        text = REPLACEMENT * size
        return space.newtuple([space.newutf8(text, size), w_end])
    else:
        raise oefmt(space.w_TypeError,
                    "don't know how to handle %T in error callback", w_exc)

def xmlcharrefreplace_errors(space, w_exc):
    check_exception(space, w_exc)
    if space.isinstance_w(w_exc, space.w_UnicodeEncodeError):
        w_obj = space.getattr(w_exc, space.newtext('object'))
        space.realutf8_w(w_obj) # weeoes
        w_obj = space.convert_arg_to_w_unicode(w_obj)
        start = space.int_w(space.getattr(w_exc, space.newtext('start')))
        w_end = space.getattr(w_exc, space.newtext('end'))
        end = space.int_w(w_end)
        start = w_obj._index_to_byte(start)
        end = w_obj._index_to_byte(end)
        builder = StringBuilder()
        pos = start
        obj = w_obj._utf8
        while pos < end:
            code = rutf8.codepoint_at_pos(obj, pos)
            builder.append("&#")
            builder.append(str(code))
            builder.append(";")
            pos = rutf8.next_codepoint_pos(obj, pos)
        r = builder.build()
        lgt = rutf8.check_utf8(r, True)
        return space.newtuple([space.newutf8(r, lgt), w_end])
    else:
        raise oefmt(space.w_TypeError,
                    "don't know how to handle %T in error callback", w_exc)

def backslashreplace_errors(space, w_exc):
    check_exception(space, w_exc)
    if space.isinstance_w(w_exc, space.w_UnicodeEncodeError):
        w_obj = space.getattr(w_exc, space.newtext('object'))
        space.realutf8_w(w_obj) # for errors
        w_obj = space.convert_arg_to_w_unicode(w_obj)
        start = space.int_w(space.getattr(w_exc, space.newtext('start')))
        w_end = space.getattr(w_exc, space.newtext('end'))
        end = space.int_w(w_end)
        start = w_obj._index_to_byte(start)
        end = w_obj._index_to_byte(end)
        builder = StringBuilder()
        obj = w_obj._utf8
        pos = start
        while pos < end:
            oc = rutf8.codepoint_at_pos(obj, pos)
            num = hex(oc)
            if (oc >= 0x10000):
                builder.append("\\U")
                zeros = 8
            elif (oc >= 0x100):
                builder.append("\\u")
                zeros = 4
            else:
                builder.append("\\x")
                zeros = 2
            lnum = len(num)
            nb = zeros + 2 - lnum # num starts with '0x'
            if nb > 0:
                builder.append_multiple_char('0', nb)
            builder.append_slice(num, 2, lnum)
            pos = rutf8.next_codepoint_pos(obj, pos)
        r = builder.build()
        lgt = rutf8.check_utf8(r, True)
        return space.newtuple([space.newutf8(r, lgt), w_end])
    else:
        raise oefmt(space.w_TypeError,
                    "don't know how to handle %T in error callback", w_exc)

@not_rpython
def register_builtin_error_handlers(space):
    state = space.fromcache(CodecState)
    for error in ("strict", "ignore", "replace", "xmlcharrefreplace",
                  "backslashreplace"):
        name = error + "_errors"
        state.codec_error_registry[error] = interp2app(
                globals()[name]).spacebind(space)


@unwrap_spec(errors='text')
def lookup_error(space, errors):
    """lookup_error(errors) -> handler

    Return the error handler for the specified error handling name
    or raise a LookupError, if no handler exists under this name.
    """

    state = space.fromcache(CodecState)
    try:
        w_err_handler = state.codec_error_registry[errors]
    except KeyError:
        raise oefmt(space.w_LookupError,
                    "unknown error handler name %s", errors)
    return w_err_handler


@unwrap_spec(encoding='text_or_none', errors='text_or_none')
def encode(space, w_obj, encoding=None, errors=None):
    """encode(obj, [encoding[,errors]]) -> object

    Encodes obj using the codec registered for encoding. encoding defaults
    to the default encoding. errors may be given to set a different error
    handling scheme. Default is 'strict' meaning that encoding errors raise
    a ValueError. Other possible values are 'ignore', 'replace' and
    'xmlcharrefreplace' as well as any other name registered with
    codecs.register_error that can handle ValueErrors.
    """
    if encoding is None:
        encoding = space.sys.defaultencoding
    w_encoder = space.getitem(lookup_codec(space, encoding), space.newint(0))
    if errors:
        w_res = space.call_function(w_encoder, w_obj, space.newtext(errors))
    else:
        w_res = space.call_function(w_encoder, w_obj)
    w_retval = space.getitem(w_res, space.newint(0))
    if not space.isinstance_w(w_retval, space.w_bytes):
        raise oefmt(space.w_TypeError,
                    "encoder did not return an string object (type '%T')",
                    w_retval)
    return w_retval

@unwrap_spec(errors='text_or_none')
def readbuffer_encode(space, w_data, errors='strict'):
    s = space.getarg_w('s#', w_data)
    return space.newtuple([space.newbytes(s), space.newint(len(s))])

@unwrap_spec(errors='text_or_none')
def charbuffer_encode(space, w_data, errors='strict'):
    s = space.getarg_w('t#', w_data)
    return space.newtuple([space.newbytes(s), space.newint(len(s))])

@unwrap_spec(encoding='text_or_none', errors='text_or_none')
def decode(space, w_obj, encoding=None, errors=None):
    """decode(obj, [encoding[,errors]]) -> object

    Decodes obj using the codec registered for encoding. encoding defaults
    to the default encoding. errors may be given to set a different error
    handling scheme. Default is 'strict' meaning that encoding errors raise
    a ValueError. Other possible values are 'ignore' and 'replace'
    as well as any other name registered with codecs.register_error that is
    able to handle ValueErrors.
    """
    if encoding is None:
        encoding = space.sys.defaultencoding
    w_decoder = space.getitem(lookup_codec(space, encoding), space.newint(1))
    if errors:
        w_res = space.call_function(w_decoder, w_obj, space.newtext(errors))
    else:
        w_res = space.call_function(w_decoder, w_obj)
    if (not space.isinstance_w(w_res, space.w_tuple) or space.len_w(w_res) != 2):
        raise oefmt(space.w_TypeError,
                    "encoder must return a tuple (object, integer)")
    return space.getitem(w_res, space.newint(0))

@unwrap_spec(errors='text')
def register_error(space, errors, w_handler):
    """register_error(errors, handler)

    Register the specified error handler under the name
    errors. handler must be a callable object, that
    will be called with an exception instance containing
    information about the location of the encoding/decoding
    error and must return a (replacement, new position) tuple.
    """
    state = space.fromcache(CodecState)
    if space.is_true(space.callable(w_handler)):
        state.codec_error_registry[errors] = w_handler
    else:
        raise oefmt(space.w_TypeError, "handler must be callable")

# ____________________________________________________________
# delegation to unicodehelper

def _find_implementation(impl_name):
    func = getattr(unicodehelper, impl_name)
    return func

def make_encoder_wrapper(name):
    rname = "utf8_encode_%s" % (name.replace("_encode", ""), )
    func = _find_implementation(rname)
    @unwrap_spec(errors='text_or_none')
    def wrap_encoder(space, w_arg, errors="strict"):
        w_arg = space.convert_arg_to_w_unicode(w_arg)
        if errors is None:
            errors = 'strict'
        state = space.fromcache(CodecState)
        utf8len = w_arg._length
        # XXX deal with func() returning length or not
        result = func(w_arg._utf8, errors, state.encode_error_handler)
        return space.newtuple([space.newbytes(result), space.newint(utf8len)])
    wrap_encoder.func_name = rname
    globals()[name] = wrap_encoder

def make_decoder_wrapper(name):
    rname = "str_decode_%s" % (name.replace("_decode", ""), )
    func = _find_implementation(rname)
    @unwrap_spec(string='bufferstr', errors='text_or_none',
                 w_final=WrappedDefault(False))
    def wrap_decoder(space, string, errors="strict", w_final=None):
        if errors is None:
            errors = 'strict'
        final = space.is_true(w_final)
        state = space.fromcache(CodecState)
        result, consumed, length = func(string, errors,
                                              final, state.decode_error_handler)
        return space.newtuple([space.newutf8(result, length),
                               space.newint(consumed)])
    wrap_decoder.func_name = rname
    globals()[name] = wrap_decoder

for encoder in [
         "ascii_encode",
         "latin_1_encode",
         "utf_7_encode",
         "utf_16_encode",
         "utf_16_be_encode",
         "utf_16_le_encode",
         "utf_32_encode",
         "utf_32_be_encode",
         "utf_32_le_encode",
         "unicode_escape_encode",
         "raw_unicode_escape_encode",
         "unicode_internal_encode",
        ]:
    make_encoder_wrapper(encoder)

for decoder in [
         "ascii_decode",
         "latin_1_decode",
         "utf_7_decode",
         "utf_16_decode",
         "utf_16_be_decode",
         "utf_16_le_decode",
         "utf_32_decode",
         "utf_32_be_decode",
         "utf_32_le_decode",
         "raw_unicode_escape_decode",
         ]:
    make_decoder_wrapper(decoder)

from rpython.rlib import runicode
if hasattr(runicode, 'str_decode_mbcs'):
    make_encoder_wrapper('mbcs_encode')
    make_decoder_wrapper('mbcs_decode')

# utf-8 functions are not regular, because we have to pass
# "allow_surrogates=True"
@unwrap_spec(errors='text_or_none')
def utf_8_encode(space, w_obj, errors="strict"):
    utf8, lgt = space.utf8_len_w(w_obj)
    if lgt == len(utf8): # ascii
        return space.newtuple([space.newbytes(utf8), space.newint(lgt)])
    if rutf8.has_surrogates(utf8):
        utf8 = rutf8.reencode_utf8_with_surrogates(utf8)
    return space.newtuple([space.newbytes(utf8), space.newint(lgt)])

@unwrap_spec(string='bufferstr', errors='text_or_none',
             w_final = WrappedDefault(False))
def utf_8_decode(space, string, errors="strict", w_final=None):
    from pypy.interpreter import unicodehelper

    if errors is None:
        errors = 'strict'
    final = space.is_true(w_final)
    state = space.fromcache(CodecState)
    # call the fast version for checking
    try:
        lgt = rutf8.check_utf8(string, allow_surrogates=True)
    except rutf8.CheckError:
        res, consumed, lgt = unicodehelper.str_decode_utf8(string,
            errors, final, state.decode_error_handler)
        return space.newtuple([space.newutf8(res, lgt),
                               space.newint(consumed)])
    else:
        return space.newtuple([space.newutf8(string, lgt),
                               space.newint(len(string))])

@unwrap_spec(data='bufferstr', errors='text_or_none', byteorder=int,
             w_final=WrappedDefault(False))
def utf_16_ex_decode(space, data, errors='strict', byteorder=0, w_final=None):
    from pypy.interpreter.unicodehelper import str_decode_utf_16_helper

    if errors is None:
        errors = 'strict'
    final = space.is_true(w_final)
    state = space.fromcache(CodecState)
    if byteorder == 0:
        byteorder = 'native'
    elif byteorder == -1:
        byteorder = 'little'
    else:
        byteorder = 'big'
    consumed = len(data)
    if final:
        consumed = 0
    res, consumed, lgt, byteorder = str_decode_utf_16_helper(
        data, errors, final,
        state.decode_error_handler, byteorder)
    return space.newtuple([space.newutf8(res, lgt),
                           space.newint(consumed),
                           space.newint(byteorder)])

@unwrap_spec(data='bufferstr', errors='text_or_none', byteorder=int,
             w_final=WrappedDefault(False))
def utf_32_ex_decode(space, data, errors='strict', byteorder=0, w_final=None):
    from pypy.interpreter.unicodehelper import str_decode_utf_32_helper

    final = space.is_true(w_final)
    state = space.fromcache(CodecState)
    if byteorder == 0:
        byteorder = 'native'
    elif byteorder == -1:
        byteorder = 'little'
    else:
        byteorder = 'big'
    consumed = len(data)
    if final:
        consumed = 0
    res, consumed, lgt, byteorder = str_decode_utf_32_helper(
        data, errors, final,
        state.decode_error_handler, byteorder)
    return space.newtuple([space.newutf8(res, lgt),
                           space.newint(consumed),
                           space.newint(byteorder)])

# ____________________________________________________________
# Charmap

class Charmap_Decode:
    def __init__(self, space, w_mapping):
        self.space = space
        self.w_mapping = w_mapping

        # fast path for all the stuff in the encodings module
        if space.isinstance_w(w_mapping, space.w_tuple):
            self.mapping_w = space.fixedview(w_mapping)
        else:
            self.mapping_w = None

    def get(self, ch, errorchar):
        space = self.space

        # get the character from the mapping
        if self.mapping_w is not None:
            w_ch = self.mapping_w[ch]
        else:
            try:
                w_ch = space.getitem(self.w_mapping, space.newint(ch))
            except OperationError as e:
                if not e.match(space, space.w_LookupError):
                    raise
                return errorchar

        if space.isinstance_w(w_ch, space.w_unicode):
            # Charmap may return a unicode string
            return space.utf8_w(w_ch)
        elif space.isinstance_w(w_ch, space.w_int):
            # Charmap may return a number
            x = space.int_w(w_ch)
            if not 0 <= x <= 0x10FFFF:
                raise oefmt(space.w_TypeError,
                    "character mapping must be in range(0x110000)")
            return rutf8.unichr_as_utf8(x, allow_surrogates=True)
        elif space.is_w(w_ch, space.w_None):
            # Charmap may return None
            return errorchar

        raise oefmt(space.w_TypeError,
            "character mapping must return integer, None or unicode")

class Charmap_Encode:
    def __init__(self, space, w_mapping):
        self.space = space
        self.w_mapping = w_mapping

    def get(self, ch, errorchar):
        space = self.space

        # get the character from the mapping
        try:
            w_ch = space.getitem(self.w_mapping, space.newint(ch))
        except OperationError as e:
            if not e.match(space, space.w_LookupError):
                raise
            return errorchar

        if space.isinstance_w(w_ch, space.w_bytes):
            # Charmap may return a string
            return space.bytes_w(w_ch)
        elif space.isinstance_w(w_ch, space.w_int):
            # Charmap may return a number
            x = space.int_w(w_ch)
            if not 0 <= x < 256:
                raise oefmt(space.w_TypeError,
                    "character mapping must be in range(256)")
            return chr(x)
        elif space.is_w(w_ch, space.w_None):
            # Charmap may return None
            return errorchar

        raise oefmt(space.w_TypeError,
            "character mapping must return integer, None or str")


@unwrap_spec(string='bufferstr', errors='text_or_none')
def charmap_decode(space, string, errors="strict", w_mapping=None):
    from pypy.interpreter import unicodehelper

    if errors is None:
        errors = 'strict'
    if len(string) == 0:
        return space.newtuple([space.newutf8('', 0),
                               space.newint(0)])

    if space.is_none(w_mapping):
        mapping = None
    else:
        mapping = Charmap_Decode(space, w_mapping)

    final = True
    state = space.fromcache(CodecState)
    result, consumed, lgt = unicodehelper.str_decode_charmap(
        string, errors, final, state.decode_error_handler, mapping)
    return space.newtuple([space.newutf8(result, lgt),
                           space.newint(consumed)])

@unwrap_spec(errors='text_or_none')
def charmap_encode(space, w_unicode, errors="strict", w_mapping=None):
    from pypy.interpreter import unicodehelper

    if errors is None:
        errors = 'strict'
    if space.is_none(w_mapping):
        mapping = None
    else:
        mapping = Charmap_Encode(space, w_mapping)

    state = space.fromcache(CodecState)
    w_uni = space.convert_arg_to_w_unicode(w_unicode)
    result = unicodehelper.utf8_encode_charmap(
        space.utf8_w(w_uni), errors, state.encode_error_handler, mapping)
    return space.newtuple([space.newbytes(result), space.newint(w_uni._len())])


@unwrap_spec(chars='utf8')
def charmap_build(space, chars):
    # XXX CPython sometimes uses a three-level trie
    w_charmap = space.newdict()
    pos = 0
    num = 0
    while pos < len(chars):
        w_char = space.newint(rutf8.codepoint_at_pos(chars, pos))
        space.setitem(w_charmap, w_char, space.newint(num))
        pos = rutf8.next_codepoint_pos(chars, pos)
        num += 1
    return w_charmap

# ____________________________________________________________
# Unicode escape

class UnicodeData_Handler:
    def __init__(self, space, w_getcode):
        self.space = space
        self.w_getcode = w_getcode

    def call(self, name):
        space = self.space
        try:
            w_code = space.call_function(self.w_getcode, space.newtext(name))
        except OperationError as e:
            if not e.match(space, space.w_KeyError):
                raise
            return -1
        return space.int_w(w_code)

@unwrap_spec(string='bufferstr', errors='text_or_none',
             w_final=WrappedDefault(False))
def unicode_escape_decode(space, string, errors="strict", w_final=None):
    from pypy.interpreter import unicodehelper

    if errors is None:
        errors = 'strict'
    final = space.is_true(w_final)
    state = space.fromcache(CodecState)

    unicode_name_handler = state.get_unicodedata_handler(space)

    result, consumed, lgt = unicodehelper.str_decode_unicode_escape(
        string, errors,
        final, state.decode_error_handler,
        unicode_name_handler)

    return space.newtuple([space.newutf8(result, lgt), space.newint(consumed)])

# ____________________________________________________________
# Unicode-internal

@unwrap_spec(errors='text_or_none')
def unicode_internal_decode(space, w_string, errors="strict"):
    from pypy.interpreter import unicodehelper

    if errors is None:
        errors = 'strict'
    # special case for this codec: unicodes are returned as is
    if space.isinstance_w(w_string, space.w_unicode):
        return space.newtuple([w_string, space.len(w_string)])

    string = space.readbuf_w(w_string).as_str()

    if len(string) == 0:
        return space.newtuple([space.newutf8('', 0),
                               space.newint(0)])

    final = True
    state = space.fromcache(CodecState)
    result, consumed, lgt = unicodehelper.str_decode_unicode_internal(
        string, errors,
        final, state.decode_error_handler)
    return space.newtuple([space.newutf8(result, lgt),
                           space.newint(consumed)])

# ____________________________________________________________
# support for the "string escape" codec
# This is a bytes-to bytes transformation

@unwrap_spec(data='bytes', errors='text_or_none')
def escape_encode(space, data, errors='strict'):
    from pypy.objspace.std.bytesobject import string_escape_encode
    result = string_escape_encode(data, quote="'")
    start = 1
    end = len(result) - 1
    assert end >= 0
    w_result = space.newbytes(result[start:end])
    return space.newtuple([w_result, space.newint(len(data))])

@unwrap_spec(data='bytes', errors='text_or_none')
def escape_decode(space, data, errors='strict'):
    from pypy.interpreter.pyparser.parsestring import PyString_DecodeEscape
    result = PyString_DecodeEscape(space, data, errors, None)
    return space.newtuple([space.newbytes(result), space.newint(len(data))])
