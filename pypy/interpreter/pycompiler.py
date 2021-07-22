"""
General classes for bytecode compilers.
Compiler instances are stored into 'space.getexecutioncontext().compiler'.
"""

from pypy.interpreter import pycode
from pypy.interpreter.pyparser import future, pyparse, error as parseerror
from pypy.interpreter.astcompiler import (astbuilder, codegen, consts, misc,
                                          optimize, ast)
from pypy.interpreter.error import OperationError, oefmt


class AbstractCompiler(object):
    """Abstract base class for a bytecode compiler."""

    # The idea is to grow more methods here over the time,
    # e.g. to handle .pyc files in various ways if we have multiple compilers.

    def __init__(self, space):
        self.space = space
        self.w_compile_hook = space.w_None

    def compile(self, source, filename, mode, flags):
        """Compile and return an pypy.interpreter.eval.Code instance."""
        raise NotImplementedError

    def getcodeflags(self, code):
        """Return the __future__ compiler flags that were used to compile
        the given code object."""
        return 0

    def compile_command(self, source, filename, mode, flags):
        """Same as compile(), but tries to compile a possibly partial
        interactive input.  If more input is needed, it returns None.
        """
        # Hackish default implementation based on the stdlib 'codeop' module.
        # See comments over there.
        space = self.space
        flags |= consts.PyCF_DONT_IMPLY_DEDENT
        # Check for source consisting of only blank lines and comments
        if mode != "eval":
            in_comment = False
            for c in source:
                if c in ' \t\f\v':   # spaces
                    pass
                elif c == '#':
                    in_comment = True
                elif c in '\n\r':
                    in_comment = False
                elif not in_comment:
                    break    # non-whitespace, non-comment character
            else:
                source = "pass"     # Replace it with a 'pass' statement

        try:
            code = self.compile(source, filename, mode, flags)
            return code   # success
        except OperationError as err:
            if not err.match(space, space.w_SyntaxError):
                raise

        try:
            self.compile(source + "\n", filename, mode, flags)
            return None   # expect more
        except OperationError as err1:
            if not err1.match(space, space.w_SyntaxError):
                raise

        try:
            self.compile(source + "\n\n", filename, mode, flags)
            raise     # uh? no error with \n\n.  re-raise the previous error
        except OperationError as err2:
            if not err2.match(space, space.w_SyntaxError):
                raise

        if space.eq_w(err1.get_w_value(space), err2.get_w_value(space)):
            raise     # twice the same error, re-raise

        return None   # two different errors, expect more


class PyCodeCompiler(AbstractCompiler):
    """Base class for compilers producing PyCode objects."""

    def getcodeflags(self, code):
        """Return the __future__ compiler flags that were used to compile
        the given code object."""
        if isinstance(code, pycode.PyCode):
            return code.co_flags & self.compiler_flags
        else:
            return 0


class PythonAstCompiler(PyCodeCompiler):
    """Uses the stdlib's python implementation of compiler

    XXX: This class should override the baseclass implementation of
         compile_command() in order to optimize it, especially in case
         of incomplete inputs (e.g. we shouldn't re-compile from scratch
         the whole source after having only added a new '\n')
    """
    def __init__(self, space, override_version=None):
        PyCodeCompiler.__init__(self, space)
        self.future_flags = future.futureFlags_2_7
        self.parser = pyparse.PythonParser(space, self.future_flags)
        self.additional_rules = {}
        self.compiler_flags = self.future_flags.allowed_flags

    def compile_ast(self, node, filename, mode, flags):
        if mode == 'eval':
            check = isinstance(node, ast.Expression)
        elif mode == 'exec':
            check = isinstance(node, ast.Module)
        elif mode == 'input':
            check = isinstance(node, ast.Interactive)
        else:
            check = True
        if not check:
            raise oefmt(self.space.w_TypeError, "invalid node type")

        fut = misc.parse_future(node, self.future_flags.compiler_features)
        f_flags, f_lineno, f_col = fut
        future_pos = f_lineno, f_col
        flags |= f_flags
        info = pyparse.CompileInfo(filename, mode, flags, future_pos)
        return self._compile_ast(node, info)

    def _compile_ast(self, node, info, source=None):
        space = self.space
        try:
            mod = optimize.optimize_ast(space, node, info)
            code = codegen.compile_ast(space, mod, info)
        except parseerror.SyntaxError as e:
            raise OperationError(space.w_SyntaxError, e.find_sourceline_and_wrap_info(space, source))
        return code

    def compile_to_ast(self, source, filename, mode, flags):
        info = pyparse.CompileInfo(filename, mode, flags)
        return self._compile_to_ast(source, info)

    def _compile_to_ast(self, source, info):
        space = self.space
        try:
            parse_tree = self.parser.parse_source(source, info)
            mod = astbuilder.ast_from_node(space, parse_tree, info)
        except parseerror.IndentationError as e:
            raise OperationError(space.w_IndentationError, e.find_sourceline_and_wrap_info(space))
        except parseerror.SyntaxError as e:
            raise OperationError(space.w_SyntaxError, e.find_sourceline_and_wrap_info(space, source))
        return mod

    def compile(self, source, filename, mode, flags, hidden_applevel=False):
        info = pyparse.CompileInfo(filename, mode, flags,
                                   hidden_applevel=hidden_applevel)
        mod = self._compile_to_ast(source, info)
        return self._compile_ast(mod, info, source)
