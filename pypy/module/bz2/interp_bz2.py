from __future__ import with_statement
from rpython.rtyper.tool import rffi_platform as platform
from rpython.rtyper.lltypesystem import rffi
from rpython.rtyper.lltypesystem import lltype
from pypy.interpreter.error import OperationError, oefmt
from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.typedef import TypeDef, interp_attrproperty
from pypy.interpreter.gateway import interp2app, unwrap_spec
from rpython.rlib.streamio import Stream
from rpython.translator.tool.cbuild import ExternalCompilationInfo
from rpython.translator.platform import platform as compiler
from rpython.rlib.rarithmetic import intmask, r_longlong
import sys


if compiler.name == "msvc":
    libname = 'libbz2'
else:
    libname = 'bz2'
eci = ExternalCompilationInfo(
    includes = ['stdio.h', 'sys/types.h', 'bzlib.h'],
    libraries = [libname],
    )
eci = platform.configure_external_library(
    'bz2', eci,
    [dict(prefix='bzip2-')])
if not eci:
    raise ImportError("Could not find bzip2 library")

class CConfig:
    _compilation_info_ = eci
    calling_conv = 'c'

    CHECK_LIBRARY = platform.Has('dump("x", (long)&BZ2_bzCompress)')

    off_t = platform.SimpleType("off_t", rffi.LONGLONG)
    size_t = platform.SimpleType("size_t", rffi.UNSIGNED)
    BUFSIZ = platform.ConstantInteger("BUFSIZ")
    _alloc_type = lltype.FuncType([rffi.VOIDP, rffi.INT, rffi.INT], rffi.VOIDP)
    _free_type = lltype.FuncType([rffi.VOIDP, rffi.VOIDP], lltype.Void)
    SEEK_SET = platform.ConstantInteger("SEEK_SET")
    bz_stream = platform.Struct('bz_stream',
                                [('next_in', rffi.CCHARP),
                                 ('avail_in', rffi.UINT),
                                 ('total_in_lo32', rffi.UINT),
                                 ('total_in_hi32', rffi.UINT),
                                 ('next_out', rffi.CCHARP),
                                 ('avail_out', rffi.UINT),
                                 ('total_out_lo32', rffi.UINT),
                                 ('total_out_hi32', rffi.UINT),
                                 ('state', rffi.VOIDP),
                                 ('bzalloc', lltype.Ptr(_alloc_type)),
                                 ('bzfree', lltype.Ptr(_free_type)),
                                 ('opaque', rffi.VOIDP),
                                 ])

FILE = rffi.COpaquePtr('FILE')
BZFILE = rffi.COpaquePtr('BZFILE')


constants = {}
constant_names = ['BZ_RUN', 'BZ_FLUSH', 'BZ_FINISH', 'BZ_OK',
    'BZ_RUN_OK', 'BZ_FLUSH_OK', 'BZ_FINISH_OK', 'BZ_STREAM_END',
    'BZ_SEQUENCE_ERROR', 'BZ_PARAM_ERROR', 'BZ_MEM_ERROR', 'BZ_DATA_ERROR',
    'BZ_DATA_ERROR_MAGIC', 'BZ_IO_ERROR', 'BZ_UNEXPECTED_EOF',
    'BZ_OUTBUFF_FULL', 'BZ_CONFIG_ERROR']
for name in constant_names:
    setattr(CConfig, name, platform.DefinedConstantInteger(name))

class cConfig(object):
    pass
for k, v in platform.configure(CConfig).items():
    setattr(cConfig, k, v)
if not cConfig.CHECK_LIBRARY:
    raise ImportError("Invalid bz2 library")

for name in constant_names:
    value = getattr(cConfig, name)
    if value is not None:
        constants[name] = value
locals().update(constants)

off_t = cConfig.off_t
bz_stream = lltype.Ptr(cConfig.bz_stream)
BUFSIZ = cConfig.BUFSIZ
SEEK_SET = cConfig.SEEK_SET
BZ_OK = cConfig.BZ_OK
BZ_STREAM_END = cConfig.BZ_STREAM_END
BZ_CONFIG_ERROR = cConfig.BZ_CONFIG_ERROR
BZ_PARAM_ERROR = cConfig.BZ_PARAM_ERROR
BZ_DATA_ERROR = cConfig.BZ_DATA_ERROR
BZ_DATA_ERROR_MAGIC = cConfig.BZ_DATA_ERROR_MAGIC
BZ_IO_ERROR = cConfig.BZ_IO_ERROR
BZ_MEM_ERROR = cConfig.BZ_MEM_ERROR
BZ_UNEXPECTED_EOF = cConfig.BZ_UNEXPECTED_EOF
BZ_SEQUENCE_ERROR = cConfig.BZ_SEQUENCE_ERROR

