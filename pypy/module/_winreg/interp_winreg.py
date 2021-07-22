from __future__ import with_statement
from pypy.interpreter.baseobjspace import W_Root, BufferInterfaceNotFound
from pypy.interpreter.gateway import interp2app, unwrap_spec
from pypy.interpreter.typedef import TypeDef, GetSetProperty
from pypy.interpreter.error import OperationError, oefmt, wrap_windowserror
from rpython.rtyper.lltypesystem import rffi, lltype
from rpython.rlib import rwinreg, rwin32
from rpython.rlib.rarithmetic import r_uint, intmask
from rpython.translator.tool.cbuild import ExternalCompilationInfo


# wrappers needed to call the reflection functions loaded at runtime
# using WINAPI convention
eci = ExternalCompilationInfo(
    includes=['windows.h'],
    post_include_bits=[
        "RPY_EXTERN LONG\n"
        "pypy_RegChangeReflectionKey(FARPROC address, HKEY key);\n"
        "RPY_EXTERN LONG\n"
        "pypy_RegQueryReflectionKey(FARPROC address, HKEY key, LPBOOL isDisabled);\n"
        "RPY_EXTERN LONG\n"
        "pypy_RegDeleteKeyExA(FARPROC address, HKEY key, LPCSTR subkey,\n"
        "                    REGSAM sam, DWORD reserved);\n"
    ],
    separate_module_sources=['''
        LONG
        pypy_RegChangeReflectionKey(FARPROC address, HKEY key) {
            LONG (WINAPI *func)(HKEY);
            *(FARPROC*)&func = address;
            return func(key);
        }

        LONG
        pypy_RegQueryReflectionKey(FARPROC address, HKEY key, LPBOOL isDisabled) {
            LONG (WINAPI *func)(HKEY, LPBOOL);
            *(FARPROC*)&func = address;
            return func(key, isDisabled);
        }

        LONG
        pypy_RegDeleteKeyExA(FARPROC address, HKEY key, LPCSTR subkey,
                            REGSAM sam, DWORD reserved) {
            LONG (WINAPI *func)(HKEY, LPCSTR, REGSAM, DWORD);
            *(FARPROC*)&func = address;
            return func(key, subkey, sam, reserved);
        }
    '''],
)
pypy_RegChangeReflectionKey = rffi.llexternal(
    'pypy_RegChangeReflectionKey',
    [rffi.VOIDP, rwinreg.HKEY],
    rffi.LONG, compilation_info=eci)

pypy_RegQueryReflectionKey = rffi.llexternal(
    'pypy_RegQueryReflectionKey',
    [rffi.VOIDP, rwinreg.HKEY, rwin32.LPBOOL],
    rffi.LONG, compilation_info=eci)

pypy_RegDeleteKeyExA = rffi.llexternal(
    'pypy_RegDeleteKeyExA',
    [rffi.VOIDP, rwinreg.HKEY, rffi.CCHARP, rwinreg.REGSAM, rwin32.DWORD],
    rffi.LONG, compilation_info=eci)


def raiseWindowsError(space, errcode, context):
    message = rwin32.FormatError(errcode)
    raise OperationError(space.w_WindowsError,
                         space.newtuple([space.newint(errcode),
                                         space.newtext(message)]))

class W_HKEY(W_Root):
    def __init__(self, space, hkey):
        self.hkey = hkey
        self.space = space
        self.register_finalizer(space)

    def _finalize_(self):
        self.Close(self.space)

    def as_int(self):
        return rffi.cast(rffi.SIZE_T, self.hkey)

    def descr_nonzero(self, space):
        return space.newbool(self.as_int() != 0)

    def descr_handle_get(self, space):
        return space.newint(self.as_int())

    def descr_repr(self, space):
        return space.newtext("<PyHKEY:0x%x>" % (self.as_int(),))

    def descr_int(self, space):
        return space.newint(self.as_int())

    def descr__enter__(self, space):
        return self

    def descr__exit__(self, space, __args__):
        CloseKey(space, self)

    def Close(self, space):
        """key.Close() - Closes the underlying Windows handle.
If the handle is already closed, no error is raised."""
        CloseKey(space, self)

    def Detach(self, space):
        """int = key.Detach() - Detaches the Windows handle from the handle object.

The result is the value of the handle before it is detached.  If the
handle is already detached, this will return zero.

After calling this function, the handle is effectively invalidated,
but the handle is not closed.  You would call this function when you
need the underlying win32 handle to exist beyond the lifetime of the
handle object."""
        key = self.as_int()
        self.hkey = rwin32.NULL_HANDLE
        return space.newint(key)

