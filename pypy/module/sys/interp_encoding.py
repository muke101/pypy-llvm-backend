import sys
from rpython.rlib import rlocale
from rpython.rlib.objectmodel import we_are_translated

def getdefaultencoding(space):
    """Return the current default string encoding used by the Unicode
implementation."""
    return space.newtext(space.sys.defaultencoding)

def setdefaultencoding(space, w_encoding):
    """Set the current default string encoding used by the Unicode
implementation."""
    encoding = space.text_w(w_encoding)
    mod = space.getbuiltinmodule("_codecs")
    w_lookup = space.getattr(mod, space.newtext("lookup"))
    # check whether the encoding is there
    space.call_function(w_lookup, w_encoding)
    space.sys.w_default_encoder = None
    space.sys.defaultencoding = encoding

def get_w_default_encoder(space):
    assert not (space.config.translating and not we_are_translated()), \
        "get_w_default_encoder() should not be called during translation"
    w_encoding = space.newtext(space.sys.defaultencoding)
    mod = space.getbuiltinmodule("_codecs")
    w_lookup = space.getattr(mod, space.newtext("lookup"))
    w_functuple = space.call_function(w_lookup, w_encoding)
    w_encoder = space.getitem(w_functuple, space.newint(0))
    space.sys.w_default_encoder = w_encoder    # cache it
    return w_encoder

if sys.platform == "win32":
    base_encoding = "mbcs"
elif sys.platform == "darwin":
    base_encoding = "utf-8"
else:
    # In CPython, the default base encoding is NULL. This is paired with a
    # comment that says "If non-NULL, this is different than the default
    # encoding for strings". Therefore, the default filesystem encoding is the
    # default encoding for strings, which is ASCII.
    base_encoding = "ascii"

def _getfilesystemencoding(space):
    encoding = base_encoding
    if rlocale.HAVE_LANGINFO:
        try:
            oldlocale = rlocale.setlocale(rlocale.LC_CTYPE, None)
            rlocale.setlocale(rlocale.LC_CTYPE, "")
            try:
                loc_codeset = rlocale.nl_langinfo(rlocale.CODESET)
                if loc_codeset:
                    codecmod = space.getbuiltinmodule('_codecs')
                    w_res = space.call_method(codecmod, 'lookup',
                                              space.newtext(loc_codeset))
                    if space.is_true(w_res):
                        encoding = loc_codeset
            finally:
                rlocale.setlocale(rlocale.LC_CTYPE, oldlocale)
        except rlocale.LocaleError:
            pass
    return encoding

def getfilesystemencoding(space):
    """Return the encoding used to convert Unicode filenames in
    operating system filenames.
    """
    if space.sys.filesystemencoding is None:
        space.sys.filesystemencoding = _getfilesystemencoding(space)
    return space.newtext(space.sys.filesystemencoding)