if BUFSIZ < 8192:
    SMALLCHUNK = 8192
else:
    SMALLCHUNK = BUFSIZ

if rffi.sizeof(rffi.INT) > 4:
    BIGCHUNK = 512 * 32
else:
    BIGCHUNK = 512 * 1024

if BZ_CONFIG_ERROR:
    if rffi.sizeof(rffi.SIGNED) >= 8:
        def _bzs_total_out(bzs):
            return (rffi.getintfield(bzs, 'c_total_out_hi32') << 32) + \
                   rffi.getintfield(bzs, 'c_total_out_lo32')
    else:
        # we can't return a long long value from here, because most
        # callers wouldn't be able to handle it anyway
        def _bzs_total_out(bzs):
            if rffi.getintfield(bzs, 'c_total_out_hi32') != 0 or \
                   rffi.getintfield(bzs, 'c_total_out_lo32') > sys.maxint:
                raise MemoryError
            return rffi.getintfield(bzs, 'c_total_out_lo32')
else:
    XXX    # this case needs fixing (old bz2 library?)
    def _bzs_total_out(bzs):
        return bzs.total_out

def external(name, args, result, **kwds):
    return rffi.llexternal(name, args, result, compilation_info=
                           CConfig._compilation_info_, **kwds)

# the least but one parameter should be rffi.VOIDP but it's not used
# so I trick the compiler to not complain about constanst pointer passed
# to void* arg
BZ2_bzReadOpen = external('BZ2_bzReadOpen', [rffi.INTP, FILE, rffi.INT,
    rffi.INT, rffi.INTP, rffi.INT], BZFILE)
BZ2_bzWriteOpen = external('BZ2_bzWriteOpen', [rffi.INTP, FILE, rffi.INT,
    rffi.INT, rffi.INT], BZFILE)
BZ2_bzReadClose = external('BZ2_bzReadClose', [rffi.INTP, BZFILE], lltype.Void)
BZ2_bzWriteClose = external('BZ2_bzWriteClose', [rffi.INTP, BZFILE,
    rffi.INT, rffi.UINTP, rffi.UINTP], lltype.Void)
BZ2_bzRead = external('BZ2_bzRead', [rffi.INTP, BZFILE, rffi.CCHARP, rffi.INT],
                      rffi.INT)
BZ2_bzWrite = external('BZ2_bzWrite', [rffi.INTP, BZFILE, rffi.CCHARP,
                                       rffi.INT], lltype.Void)
BZ2_bzCompressInit = external('BZ2_bzCompressInit', [bz_stream, rffi.INT,
                              rffi.INT, rffi.INT], rffi.INT)
BZ2_bzCompressEnd = external('BZ2_bzCompressEnd', [bz_stream], rffi.INT,
                             releasegil=False)
BZ2_bzCompress = external('BZ2_bzCompress', [bz_stream, rffi.INT], rffi.INT)
BZ2_bzDecompressInit = external('BZ2_bzDecompressInit', [bz_stream, rffi.INT,
                                                         rffi.INT], rffi.INT)
BZ2_bzDecompressEnd = external('BZ2_bzDecompressEnd', [bz_stream], rffi.INT,
                               releasegil=False)
BZ2_bzDecompress = external('BZ2_bzDecompress', [bz_stream], rffi.INT)

def _catch_bz2_error(space, bzerror):
    if BZ_CONFIG_ERROR and bzerror == BZ_CONFIG_ERROR:
        raise oefmt(space.w_SystemError,
                    "the bz2 library was not compiled correctly")
    if bzerror == BZ_PARAM_ERROR:
        raise oefmt(space.w_SystemError,
                    "the bz2 library has received wrong parameters")
    elif bzerror == BZ_MEM_ERROR:
        raise OperationError(space.w_MemoryError, space.w_None)
    elif bzerror in (BZ_DATA_ERROR, BZ_DATA_ERROR_MAGIC):
        raise oefmt(space.w_IOError, "invalid data stream")
    elif bzerror == BZ_IO_ERROR:
        raise oefmt(space.w_IOError, "unknown IO error")
    elif bzerror == BZ_UNEXPECTED_EOF:
        raise oefmt(space.w_EOFError,
                    "compressed file ended before the logical end-of-stream "
                    "was detected")
    elif bzerror == BZ_SEQUENCE_ERROR:
        raise oefmt(space.w_RuntimeError,
                    "wrong sequence of bz2 library commands used")