@unwrap_spec(key=int)
def new_HKEY(space, w_subtype, key):
    hkey = rffi.cast(rwinreg.HKEY, key)
    return W_HKEY(space, hkey)
descr_HKEY_new = interp2app(new_HKEY)

W_HKEY.typedef = TypeDef(
    "_winreg.HKEYType",
    __doc__ = """\
PyHKEY Object - A Python object, representing a win32 registry key.

This object wraps a Windows HKEY object, automatically closing it when
the object is destroyed.  To guarantee cleanup, you can call either
the Close() method on the PyHKEY, or the CloseKey() method.

All functions which accept a handle object also accept an integer -
however, use of the handle object is encouraged.

Functions:
Close() - Closes the underlying handle.
Detach() - Returns the integer Win32 handle, detaching it from the object

Properties:
handle - The integer Win32 handle.

Operations:
__nonzero__ - Handles with an open object return true, otherwise false.
__int__ - Converting a handle to an integer returns the Win32 handle.
__cmp__ - Handle objects are compared using the handle value.""",
    __new__ = descr_HKEY_new,
    __repr__ = interp2app(W_HKEY.descr_repr),
    __int__ = interp2app(W_HKEY.descr_int),
    __nonzero__ = interp2app(W_HKEY.descr_nonzero),
    __enter__ = interp2app(W_HKEY.descr__enter__),
    __exit__ = interp2app(W_HKEY.descr__exit__),
    handle = GetSetProperty(W_HKEY.descr_handle_get),
    Close = interp2app(W_HKEY.Close),
    Detach = interp2app(W_HKEY.Detach),
    )

def hkey_w(w_hkey, space):
    if space.is_w(w_hkey, space.w_None):
        raise oefmt(space.w_TypeError,
                    "None is not a valid HKEY in this context")
    elif isinstance(w_hkey, W_HKEY):
        return w_hkey.hkey
    elif space.isinstance_w(w_hkey, space.w_int):
        return rffi.cast(rwinreg.HKEY, space.int_w(w_hkey))
    elif space.isinstance_w(w_hkey, space.w_long):
        return rffi.cast(rwinreg.HKEY, space.uint_w(w_hkey))
    else:
        raise oefmt(space.w_TypeError, "The object is not a PyHKEY object")

def CloseKey(space, w_hkey):
    """CloseKey(hkey) - Closes a previously opened registry key.

The hkey argument specifies a previously opened key.

Note that if the key is not closed using this method, it will be
closed when the hkey object is destroyed by Python."""
    hkey = hkey_w(w_hkey, space)
    if hkey:
        ret = rwinreg.RegCloseKey(hkey)
        if ret != 0:
            raiseWindowsError(space, ret, 'RegCloseKey')
    if isinstance(w_hkey, W_HKEY):
        space.interp_w(W_HKEY, w_hkey).hkey = rwin32.NULL_HANDLE

def FlushKey(space, w_hkey):
    """FlushKey(key) - Writes all the attributes of a key to the registry.

key is an already open key, or any one of the predefined HKEY_* constants.

It is not necessary to call RegFlushKey to change a key.
Registry changes are flushed to disk by the registry using its lazy flusher.
Registry changes are also flushed to disk at system shutdown.
Unlike CloseKey(), the FlushKey() method returns only when all the data has
been written to the registry.
An application should only call FlushKey() if it requires absolute certainty that registry changes are on disk.
If you don't know whether a FlushKey() call is required, it probably isn't."""
    hkey = hkey_w(w_hkey, space)
    if hkey:
        ret = rwinreg.RegFlushKey(hkey)
        if ret != 0:
            raiseWindowsError(space, ret, 'RegFlushKey')

@unwrap_spec(subkey="text", filename="text")
def LoadKey(space, w_hkey, subkey, filename):
    """LoadKey(key, sub_key, file_name) - Creates a subkey under the specified key
and stores registration information from a specified file into that subkey.

key is an already open key, or any one of the predefined HKEY_* constants.
sub_key is a string that identifies the sub_key to load
file_name is the name of the file to load registry data from.
 This file must have been created with the SaveKey() function.
 Under the file allocation table (FAT) file system, the filename may not
have an extension.

A call to LoadKey() fails if the calling process does not have the
SE_RESTORE_PRIVILEGE privilege.

If key is a handle returned by ConnectRegistry(), then the path specified
in fileName is relative to the remote computer.

The docs imply key must be in the HKEY_USER or HKEY_LOCAL_MACHINE tree"""
    hkey = hkey_w(w_hkey, space)
    ret = rwinreg.RegLoadKeyA(hkey, subkey, filename)
    if ret != 0:
        raiseWindowsError(space, ret, 'RegLoadKey')

