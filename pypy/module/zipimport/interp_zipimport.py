
from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.error import OperationError, oefmt
from pypy.interpreter.gateway import interp2app, unwrap_spec
from pypy.interpreter.typedef import TypeDef, GetSetProperty
from pypy.interpreter.module import Module
from pypy.module.imp import importing
from pypy.module.zlib.interp_zlib import zlib_error
from rpython.rlib.unroll import unrolling_iterable
from rpython.rlib.rzipfile import RZipFile, BadZipfile
from rpython.rlib.rzlib import RZlibError
import os
import stat

ZIPSEP = '/'
# note that zipfiles always use slash, but for OSes with other
# separators, we need to pretend that we had the os.sep.

ENUMERATE_EXTS = unrolling_iterable(
    [(True, True, ZIPSEP + '__init__.pyc'),
     (True, True, ZIPSEP + '__init__.pyo'),
     (False, True, ZIPSEP + '__init__.py'),
     (True, False, '.pyc'),
     (True, False, '.pyo'),
     (False, False, '.py')])

class Cache:
    def __init__(self, space):
        self.w_error = space.new_exception_class("zipimport.ZipImportError",
                                                 space.w_ImportError)

def get_error(space):
    return space.fromcache(Cache).w_error

class W_ZipCache(W_Root):
    def __init__(self):
        self.cache = {}

    def get(self, name):
        return self.cache[name]

    def set(self, name, w_importer):
        self.cache[name] = w_importer

    # -------------- dict-like interface -----------------
    # I don't care about speed of those, they're obscure anyway
    # THIS IS A TERRIBLE HACK TO BE CPYTHON COMPATIBLE

    @unwrap_spec(name='text')
    def getitem(self, space, name):
        try:
            w_zipimporter = self.cache[name]
        except KeyError:
            raise OperationError(space.w_KeyError, space.newtext(name))
        assert isinstance(w_zipimporter, W_ZipImporter)
        w_d = space.newdict()
        for key, info in w_zipimporter.zip_file.NameToInfo.iteritems():
            if ZIPSEP != os.path.sep:
                key = key.replace(ZIPSEP, os.path.sep)
            space.setitem(w_d, space.newtext(key), space.newtuple([
                space.newtext(info.filename), space.newint(info.compress_type), space.newint(info.compress_size),
                space.newint(info.file_size), space.newint(info.file_offset), space.newint(info.dostime),
                space.newint(info.dosdate), space.newint(info.CRC)]))
        return w_d

    def keys(self, space):
        return space.newlist([space.newtext(s)
                              for s in self.cache.keys()])

    def values(self, space):
        keys = self.cache.keys()
        values_w = [self.getitem(space, key) for key in keys]
        return space.newlist(values_w)

    def items(self, space):
        items_w = [space.newtuple([space.newtext(key), self.getitem(space, key)])
                   for key in self.cache.keys()]
        return space.newlist(items_w)

    def iterkeys(self, space):
        return space.iter(self.keys(space))

    def itervalues(self, space):
        return space.iter(self.values(space))

    def iteritems(self, space):
        return space.iter(self.items(space))

    @unwrap_spec(name='text')
    def contains(self, space, name):
        return space.newbool(name in self.cache)

    def clear(self, space):
        self.cache = {}

    @unwrap_spec(name='text')
    def delitem(self, space, name):
        del self.cache[name]

W_ZipCache.typedef = TypeDef(
    'zip_dict',
    __getitem__ = interp2app(W_ZipCache.getitem),
    __contains__ = interp2app(W_ZipCache.contains),
    __iter__ = interp2app(W_ZipCache.iterkeys),
    items = interp2app(W_ZipCache.items),
    iteritems = interp2app(W_ZipCache.iteritems),
    keys = interp2app(W_ZipCache.keys),
    iterkeys = interp2app(W_ZipCache.iterkeys),
    values = interp2app(W_ZipCache.values),
    itervalues = interp2app(W_ZipCache.itervalues),
    clear = interp2app(W_ZipCache.clear),
    __delitem__ = interp2app(W_ZipCache.delitem),
)