def _new_buffer_size(current_size):
    # keep doubling until we reach BIGCHUNK; then the buffer size is no
    # longer increased
    if current_size < BIGCHUNK:
        return current_size + current_size
    return current_size

# ____________________________________________________________

class OutBuffer(object):
    """Handler for the output buffer.  A bit custom code trying to
    encapsulate the logic of setting up the fields of 'bzs' and
    allocating raw memory as needed.
    """
    def __init__(self, bzs, initial_size=SMALLCHUNK):
        # when the constructor is called, allocate a piece of memory
        # of length 'piece_size' and make bzs ready to dump there.
        self.temp = []
        self.bzs = bzs
        self._allocate_chunk(initial_size)

    def _allocate_chunk(self, size):
        self.raw_buf, self.gc_buf, self.case_num = rffi.alloc_buffer(size)
        self.current_size = size
        self.bzs.c_next_out = self.raw_buf
        rffi.setintfield(self.bzs, 'c_avail_out', size)

    def _get_chunk(self, chunksize):
        assert 0 <= chunksize <= self.current_size
        raw_buf = self.raw_buf
        gc_buf = self.gc_buf
        case_num = self.case_num
        s = rffi.str_from_buffer(raw_buf, gc_buf, case_num,
                                 self.current_size, chunksize)
        rffi.keep_buffer_alive_until_here(raw_buf, gc_buf, case_num)
        self.current_size = 0
        return s

    def prepare_next_chunk(self):
        size = self.current_size
        self.temp.append(self._get_chunk(size))
        self._allocate_chunk(_new_buffer_size(size))

    def make_result_string(self):
        count_unoccupied = rffi.getintfield(self.bzs, 'c_avail_out')
        s = self._get_chunk(self.current_size - count_unoccupied)
        if self.temp:
            self.temp.append(s)
            return ''.join(self.temp)
        else:
            return s

    def free(self):
        if self.current_size > 0:
            rffi.keep_buffer_alive_until_here(self.raw_buf, self.gc_buf,
                                              self.case_num)

    def __enter__(self):
        return self
    def __exit__(self, *args):
        self.free()

# ____________________________________________________________
#
# Make the BZ2File type by internally inheriting from W_File.
# XXX this depends on internal details of W_File to work properly.

from pypy.module._file.interp_file import W_File

class W_BZ2File(W_File):

    def check_mode_ok(self, mode):
        if (not mode or mode[0] not in ['r', 'w', 'a', 'U']):
            space = self.space
            raise oefmt(space.w_ValueError, "invalid mode: '%s'", mode)

    @unwrap_spec(mode='text', buffering=int, compresslevel=int)
    def direct_bz2__init__(self, w_name, mode='r', buffering=-1,
                           compresslevel=9):
        self.direct_close()
        self.w_name = w_name
        # the stream should always be opened in binary mode
        if "b" not in mode:
            mode = mode + "b"
        self.check_mode_ok(mode)
        stream = open_bz2file_as_stream(self.space, w_name, mode,
                                        buffering, compresslevel)
        fd = stream.try_to_find_file_descriptor()
        self.fdopenstream(stream, fd, mode, w_name)

    _exposed_method_names = []
    W_File._decl.im_func(locals(), "bz2__init__",
                         """Opens a BZ2-compressed file.""",
                         wrapresult="space.w_None")
    # XXX ^^^ hacking hacking... can't just use the name "__init__" again
    # because the RTyper is confused about the two direct__init__() with
    # a different signature, confusion caused by the fact that
    # W_File.file__init__() would appear to contain an indirect call to
    # one of the two versions of direct__init__().

    def file_bz2__repr__(self):
        if self.stream is None:
            head = "closed"
        else:
            head = "open"
        info = "%s bz2.BZ2File %s, mode '%s'" % (head, self.getdisplayname(),
                                                 self.mode)
        return self.getrepr(self.space, info)