@unwrap_spec(filename="text")
def SaveKey(space, w_hkey, filename):
    """SaveKey(key, file_name) - Saves the specified key, and all its subkeys to the specified file.

key is an already open key, or any one of the predefined HKEY_* constants.
file_name is the name of the file to save registry data to.
 This file cannot already exist. If this filename includes an extension,
 it cannot be used on file allocation table (FAT) file systems by the
 LoadKey(), ReplaceKey() or RestoreKey() methods.

If key represents a key on a remote computer, the path described by
file_name is relative to the remote computer.
The caller of this method must possess the SeBackupPrivilege security privilege.
This function passes NULL for security_attributes to the API."""
    hkey = hkey_w(w_hkey, space)
    ret = rwinreg.RegSaveKeyA(hkey, filename, None)
    if ret != 0:
        raiseWindowsError(space, ret, 'RegSaveKey')

@unwrap_spec(typ=int, value="text")
def SetValue(space, w_hkey, w_subkey, typ, value):
    """SetValue(key, sub_key, type, value) - Associates a value with a specified key.

key is an already open key, or any one of the predefined HKEY_* constants.
sub_key is a string that names the subkey with which the value is associated.
type is an integer that specifies the type of the data.  Currently this
 must be REG_SZ, meaning only strings are supported.
value is a string that specifies the new value.

If the key specified by the sub_key parameter does not exist, the SetValue
function creates it.

Value lengths are limited by available memory. Long values (more than
2048 bytes) should be stored as files with the filenames stored in
the configuration registry.  This helps the registry perform efficiently.

The key identified by the key parameter must have been opened with
KEY_SET_VALUE access."""
    if typ != rwinreg.REG_SZ:
        raise oefmt(space.w_ValueError, "Type must be _winreg.REG_SZ")
    hkey = hkey_w(w_hkey, space)
    if space.is_w(w_subkey, space.w_None):
        subkey = None
    else:
        subkey = space.text_w(w_subkey)
    with rffi.scoped_str2charp(value) as dataptr:
        ret = rwinreg.RegSetValueA(hkey, subkey, rwinreg.REG_SZ, dataptr, len(value))
        if ret != 0:
            raiseWindowsError(space, ret, 'RegSetValue')

def QueryValue(space, w_hkey, w_subkey):
    """string = QueryValue(key, sub_key) - retrieves the unnamed value for a key.

key is an already open key, or any one of the predefined HKEY_* constants.
sub_key is a string that holds the name of the subkey with which the value
 is associated.  If this parameter is None or empty, the function retrieves
 the value set by the SetValue() method for the key identified by key.

Values in the registry have name, type, and data components. This method
retrieves the data for a key's first value that has a NULL name.
But the underlying API call doesn't return the type, Lame Lame Lame, DONT USE THIS!!!"""
    hkey = hkey_w(w_hkey, space)
    if space.is_w(w_subkey, space.w_None):
        subkey = None
    else:
        subkey = space.text_w(w_subkey)
    with lltype.scoped_alloc(rwin32.PLONG.TO, 1) as bufsize_p:
        ret = rwinreg.RegQueryValueA(hkey, subkey, None, bufsize_p)
        bufSize = intmask(bufsize_p[0])
        if ret == rwinreg.ERROR_MORE_DATA:
            bufSize = 256
        elif ret != 0:
            raiseWindowsError(space, ret, 'RegQueryValue')

        while True:
            with lltype.scoped_alloc(rffi.CCHARP.TO, bufSize) as buf:
                ret = rwinreg.RegQueryValueA(hkey, subkey, buf, bufsize_p)
                if ret == rwinreg.ERROR_MORE_DATA:
                    # Resize and retry
                    bufSize *= 2
                    bufsize_p[0] = rffi.cast(rwin32.LONG, bufSize)
                    continue

                if ret != 0:
                    raiseWindowsError(space, ret, 'RegQueryValue')
                length = intmask(bufsize_p[0])
                if length == 0:
                    return space.w_None
                return space.newtext(rffi.charp2strn(buf, length - 1))

