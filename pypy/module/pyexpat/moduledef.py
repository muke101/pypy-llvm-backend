from pypy.interpreter.mixedmodule import MixedModule

class ErrorsModule(MixedModule):
    "Definition of pyexpat.errors module."
    appleveldefs = {}
    interpleveldefs = {}

    def setup_after_space_initialization(self):
        from pypy.module.pyexpat import interp_pyexpat
        for name in interp_pyexpat.xml_error_list:
            self.space.setattr(self, self.space.newtext(name),
                    interp_pyexpat.ErrorString(self.space,
                    getattr(interp_pyexpat, name)))

class ModelModule(MixedModule):
    "Definition of pyexpat.model module."
    appleveldefs = {}
    interpleveldefs = {}

    def setup_after_space_initialization(self):
        from pypy.module.pyexpat import interp_pyexpat
        space = self.space
        for name in interp_pyexpat.xml_model_list:
            value = getattr(interp_pyexpat, name)
            space.setattr(self, space.newtext(name), space.wrap(value))

class Module(MixedModule):
    "Python wrapper for Expat parser."

    appleveldefs = {
        }

    interpleveldefs = {
        'ParserCreate':  'interp_pyexpat.ParserCreate',
        'XMLParserType': 'interp_pyexpat.W_XMLParserType',
        'ErrorString':   'interp_pyexpat.ErrorString',

        'ExpatError':    'space.fromcache(interp_pyexpat.Cache).w_error',
        'error':         'space.fromcache(interp_pyexpat.Cache).w_error',

        '__version__':   'space.newtext("85819")',
        }

    submodules = {
        'errors': ErrorsModule,
        'model':  ModelModule,
    }

    for name in ['XML_PARAM_ENTITY_PARSING_NEVER',
                 'XML_PARAM_ENTITY_PARSING_UNLESS_STANDALONE',
                 'XML_PARAM_ENTITY_PARSING_ALWAYS']:
        interpleveldefs[name] = 'space.wrap(interp_pyexpat.%s)' % (name,)

    def __init__(self, space, w_name):
        "NOT_RPYTHON"
        from pypy.module.pyexpat import interp_pyexpat
        super(Module, self).__init__(space, w_name)
        ver = space.unwrap(interp_pyexpat.get_expat_version(space))
        assert len(ver) >= 5, (
            "Cannot compile with the wide (UTF-16) version of Expat")

    def startup(self, space):
        from pypy.module.pyexpat import interp_pyexpat
        w_ver = interp_pyexpat.get_expat_version(space)
        space.setattr(self, space.newtext("EXPAT_VERSION"), w_ver)
        w_ver = interp_pyexpat.get_expat_version_info(space)
        space.setattr(self, space.newtext("version_info"), w_ver)
