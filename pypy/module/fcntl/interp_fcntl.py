from rpython.rtyper.tool import rffi_platform as platform
from rpython.rtyper.lltypesystem import rffi, lltype
from pypy.interpreter.error import OperationError, oefmt, wrap_oserror
from pypy.interpreter.gateway import unwrap_spec, WrappedDefault
from rpython.rlib import rposix
from rpython.translator.tool.cbuild import ExternalCompilationInfo
import sys

class CConfig:
    _compilation_info_ = ExternalCompilationInfo(
        includes = ['fcntl.h', 'sys/file.h', 'sys/ioctl.h']
    )
    flock = platform.Struct("struct flock",
        [('l_start', rffi.LONGLONG), ('l_len', rffi.LONGLONG),
        ('l_pid', rffi.LONG), ('l_type', rffi.SHORT),
        ('l_whence', rffi.SHORT)])
    has_flock = platform.Has('flock')

# constants, look in fcntl.h and platform docs for the meaning
# some constants are linux only so they will be correctly exposed outside
# depending on the OS
constants = {}
constant_names = ['LOCK_SH', 'LOCK_EX', 'LOCK_NB', 'LOCK_UN', 'F_DUPFD',
    'F_GETFD', 'F_SETFD', 'F_GETFL', 'F_SETFL', 'F_UNLCK', 'FD_CLOEXEC',
    'LOCK_MAND', 'LOCK_READ', 'LOCK_WRITE', 'LOCK_RW', 'F_GETSIG', 'F_SETSIG',
    'F_GETLK64', 'F_SETLK64', 'F_SETLKW64', 'F_GETLK', 'F_SETLK', 'F_SETLKW',
    'F_GETOWN', 'F_SETOWN', 'F_RDLCK', 'F_WRLCK', 'F_SETLEASE', 'F_GETLEASE',
    'F_NOTIFY', 'F_EXLCK', 'F_SHLCK', 'DN_ACCESS', 'DN_MODIFY', 'DN_CREATE',
    'DN_DELETE', 'DN_RENAME', 'DN_ATTRIB', 'DN_MULTISHOT', 'I_NREAD',
    'I_PUSH', 'I_POP', 'I_LOOK', 'I_FLUSH', 'I_SRDOPT', 'I_GRDOPT', 'I_STR',
    'I_SETSIG', 'I_GETSIG', 'I_FIND', 'I_LINK', 'I_UNLINK', 'I_PEEK',
    'I_FDINSERT', 'I_SENDFD', 'I_RECVFD', 'I_SWROPT', 'I_LIST', 'I_PLINK',
    'I_PUNLINK', 'I_FLUSHBAND', 'I_CKBAND', 'I_GETBAND', 'I_ATMARK',
    'I_SETCLTIME', 'I_GETCLTIME', 'I_CANPUT']
for name in constant_names:
    setattr(CConfig, name, platform.DefinedConstantInteger(name))

class cConfig(object):
    pass

for k, v in platform.configure(CConfig).items():
    setattr(cConfig, k, v)
cConfig.flock.__name__ = "_flock"

if "linux" in sys.platform:
    cConfig.F_GETSIG = 11
    cConfig.F_SETSIG = 10
    cConfig.F_GETLEASE = 1025
    cConfig.F_SETLEASE = 1024

# needed to export the constants inside and outside. see __init__.py
for name in constant_names:
    value = getattr(cConfig, name)
    if value is not None:
        constants[name] = value
locals().update(constants)

def external(name, args, result, **kwds):
    return rffi.llexternal(name, args, result,
                           compilation_info=CConfig._compilation_info_,
                           **kwds)

_flock = lltype.Ptr(cConfig.flock)
fcntl_int = external('fcntl', [rffi.INT, rffi.INT, rffi.INT], rffi.INT,
                     save_err=rffi.RFFI_SAVE_ERRNO)
fcntl_str = external('fcntl', [rffi.INT, rffi.INT, rffi.CCHARP], rffi.INT,
                     save_err=rffi.RFFI_SAVE_ERRNO)