def convert_to_regdata(space, w_value, typ):
    buf = None

    if typ == rwinreg.REG_DWORD:
        if space.is_none(w_value) or (
                space.isinstance_w(w_value, space.w_int) or
                space.isinstance_w(w_value, space.w_long)):
            if space.is_none(w_value):
                value = r_uint(0)
            else:
                value = space.c_uint_w(w_value)
            buflen = rffi.sizeof(rwin32.DWORD)
            buf1 = lltype.malloc(rffi.CArray(rwin32.DWORD), 1, flavor='raw')
            buf1[0] = rffi.cast(rffi.UINT, value)
            buf = rffi.cast(rffi.CCHARP, buf1)

    elif typ == rwinreg.REG_SZ or typ == rwinreg.REG_EXPAND_SZ:
        if space.is_w(w_value, space.w_None):
            buflen = 1
            buf = lltype.malloc(rffi.CCHARP.TO, buflen, flavor='raw')
            buf[0] = '\0'
        else:
            if space.isinstance_w(w_value, space.w_unicode):
                w_value = space.call_method(w_value, 'encode',
                                            space.newtext('mbcs'))
            buf = rffi.str2charp(space.text_w(w_value))
            buflen = space.len_w(w_value) + 1

    elif typ == rwinreg.REG_MULTI_SZ:
        if space.is_w(w_value, space.w_None):
            buflen = 1
            buf = lltype.malloc(rffi.CCHARP.TO, buflen, flavor='raw')
            buf[0] = '\0'
        elif space.isinstance_w(w_value, space.w_list):
            strings = []
            buflen = 0

            # unwrap strings and compute total size
            w_iter = space.iter(w_value)
            while True:
                try:
                    w_item = space.next(w_iter)
                    if space.isinstance_w(w_item, space.w_unicode):
                        w_item = space.call_method(w_item, 'encode',
                                                   space.newtext('mbcs'))
                    item = space.bytes_w(w_item)
                    strings.append(item)
                    buflen += len(item) + 1
                except OperationError as e:
                    if not e.match(space, space.w_StopIteration):
                        raise       # re-raise other app-level exceptions
                    break
            buflen += 1
            buf = lltype.malloc(rffi.CCHARP.TO, buflen, flavor='raw')

            # Now copy data
            buflen = 0
            for string in strings:
                for i in range(len(string)):
                    buf[buflen + i] = string[i]
                buflen += len(string) + 1
                buf[buflen - 1] = '\0'
            buflen += 1
            buf[buflen - 1] = '\0'

    else: # REG_BINARY and ALL unknown data types.
        if space.is_w(w_value, space.w_None):
            buflen = 0
            buf = lltype.nullptr(rffi.CCHARP.TO)
        else:
            try:
                value = w_value.readbuf_w(space)
            except BufferInterfaceNotFound:
                raise oefmt(space.w_TypeError,
                            "Objects of type '%T' can not be used as binary "
                            "registry values", w_value)
            else:
                value = value.as_str()
            buflen = len(value)
            buf = rffi.str2charp(value)

    if buf is not None:
        return rffi.cast(rffi.CCHARP, buf), buflen

    raise oefmt(space.w_ValueError,
                "Could not convert the data to the specified type")

def convert_from_regdata(space, buf, buflen, typ):
    if typ == rwinreg.REG_DWORD:
        if not buflen:
            return space.newint(0)
        d = rffi.cast(rwin32.LPDWORD, buf)[0]
        return space.newint(d)

    elif typ == rwinreg.REG_SZ or typ == rwinreg.REG_EXPAND_SZ:
        if not buflen:
            s = ""
        else:
            # may or may not have a trailing NULL in the buffer.
            buf = rffi.cast(rffi.CCHARP, buf)
            if buf[buflen - 1] == '\x00':
                buflen -= 1
            s = rffi.charp2strn(buf, buflen)
        w_s = space.newbytes(s)
        return space.call_method(w_s, 'decode', space.newtext('mbcs'))

    elif typ == rwinreg.REG_MULTI_SZ:
        if not buflen:
            return space.newlist([])
        i = 0
        l = []
        while i < buflen and buf[i]:
            s = []
            while i < buflen and buf[i] != '\0':
                s.append(buf[i])
                i += 1
            if len(s) == 0:
                break
            s = ''.join(s)
            l.append(space.newtext(s))
            i += 1
        return space.newlist(l)

    else: # REG_BINARY and all other types
        if buflen == 0:
            return space.w_None
        else:
            return space.newbytes(rffi.charpsize2str(buf, buflen))