def descr_bz2file__new__(space, w_subtype, __args__):
    bz2file = space.allocate_instance(W_BZ2File, w_subtype)
    W_BZ2File.__init__(bz2file, space)
    return bz2file

same_attributes_as_in_file = list(W_File._exposed_method_names)
same_attributes_as_in_file.remove('__init__')
same_attributes_as_in_file.extend([
    'name', 'mode', 'encoding', 'closed', 'newlines', 'softspace',
    'writelines', '__exit__', '__weakref__', 'write'])

W_BZ2File.typedef = TypeDef(
    "BZ2File",
    __doc__ = """\
BZ2File(name [, mode='r', buffering=-1, compresslevel=9]) -> file object

Open a bz2 file. The mode can be 'r' or 'w', for reading (default) or
writing. When opened for writing, the file will be created if it doesn't
exist, and truncated otherwise. If the buffering argument is given, 0 means
unbuffered, and larger numbers specify the buffer size. If compresslevel
is given, must be a number between 1 and 9.

Add a 'U' to mode to open the file for input with universal newline
support. Any line ending in the input file will be seen as a '\\n' in
Python. Also, a file so opened gains the attribute 'newlines'; the value
for this attribute is one of None (no newline read yet), '\\r', '\\n',
'\\r\\n' or a tuple containing all the newline types seen. Universal
newlines are available only when reading.""",
    __new__  = interp2app(descr_bz2file__new__),
    __init__ = interp2app(W_BZ2File.file_bz2__init__),
    __repr__ = interp2app(W_BZ2File.file_bz2__repr__),
    **dict([(name, W_File.typedef.rawdict[name])
            for name in same_attributes_as_in_file]))


# ____________________________________________________________

def open_bz2file_as_stream(space, w_path, mode="r", buffering=-1,
                           compresslevel=9):
    from rpython.rlib.streamio import decode_mode, open_path_helper
    from rpython.rlib.streamio import construct_stream_tower
    os_flags, universal, reading, writing, basemode, binary = decode_mode(mode)
    if reading and writing:
        raise oefmt(space.w_ValueError, "cannot open in read-write mode")
    if basemode == "a":
        raise oefmt(space.w_ValueError, "cannot append to bz2 file")
    stream = open_path_helper(space.fsencode_w(w_path), os_flags, False)
    if reading:
        bz2stream = ReadBZ2Filter(space, stream, buffering)
        buffering = 0     # by construction, the ReadBZ2Filter acts like
                          # a read buffer too - no need for another one
    else:
        assert writing
        bz2stream = WriteBZ2Filter(space, stream, compresslevel)
    stream = construct_stream_tower(bz2stream, buffering, universal, reading,
                                    writing, binary)
    return stream


class ReadBZ2Filter(Stream):

    """Standard I/O stream filter that decompresses the stream with bz2."""

    def __init__(self, space, stream, buffering):
        self.space = space
        self.stream = stream
        self.decompressor = W_BZ2Decompressor(space)
        self.readlength = r_longlong(0)
        self.buffer = ""
        self.pos = 0
        self.finished = False
        if buffering < 1024:
            buffering = 1024   # minimum amount of compressed data read at once
        self.buffering = buffering

    def close1(self, closefileno):
        self.stream.close1(closefileno)

    def tell(self):
        return self.readlength

    def seek(self, offset, whence):
        READMAX = 2**18   # 256KB

        # Make offset relative to the start of the file
        if whence == 2:
            # Read everything to arrive at the end
            while len(self.read(READMAX)) > 0:
                pass
            offset += self.readlength
        elif whence == 1:
            offset += self.readlength
        elif whence == 0:
            pass
        else:
            raise oefmt(self.space.w_ValueError,
                        "Invalid value for whence: %d", whence)

        # Make offset relative to the current pos
        # Rewind iff necessary
        if offset < self.readlength:
            self.stream.seek(0, 0)
            self.decompressor = W_BZ2Decompressor(self.space)
            self.readlength = r_longlong(0)
            self.pos = 0
            self.buffer = ""
            self.finished = False
        else:
            offset -= self.readlength

        # Seek
        read = r_longlong(0)
        while read < offset:
            count = offset - read
            if count < READMAX:
                count = intmask(count)
            else:
                count = READMAX
            length = len(self.read(count))
            if not length:
                break
            read += length

    def readall(self):
        raw = self.stream.readall()
        if raw:
            w_result = self.decompressor.decompress(raw)
            if self.decompressor.running:
                raise oefmt(self.space.w_EOFError,
                            "compressed file ended before the logical "
                            "end-of-the-stream was detected")
            result = self.space.bytes_w(w_result)
            self.readlength += len(result)
        else:
            result = ""
        if len(self.buffer) != self.pos:
            pos = self.pos
            assert pos >= 0
            result = self.buffer[pos:] + result
        self.buffer = ''
        self.pos = 0
        return result

    def read(self, n):
        # XXX not nice
        if n <= 0:
            return ''
        while self.pos == len(self.buffer):
            if self.finished:
                return ""
            moredata = self.stream.read(max(self.buffering, n))
            if not moredata:
                self.finished = True
                return ""
            try:
                w_read = self.decompressor.decompress(moredata)
            except OperationError as e:
                if e.match(self.space, self.space.w_EOFError):
                    self.finished = True
                    return ""
                raise
            self.buffer = self.space.bytes_w(w_read)
            self.pos = 0
        if len(self.buffer) - self.pos >= n:
            pos = self.pos
            assert pos >= 0
            result = self.buffer[pos:pos + n]
            self.pos += n
        else:
            pos = self.pos
            assert pos >= 0
            result = self.buffer[pos:]
            self.pos = 0
            self.buffer = ""
        self.readlength += len(result)
        return result

    def peek(self):
        return (self.pos, self.buffer)

    def try_to_find_file_descriptor(self):
        return self.stream.try_to_find_file_descriptor()

    def write(self, s):
        raise oefmt(self.space.w_IOError, "file is not ready for writing")

