from rpython.rlib import rsocket
from rpython.rlib.rsocket import SocketError, INVALID_SOCKET
from rpython.rlib.rarithmetic import intmask, r_longlong, r_uint32

from pypy.interpreter.error import OperationError, oefmt
from pypy.interpreter.gateway import unwrap_spec, WrappedDefault
from pypy.module._socket.interp_socket import (
    converted_error, W_Socket, addr_as_object, ipaddr_from_object
)


def gethostname(space):
    """gethostname() -> string

    Return the current host name.
    """
    try:
        res = rsocket.gethostname()
    except SocketError as e:
        raise converted_error(space, e)
    return space.newtext(res)

@unwrap_spec(host='text')
def gethostbyname(space, host):
    """gethostbyname(host) -> address

    Return the IP address (a string of the form '255.255.255.255') for a host.
    """
    try:
        addr = rsocket.gethostbyname(host)
        ip = addr.get_host()
    except SocketError as e:
        raise converted_error(space, e)
    return space.newtext(ip)

def common_wrapgethost(space, (name, aliases, address_list)):
    aliases = [space.newtext(alias) for alias in aliases]
    address_list = [space.newtext(addr.get_host()) for addr in address_list]
    return space.newtuple([space.newtext(name),
                           space.newlist(aliases),
                           space.newlist(address_list)])

@unwrap_spec(host='text')
def gethostbyname_ex(space, host):
    """gethostbyname_ex(host) -> (name, aliaslist, addresslist)

    Return the true host name, a list of aliases, and a list of IP addresses,
    for a host.  The host argument is a string giving a host name or IP number.
    """
    try:
        res = rsocket.gethostbyname_ex(host)
    except SocketError as e:
        raise converted_error(space, e)
    return common_wrapgethost(space, res)

@unwrap_spec(host='text')
def gethostbyaddr(space, host):
    """gethostbyaddr(host) -> (name, aliaslist, addresslist)

    Return the true host name, a list of aliases, and a list of IP addresses,
    for a host.  The host argument is a string giving a host name or IP number.
    """
    try:
        res = rsocket.gethostbyaddr(host)
    except SocketError as e:
        raise converted_error(space, e)
    return common_wrapgethost(space, res)

@unwrap_spec(name='text', w_proto = WrappedDefault(None))
def getservbyname(space, name, w_proto):
    """getservbyname(servicename[, protocolname]) -> integer

    Return a port number from a service name and protocol name.
    The optional protocol name, if given, should be 'tcp' or 'udp',
    otherwise any protocol will match.
    """
    if space.is_w(w_proto, space.w_None):
        proto = None
    else:
        proto = space.text_w(w_proto)
    try:
        port = rsocket.getservbyname(name, proto)
    except SocketError as e:
        raise converted_error(space, e)
    return space.newint(port)

@unwrap_spec(port=int, w_proto = WrappedDefault(None))
def getservbyport(space, port, w_proto):
    """getservbyport(port[, protocolname]) -> string

    Return the service name from a port number and protocol name.
    The optional protocol name, if given, should be 'tcp' or 'udp',
    otherwise any protocol will match.
    """
    if space.is_w(w_proto, space.w_None):
        proto = None
    else:
        proto = space.text_w(w_proto)

    if port < 0 or port > 0xffff:
        raise oefmt(space.w_OverflowError,
                    "getservbyport: port must be 0-65535.")

    try:
        service = rsocket.getservbyport(port, proto)
    except SocketError as e:
        raise converted_error(space, e)
    return space.newtext(service)

@unwrap_spec(name='text')
def getprotobyname(space, name):
    """getprotobyname(name) -> integer

    Return the protocol number for the named protocol.  (Rarely used.)
    """
    try:
        proto = rsocket.getprotobyname(name)
    except SocketError as e:
        raise converted_error(space, e)
    return space.newint(proto)

