from rpython.rtyper.lltypesystem import rffi, lltype
from pypy.module.cpyext.api import cpython_api, cpython_struct, \
        METH_STATIC, METH_CLASS, METH_COEXIST, CANNOT_FAIL, CONST_STRING, \
        METH_NOARGS, METH_O, METH_VARARGS
from pypy.module.cpyext.pyobject import PyObject, as_pyobj
from pypy.interpreter.module import Module
from pypy.module.cpyext.methodobject import (
    W_PyCFunctionObject, PyCFunction_NewEx, PyDescr_NewMethod,
    PyMethodDef, PyDescr_NewClassMethod, PyStaticMethod_New)
from pypy.module.cpyext.pyerrors import PyErr_BadInternalCall
from pypy.module.cpyext.state import State
from pypy.interpreter.error import oefmt

@cpython_api([rffi.CCHARP], PyObject)
def PyModule_New(space, name):
    """
    Return a new module object with the __name__ attribute set to name.
    Only the module's __doc__ and __name__ attributes are filled in;
    the caller is responsible for providing a __file__ attribute."""
    return Module(space, space.newtext(rffi.charp2str(name)))

#@cpython_api([rffi.CCHARP], PyObject)
def PyImport_AddModule(space, name):
    """Return the module object corresponding to a module name.  The name argument
    may be of the form package.module. First check the modules dictionary if
    there's one there, and if not, create a new one and insert it in the modules
    dictionary.

    This function does not load or import the module; if the module wasn't already
    loaded, you will get an empty module object. Use PyImport_ImportModule()
    or one of its variants to import a module.  Package structures implied by a
    dotted name for name are not created if not already present."""
    w_name = space.newtext(name)
    w_modules = space.sys.get('modules')

    w_mod = space.finditem_str(w_modules, name)
    if w_mod is None:
        w_mod = Module(space, w_name)
        space.setitem(w_modules, w_name, w_mod)

    return w_mod

# This is actually the Py_InitModule4 function,
# renamed to refuse modules built against CPython headers.
@cpython_api([CONST_STRING, lltype.Ptr(PyMethodDef), CONST_STRING,
              PyObject, rffi.INT_real], PyObject, result_borrowed=True)
def _Py_InitPyPyModule(space, name, methods, doc, w_self, apiver):
    """
    Create a new module object based on a name and table of functions, returning
    the new module object. If doc is non-NULL, it will be used to define the
    docstring for the module. If self is non-NULL, it will passed to the
    functions of the module as their (otherwise NULL) first parameter. (This was
    added as an experimental feature, and there are no known uses in the current
    version of Python.) For apiver, the only value which should be passed is
    defined by the constant PYTHON_API_VERSION.

    Note that the name parameter is actually ignored, and the module name is
    taken from the package_context attribute of the cpyext.State in the space
    cache.  CPython includes some extra checking here to make sure the module
    being initialized lines up with what's expected, but we don't.
    """
    from pypy.module.cpyext.api import PyTypeObjectPtr
    modname = rffi.charp2str(name)
    state = space.fromcache(State)
    f_name, f_path = state.package_context
    if f_name is not None:
        modname = f_name
    w_mod = PyImport_AddModule(space, modname)
    state.package_context = None, None

    if f_path is not None:
        dict_w = {'__file__': space.newtext(f_path)}
    else:
        dict_w = {}
    convert_method_defs(space, dict_w, methods, None, w_self, modname)
    for key, w_value in dict_w.items():
        space.setattr(w_mod, space.newtext(key), w_value)
    if doc:
        space.setattr(w_mod, space.newtext("__doc__"),
                      space.newtext(rffi.charp2str(doc)))
    return w_mod   # borrowed result kept alive in PyImport_AddModule()

def convert_method_defs(space, dict_w, methods, w_type, w_self=None, name=None):
    w_name = space.newtext_or_none(name)
    methods = rffi.cast(rffi.CArrayPtr(PyMethodDef), methods)
    if methods:
        i = -1
        while True:
            i = i + 1
            method = methods[i]
            if not method.c_ml_name: break

            methodname = rffi.charp2str(rffi.cast(rffi.CCHARP, method.c_ml_name))
            flags = rffi.cast(lltype.Signed, method.c_ml_flags)

            if w_type is None:
                if flags & METH_CLASS or flags & METH_STATIC:
                    raise oefmt(space.w_ValueError,
                            "module functions cannot set METH_CLASS or "
                            "METH_STATIC")
                w_obj = W_PyCFunctionObject(space, method, w_self, w_name)
            else:
                if methodname in dict_w and not (flags & METH_COEXIST):
                    continue
                if flags & METH_CLASS:
                    if flags & METH_STATIC:
                        raise oefmt(space.w_ValueError,
                                    "method cannot be both class and static")
                    w_obj = PyDescr_NewClassMethod(space, w_type, method)
                elif flags & METH_STATIC:
                    w_func = PyCFunction_NewEx(space, method, None, None)
                    w_obj = PyStaticMethod_New(space, w_func)
                else:
                    w_obj = PyDescr_NewMethod(space, w_type, method)

            dict_w[methodname] = w_obj


@cpython_api([PyObject], rffi.INT_real, error=CANNOT_FAIL)
def PyModule_Check(space, w_obj):
    w_type = space.gettypeobject(Module.typedef)
    w_obj_type = space.type(w_obj)
    return int(space.is_w(w_type, w_obj_type) or
               space.issubtype_w(w_obj_type, w_type))

@cpython_api([PyObject], PyObject, result_borrowed=True)
def PyModule_GetDict(space, w_mod):
    if PyModule_Check(space, w_mod):
        assert isinstance(w_mod, Module)
        w_dict = w_mod.getdict(space)
        return w_dict    # borrowed reference, likely from w_mod.w_dict
    else:
        PyErr_BadInternalCall(space)

@cpython_api([PyObject], rffi.CCHARP)
def PyModule_GetName(space, w_mod):
    """
    Return module's __name__ value.  If the module does not provide one,
    or if it is not a string, SystemError is raised and NULL is returned.
    """
    # NOTE: this version of the code works only because w_mod.w_name is
    # a wrapped string object attached to w_mod; so it makes a
    # PyStringObject that will live as long as the module itself,
    # and returns a "char *" inside this PyStringObject.
    if not isinstance(w_mod, Module):
        raise oefmt(space.w_SystemError, "PyModule_GetName(): not a module")
    from pypy.module.cpyext.bytesobject import PyString_AsString
    return PyString_AsString(space, as_pyobj(space, w_mod.w_name))