class WriteBZ2Filter(Stream):
    """Standard I/O stream filter that compresses the stream with bz2."""

    def __init__(self, space, stream, compresslevel):
        self.stream = stream
        self.space = space
        self.compressor = W_BZ2Compressor(space, compresslevel)
        self.writtenlength = 0

    def close1(self, closefileno):
        self.stream.write(self.space.bytes_w(self.compressor.flush()))
        self.stream.close1(closefileno)

    def write(self, data):
        self.stream.write(self.space.bytes_w(self.compressor.compress(data)))
        self.writtenlength += len(data)

    def tell(self):
        return self.writtenlength

    def seek(self, offset, whence):
        raise oefmt(self.space.w_IOError, "seek works only while reading")

    def read(self, n):
        raise oefmt(self.space.w_IOError, "file is not ready for reading")

    def readall(self):
        raise oefmt(self.space.w_IOError, "file is not ready for reading")

    def try_to_find_file_descriptor(self):
        return self.stream.try_to_find_file_descriptor()

@unwrap_spec(compresslevel=int)
def descr_compressor__new__(space, w_subtype, compresslevel=9):
    x = space.allocate_instance(W_BZ2Compressor, w_subtype)
    W_BZ2Compressor.__init__(x, space, compresslevel)
    return x

class W_BZ2Compressor(W_Root):
    """BZ2Compressor([compresslevel=9]) -> compressor object

    Create a new compressor object. This object may be used to compress
    data sequentially. If you want to compress data in one shot, use the
    compress() function instead. The compresslevel parameter, if given,
    must be a number between 1 and 9."""
    def __init__(self, space, compresslevel):
        self.space = space
        self.bzs = lltype.malloc(bz_stream.TO, flavor='raw', zero=True)
        try:
            self.running = False
            self._init_bz2comp(compresslevel)
        except:
            lltype.free(self.bzs, flavor='raw')
            self.bzs = lltype.nullptr(bz_stream.TO)
            raise
        self.register_finalizer(space)

    def _init_bz2comp(self, compresslevel):
        if compresslevel < 1 or compresslevel > 9:
            raise oefmt(self.space.w_ValueError,
                        "compresslevel must be between 1 and 9")

        bzerror = intmask(BZ2_bzCompressInit(self.bzs, compresslevel, 0, 0))
        if bzerror != BZ_OK:
            _catch_bz2_error(self.space, bzerror)

        self.running = True

    def _finalize_(self):
        bzs = self.bzs
        if bzs:
            self.bzs = lltype.nullptr(bz_stream.TO)
            BZ2_bzCompressEnd(bzs)
            lltype.free(bzs, flavor='raw')

    @unwrap_spec(data='bufferstr')
    def compress(self, data):
        """compress(data) -> string

        Provide more data to the compressor object. It will return chunks of
        compressed data whenever possible. When you've finished providing data
        to compress, call the flush() method to finish the compression process,
        and return what is left in the internal buffers."""

        assert data is not None
        datasize = len(data)

        if datasize == 0:
            return self.space.newbytes("")

        if not self.running:
            raise oefmt(self.space.w_ValueError,
                        "this object was already flushed")

        in_bufsize = datasize

        with OutBuffer(self.bzs) as out:
            with rffi.scoped_nonmovingbuffer(data) as in_buf:

                self.bzs.c_next_in = in_buf
                rffi.setintfield(self.bzs, 'c_avail_in', in_bufsize)

                while True:
                    bzerror = BZ2_bzCompress(self.bzs, BZ_RUN)
                    if bzerror != BZ_RUN_OK:
                        _catch_bz2_error(self.space, bzerror)

                    if rffi.getintfield(self.bzs, 'c_avail_in') == 0:
                        break
                    elif rffi.getintfield(self.bzs, 'c_avail_out') == 0:
                        out.prepare_next_chunk()

                res = out.make_result_string()
                return self.space.newbytes(res)

    def flush(self):
        if not self.running:
            raise oefmt(self.space.w_ValueError,
                        "this object was already flushed")
        self.running = False

        with OutBuffer(self.bzs) as out:
            while True:
                bzerror = BZ2_bzCompress(self.bzs, BZ_FINISH)
                if bzerror == BZ_STREAM_END:
                    break
                elif bzerror != BZ_FINISH_OK:
                    _catch_bz2_error(self.space, bzerror)

                if rffi.getintfield(self.bzs, 'c_avail_out') == 0:
                    out.prepare_next_chunk()

            res = out.make_result_string()
            return self.space.newbytes(res)