@unwrap_spec(value_name="text", typ=int)
def SetValueEx(space, w_hkey, value_name, w_reserved, typ, w_value):
    """SetValueEx(key, value_name, reserved, type, value) - Stores data in the value field of an open registry key.

key is an already open key, or any one of the predefined HKEY_* constants.
value_name is a string containing the name of the value to set, or None
type is an integer that specifies the type of the data.  This should be one of:
  REG_BINARY -- Binary data in any form.
  REG_DWORD -- A 32-bit number.
  REG_DWORD_LITTLE_ENDIAN -- A 32-bit number in little-endian format.
  REG_DWORD_BIG_ENDIAN -- A 32-bit number in big-endian format.
  REG_EXPAND_SZ -- A null-terminated string that contains unexpanded references
                   to environment variables (for example, %PATH%).
  REG_LINK -- A Unicode symbolic link.
  REG_MULTI_SZ -- An sequence of null-terminated strings, terminated by
                  two null characters.  Note that Python handles this
                  termination automatically.
  REG_NONE -- No defined value type.
  REG_RESOURCE_LIST -- A device-driver resource list.
  REG_SZ -- A null-terminated string.
reserved can be anything - zero is always passed to the API.
value is a string that specifies the new value.

This method can also set additional value and type information for the
specified key.  The key identified by the key parameter must have been
opened with KEY_SET_VALUE access.

To open the key, use the CreateKeyEx() or OpenKeyEx() methods.

Value lengths are limited by available memory. Long values (more than
2048 bytes) should be stored as files with the filenames stored in
the configuration registry.  This helps the registry perform efficiently."""
    hkey = hkey_w(w_hkey, space)
    buf, buflen = convert_to_regdata(space, w_value, typ)
    try:
        ret = rwinreg.RegSetValueExA(hkey, value_name, 0, typ, buf, buflen)
    finally:
        if buf != lltype.nullptr(rffi.CCHARP.TO):
            lltype.free(buf, flavor='raw')
    if ret != 0:
        raiseWindowsError(space, ret, 'RegSetValueEx')

def QueryValueEx(space, w_hkey, w_subkey):
    """value,type_id = QueryValueEx(key, value_name) - Retrieves the type and data for a specified value name associated with an open registry key.

key is an already open key, or any one of the predefined HKEY_* constants.
value_name is a string indicating the value to query"""
    hkey = hkey_w(w_hkey, space)
    if space.is_w(w_subkey, space.w_None):
        subkey = None
    else:
        subkey = space.text_w(w_subkey)
    null_dword = lltype.nullptr(rwin32.LPDWORD.TO)
    with lltype.scoped_alloc(rwin32.LPDWORD.TO, 1) as retDataSize:
        ret = rwinreg.RegQueryValueExA(hkey, subkey, null_dword, null_dword,
                                      None, retDataSize)
        bufSize = intmask(retDataSize[0])
        if ret == rwinreg.ERROR_MORE_DATA:
            bufSize = 256
        elif ret != 0:
            raiseWindowsError(space, ret, 'RegQueryValueEx')

        while True:
            with lltype.scoped_alloc(rffi.CCHARP.TO, bufSize) as databuf:
                with lltype.scoped_alloc(rwin32.LPDWORD.TO, 1) as retType:

                    ret = rwinreg.RegQueryValueExA(hkey, subkey, null_dword,
                                                  retType, databuf, retDataSize)
                    if ret == rwinreg.ERROR_MORE_DATA:
                        # Resize and retry
                        bufSize *= 2
                        retDataSize[0] = rffi.cast(rwin32.DWORD, bufSize)
                        continue
                    if ret != 0:
                        raiseWindowsError(space, ret, 'RegQueryValueEx')
                    length = intmask(retDataSize[0])
                    ret_type = intmask(retType[0])
                    return space.newtuple([
                        convert_from_regdata(space, databuf,
                                             length, ret_type),
                        space.newint(intmask(ret_type)),
                        ])

@unwrap_spec(subkey="text")
def CreateKey(space, w_hkey, subkey):
    """key = CreateKey(key, sub_key) - Creates or opens the specified key.

key is an already open key, or one of the predefined HKEY_* constants
sub_key is a string that names the key this method opens or creates.
 If key is one of the predefined keys, sub_key may be None. In that case,
 the handle returned is the same key handle passed in to the function.

If the key already exists, this function opens the existing key

The return value is the handle of the opened key.
If the function fails, an exception is raised."""
    hkey = hkey_w(w_hkey, space)
    with lltype.scoped_alloc(rwinreg.PHKEY.TO, 1) as rethkey:
        ret = rwinreg.RegCreateKeyA(hkey, subkey, rethkey)
        if ret != 0:
            raiseWindowsError(space, ret, 'CreateKey')
        return W_HKEY(space, rethkey[0])

@unwrap_spec(subkey="text", res=int, sam=r_uint)
def CreateKeyEx(space, w_hkey, subkey, res=0, sam=rwinreg.KEY_WRITE):
    """key = CreateKey(key, sub_key) - Creates or opens the specified key.

key is an already open key, or one of the predefined HKEY_* constants
sub_key is a string that names the key this method opens or creates.
 If key is one of the predefined keys, sub_key may be None. In that case,
 the handle returned is the same key handle passed in to the function.

If the key already exists, this function opens the existing key

The return value is the handle of the opened key.
If the function fails, an exception is raised."""
    hkey = hkey_w(w_hkey, space)
    with lltype.scoped_alloc(rwinreg.PHKEY.TO, 1) as rethkey:
        ret = rwinreg.RegCreateKeyExA(hkey, subkey, res, None, 0,
                                     sam, None, rethkey,
                                     lltype.nullptr(rwin32.LPDWORD.TO))
        if ret != 0:
            raiseWindowsError(space, ret, 'CreateKeyEx')
        return W_HKEY(space, rethkey[0])

