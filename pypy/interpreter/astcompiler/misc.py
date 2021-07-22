from pypy.interpreter import gateway
from rpython.rlib.objectmodel import we_are_translated
from rpython.rlib.unroll import unrolling_iterable


app = gateway.applevel("""
def syntax_warning(msg, fn, lineno, offset):
    import warnings
    try:
        warnings.warn_explicit(msg, SyntaxWarning, fn, lineno)
    except SyntaxWarning:
        raise SyntaxError(msg, (fn, lineno, offset, msg))
""", filename=__file__)
_emit_syntax_warning = app.interphook("syntax_warning")
del app

def syntax_warning(space, msg, fn, lineno, offset):
    """Raise an applevel SyntaxWarning.

    If the user has set this warning to raise an error, a SyntaxError will be
    raised."""
    w_msg = space.newtext(msg)
    w_filename = space.newtext(fn)
    w_lineno = space.newint(lineno)
    w_offset = space.newint(offset)
    _emit_syntax_warning(space, w_msg, w_filename, w_lineno, w_offset)


def parse_future(tree, feature_flags):
    from pypy.interpreter.astcompiler import ast
    future_lineno = 0
    future_column = 0
    flags = 0
    have_docstring = False
    body = None
    if isinstance(tree, ast.Module):
        body = tree.body
    elif isinstance(tree, ast.Interactive):
        body = tree.body
    if body is None:
        return 0, 0, 0
    for stmt in body:
        if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Str):
            if have_docstring:
                break
            else:
                have_docstring = True
        elif isinstance(stmt, ast.ImportFrom):
            if stmt.module == "__future__":
                future_lineno = stmt.lineno
                future_column = stmt.col_offset
                for alias in stmt.names:
                    assert isinstance(alias, ast.alias)
                    # If this is an invalid flag, it will be caught later in
                    # codegen.py.
                    flags |= feature_flags.get(alias.name, 0)
            else:
                break
        else:
            break
    return flags, future_lineno, future_column


class ForbiddenNameAssignment(Exception):

    def __init__(self, name, node):
        self.name = name
        self.node = node


def check_forbidden_name(name, node=None):
    """Raise an error if the name cannot be assigned to."""
    if name in ("None", "__debug__"):
        raise ForbiddenNameAssignment(name, node)
    # XXX Warn about using True and False


def dict_to_switch(d):
    """Convert of dictionary with integer keys to a switch statement."""
    def lookup(query):
        if we_are_translated():
            for key, value in unrolling_iteritems:
                if key == query:
                    return value
            else:
                raise KeyError
        else:
            return d[query]
    lookup._always_inline_ = True
    unrolling_iteritems = unrolling_iterable(d.iteritems())
    return lookup


def mangle(name, klass):
    if not name.startswith('__'):
        return name
    # Don't mangle __id__ or names with dots. The only time a name with a dot
    # can occur is when we are compiling an import statement that has a package
    # name.
    if name.endswith('__') or '.' in name:
        return name
    try:
        i = 0
        while klass[i] == '_':
            i = i + 1
    except IndexError:
        return name
    return "_%s%s" % (klass[i:], name)


def intern_if_common_string(space, w_const):
    # only intern identifier-like strings
    if not space.is_w(space.type(w_const), space.w_text):
        return w_const
    for c in space.text_w(w_const):
        if not (c.isalnum() or c == '_'):
            return w_const
    return space.new_interned_w_str(w_const)
