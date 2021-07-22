from pypy.module.imp import importing
from pypy.module._file.interp_file import W_File
from rpython.rlib import streamio
from rpython.rlib.streamio import StreamErrors
from pypy.interpreter.error import oefmt
from pypy.interpreter.module import Module
from pypy.interpreter.gateway import unwrap_spec
from pypy.interpreter.streamutil import wrap_streamerror


def get_suffixes(space):
    suffixes_w = []
    if importing.has_so_extension(space):
        suffixes_w.append(
            space.newtuple([space.newtext(importing.get_so_extension(space)),
                            space.newtext('rb'),
                            space.newint(importing.C_EXTENSION)]))
    suffixes_w.extend([
        space.newtuple([space.newtext('.py'),
                        space.newtext('U'),
                        space.newint(importing.PY_SOURCE)]),
        space.newtuple([space.newtext('.pyc'),
                        space.newtext('rb'),
                        space.newint(importing.PY_COMPILED)]),
        ])
    return space.newlist(suffixes_w)

def get_magic(space):
    x = importing.get_pyc_magic(space)
    a = x & 0xff
    x >>= 8
    b = x & 0xff
    x >>= 8
    c = x & 0xff
    x >>= 8
    d = x & 0xff
    return space.newbytes(chr(a) + chr(b) + chr(c) + chr(d))

def get_file(space, w_file, filename, filemode):
    if space.is_none(w_file):
        try:
            return streamio.open_file_as_stream(filename, filemode)
        except StreamErrors as e:
            # XXX this is not quite the correct place, but it will do for now.
            # XXX see the issue which I'm sure exists already but whose number
            # XXX I cannot find any more...
            raise wrap_streamerror(space, e)
    else:
        return space.interp_w(W_File, w_file).stream

def find_module(space, w_name, w_path=None):
    name = space.text0_w(w_name)
    if space.is_none(w_path):
        w_path = None

    find_info = importing.find_module(
        space, name, w_name, name, w_path, use_loader=False)
    if not find_info:
        raise oefmt(space.w_ImportError, "No module named %s", name)

    w_filename = space.newtext(find_info.filename)
    stream = find_info.stream

    if stream is not None:
        fileobj = W_File(space)
        fileobj.fdopenstream(
            stream, stream.try_to_find_file_descriptor(),
            find_info.filemode, w_filename)
        w_fileobj = fileobj
    else:
        w_fileobj = space.w_None
    w_import_info = space.newtuple(
        [space.newtext(find_info.suffix),
         space.newtext(find_info.filemode),
         space.newint(find_info.modtype)])
    return space.newtuple([w_fileobj, w_filename, w_import_info])

def load_module(space, w_name, w_file, w_filename, w_info):
    w_suffix, w_filemode, w_modtype = space.unpackiterable(w_info, 3)

    filename = space.fsencode_w(w_filename)
    filemode = space.text_w(w_filemode)
    if space.is_w(w_file, space.w_None):
        stream = None
    else:
        stream = get_file(space, w_file, filename, filemode)

    find_info = importing.FindInfo(
        space.int_w(w_modtype),
        filename,
        stream,
        space.text_w(w_suffix),
        filemode)
    return importing.load_module(
        space, w_name, find_info, reuse=True)

def load_source(space, w_modulename, w_filename, w_file=None):
    filename = space.fsencode_w(w_filename)

    stream = get_file(space, w_file, filename, 'U')

    w_mod = Module(space, w_modulename)
    importing._prepare_module(space, w_mod, filename, None)

    w_mod = importing.load_source_module(
        space, w_modulename, w_mod,
        filename, importing._wrap_readall(space, stream),
        stream.try_to_find_file_descriptor())
    if space.is_none(w_file):
        importing._wrap_close(space, stream)
    return w_mod

@unwrap_spec(filename='fsencode', check_afterwards=int)
def _run_compiled_module(space, w_modulename, filename, w_file, w_module,
                         check_afterwards=False):
    # the function 'imp._run_compiled_module' is a pypy-only extension
    stream = get_file(space, w_file, filename, 'rb')

    magic = importing._wrap_r_long(space, stream)
    timestamp = importing._wrap_r_long(space, stream)

    w_mod = importing.load_compiled_module(
        space, w_modulename, w_module, filename, magic, timestamp,
        importing._wrap_readall(space, stream),
        check_afterwards=check_afterwards)
    if space.is_none(w_file):
        importing._wrap_close(space, stream)
    return w_mod

@unwrap_spec(filename='fsencode')
def load_compiled(space, w_modulename, filename, w_file=None):
    w_mod = Module(space, w_modulename)
    importing._prepare_module(space, w_mod, filename, None)
    return _run_compiled_module(space, w_modulename, filename, w_file, w_mod,
                                check_afterwards=True)

@unwrap_spec(filename='fsencode')
def load_dynamic(space, w_modulename, filename, w_file=None):
    if not importing.has_so_extension(space):
        raise oefmt(space.w_ImportError, "Not implemented")
    return importing.load_c_extension(space, filename,
                                      space.text_w(w_modulename))

def new_module(space, w_name):
    return Module(space, w_name, add_package=False)

def init_builtin(space, w_name):
    name = space.text0_w(w_name)
    if name not in space.builtin_modules:
        return
    if space.finditem(space.sys.get('modules'), w_name) is not None:
        raise oefmt(space.w_ImportError,
                    "cannot initialize a built-in module twice in PyPy")
    return space.getbuiltinmodule(name)

def init_frozen(space, w_name):
    return None

def is_builtin(space, w_name):
    name = space.text0_w(w_name)
    if name not in space.builtin_modules:
        return space.newint(0)
    if space.finditem(space.sys.get('modules'), w_name) is not None:
        return space.newint(-1)   # cannot be initialized again
    return space.newint(1)

def is_frozen(space, w_name):
    return space.w_False

#__________________________________________________________________

def lock_held(space):
    if space.config.objspace.usemodules.thread:
        return space.newbool(importing.getimportlock(space).lock_held_by_anyone())
    else:
        return space.w_False

def acquire_lock(space):
    if space.config.objspace.usemodules.thread:
        importing.getimportlock(space).acquire_lock()

def release_lock(space):
    if space.config.objspace.usemodules.thread:
        importing.getimportlock(space).release_lock(silent_after_fork=False)

def reinit_lock(space):
    if space.config.objspace.usemodules.thread:
        importing.getimportlock(space).reinit_lock()