W_BZ2Compressor.typedef = TypeDef("BZ2Compressor",
    __doc__ = W_BZ2Compressor.__doc__,
    __new__ = interp2app(descr_compressor__new__),
    compress = interp2app(W_BZ2Compressor.compress),
    flush = interp2app(W_BZ2Compressor.flush),
)


def descr_decompressor__new__(space, w_subtype):
    x = space.allocate_instance(W_BZ2Decompressor, w_subtype)
    W_BZ2Decompressor.__init__(x, space)
    return x


class W_BZ2Decompressor(W_Root):
    """BZ2Decompressor() -> decompressor object

    Create a new decompressor object. This object may be used to decompress
    data sequentially. If you want to decompress data in one shot, use the
    decompress() function instead."""

    def __init__(self, space):
        self.space = space

        self.bzs = lltype.malloc(bz_stream.TO, flavor='raw', zero=True)
        try:
            self.running = False
            self.unused_data = ""

            self._init_bz2decomp()
        except:
            lltype.free(self.bzs, flavor='raw')
            self.bzs = lltype.nullptr(bz_stream.TO)
            raise
        self.register_finalizer(space)

    def _init_bz2decomp(self):
        bzerror = BZ2_bzDecompressInit(self.bzs, 0, 0)
        if bzerror != BZ_OK:
            _catch_bz2_error(self.space, bzerror)

        self.running = True

    def _finalize_(self):
        bzs = self.bzs
        if bzs:
            self.bzs = lltype.nullptr(bz_stream.TO)
            BZ2_bzDecompressEnd(bzs)
            lltype.free(bzs, flavor='raw')

    @unwrap_spec(data='bufferstr')
    def decompress(self, data):
        """decompress(data) -> string

        Provide more data to the decompressor object. It will return chunks
        of decompressed data whenever possible. If you try to decompress data
        after the end of stream is found, EOFError will be raised. If any data
        was found after the end of stream, it'll be ignored and saved in
        unused_data attribute."""

        assert data is not None
        if not self.running:
            raise oefmt(self.space.w_EOFError,
                        "end of stream was already found")
        if data == '':
            return self.space.newbytes('')

        in_bufsize = len(data)

        with rffi.scoped_nonmovingbuffer(data) as in_buf:
            self.bzs.c_next_in = in_buf
            rffi.setintfield(self.bzs, 'c_avail_in', in_bufsize)

            with OutBuffer(self.bzs) as out:
                while True:
                    bzerror = BZ2_bzDecompress(self.bzs)
                    if bzerror == BZ_STREAM_END:
                        if rffi.getintfield(self.bzs, 'c_avail_in') != 0:
                            unused = [self.bzs.c_next_in[i]
                                      for i in range(
                                          rffi.getintfield(self.bzs,
                                                           'c_avail_in'))]
                            self.unused_data = "".join(unused)
                        self.running = False
                        break
                    if bzerror != BZ_OK:
                        _catch_bz2_error(self.space, bzerror)

                    if rffi.getintfield(self.bzs, 'c_avail_in') == 0:
                        break
                    elif rffi.getintfield(self.bzs, 'c_avail_out') == 0:
                        out.prepare_next_chunk()

                res = out.make_result_string()
                return self.space.newbytes(res)