@unwrap_spec(subkey="text")
def DeleteKey(space, w_hkey, subkey):
    """DeleteKey(key, sub_key) - Deletes the specified key.

key is an already open key, or any one of the predefined HKEY_* constants.
sub_key is a string that must be a subkey of the key identified by the key parameter.
 This value must not be None, and the key may not have subkeys.

This method can not delete keys with subkeys.

If the method succeeds, the entire key, including all of its values,
is removed.  If the method fails, an EnvironmentError exception is raised."""
    hkey = hkey_w(w_hkey, space)
    ret = rwinreg.RegDeleteKeyA(hkey, subkey)
    if ret != 0:
        raiseWindowsError(space, ret, 'RegDeleteKey')

@unwrap_spec(subkey="text")
def DeleteValue(space, w_hkey, subkey):
    """DeleteValue(key, value) - Removes a named value from a registry key.

key is an already open key, or any one of the predefined HKEY_* constants.
value is a string that identifies the value to remove."""
    hkey = hkey_w(w_hkey, space)
    ret = rwinreg.RegDeleteValueA(hkey, subkey)
    if ret != 0:
        raiseWindowsError(space, ret, 'RegDeleteValue')

@unwrap_spec(subkey="text", res=int, sam=r_uint)
def OpenKey(space, w_hkey, subkey, res=0, sam=rwinreg.KEY_READ):
    """key = OpenKey(key, sub_key, res = 0, sam = KEY_READ) - Opens the specified key.

key is an already open key, or any one of the predefined HKEY_* constants.
sub_key is a string that identifies the sub_key to open
res is a reserved integer, and must be zero.  Default is zero.
sam is an integer that specifies an access mask that describes the desired
 security access for the key.  Default is KEY_READ

The result is a new handle to the specified key
If the function fails, an EnvironmentError exception is raised."""
    hkey = hkey_w(w_hkey, space)
    with lltype.scoped_alloc(rwinreg.PHKEY.TO, 1) as rethkey:
        ret = rwinreg.RegOpenKeyExA(hkey, subkey, res, sam, rethkey)
        if ret != 0:
            raiseWindowsError(space, ret, 'RegOpenKeyEx')
        return W_HKEY(space, rethkey[0])

@unwrap_spec(index=int)
def EnumValue(space, w_hkey, index):
    """tuple = EnumValue(key, index) - Enumerates values of an open registry key.
key is an already open key, or any one of the predefined HKEY_* constants.
index is an integer that identifies the index of the value to retrieve.

The function retrieves the name of one subkey each time it is called.
It is typically called repeatedly, until an EnvironmentError exception
is raised, indicating no more values.

The result is a tuple of 3 items:
value_name is a string that identifies the value.
value_data is an object that holds the value data, and whose type depends
 on the underlying registry type.
data_type is an integer that identifies the type of the value data."""
    hkey = hkey_w(w_hkey, space)
    null_dword = lltype.nullptr(rwin32.LPDWORD.TO)

    with lltype.scoped_alloc(rwin32.LPDWORD.TO, 1) as retValueSize:
        with lltype.scoped_alloc(rwin32.LPDWORD.TO, 1) as retDataSize:
            ret = rwinreg.RegQueryInfoKeyA(
                hkey, None, null_dword, null_dword,
                null_dword, null_dword, null_dword,
                null_dword, retValueSize, retDataSize,
                null_dword, lltype.nullptr(rwin32.PFILETIME.TO))
            if ret != 0:
                raiseWindowsError(space, ret, 'RegQueryInfoKey')
            # include null terminators
            bufDataSize = intmask(retDataSize[0]) + 1
            bufValueSize = intmask(retValueSize[0]) + 1
            retValueSize[0] = rffi.cast(rwin32.DWORD, bufValueSize)
            retDataSize[0] = rffi.cast(rwin32.DWORD, bufDataSize)

            with lltype.scoped_alloc(rffi.CCHARP.TO,
                                     intmask(retValueSize[0])) as valuebuf:
                while True:
                    with lltype.scoped_alloc(rffi.CCHARP.TO,
                                             bufDataSize) as databuf:
                        with lltype.scoped_alloc(rwin32.LPDWORD.TO,
                                                 1) as retType:
                            ret = rwinreg.RegEnumValueA(
                                hkey, index, valuebuf, retValueSize,
                                null_dword, retType, databuf, retDataSize)
                            if ret == rwinreg.ERROR_MORE_DATA:
                                # Resize and retry
                                bufDataSize *= 2
                                retDataSize[0] = rffi.cast(rwin32.DWORD,
                                                           bufDataSize)
                                retValueSize[0] = rffi.cast(rwin32.DWORD,
                                                            bufValueSize)
                                continue

                            if ret != 0:
                                raiseWindowsError(space, ret, 'RegEnumValue')

                            length = intmask(retDataSize[0])
                            ret_type = intmask(retType[0])
                            return space.newtuple([
                                space.newtext(rffi.charp2str(valuebuf)),
                                convert_from_regdata(space, databuf,
                                                     length, ret_type),
                                space.newint(ret_type),
                                ])