zip_cache = W_ZipCache()

class W_ZipImporter(W_Root):
    def __init__(self, space, name, filename, zip_file, prefix):
        self.space = space
        self.name = name
        self.filename = filename
        self.zip_file = zip_file
        self.prefix = prefix

    def getprefix(self, space):
        if ZIPSEP == os.path.sep:
            return space.newtext(self.prefix)
        return space.newtext(self.prefix.replace(ZIPSEP, os.path.sep))

    def _find_relative_path(self, filename):
        if filename.startswith(self.filename):
            filename = filename[len(self.filename):]
        if filename.startswith(os.path.sep) or filename.startswith(ZIPSEP):
            filename = filename[1:]
        if ZIPSEP != os.path.sep:
            filename = filename.replace(os.path.sep, ZIPSEP)
        return filename

    def corr_zname(self, fname):
        if ZIPSEP != os.path.sep:
            return fname.replace(ZIPSEP, os.path.sep)
        else:
            return fname

    def import_py_file(self, space, modname, filename, buf, pkgpath):
        w_mod = Module(space, space.newtext(modname))
        real_name = self.filename + os.path.sep + self.corr_zname(filename)
        space.setattr(w_mod, space.newtext('__loader__'), self)
        importing._prepare_module(space, w_mod, real_name, pkgpath)
        co_filename = self.make_co_filename(filename)
        code_w = importing.parse_source_module(space, co_filename, buf)
        return importing.exec_code_module(space, w_mod, code_w, space.newtext(modname))

    def _parse_mtime(self, space, filename):
        try:
            info = self.zip_file.NameToInfo[filename]
            t = info.date_time
        except KeyError:
            return 0
        else:
            w_mktime = space.getattr(space.getbuiltinmodule('time'),
                                     space.newtext('mktime'))
            # XXX this is incredible fishing around module limitations
            #     in order to compare timestamps of .py and .pyc files
            # we need time.mktime support on rpython level
            w = space.newint
            all = [w(t[0]), w(t[1]), w(t[2]), w(t[3]), w(t[4]),
                   w(t[5]), w(0), w(1), w(-1)]
            mtime = int(space.float_w(space.call_function(
                w_mktime, space.newtuple(all))))
            return mtime

    def check_newer_pyfile(self, space, filename, timestamp):
        # check if the timestamp stored in the .pyc is matching
        # the actual timestamp of the .py file, if any
        mtime = self._parse_mtime(space, filename)
        if mtime == 0:
            return False
        # Lenient date/time comparison function. The precision of the mtime
        # in the archive is lower than the mtime stored in a .pyc: we
        # must allow a difference of at most one second.
        d = mtime - timestamp
        if d < 0:
            d = -d
        return d > 1    # more than one second => different

    def can_use_pyc(self, space, filename, magic, timestamp):
        if magic != importing.get_pyc_magic(space):
            return False
        if self.check_newer_pyfile(space, filename[:-1], timestamp):
            return False
        return True

    def import_pyc_file(self, space, modname, filename, buf, pkgpath):
        if len(buf) < 8:
            raise oefmt(get_error(space), "bad pyc data")
        magic = importing._get_long(buf[:4])
        timestamp = importing._get_long(buf[4:8])
        if not self.can_use_pyc(space, filename, magic, timestamp):
            return None
        buf = buf[8:] # XXX ugly copy, should use sequential read instead
        w_mod = Module(space, space.newtext(modname))
        real_name = self.filename + os.path.sep + self.corr_zname(filename)
        space.setattr(w_mod, space.newtext('__loader__'), self)
        importing._prepare_module(space, w_mod, real_name, pkgpath)
        w_result = importing.load_compiled_module(space, space.newtext(modname), w_mod,
                                                filename, magic, timestamp,
                                                buf)
        return w_result

    def have_modulefile(self, space, filename):
        if ZIPSEP != os.path.sep:
            filename = filename.replace(os.path.sep, ZIPSEP)
        try:
            self.zip_file.NameToInfo[filename]
            return True
        except KeyError:
            return False

    @unwrap_spec(fullname='text')
    def find_module(self, space, fullname, w_path=None):
        filename = self.make_filename(fullname)
        for _, _, ext in ENUMERATE_EXTS:
            if self.have_modulefile(space, filename + ext):
                return self

    def make_filename(self, fullname):
        startpos = fullname.rfind('.') + 1 # 0 when not found
        assert startpos >= 0
        subname = fullname[startpos:]
        if ZIPSEP == os.path.sep:
            return self.prefix + subname.replace('.', '/')
        else:
            return self.prefix.replace(os.path.sep, ZIPSEP) + \
                    subname.replace('.', '/')

    def make_co_filename(self, filename):
        """
        Return the filename to be used for compiling the module, i.e. what
        gets in code_object.co_filename. Something like
        'myfile.zip/mymodule.py'
        """
        return self.filename + os.path.sep + filename

    @unwrap_spec(fullname='text')
    def load_module(self, space, fullname):
        filename = self.make_filename(fullname)
        for compiled, is_package, ext in ENUMERATE_EXTS:
            fname = filename + ext
            try:
                buf = self.zip_file.read(fname)
            except (KeyError, OSError, BadZipfile):
                pass
            except RZlibError as e:
                # in this case, CPython raises the direct exception coming
                # from the zlib module: let's do the same
                raise zlib_error(space, e.msg)
            else:
                if is_package:
                    pkgpath = (self.filename + os.path.sep +
                               self.corr_zname(filename))
                else:
                    pkgpath = None
                try:
                    if compiled:
                        w_result = self.import_pyc_file(space, fullname, fname,
                                                        buf, pkgpath)
                        if w_result is None:
                            continue
                    else:
                        w_result = self.import_py_file(space, fullname, fname,
                                                   buf, pkgpath)
                    if space.sys.get_flag('verbose') >= 1:
                        w_stderr = space.sys.get('stderr')
                        message = "import %s # loaded from Zip %s%s%s\n" % (
                                fullname, self.filename, os.path.sep, fname)
                        space.call_method(w_stderr, "write",
                                          space.newtext(message))
                    return w_result
                except:
                    w_mods = space.sys.get('modules')
                    space.call_method(w_mods, 'pop', space.newtext(fullname), space.w_None)
                    raise
        raise oefmt(get_error(space), "can't find module '%s'", fullname)

    @unwrap_spec(filename='text')
    def get_data(self, space, filename):
        filename = self._find_relative_path(filename)
        try:
            data = self.zip_file.read(filename)
            return space.newbytes(data)
        except (KeyError, OSError, BadZipfile):
            raise oefmt(space.w_IOError, "Error reading file")
        except RZlibError as e:
            # in this case, CPython raises the direct exception coming
            # from the zlib module: let's do the same
            raise zlib_error(space, e.msg)

    @unwrap_spec(fullname='text')
    def get_code(self, space, fullname):
        filename = self.make_filename(fullname)
        for compiled, _, ext in ENUMERATE_EXTS:
            if self.have_modulefile(space, filename + ext):
                w_source = self.get_data(space, filename + ext)
                source = space.bytes_w(w_source)
                if compiled:
                    if len(source) < 8:
                        raise oefmt(get_error(space), "bad pyc data")
                    magic = importing._get_long(source[:4])
                    timestamp = importing._get_long(source[4:8])
                    if not self.can_use_pyc(space, filename + ext,
                                            magic, timestamp):
                        continue
                    w_code = importing.read_compiled_module(
                        space, filename + ext, source[8:])
                else:
                    co_filename = self.make_co_filename(filename+ext)
                    w_code = importing.parse_source_module(
                        space, co_filename, source)
                return w_code
        raise oefmt(get_error(space),
                    "Cannot find source or code for %s in %s",
                    filename, self.name)

    @unwrap_spec(fullname='text')
    def get_source(self, space, fullname):
        filename = self.make_filename(fullname)
        found = False
        for compiled, _, ext in ENUMERATE_EXTS:
            fname = filename + ext
            if self.have_modulefile(space, fname):
                if not compiled:
                    return self.get_data(space, fname)
                else:
                    found = True
        if found:
            return space.w_None
        raise oefmt(get_error(space),
                    "Cannot find source for %s in %s", filename, self.name)

    @unwrap_spec(fullname='text')
    def get_filename(self, space, fullname):
        filename = self.make_filename(fullname)
        for _, is_package, ext in ENUMERATE_EXTS:
            if self.have_modulefile(space, filename + ext):
                return space.newtext(self.filename + os.path.sep +
                                     self.corr_zname(filename + ext))
        raise oefmt(get_error(space),
                    "Cannot find module %s in %s", filename, self.name)

    @unwrap_spec(fullname='text')
    def is_package(self, space, fullname):
        filename = self.make_filename(fullname)
        for _, is_package, ext in ENUMERATE_EXTS:
            if self.have_modulefile(space, filename + ext):
                return space.newbool(is_package)
        raise oefmt(get_error(space),
                    "Cannot find module %s in %s", filename, self.name)

    def getarchive(self, space):
        space = self.space
        return space.newtext(self.filename)

