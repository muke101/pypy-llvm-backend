from pypy.interpreter.error import OperationError
from pypy.interpreter import module
from pypy.interpreter.mixedmodule import MixedModule
import pypy.module.imp.importing

# put builtins here that should be optimized somehow

class Module(MixedModule):
    """Built-in functions, exceptions, and other objects."""

    appleveldefs = {
        'execfile'      : 'app_io.execfile',
        'raw_input'     : 'app_io.raw_input',
        'input'         : 'app_io.input',
        'print'         : 'app_io.print_',

        'apply'         : 'app_functional.apply',
        'sorted'        : 'app_functional.sorted',
        'any'           : 'app_functional.any',
        'all'           : 'app_functional.all',
        'sum'           : 'app_functional.sum',
        'map'           : 'app_functional.map',
        'reduce'        : 'app_functional.reduce',
        'filter'        : 'app_functional.filter',
        'zip'           : 'app_functional.zip',
        'vars'          : 'app_inspect.vars',
        'dir'           : 'app_inspect.dir',

        'bin'           : 'app_operation.bin',

    }

    interpleveldefs = {
        # constants
        '__debug__'     : '(space.w_True)',
        'None'          : '(space.w_None)',
        'False'         : '(space.w_False)',
        'True'          : '(space.w_True)',
        'bytes'         : '(space.w_bytes)',

        'file'          : 'state.get(space).w_file',
        'open'          : 'state.get(space).w_file',

        # default __metaclass__: old-style class
        '__metaclass__' : 'interp_classobj.W_ClassObject',

        # interp-level function definitions
        'abs'           : 'operation.abs',
        'chr'           : 'operation.chr',
        'unichr'        : 'operation.unichr',
        'len'           : 'operation.len',
        'ord'           : 'operation.ord',
        'pow'           : 'operation.pow',
        'repr'          : 'operation.repr',
        'hash'          : 'operation.hash',
        'oct'           : 'operation.oct',
        'hex'           : 'operation.hex',
        'round'         : 'operation.round',
        'cmp'           : 'operation.cmp',
        'coerce'        : 'operation.coerce',
        'divmod'        : 'operation.divmod',
        'format'        : 'operation.format',
        '_issubtype'    : 'operation._issubtype',
        'issubclass'    : 'abstractinst.app_issubclass',
        'isinstance'    : 'abstractinst.app_isinstance',
        'getattr'       : 'operation.getattr',
        'setattr'       : 'operation.setattr',
        'delattr'       : 'operation.delattr',
        'hasattr'       : 'operation.hasattr',
        'iter'          : 'operation.iter',
        'next'          : 'operation.next',
        'id'            : 'operation.id',
        'intern'        : 'operation.intern',
        'callable'      : 'operation.callable',

        'compile'       : 'compiling.compile',
        'eval'          : 'compiling.eval',

        '__import__'    : 'pypy.module.imp.importing.importhook',
        'reload'        : 'pypy.module.imp.importing.reload',

        'range'         : 'functional.range_int',
        'xrange'        : 'functional.W_XRange',
        'enumerate'     : 'functional.W_Enumerate',
        'min'           : 'functional.min',
        'max'           : 'functional.max',
        'reversed'      : 'functional.reversed',
        'super'         : 'descriptor.W_Super',
        'staticmethod'  : 'pypy.interpreter.function.StaticMethod',
        'classmethod'   : 'pypy.interpreter.function.ClassMethod',
        'property'      : 'descriptor.W_Property',

        'globals'       : 'interp_inspect.globals',
        'locals'        : 'interp_inspect.locals',

    }

    def pick_builtin(self, w_globals):
        "Look up the builtin module to use from the __builtins__ global"
        # pick the __builtins__ roughly in the same way CPython does it
        # this is obscure and slow
        space = self.space
        try:
            w_builtin = space.getitem(w_globals, space.newtext('__builtins__'))
        except OperationError as e:
            if not e.match(space, space.w_KeyError):
                raise
        else:
            if w_builtin is space.builtin:   # common case
                return space.builtin
            if space.isinstance_w(w_builtin, space.w_dict):
                return module.Module(space, None, w_builtin)
            if isinstance(w_builtin, module.Module):
                return w_builtin
        # no builtin! make a default one.  Give them None, at least.
        builtin = module.Module(space, None)
        space.setitem(builtin.w_dict, space.newtext('None'), space.w_None)
        return builtin

    def setup_after_space_initialization(self):
        """NOT_RPYTHON"""
        space = self.space
        # install the more general version of isinstance() & co. in the space
        from pypy.module.__builtin__ import abstractinst as ab
        space.abstract_isinstance_w = ab.abstract_isinstance_w.__get__(space)
        space.abstract_issubclass_w = ab.abstract_issubclass_w.__get__(space)
        space.abstract_isclass_w = ab.abstract_isclass_w.__get__(space)
        space.abstract_getclass = ab.abstract_getclass.__get__(space)
        space.exception_is_valid_class_w = ab.exception_is_valid_class_w.__get__(space)
        space.exception_is_valid_obj_as_class_w = ab.exception_is_valid_obj_as_class_w.__get__(space)
        space.exception_getclass = ab.exception_getclass.__get__(space)
        space.exception_issubclass_w = ab.exception_issubclass_w.__get__(space)