fcntl_flock = external('fcntl', [rffi.INT, rffi.INT, _flock], rffi.INT,
                       save_err=rffi.RFFI_SAVE_ERRNO)
ioctl_int = external('ioctl', [rffi.INT, rffi.UINT, rffi.INT], rffi.INT,
                     save_err=rffi.RFFI_SAVE_ERRNO)
ioctl_str = external('ioctl', [rffi.INT, rffi.UINT, rffi.CCHARP], rffi.INT,
                     save_err=rffi.RFFI_SAVE_ERRNO)

has_flock = cConfig.has_flock
if has_flock:
    c_flock = external('flock', [rffi.INT, rffi.INT], rffi.INT,
                       save_err=rffi.RFFI_SAVE_ERRNO)

def _get_error(space, funcname):
    errno = rposix.get_saved_errno()
    return wrap_oserror(space, OSError(errno, funcname),
                        w_exception_class=space.w_IOError)

@unwrap_spec(op=int, w_arg=WrappedDefault(0))
def fcntl(space, w_fd, op, w_arg):
    """fcntl(fd, op, [arg])

    Perform the requested operation on file descriptor fd.  The operation
    is defined by op and is operating system dependent.  These constants are
    available from the fcntl module.  The argument arg is optional, and
    defaults to 0; it may be an int or a string. If arg is given as a string,
    the return value of fcntl is a string of that length, containing the
    resulting value put in the arg buffer by the operating system. If the
    arg given is an integer or if none is specified, the result value is an
    integer corresponding to the return value of the fcntl call in the C code.
    """

    fd = space.c_filedescriptor_w(w_fd)
    op = rffi.cast(rffi.INT, op)        # C long => C int

    try:
        arg = space.getarg_w('s#', w_arg)
    except OperationError as e:
        if not e.match(space, space.w_TypeError):
            raise
    else:
        ll_arg = rffi.str2charp(arg)
        try:
            rv = fcntl_str(fd, op, ll_arg)
            if rv < 0:
                raise _get_error(space, "fcntl")
            arg = rffi.charpsize2str(ll_arg, len(arg))
            return space.newbytes(arg)
        finally:
            lltype.free(ll_arg, flavor='raw')

    intarg = space.int_w(w_arg)
    intarg = rffi.cast(rffi.INT, intarg)   # C long => C int
    rv = fcntl_int(fd, op, intarg)
    if rv < 0:
        raise _get_error(space, "fcntl")
    return space.newint(rv)

@unwrap_spec(op=int)
def flock(space, w_fd, op):
    """flock(fd, operation)

    Perform the lock operation op on file descriptor fd.  See the Unix
    manual flock(3) for details.  (On some systems, this function is
    emulated using fcntl().)"""

    if has_flock:
        fd = space.c_filedescriptor_w(w_fd)
        op = rffi.cast(rffi.INT, op)        # C long => C int
        rv = c_flock(fd, op)
        if rv < 0:
            raise _get_error(space, "flock")
    else:
        lockf(space, w_fd, op)

@unwrap_spec(op=int, length=int, start=int, whence=int)
def lockf(space, w_fd, op, length=0, start=0, whence=0):
    """lockf (fd, operation, length=0, start=0, whence=0)

    This is essentially a wrapper around the fcntl() locking calls.  fd is the
    file descriptor of the file to lock or unlock, and operation is one of the
    following values:

    LOCK_UN - unlock
    LOCK_SH - acquire a shared lock
    LOCK_EX - acquire an exclusive lock

    When operation is LOCK_SH or LOCK_EX, it can also be bit-wise OR'd with
    LOCK_NB to avoid blocking on lock acquisition.  If LOCK_NB is used and the
    lock cannot be acquired, an IOError will be raised and the exception will
    have an errno attribute set to EACCES or EAGAIN (depending on the
    operating system -- for portability, check for either value).

    length is the number of bytes to lock, with the default meaning to lock to
    EOF.  start is the byte offset, relative to whence, to that the lock
    starts.  whence is as with fileobj.seek(), specifically:

    0 - relative to the start of the file (SEEK_SET)
    1 - relative to the current buffer position (SEEK_CUR)
    2 - relative to the end of the file (SEEK_END)"""

    fd = space.c_filedescriptor_w(w_fd)

    if op == LOCK_UN:
        l_type = F_UNLCK
    elif op & LOCK_SH:
        l_type = F_RDLCK
    elif op & LOCK_EX:
        l_type = F_WRLCK
    else:
        raise oefmt(space.w_ValueError, "unrecognized lock operation")

    op = [F_SETLKW, F_SETLK][int(bool(op & LOCK_NB))]
    op = rffi.cast(rffi.INT, op)        # C long => C int

    l = lltype.malloc(_flock.TO, flavor='raw')
    try:
        rffi.setintfield(l, 'c_l_type', l_type)
        rffi.setintfield(l, 'c_l_start', int(start))
        rffi.setintfield(l, 'c_l_len', int(length))
        rffi.setintfield(l, 'c_l_whence', int(whence))
        rv = fcntl_flock(fd, op, l)
        if rv < 0:
            raise _get_error(space, "fcntl")
    finally:
        lltype.free(l, flavor='raw')