@unwrap_spec(name='text0')
def descr_new_zipimporter(space, w_type, name):
    ok = False
    parts_ends = [i for i in range(0, len(name))
                    if name[i] == os.path.sep or name[i] == ZIPSEP]
    parts_ends.append(len(name))
    filename = "" # make annotator happy
    for i in parts_ends:
        filename = name[:i]
        if not filename:
            filename = os.path.sep
        try:
            s = os.stat(filename)
        except OSError:
            raise oefmt(get_error(space), "Cannot find name %s", filename)
        if not stat.S_ISDIR(s.st_mode):
            ok = True
            break
    if not ok:
        raise oefmt(get_error(space), "Did not find %s to be a valid zippath",
                    name)
    try:
        w_result = zip_cache.get(filename)
        if w_result is None:
            raise oefmt(get_error(space),
                        "Cannot import %s from zipfile, recursion detected or"
                        "already tried and failed", name)
    except KeyError:
        zip_cache.cache[filename] = None
    try:
        zip_file = RZipFile(filename, 'r')
    except (BadZipfile, OSError):
        raise oefmt(get_error(space), "%s seems not to be a zipfile", filename)
    except RZlibError as e:
        # in this case, CPython raises the direct exception coming
        # from the zlib module: let's do the same
        raise zlib_error(space, e.msg)

    prefix = name[len(filename):]
    if prefix.startswith(os.path.sep) or prefix.startswith(ZIPSEP):
        prefix = prefix[1:]
    if prefix and not prefix.endswith(ZIPSEP) and not prefix.endswith(os.path.sep):
        prefix += ZIPSEP
    w_result = W_ZipImporter(space, name, filename, zip_file, prefix)
    zip_cache.set(filename, w_result)
    return w_result

W_ZipImporter.typedef = TypeDef(
    'zipimporter',
    __new__     = interp2app(descr_new_zipimporter),
    find_module = interp2app(W_ZipImporter.find_module),
    get_data    = interp2app(W_ZipImporter.get_data),
    get_code    = interp2app(W_ZipImporter.get_code),
    get_source  = interp2app(W_ZipImporter.get_source),
    get_filename = interp2app(W_ZipImporter.get_filename),
    is_package  = interp2app(W_ZipImporter.is_package),
    load_module = interp2app(W_ZipImporter.load_module),
    archive     = GetSetProperty(W_ZipImporter.getarchive),
    prefix      = GetSetProperty(W_ZipImporter.getprefix),
)