@unwrap_spec(flags=int)
def getnameinfo(space, w_sockaddr, flags):
    """getnameinfo(sockaddr, flags) --> (host, port)

    Get host and port for a sockaddr."""
    try:
        addr = ipaddr_from_object(space, w_sockaddr)
        host, servport = rsocket.getnameinfo(addr, flags)
    except SocketError as e:
        raise converted_error(space, e)
    return space.newtuple([space.newtext(host), space.newtext(servport)])

@unwrap_spec(fd=int, family=int, type=int, proto=int)
def fromfd(space, fd, family, type, proto=0):
    """fromfd(fd, family, type[, proto]) -> socket object

    Create a socket object from the given file descriptor.
    The remaining arguments are the same as for socket().
    """
    try:
        sock = rsocket.fromfd(fd, family, type, proto)
    except SocketError as e:
        raise converted_error(space, e)
    return W_Socket(space, sock)

@unwrap_spec(family=int, type=int, proto=int)
def socketpair(space, family=rsocket.socketpair_default_family,
                      type  =rsocket.SOCK_STREAM,
                      proto =0):
    """socketpair([family[, type[, proto]]]) -> (socket object, socket object)

    Create a pair of socket objects from the sockets returned by the platform
    socketpair() function.
    The arguments are the same as for socket() except the default family is
    AF_UNIX if defined on the platform; otherwise, the default is AF_INET.
    """
    try:
        sock1, sock2 = rsocket.socketpair(family, type, proto)
    except SocketError as e:
        raise converted_error(space, e)
    return space.newtuple([
        W_Socket(space, sock1),
        W_Socket(space, sock2)
    ])

# The following 4 functions refuse all negative numbers.
# They also check that the argument is not too large, but note that
# CPython 2.7 is not doing that consistently (CPython 3.x does).
LONGLONG_UINT32_MAX = r_longlong(2**32-1)

@unwrap_spec(x="c_int")
def ntohs(space, x):
    """ntohs(integer) -> integer

    Convert a 16-bit integer from network to host byte order.
    """
    if x < 0:
        raise oefmt(space.w_OverflowError,
                    "can't convert negative number to unsigned long")
    return space.newint(rsocket.ntohs(intmask(x)))

@unwrap_spec(x=r_longlong)
def ntohl(space, x):
    """ntohl(integer) -> integer

    Convert a 32-bit integer from network to host byte order.
    """
    if x < r_longlong(0):
        raise oefmt(space.w_OverflowError,
                    "can't convert negative number to unsigned long")
    if x > LONGLONG_UINT32_MAX:
        raise oefmt(space.w_OverflowError, "long int larger than 32 bits")
    return space.newint(rsocket.ntohl(r_uint32(x)))

@unwrap_spec(x="c_int")
def htons(space, x):
    """htons(integer) -> integer

    Convert a 16-bit integer from host to network byte order.
    """
    if x < 0:
        raise oefmt(space.w_OverflowError,
                    "can't convert negative number to unsigned long")
    return space.newint(rsocket.htons(x))

@unwrap_spec(x=r_longlong)
def htonl(space, x):
    """htonl(integer) -> integer

    Convert a 32-bit integer from host to network byte order.
    """
    if x < r_longlong(0):
        raise oefmt(space.w_OverflowError,
                    "can't convert negative number to unsigned long")
    if x > LONGLONG_UINT32_MAX:
        raise oefmt(space.w_OverflowError, "long int larger than 32 bits")
    return space.newint(rsocket.htonl(r_uint32(x)))

@unwrap_spec(ip='text')
def inet_aton(space, ip):
    """inet_aton(string) -> packed 32-bit IP representation

    Convert an IP address in string format (123.45.67.89) to the 32-bit packed
    binary format used in low-level network functions.
    """
    try:
        buf = rsocket.inet_aton(ip)
    except SocketError as e:
        raise converted_error(space, e)
    return space.newbytes(buf)

