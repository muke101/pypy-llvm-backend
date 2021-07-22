from pypy.interpreter.mixedmodule import MixedModule

class Module(MixedModule):

    appleveldefs = {
    }

    interpleveldefs = {
        'SocketType':  'interp_socket.W_Socket',
        'socket'    :  'interp_socket.W_Socket',
        'error'     :  'interp_socket.get_error(space, "error")',
        'herror'    :  'interp_socket.get_error(space, "herror")',
        'gaierror'  :  'interp_socket.get_error(space, "gaierror")',
        'timeout'   :  'interp_socket.get_error(space, "timeout")',
    }

    def startup(self, space):
        from rpython.rlib.rsocket import rsocket_startup
        rsocket_startup()

    def shutdown(self, space):
        from pypy.module._socket.interp_socket import close_all_sockets
        close_all_sockets(space)

    def buildloaders(cls):
        from rpython.rlib import rsocket
        for name in """
            gethostbyname gethostbyname_ex gethostbyaddr gethostname
            getservbyname getservbyport getprotobyname
            fromfd socketpair
            ntohs ntohl htons htonl inet_aton inet_ntoa inet_pton inet_ntop
            getaddrinfo getnameinfo
            getdefaulttimeout setdefaulttimeout sethostname
            """.split():

            if name in ('inet_pton', 'inet_ntop', 'fromfd', 'socketpair',
                        'sethostname') \
                    and not hasattr(rsocket, name):
                continue

            Module.interpleveldefs[name] = 'interp_func.%s' % (name, )

        for constant, value in rsocket.constants.iteritems():
            if constant in ("SOCK_NONBLOCK", "SOCK_CLOEXEC"):
                continue
            Module.interpleveldefs[constant] = "space.wrap(%r)" % value
        super(Module, cls).buildloaders()
    buildloaders = classmethod(buildloaders)

#Module.interpleveldefs['has_ipv6'] = "space.wrap(%s)" % _socket.has_ipv6