@unwrap_spec(op=int, mutate_flag=int, w_arg=WrappedDefault(0))
def ioctl(space, w_fd, op, w_arg, mutate_flag=-1):
    """ioctl(fd, opt[, arg[, mutate_flag]])

    Perform the requested operation on file descriptor fd.  The operation is
    defined by opt and is operating system dependent.  Typically these codes
    are retrieved from the fcntl or termios library modules.
    """
    # removed the largish docstring because it is not in sync with the
    # documentation any more (even in CPython's docstring is out of date)

    # XXX this function's interface is a mess.
    # We try to emulate the behavior of Python >= 2.5 w.r.t. mutate_flag
    IOCTL_BUFSZ = 1024 # like cpython

    fd = space.c_filedescriptor_w(w_fd)
    op = rffi.cast(rffi.INT, op)        # C long => C int

    try:
        rwbuffer = space.writebuf_w(w_arg)
    except OperationError as e:
        if not e.match(space, space.w_TypeError):
            raise
    else:
        arg = rwbuffer.as_str()
        ll_arg = rffi.str2charp(arg)
        to_alloc = max(IOCTL_BUFSZ, len(arg))
        try:
            with rffi.scoped_alloc_buffer(to_alloc) as buf:
                rffi.c_memcpy(rffi.cast(rffi.VOIDP, buf.raw),
                              rffi.cast(rffi.VOIDP, ll_arg), len(arg))
                rv = ioctl_str(fd, op, buf.raw)
                if rv < 0:
                    raise _get_error(space, "ioctl")
                arg = rffi.charpsize2str(buf.raw, len(arg))
                if mutate_flag != 0:
                    rwbuffer.setslice(0, arg)
                    return space.newint(rv)
                return space.newbytes(arg)
        finally:
            lltype.free(ll_arg, flavor='raw')

    if mutate_flag != -1:
        raise oefmt(space.w_TypeError,
                    "ioctl requires a file or file descriptor, an integer and "
                    "optionally an integer or buffer argument")

    try:
        arg = space.getarg_w('s#', w_arg)
    except OperationError as e:
        if not e.match(space, space.w_TypeError):
            raise
    else:
        ll_arg = rffi.str2charp(arg)
        to_alloc = max(IOCTL_BUFSZ, len(arg))
        try:
            with rffi.scoped_alloc_buffer(to_alloc) as buf:
                rffi.c_memcpy(rffi.cast(rffi.VOIDP, buf.raw),
                              rffi.cast(rffi.VOIDP, ll_arg), len(arg))
                rv = ioctl_str(fd, op, buf.raw)
                if rv < 0:
                    raise _get_error(space, "ioctl")
                arg = rffi.charpsize2str(buf.raw, len(arg))
            return space.newbytes(arg)
        finally:
            lltype.free(ll_arg, flavor='raw')

    intarg = space.int_w(w_arg)
    intarg = rffi.cast(rffi.INT, intarg)   # C long => C int
    rv = ioctl_int(fd, op, intarg)
    if rv < 0:
        raise _get_error(space, "ioctl")
    return space.newint(rv)
