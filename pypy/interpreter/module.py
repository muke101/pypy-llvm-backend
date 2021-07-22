"""
Module objects.
"""

from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.error import OperationError
from rpython.rlib.objectmodel import we_are_translated, not_rpython


class Module(W_Root):
    """A module."""

    _immutable_fields_ = ["w_dict?"]

    _frozen = False

    def __init__(self, space, w_name, w_dict=None, add_package=True):
        self.space = space
        if w_dict is None:
            w_dict = space.newdict(module=True)
        self.w_dict = w_dict
        self.w_name = w_name
        if w_name is not None:
            space.setitem(w_dict, space.new_interned_str('__name__'), w_name)
        if add_package:
            # add the __package__ attribute only when created from internal
            # code, but not when created from Python code (as in CPython)
            space.setitem(w_dict, space.new_interned_str('__package__'),
                          space.w_None)
        self.startup_called = False

    def _cleanup_(self):
        """Called by the annotator on prebuilt Module instances.
        We don't have many such modules, but for the ones that
        show up, remove their __file__ rather than translate it
        statically inside the executable."""
        try:
            space = self.space
            space.delitem(self.w_dict, space.newtext('__file__'))
        except OperationError:
            pass

    @not_rpython
    def install(self):
        """installs this module into space.builtin_modules"""
        modulename = self.space.text0_w(self.w_name)
        self.space.builtin_modules[modulename] = self

    @not_rpython
    def setup_after_space_initialization(self):
        """to allow built-in modules to do some more setup
        after the space is fully initialized."""

    def init(self, space):
        """This is called each time the module is imported or reloaded
        """
        if not self.startup_called:
            if not we_are_translated():
                # this special case is to handle the case, during annotation,
                # of module A that gets frozen, then module B (e.g. during
                # a getdict()) runs some code that imports A
                if self._frozen:
                    return
            self.startup_called = True
            self.startup(space)

    def startup(self, space):
        """This is called at runtime on import to allow the module to
        do initialization when it is imported for the first time.
        """

    def shutdown(self, space):
        """This is called when the space is shut down, just after
        sys.exitfunc(), if the module has been imported.
        """

    def getdict(self, space):
        return self.w_dict

    def descr_module__new__(space, w_subtype, __args__):
        module = space.allocate_instance(Module, w_subtype)
        Module.__init__(module, space, None, add_package=False)
        return module

    def descr_module__init__(self, w_name, w_doc=None):
        space = self.space
        self.w_name = w_name
        if w_doc is None:
            w_doc = space.w_None
        space.setitem(self.w_dict, space.new_interned_str('__name__'), w_name)
        space.setitem(self.w_dict, space.new_interned_str('__doc__'), w_doc)

    def descr__reduce__(self, space):
        w_name = space.finditem(self.w_dict, space.newtext('__name__'))
        if (w_name is None or
            not space.isinstance_w(w_name, space.w_text)):
            # maybe raise exception here (XXX this path is untested)
            return space.w_None
        w_modules = space.sys.get('modules')
        if space.finditem(w_modules, w_name) is None:
            #not imported case
            from pypy.interpreter.mixedmodule import MixedModule
            w_mod    = space.getbuiltinmodule('_pickle_support')
            mod      = space.interp_w(MixedModule, w_mod)
            new_inst = mod.get('module_new')
            return space.newtuple([new_inst,
                                   space.newtuple([w_name,
                                                   self.getdict(space)]),
                                  ])
        #already imported case
        w_import = space.builtin.get('__import__')
        tup_return = [
            w_import,
            space.newtuple([
                w_name,
                space.w_None,
                space.w_None,
                space.newtuple([space.newtext('')])
            ])
        ]

        return space.newtuple(tup_return)

    def descr_module__repr__(self, space):
        from pypy.interpreter.mixedmodule import MixedModule
        if self.w_name is not None:
            name = space.text_w(space.repr(self.w_name))
        else:
            name = "'?'"
        if isinstance(self, MixedModule):
            return space.newtext("<module %s (built-in)>" % name)
        try:
            w___file__ = space.getattr(self, space.newtext('__file__'))
            __file__ = space.text_w(space.repr(w___file__))
        except OperationError:
            __file__ = '?'
        return space.newtext("<module %s from %s>" % (name, __file__))