@unwrap_spec(index=int)
def EnumKey(space, w_hkey, index):
    """string = EnumKey(key, index) - Enumerates subkeys of an open registry key.

key is an already open key, or any one of the predefined HKEY_* constants.
index is an integer that identifies the index of the key to retrieve.

The function retrieves the name of one subkey each time it is called.
It is typically called repeatedly until an EnvironmentError exception is
raised, indicating no more values are available."""
    hkey = hkey_w(w_hkey, space)
    null_dword = lltype.nullptr(rwin32.LPDWORD.TO)

    # The Windows docs claim that the max key name length is 255
    # characters, plus a terminating nul character.  However,
    # empirical testing demonstrates that it is possible to
    # create a 256 character key that is missing the terminating
    # nul.  RegEnumKeyEx requires a 257 character buffer to
    # retrieve such a key name.
    with lltype.scoped_alloc(rffi.CCHARP.TO, 257) as buf:
        with lltype.scoped_alloc(rwin32.LPDWORD.TO, 1) as retValueSize:
            retValueSize[0] = rffi.r_uint(257) # includes NULL terminator
            ret = rwinreg.RegEnumKeyExA(hkey, index, buf, retValueSize,
                                       null_dword, None, null_dword,
                                       lltype.nullptr(rwin32.PFILETIME.TO))
            if ret != 0:
                raiseWindowsError(space, ret, 'RegEnumKeyEx')
            return space.newtext(rffi.charp2str(buf))

def QueryInfoKey(space, w_hkey):
    """tuple = QueryInfoKey(key) - Returns information about a key.

key is an already open key, or any one of the predefined HKEY_* constants.

The result is a tuple of 3 items:
An integer that identifies the number of sub keys this key has.
An integer that identifies the number of values this key has.
A long integer that identifies when the key was last modified (if available)
 as 100's of nanoseconds since Jan 1, 1600."""
    hkey = hkey_w(w_hkey, space)
    with lltype.scoped_alloc(rwin32.LPDWORD.TO, 1) as nSubKeys:
        with lltype.scoped_alloc(rwin32.LPDWORD.TO, 1) as nValues:
            with lltype.scoped_alloc(rwin32.PFILETIME.TO, 1) as ft:
                null_dword = lltype.nullptr(rwin32.LPDWORD.TO)
                ret = rwinreg.RegQueryInfoKeyA(
                    hkey, None, null_dword, null_dword,
                    nSubKeys, null_dword, null_dword,
                    nValues, null_dword, null_dword,
                    null_dword, ft)
                if ret != 0:
                    raiseWindowsError(space, ret, 'RegQueryInfoKey')
                l = ((lltype.r_longlong(ft[0].c_dwHighDateTime) << 32) +
                     lltype.r_longlong(ft[0].c_dwLowDateTime))
                return space.newtuple([space.newint(nSubKeys[0]),
                                       space.newint(nValues[0]),
                                       space.newint(l)])

def ConnectRegistry(space, w_machine, w_hkey):
    """key = ConnectRegistry(computer_name, key)

Establishes a connection to a predefined registry handle on another computer.

computer_name is the name of the remote computer, of the form \\\\computername.
 If None, the local computer is used.
key is the predefined handle to connect to.

The return value is the handle of the opened key.
If the function fails, an EnvironmentError exception is raised."""
    machine = space.text_or_none_w(w_machine)
    hkey = hkey_w(w_hkey, space)
    with lltype.scoped_alloc(rwinreg.PHKEY.TO, 1) as rethkey:
        ret = rwinreg.RegConnectRegistryA(machine, hkey, rethkey)
        if ret != 0:
            raiseWindowsError(space, ret, 'RegConnectRegistry')
        return W_HKEY(space, rethkey[0])

