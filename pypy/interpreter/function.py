"""
Function objects.

In PyPy there is no difference between built-in and user-defined function
objects; the difference lies in the code object found in their func_code
attribute.
"""

from rpython.rlib.unroll import unrolling_iterable
from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.error import OperationError, oefmt
from pypy.interpreter.eval import Code
from pypy.interpreter.argument import Arguments
from rpython.rlib import jit

from rpython.rlib.rarithmetic import LONG_BIT
from rpython.rlib.rbigint import rbigint


funccallunrolling = unrolling_iterable(range(4))


@jit.elidable_promote()
def _get_immutable_code(func):
    assert not func.can_change_code
    return func.code

class Function(W_Root):
    """A function is a code object captured with some environment:
    an object space, a dictionary of globals, default arguments,
    and an arbitrary 'closure' passed to the code object."""

    can_change_code = True
    _immutable_fields_ = ['code?',
                          'w_func_globals?',
                          'closure?[*]',
                          'defs_w?[*]',
                          'name?']

    def __init__(self, space, code, w_globals=None, defs_w=[], closure=None,
                 forcename=None):
        self.space = space
        self.name = forcename or code.co_name
        self.w_doc = None   # lazily read from code.getdocstring()
        self.code = code       # Code instance
        self.w_func_globals = w_globals  # the globals dictionary
        self.closure = closure    # normally, list of Cell instances or None
        self.defs_w = defs_w
        self.w_func_dict = None # filled out below if needed
        self.w_module = None

    def __repr__(self):
        # return "function %s.%s" % (self.space, self.name)
        # maybe we want this shorter:
        name = getattr(self, 'name', None)
        if not isinstance(name, str):
            name = '?'
        return "<%s %s>" % (self.__class__.__name__, name)

    def call_args(self, args):
        # delegate activation to code
        w_res = self.getcode().funcrun(self, args)
        assert isinstance(w_res, W_Root)
        return w_res

    def call_obj_args(self, w_obj, args):
        # delegate activation to code
        w_res = self.getcode().funcrun_obj(self, w_obj, args)
        assert isinstance(w_res, W_Root)
        return w_res

    def getcode(self):
        if jit.we_are_jitted():
            if not self.can_change_code:
                return _get_immutable_code(self)
            return jit.promote(self.code)
        return self.code

    def funccall(self, *args_w): # speed hack
        from pypy.interpreter import gateway
        from pypy.interpreter.pycode import PyCode

        code = self.getcode() # hook for the jit
        nargs = len(args_w)
        fast_natural_arity = code.fast_natural_arity
        if nargs == fast_natural_arity:
            if nargs == 0:
                assert isinstance(code, gateway.BuiltinCode0)
                return code.fastcall_0(self.space, self)
            elif nargs == 1:
                assert isinstance(code, gateway.BuiltinCode1)
                return code.fastcall_1(self.space, self, args_w[0])
            elif nargs == 2:
                assert isinstance(code, gateway.BuiltinCode2)
                return code.fastcall_2(self.space, self, args_w[0], args_w[1])
            elif nargs == 3:
                assert isinstance(code, gateway.BuiltinCode3)
                return code.fastcall_3(self.space, self, args_w[0],
                                       args_w[1], args_w[2])
            elif nargs == 4:
                assert isinstance(code, gateway.BuiltinCode4)
                return code.fastcall_4(self.space, self, args_w[0],
                                       args_w[1], args_w[2], args_w[3])
        elif (nargs | PyCode.FLATPYCALL) == fast_natural_arity:
            assert isinstance(code, PyCode)
            if nargs < 5:
                new_frame = self.space.createframe(code, self.w_func_globals,
                                                   self)
                for i in funccallunrolling:
                    if i < nargs:
                        new_frame.locals_cells_stack_w[i] = args_w[i]
                return new_frame.run()
        elif nargs >= 1 and fast_natural_arity == Code.PASSTHROUGHARGS1:
            assert isinstance(code, gateway.BuiltinCodePassThroughArguments1)
            return code.funcrun_obj(self, args_w[0],
                                    Arguments(self.space,
                                              list(args_w[1:])))
        return self.call_args(Arguments(self.space, list(args_w)))

    def funccall_valuestack(self, nargs, frame, methodcall=False): # speed hack
        # methodcall is only for better error messages
        from pypy.interpreter import gateway
        from pypy.interpreter.pycode import PyCode

        code = self.getcode() # hook for the jit
        #
        if (jit.we_are_jitted() and code is self.space._code_of_sys_exc_info
                                and nargs == 0):
            from pypy.module.sys.vm import exc_info_direct
            return exc_info_direct(self.space, frame)
        #
        fast_natural_arity = code.fast_natural_arity
        if nargs == fast_natural_arity:
            if nargs == 0:
                assert isinstance(code, gateway.BuiltinCode0)
                return code.fastcall_0(self.space, self)
            elif nargs == 1:
                assert isinstance(code, gateway.BuiltinCode1)
                return code.fastcall_1(self.space, self, frame.peekvalue(0))
            elif nargs == 2:
                assert isinstance(code, gateway.BuiltinCode2)
                return code.fastcall_2(self.space, self, frame.peekvalue(1),
                                       frame.peekvalue(0))
            elif nargs == 3:
                assert isinstance(code, gateway.BuiltinCode3)
                return code.fastcall_3(self.space, self, frame.peekvalue(2),
                                       frame.peekvalue(1), frame.peekvalue(0))
            elif nargs == 4:
                assert isinstance(code, gateway.BuiltinCode4)
                return code.fastcall_4(self.space, self, frame.peekvalue(3),
                                       frame.peekvalue(2), frame.peekvalue(1),
                                        frame.peekvalue(0))
        elif (nargs | Code.FLATPYCALL) == fast_natural_arity:
            assert isinstance(code, PyCode)
            return self._flat_pycall(code, nargs, frame)
        elif fast_natural_arity & Code.FLATPYCALL:
            natural_arity = fast_natural_arity & 0xff
            if natural_arity > nargs >= natural_arity - len(self.defs_w):
                assert isinstance(code, PyCode)
                return self._flat_pycall_defaults(code, nargs, frame,
                                                  natural_arity - nargs)
        elif fast_natural_arity == Code.PASSTHROUGHARGS1 and nargs >= 1:
            assert isinstance(code, gateway.BuiltinCodePassThroughArguments1)
            w_obj = frame.peekvalue(nargs-1)
            args = frame.make_arguments(nargs-1)
            return code.funcrun_obj(self, w_obj, args)

        args = frame.make_arguments(nargs, methodcall=methodcall)
        return self.call_args(args)

    @jit.unroll_safe
    def _flat_pycall(self, code, nargs, frame):
        # code is a PyCode
        new_frame = self.space.createframe(code, self.w_func_globals,
                                                   self)
        for i in xrange(nargs):
            w_arg = frame.peekvalue(nargs-1-i)
            new_frame.locals_cells_stack_w[i] = w_arg

        return new_frame.run()

    @jit.unroll_safe
    def _flat_pycall_defaults(self, code, nargs, frame, defs_to_load):
        # code is a PyCode
        new_frame = self.space.createframe(code, self.w_func_globals,
                                                   self)
        for i in xrange(nargs):
            w_arg = frame.peekvalue(nargs-1-i)
            new_frame.locals_cells_stack_w[i] = w_arg

        ndefs = len(self.defs_w)
        start = ndefs - defs_to_load
        i = nargs
        for j in xrange(start, ndefs):
            new_frame.locals_cells_stack_w[i] = self.defs_w[j]
            i += 1
        return new_frame.run()

    def getdict(self, space):
        if self.w_func_dict is None:
            self.w_func_dict = space.newdict(instance=True)
        return self.w_func_dict

    def setdict(self, space, w_dict):
        if not space.isinstance_w(w_dict, space.w_dict):
            raise oefmt(space.w_TypeError,
                        "setting function's dictionary to a non-dict")
        self.w_func_dict = w_dict

    def descr_function__new__(space, w_subtype, w_code, w_globals,
                              w_name=None, w_argdefs=None, w_closure=None):
        code = space.interp_w(Code, w_code)
        if not space.isinstance_w(w_globals, space.w_dict):
            raise oefmt(space.w_TypeError, "expected dict")
        if not space.is_none(w_name):
            name = space.text_w(w_name)
        else:
            name = None
        if not space.is_none(w_argdefs):
            defs_w = space.fixedview(w_argdefs)
        else:
            defs_w = []
        nfreevars = 0
        from pypy.interpreter.pycode import PyCode
        if isinstance(code, PyCode):
            nfreevars = len(code.co_freevars)
        if space.is_none(w_closure) and nfreevars == 0:
            closure = None
        elif not space.is_w(space.type(w_closure), space.w_tuple):
            raise oefmt(space.w_TypeError, "invalid closure")
        else:
            from pypy.interpreter.nestedscope import Cell
            closure_w = space.unpackiterable(w_closure)
            n = len(closure_w)
            if nfreevars == 0:
                raise oefmt(space.w_ValueError, "no closure needed")
            elif nfreevars != n:
                raise oefmt(space.w_ValueError, "closure is wrong size")
            closure = [space.interp_w(Cell, w_cell) for w_cell in closure_w]
        func = space.allocate_instance(Function, w_subtype)
        Function.__init__(func, space, code, w_globals, defs_w, closure, name)
        return func

    def descr_function_call(self, __args__):
        return self.call_args(__args__)

    def descr_function_repr(self):
        return self.getrepr(self.space, 'function %s' % (self.name,))


    def _cleanup_(self):
        # delicate
        from pypy.interpreter.gateway import BuiltinCode
        if isinstance(self.code, BuiltinCode):
            # we have been seen by other means so rtyping should not choke
            # on us
            identifier = self.code.identifier
            previous = self.space._builtin_functions_by_identifier.get(identifier, self)
            assert previous is self, (
                "duplicate function ids with identifier=%r: %r and %r" % (
                identifier, previous, self))
            self.add_to_table()
        return False

    def add_to_table(self):
        self.space._builtin_functions_by_identifier[self.code.identifier] = self

    def find(space, identifier):
        return space._builtin_functions_by_identifier[identifier]
    find = staticmethod(find)

    def descr_function__reduce__(self, space):
        from pypy.interpreter.gateway import BuiltinCode
        from pypy.interpreter.mixedmodule import MixedModule
        w_mod = space.getbuiltinmodule('_pickle_support')
        mod = space.interp_w(MixedModule, w_mod)
        code = self.code
        if isinstance(code, BuiltinCode):
            new_inst = mod.get('builtin_function')
            return space.newtuple([new_inst,
                                   space.newtuple([space.newtext(code.identifier)])])

        new_inst = mod.get('func_new')
        if self.closure is None:
            w_closure = space.w_None
        else:
            w_closure = space.newtuple([cell for cell in self.closure])
        if self.w_doc is None:
            w_doc = space.w_None
        else:
            w_doc = self.w_doc
        if self.w_func_globals is None:
            w_func_globals = space.w_None
        else:
            w_func_globals = self.w_func_globals
        if self.w_func_dict is None:
            w_func_dict = space.w_None
        else:
            w_func_dict = self.w_func_dict

        nt = space.newtuple
        tup_base = []
        tup_state = [
            space.newtext(self.name),
            w_doc,
            self.code,
            w_func_globals,
            w_closure,
            nt(self.defs_w),
            w_func_dict,
            self.w_module,
        ]
        return nt([new_inst, nt(tup_base), nt(tup_state)])

    def descr_function__setstate__(self, space, w_args):
        args_w = space.unpackiterable(w_args)
        try:
            (w_name, w_doc, w_code, w_func_globals, w_closure, w_defs,
             w_func_dict, w_module) = args_w
        except ValueError:
            # wrong args
            raise oefmt(space.w_ValueError,
                        "Wrong arguments to function.__setstate__")

        self.space = space
        self.name = space.text_w(w_name)
        self.code = space.interp_w(Code, w_code)
        if not space.is_w(w_closure, space.w_None):
            from pypy.interpreter.nestedscope import Cell
            closure_w = space.unpackiterable(w_closure)
            self.closure = [space.interp_w(Cell, w_cell) for w_cell in closure_w]
        else:
            self.closure = None
        if space.is_w(w_doc, space.w_None):
            w_doc = None
        self.w_doc = w_doc
        if space.is_w(w_func_globals, space.w_None):
            w_func_globals = None
        self.w_func_globals = w_func_globals
        if space.is_w(w_func_dict, space.w_None):
            w_func_dict = None
        self.w_func_dict = w_func_dict
        self.defs_w = space.fixedview(w_defs)
        self.w_module = w_module

    def _check_code_mutable(self, attr):
        if not self.can_change_code:
            raise oefmt(self.space.w_TypeError,
                        "Cannot change %s attribute of builtin functions", attr)

    def fget_func_defaults(self, space):
        values_w = self.defs_w
        # the `None in values_w` check here is to ensure that interp-level
        # functions with a default of None do not get their defaults
        # exposed at applevel
        if not values_w or None in values_w:
            return space.w_None
        return space.newtuple(values_w)

    def fset_func_defaults(self, space, w_defaults):
        self._check_code_mutable("func_defaults")
        if space.is_w(w_defaults, space.w_None):
            self.defs_w = []
            return
        if not space.isinstance_w(w_defaults, space.w_tuple):
            raise oefmt(space.w_TypeError,
                        "func_defaults must be set to a tuple object or None")
        self.defs_w = space.fixedview(w_defaults)

    def fdel_func_defaults(self, space):
        self._check_code_mutable("func_defaults")
        self.defs_w = []

    def fget_func_doc(self, space):
        if self.w_doc is None:
            self.w_doc = self.code.getdocstring(space)
        return self.w_doc

    def fset_func_doc(self, space, w_doc):
        self._check_code_mutable("func_doc")
        self.w_doc = w_doc

    def fdel_func_doc(self, space):
        self._check_code_mutable("func_doc")
        self.w_doc = space.w_None

    def fget_func_name(self, space):
        return space.newtext(self.name)

    def fset_func_name(self, space, w_name):
        self._check_code_mutable("func_name")
        if space.isinstance_w(w_name, space.w_text):
            self.name = space.text_w(w_name)
        else:
            raise oefmt(space.w_TypeError,
                        "__name__ must be set to a string object")

    def fget___module__(self, space):
        if self.w_module is None:
            if self.w_func_globals is not None and not space.is_w(self.w_func_globals, space.w_None):
                self.w_module = space.call_method(self.w_func_globals, "get", space.newtext("__name__"))
            else:
                self.w_module = space.w_None
        return self.w_module

    def fset___module__(self, space, w_module):
        self._check_code_mutable("func_name")
        self.w_module = w_module

    def fdel___module__(self, space):
        self._check_code_mutable("func_name")
        self.w_module = space.w_None

    def fget_func_code(self, space):
        return self.getcode()

    def fset_func_code(self, space, w_code):
        from pypy.interpreter.pycode import PyCode
        if not self.can_change_code:
            raise oefmt(space.w_TypeError,
                        "Cannot change code attribute of builtin functions")
        code = space.interp_w(Code, w_code)
        closure_len = 0
        if self.closure:
            closure_len = len(self.closure)
        if isinstance(code, PyCode) and closure_len != len(code.co_freevars):
            raise oefmt(space.w_ValueError,
                        "%N() requires a code object with %d free vars, not "
                        "%d", self, closure_len, len(code.co_freevars))
        self.fget_func_doc(space)    # see test_issue1293
        self.code = code

    def fget_func_closure(self, space):
        if self.closure is not None:
            w_res = space.newtuple([cell for cell in self.closure])
        else:
            w_res = space.w_None
        return w_res


