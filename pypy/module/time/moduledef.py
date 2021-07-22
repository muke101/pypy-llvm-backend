
from pypy.interpreter.mixedmodule import MixedModule
import os

_WIN = os.name == "nt"

class Module(MixedModule):
    applevel_name = 'time'

    interpleveldefs = {
        'time': 'interp_time.time',
        'clock': 'interp_time.clock',
        'ctime': 'interp_time.ctime',
        'asctime': 'interp_time.asctime',
        'gmtime': 'interp_time.gmtime',
        'localtime': 'interp_time.localtime',
        'mktime': 'interp_time.mktime',
        'strftime': 'interp_time.strftime',
        'sleep' : 'interp_time.sleep',
    }

    if os.name == "posix":
        interpleveldefs['tzset'] = 'interp_time.tzset'

    appleveldefs = {
        'struct_time': 'app_time.struct_time',
        '__doc__': 'app_time.__doc__',
        'strptime': 'app_time.strptime',
    }

    def startup(self, space):
        if _WIN:
            from pypy.module.time.interp_time import State
            space.fromcache(State).startup(space)

        # this machinery is needed to expose constants
        # that have to be initialized one time only
        from pypy.module.time import interp_time

        interp_time._init_timezone(space)
        interp_time._init_accept2dyear(space)