W_BZ2Decompressor.typedef = TypeDef("BZ2Decompressor",
    __doc__ = W_BZ2Decompressor.__doc__,
    __new__ = interp2app(descr_decompressor__new__),
    unused_data = interp_attrproperty("unused_data", W_BZ2Decompressor,
        wrapfn="newbytes"),
    decompress = interp2app(W_BZ2Decompressor.decompress),
)


@unwrap_spec(data='bufferstr', compresslevel=int)
def compress(space, data, compresslevel=9):
    """compress(data [, compresslevel=9]) -> string

    Compress data in one shot. If you want to compress data sequentially,
    use an instance of BZ2Compressor instead. The compresslevel parameter, if
    given, must be a number between 1 and 9."""

    assert data is not None
    if compresslevel < 1 or compresslevel > 9:
        raise oefmt(space.w_ValueError,
                    "compresslevel must be between 1 and 9")

    with lltype.scoped_alloc(bz_stream.TO, zero=True) as bzs:
        in_bufsize = len(data)

        with rffi.scoped_nonmovingbuffer(data) as in_buf:
            bzs.c_next_in = in_buf
            rffi.setintfield(bzs, 'c_avail_in', in_bufsize)

            # conforming to bz2 manual, this is large enough to fit compressed
            # data in one shot. We will check it later anyway.
            with OutBuffer(bzs,
                           in_bufsize + (in_bufsize / 100 + 1) + 600) as out:

                bzerror = BZ2_bzCompressInit(bzs, compresslevel, 0, 0)
                if bzerror != BZ_OK:
                    _catch_bz2_error(space, bzerror)

                while True:
                    bzerror = BZ2_bzCompress(bzs, BZ_FINISH)
                    if bzerror == BZ_STREAM_END:
                        break
                    elif bzerror != BZ_FINISH_OK:
                        BZ2_bzCompressEnd(bzs)
                        _catch_bz2_error(space, bzerror)

                    if rffi.getintfield(bzs, 'c_avail_out') == 0:
                        out.prepare_next_chunk()

                res = out.make_result_string()
                BZ2_bzCompressEnd(bzs)
                return space.newbytes(res)

@unwrap_spec(data='bufferstr')
def decompress(space, data):
    """decompress(data) -> decompressed data

    Decompress data in one shot. If you want to decompress data sequentially,
    use an instance of BZ2Decompressor instead."""

    assert data is not None
    in_bufsize = len(data)
    if in_bufsize == 0:
        return space.newbytes("")

    with lltype.scoped_alloc(bz_stream.TO, zero=True) as bzs:
        with rffi.scoped_nonmovingbuffer(data) as in_buf:
            bzs.c_next_in = in_buf
            rffi.setintfield(bzs, 'c_avail_in', in_bufsize)

            with OutBuffer(bzs) as out:
                bzerror = BZ2_bzDecompressInit(bzs, 0, 0)
                if bzerror != BZ_OK:
                    _catch_bz2_error(space, bzerror)

                while True:
                    bzerror = BZ2_bzDecompress(bzs)
                    if bzerror == BZ_STREAM_END:
                        break
                    if bzerror != BZ_OK:
                        BZ2_bzDecompressEnd(bzs)
                    _catch_bz2_error(space, bzerror)

                    if rffi.getintfield(bzs, 'c_avail_in') == 0:
                        BZ2_bzDecompressEnd(bzs)
                        raise oefmt(space.w_ValueError,
                                    "couldn't find end of stream")
                    elif rffi.getintfield(bzs, 'c_avail_out') == 0:
                        out.prepare_next_chunk()

                res = out.make_result_string()
                BZ2_bzDecompressEnd(bzs)
                return space.newbytes(res)