def descr_function_get(space, w_function, w_obj, w_cls=None):
    """functionobject.__get__(obj[, type]) -> method"""
    # this is not defined as a method on Function because it's generally
    # useful logic: w_function can be any callable.  It is used by Method too.
    asking_for_bound = (space.is_none(w_cls) or
                        not space.is_w(w_obj, space.w_None) or
                        space.is_w(w_cls, space.type(space.w_None)))
    if asking_for_bound:
        return Method(space, w_function, w_obj, w_cls)
    else:
        return Method(space, w_function, None, w_cls)


class Method(W_Root):
    """A method is a function bound to a specific instance or class."""
    _immutable_fields_ = ['w_function', 'w_instance', 'w_class']

    def __init__(self, space, w_function, w_instance, w_class):
        self.space = space
        self.w_function = w_function
        self.w_instance = w_instance   # or None
        if w_class is None:
            w_class = space.w_None
        self.w_class = w_class         # possibly space.w_None

    def descr_method__new__(space, w_subtype, w_function, w_instance,
                            w_class=None):
        if space.is_w(w_instance, space.w_None):
            w_instance = None
        if w_instance is None and space.is_none(w_class):
            raise oefmt(space.w_TypeError, "unbound methods must have class")
        method = space.allocate_instance(Method, w_subtype)
        Method.__init__(method, space, w_function, w_instance, w_class)
        return method

    def __repr__(self):
        if self.w_instance:
            pre = "bound"
        else:
            pre = "unbound"
        return "%s method %s" % (pre, self.w_function.getname(self.space))

    def call_args(self, args):
        space = self.space
        if self.w_instance is not None:
            # bound method
            return space.call_obj_args(self.w_function, self.w_instance, args)

        # unbound method
        w_firstarg = args.firstarg()
        if w_firstarg is not None and (
                space.abstract_isinstance_w(w_firstarg, self.w_class)):
            pass  # ok
        else:
            clsdescr = self.w_class.getname(space)
            if clsdescr and clsdescr != '?':
                clsdescr += " instance"
            else:
                clsdescr = "instance"
            if w_firstarg is None:
                instdescr = "nothing"
            else:
                instname = space.abstract_getclass(w_firstarg).getname(space)
                if instname and instname != '?':
                    instdescr = instname + " instance"
                else:
                    instdescr = "instance"
            raise oefmt(space.w_TypeError,
                        "unbound method %N() must be called with %s as first "
                        "argument (got %s instead)", self, clsdescr, instdescr)
        return space.call_args(self.w_function, args)

    def descr_method_get(self, w_obj, w_cls=None):
        space = self.space
        if self.w_instance is not None:
            return self    # already bound
        else:
            # only allow binding to a more specific class than before
            if (w_cls is not None and
                not space.is_w(w_cls, space.w_None) and
                not space.abstract_issubclass_w(w_cls, self.w_class,
                                                allow_override=True)):
                return self    # subclass test failed
            else:
                return descr_function_get(space, self.w_function, w_obj, w_cls)

    def descr_method_call(self, __args__):
        return self.call_args(__args__)

    def descr_method_repr(self):
        space = self.space
        name = self.w_function.getname(self.space)
        # XXX do we handle all cases sanely here?
        if space.is_w(self.w_class, space.w_None):
            w_class = space.type(self.w_instance)
        else:
            w_class = self.w_class
        typename = w_class.getname(self.space)
        if self.w_instance is None:
            s = "<unbound method %s.%s>" % (typename, name)
            return space.newtext(s)
        else:
            objrepr = space.text_w(space.repr(self.w_instance))
            s = '<bound method %s.%s of %s>' % (typename, name, objrepr)
            return space.newtext(s)

    def descr_method_getattribute(self, w_attr):
        space = self.space
        if space.text_w(w_attr) != '__doc__':
            try:
                return space.call_method(space.w_object, '__getattribute__',
                                         self, w_attr)
            except OperationError as e:
                if not e.match(space, space.w_AttributeError):
                    raise
        # fall-back to the attribute of the underlying 'im_func'
        return space.getattr(self.w_function, w_attr)

    def descr_method_eq(self, w_other):
        space = self.space
        if not isinstance(w_other, Method):
            return space.w_NotImplemented
        if self.w_instance is None:
            if w_other.w_instance is not None:
                return space.w_False
        else:
            if w_other.w_instance is None:
                return space.w_False
            if not space.eq_w(self.w_instance, w_other.w_instance):
                return space.w_False
        return space.newbool(space.eq_w(self.w_function, w_other.w_function))

    def is_w(self, space, other):
        if self.w_instance is not None:
            return W_Root.is_w(self, space, other)
        # The following special-case is only for *unbound* method objects.
        # Motivation: in CPython, it seems that no strange internal type
        # exists where the equivalent of ``x.method is x.method`` would
        # return True.  This is unlike unbound methods, where e.g.
        # ``list.append is list.append`` returns True.  The following code
        # is here to emulate that behaviour.  Unlike CPython, we return
        # True for all equal unbound methods, not just for built-in types.
        if not isinstance(other, Method):
            return False
        return (other.w_instance is None and
                self.w_function is other.w_function and
                self.w_class is other.w_class)

    def immutable_unique_id(self, space):
        if self.w_instance is not None:
            return W_Root.immutable_unique_id(self, space)
        # the special-case is only for *unbound* method objects
        #
        from pypy.objspace.std.util import IDTAG_UNBOUND_METHOD as tag
        from pypy.objspace.std.util import IDTAG_SHIFT
        id = space.bigint_w(space.id(self.w_function))
        id = id.lshift(LONG_BIT).or_(space.bigint_w(space.id(self.w_class)))
        id = id.lshift(IDTAG_SHIFT).int_or_(tag)
        return space.newlong_from_rbigint(id)

    def descr_method_hash(self):
        space = self.space
        w_result = space.hash(self.w_function)
        if self.w_instance is not None:
            w_result = space.xor(w_result, space.hash(self.w_instance))
        return w_result

    def descr_method__reduce__(self, space):
        from pypy.interpreter.mixedmodule import MixedModule
        from pypy.interpreter.gateway import BuiltinCode
        w_mod    = space.getbuiltinmodule('_pickle_support')
        mod      = space.interp_w(MixedModule, w_mod)
        new_inst = mod.get('method_new')
        w_instance = self.w_instance or space.w_None
        w_function = self.w_function
        if (isinstance(w_function, Function) and
                isinstance(w_function.code, BuiltinCode)):
            new_inst = mod.get('builtin_method_new')
            if space.is_w(w_instance, space.w_None):
                tup = [self.w_class, space.newtext(w_function.name)]
            else:
                tup = [w_instance, space.newtext(w_function.name)]
        elif space.is_w(self.w_class, space.w_None):
            tup = [self.w_function, w_instance]
        else:
            tup = [self.w_function, w_instance, self.w_class]
        return space.newtuple([new_inst, space.newtuple(tup)])