def ExpandEnvironmentStrings(space, w_source):
    "string = ExpandEnvironmentStrings(string) - Expand environment vars."
    try:
        source, source_ulen = space.utf8_len_w(w_source)
        res, res_ulen = rwinreg.ExpandEnvironmentStrings(source, source_ulen)
        return space.newutf8(res, res_ulen)
    except WindowsError as e:
        raise wrap_windowserror(space, e)


class ReflectionFunction(object):
    def __init__(self, name, stdcall_wrapper):
        self.name = name
        self.handle = lltype.nullptr(rffi.VOIDP.TO)
        self.wrapper = stdcall_wrapper

    def check(self):
        if self.handle != lltype.nullptr(rffi.VOIDP.TO):
            return True
        from rpython.rlib.rdynload import GetModuleHandle, dlsym
        lib = GetModuleHandle("advapi32.dll")
        try:
            handle = dlsym(lib, self.name)
        except KeyError:
            return False
        self.handle = handle
        return True

    def call(self, *args):
        assert self.handle != lltype.nullptr(rffi.VOIDP.TO)
        return self.wrapper(self.handle, *args)


_RegDisableReflectionKey = ReflectionFunction(
    "RegDisableReflectionKey", pypy_RegChangeReflectionKey)
_RegEnableReflectionKey = ReflectionFunction(
    "RegEnableReflectionKey", pypy_RegChangeReflectionKey)
_RegQueryReflectionKey = ReflectionFunction(
    "RegQueryReflectionKey", pypy_RegQueryReflectionKey)
_RegDeleteKeyExA = ReflectionFunction("RegDeleteKeyExA", pypy_RegDeleteKeyExA)


def DisableReflectionKey(space, w_key):
    """Disables registry reflection for 32-bit processes running on a 64-bit
    Operating System.  Will generally raise NotImplemented if executed on
    a 32-bit Operating System.
    If the key is not on the reflection list, the function succeeds but has no effect.
    Disabling reflection for a key does not affect reflection of any subkeys."""
    if not _RegDisableReflectionKey.check():
        raise oefmt(space.w_NotImplementedError,
                    "not implemented on this platform")
    else:
        hkey = hkey_w(w_key, space)
        ret = _RegDisableReflectionKey.call(hkey)
        if ret != 0:
            raiseWindowsError(space, ret, 'RegDisableReflectionKey')

def EnableReflectionKey(space, w_key):
    """Restores registry reflection for the specified disabled key.
    Will generally raise NotImplemented if executed on a 32-bit Operating System.
    Restoring reflection for a key does not affect reflection of any subkeys."""
    if not _RegEnableReflectionKey.check():
        raise oefmt(space.w_NotImplementedError,
                    "not implemented on this platform")
    else:
        hkey = hkey_w(w_key, space)
        ret = _RegEnableReflectionKey.call(hkey)
        if ret != 0:
            raiseWindowsError(space, ret, 'RegEnableReflectionKey')

def QueryReflectionKey(space, w_key):
    """bool = QueryReflectionKey(hkey) - Determines the reflection state for the specified key.
    Will generally raise NotImplemented if executed on a 32-bit Operating System."""
    if not _RegQueryReflectionKey.check():
        raise oefmt(space.w_NotImplementedError,
                    "not implemented on this platform")
    else:
        hkey = hkey_w(w_key, space)
        with lltype.scoped_alloc(rwin32.LPBOOL.TO, 1) as isDisabled:
            ret = _RegQueryReflectionKey.call(hkey, isDisabled)
            if ret != 0:
                raiseWindowsError(space, ret, 'RegQueryReflectionKey')
            return space.newbool(intmask(isDisabled[0]) != 0)


@unwrap_spec(sub_key="text", access=r_uint, reserved=int)
def DeleteKeyEx(space, w_key, sub_key, access=rwinreg.KEY_WOW64_64KEY, reserved=0):
    """DeleteKeyEx(key, sub_key, sam, res) - Deletes the specified key.

    key is an already open key, or any one of the predefined HKEY_* constants.
    sub_key is a string that must be a subkey of the key identified by the key parameter.
    res is a reserved integer, and must be zero.  Default is zero.
    sam is an integer that specifies an access mask that describes the desired
     This value must not be None, and the key may not have subkeys.

    This method can not delete keys with subkeys.

    If the method succeeds, the entire key, including all of its values,
    is removed.  If the method fails, a WindowsError exception is raised.
    On unsupported Windows versions, NotImplementedError is raised."""
    if not _RegDeleteKeyExA.check():
        raise oefmt(space.w_NotImplementedError,
                    "not implemented on this platform")
    else:
        hkey = hkey_w(w_key, space)
        ret = _RegDeleteKeyExA.call(hkey, sub_key, access, reserved)
        if ret != 0:
            raiseWindowsError(space, ret, 'RegDeleteKeyEx')