@unwrap_spec(packed='text')
def inet_ntoa(space, packed):
    """inet_ntoa(packed_ip) -> ip_address_string

    Convert an IP address from 32-bit packed binary format to string format
    """
    try:
        ip = rsocket.inet_ntoa(packed)
    except SocketError as e:
        raise converted_error(space, e)
    return space.newtext(ip)

@unwrap_spec(family=int, ip='text')
def inet_pton(space, family, ip):
    """inet_pton(family, ip) -> packed IP address string

    Convert an IP address from string format to a packed string suitable
    for use with low-level network functions.
    """
    try:
        buf = rsocket.inet_pton(family, ip)
    except SocketError as e:
        raise converted_error(space, e)
    return space.newbytes(buf)

@unwrap_spec(family=int, packed='bufferstr')
def inet_ntop(space, family, packed):
    """inet_ntop(family, packed_ip) -> string formatted IP address

    Convert a packed IP address of the given family to string format.
    """
    try:
        ip = rsocket.inet_ntop(family, packed)
    except SocketError as e:
        raise converted_error(space, e)
    except ValueError:
        raise oefmt(space.w_ValueError,
                    "invalid length of packed IP address string")
    return space.newtext(ip)

@unwrap_spec(family=int, socktype=int, proto=int, flags=int)
def getaddrinfo(space, w_host, w_port,
                family=rsocket.AF_UNSPEC, socktype=0, proto=0, flags=0):
    """getaddrinfo(host, port [, family, socktype, proto, flags])
        -> list of (family, socktype, proto, canonname, sockaddr)

    Resolve host and port into addrinfo struct.
    """
    # host can be None, string or unicode
    if space.is_w(w_host, space.w_None):
        host = None
    elif space.isinstance_w(w_host, space.w_bytes):
        host = space.bytes_w(w_host)
    elif space.isinstance_w(w_host, space.w_unicode):
        w_shost = space.call_method(w_host, "encode", space.newtext("idna"))
        host = space.bytes_w(w_shost)
    else:
        raise oefmt(space.w_TypeError,
                    "getaddrinfo() argument 1 must be string or None")

    # port can be None, int or string
    if space.is_w(w_port, space.w_None):
        port = None
    elif space.isinstance_w(w_port, space.w_int) or space.isinstance_w(w_port, space.w_long):
        port = str(space.int_w(w_port))
    elif space.isinstance_w(w_port, space.w_bytes):
        port = space.bytes_w(w_port)
    else:
        raise oefmt(space.w_TypeError,
                    "getaddrinfo() argument 2 must be integer or string")
    try:
        lst = rsocket.getaddrinfo(host, port, family, socktype,
                                  proto, flags)
    except SocketError as e:
        raise converted_error(space, e)
    lst1 = [space.newtuple([space.newint(family),
                            space.newint(socktype),
                            space.newint(protocol),
                            space.newtext(canonname),
                            addr_as_object(addr, INVALID_SOCKET, space)]) # -1 as per cpython
            for (family, socktype, protocol, canonname, addr) in lst]
    return space.newlist(lst1)

def getdefaulttimeout(space):
    """getdefaulttimeout() -> timeout

    Returns the default timeout in floating seconds for new socket objects.
    A value of None indicates that new socket objects have no timeout.
    When the socket module is first imported, the default is None.
    """
    timeout = rsocket.getdefaulttimeout()
    if timeout < 0.0:
        return space.w_None
    return space.newfloat(timeout)

def setdefaulttimeout(space, w_timeout):
    if space.is_w(w_timeout, space.w_None):
        timeout = -1.0
    else:
        timeout = space.float_w(w_timeout)
        if timeout < 0.0:
            raise oefmt(space.w_ValueError, "Timeout value out of range")
    rsocket.setdefaulttimeout(timeout)

if hasattr(rsocket, 'sethostname'):
    def sethostname(space, w_hostname):
        """sethostname(hostname)

        Set the host name.
        """
        hostname = space.text_w(w_hostname)
        try:
            res = rsocket.sethostname(hostname)
        except SocketError as e:
            raise converted_error(space, e)