class StaticMethod(W_Root):
    """The staticmethod objects."""
    _immutable_fields_ = ['w_function?']

    def __init__(self, w_function):
        self.w_function = w_function

    def descr_staticmethod_get(self, w_obj, w_cls=None):
        """staticmethod(x).__get__(obj[, type]) -> x"""
        return self.w_function

    def descr_staticmethod__new__(space, w_subtype, w_function):
        instance = space.allocate_instance(StaticMethod, w_subtype)
        instance.__init__(space.w_None)
        return instance

    def descr_init(self, space, w_function):
        self.w_function = w_function


class ClassMethod(W_Root):
    """The classmethod objects."""
    _immutable_fields_ = ['w_function?']

    def __init__(self, w_function):
        self.w_function = w_function

    def descr_classmethod_get(self, space, w_obj, w_klass=None):
        if space.is_none(w_klass):
            w_klass = space.type(w_obj)
        return Method(space, self.w_function, w_klass,
                      space.type(w_klass))

    def descr_classmethod__new__(space, w_subtype, w_function):
        instance = space.allocate_instance(ClassMethod, w_subtype)
        instance.__init__(space.w_None)
        return instance

    def descr_init(self, space, w_function):
        self.w_function = w_function

class FunctionWithFixedCode(Function):
    can_change_code = False

class BuiltinFunction(Function):
    can_change_code = False

    def __init__(self, func):
        assert isinstance(func, Function)
        Function.__init__(self, func.space, func.code, func.w_func_globals,
                          func.defs_w, func.closure, func.name)
        self.w_doc = func.w_doc
        self.w_func_dict = func.w_func_dict
        self.w_module = func.w_module

    def descr_builtinfunction__new__(space, w_subtype):
        raise oefmt(space.w_TypeError,
                    "cannot create 'builtin_function' instances")

    def descr_function_repr(self):
        return self.space.newtext('<built-in function %s>' % (self.name,))

def is_builtin_code(w_func):
    from pypy.interpreter.gateway import BuiltinCode
    if isinstance(w_func, Method):
        w_func = w_func.w_function
    if isinstance(w_func, Function):
        code = w_func.getcode()
    else:
        code = None
    return isinstance(code, BuiltinCode)
