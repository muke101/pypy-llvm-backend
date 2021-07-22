"""
Implementation of the interpreter-level compile/eval builtins.
"""

from pypy.interpreter.pycode import PyCode
from pypy.interpreter.error import OperationError, oefmt
from pypy.interpreter.astcompiler import consts, ast
from pypy.interpreter.gateway import unwrap_spec


@unwrap_spec(filename='text', mode='text', flags=int, dont_inherit=int)
def compile(space, w_source, filename, mode, flags=0, dont_inherit=0):
    """Compile the source string (a Python module, statement or expression)
into a code object that can be executed by the exec statement or eval().
The filename will be used for run-time error messages.
The mode must be 'exec' to compile a module, 'single' to compile a
single (interactive) statement, or 'eval' to compile an expression.
The flags argument, if present, controls which future statements influence
the compilation of the code.
The dont_inherit argument, if non-zero, stops the compilation inheriting
the effects of any future statements in effect in the code calling
compile; if absent or zero these statements do influence the compilation,
in addition to any features explicitly specified.
"""
    ec = space.getexecutioncontext()
    if flags & ~(ec.compiler.compiler_flags | consts.PyCF_ONLY_AST |
                 consts.PyCF_DONT_IMPLY_DEDENT | consts.PyCF_SOURCE_IS_UTF8 |
                 consts.PyCF_ACCEPT_NULL_BYTES):
        raise oefmt(space.w_ValueError, "compile() unrecognized flags")

    if not dont_inherit:
        caller = ec.gettopframe_nohidden()
        if caller:
            flags |= ec.compiler.getcodeflags(caller.getcode())

    if mode not in ('exec', 'eval', 'single'):
        raise oefmt(space.w_ValueError,
                    "compile() arg 3 must be 'exec', 'eval' or 'single'")

    if space.isinstance_w(w_source, space.gettypeobject(ast.W_AST.typedef)):
        if flags & consts.PyCF_ONLY_AST:
            return w_source
        ast_node = ast.mod.from_object(space, w_source)
        return ec.compiler.compile_ast(ast_node, filename, mode, flags)

    if space.isinstance_w(w_source, space.w_unicode):
        w_utf_8_source = space.call_method(w_source, "encode",
                                           space.newtext("utf-8"))
        source = space.bytes_w(w_utf_8_source)
        # This flag tells the parser to reject any coding cookies it sees.
        flags |= consts.PyCF_SOURCE_IS_UTF8
    else:
        source = space.readbuf_w(w_source).as_str()

    if not (flags & consts.PyCF_ACCEPT_NULL_BYTES):
        if '\x00' in source:
            raise oefmt(space.w_TypeError,
                        "compile() expected string without null bytes")

    if flags & consts.PyCF_ONLY_AST:
        node = ec.compiler.compile_to_ast(source, filename, mode, flags)
        return node.to_object(space)
    else:
        return ec.compiler.compile(source, filename, mode, flags)


def eval(space, w_code, w_globals=None, w_locals=None):
    """Evaluate the source in the context of globals and locals.
The source may be a string representing a Python expression
or a code object as returned by compile().  The globals and locals
are dictionaries, defaulting to the current current globals and locals.
If only globals is given, locals defaults to it.
"""
    if (space.isinstance_w(w_code, space.w_bytes) or
        space.isinstance_w(w_code, space.w_unicode)):
        w_code = compile(space,
                         space.call_method(w_code, 'lstrip',
                                           space.newtext(' \t')),
                         "<string>", "eval")

    if not isinstance(w_code, PyCode):
        raise oefmt(space.w_TypeError,
                    "eval() arg 1 must be a string or code object")

    if space.is_none(w_globals):
        caller = space.getexecutioncontext().gettopframe_nohidden()
        if caller is None:
            w_globals = space.newdict()
            if space.is_none(w_locals):
                w_locals = w_globals
        else:
            w_globals = caller.get_w_globals()
            if space.is_none(w_locals):
                w_locals = caller.getdictscope()
    elif space.is_none(w_locals):
        w_locals = w_globals

    # xxx removed: adding '__builtins__' to the w_globals dict, if there
    # is none.  This logic was removed as costly (it requires to get at
    # the gettopframe_nohidden()).  I bet no test fails, and it's a really
    # obscure case.

    return w_code.exec_code(space, w_globals, w_locals)
