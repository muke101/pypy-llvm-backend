"""
Generate Python bytecode from a Abstract Syntax Tree.
"""

# NOTE TO READERS: All the ugly and "obvious" isinstance assertions here are to
# help the annotator.  To it, unfortunately, everything is not so obvious.  If
# you figure out a way to remove them, great, but try a translation first,
# please.

from rpython.rlib.objectmodel import specialize
from pypy.interpreter.astcompiler import ast, assemble, symtable, consts, misc
from pypy.interpreter.astcompiler import optimize # For side effects
from pypy.interpreter.pyparser.error import SyntaxError
from pypy.tool import stdlib_opcode as ops


def compile_ast(space, module, info):
    """Generate a code object from AST."""
    symbols = symtable.SymtableBuilder(space, module, info)
    return TopLevelCodeGenerator(space, module, symbols, info).assemble()

MAX_STACKDEPTH_CONTAINERS = 100

name_ops_default = misc.dict_to_switch({
    ast.Load: ops.LOAD_NAME,
    ast.Store: ops.STORE_NAME,
    ast.Del: ops.DELETE_NAME
})

name_ops_fast = misc.dict_to_switch({
    ast.Load: ops.LOAD_FAST,
    ast.Store: ops.STORE_FAST,
    ast.Del: ops.DELETE_FAST
})

name_ops_deref = misc.dict_to_switch({
    ast.Load: ops.LOAD_DEREF,
    ast.Store: ops.STORE_DEREF,
})

name_ops_global = misc.dict_to_switch({
    ast.Load: ops.LOAD_GLOBAL,
    ast.Store: ops.STORE_GLOBAL,
    ast.Del: ops.DELETE_GLOBAL
})


unary_operations = misc.dict_to_switch({
    ast.Invert: ops.UNARY_INVERT,
    ast.Not: ops.UNARY_NOT,
    ast.UAdd: ops.UNARY_POSITIVE,
    ast.USub: ops.UNARY_NEGATIVE
})

binary_operations = misc.dict_to_switch({
    ast.Add: ops.BINARY_ADD,
    ast.Sub: ops.BINARY_SUBTRACT,
    ast.Mult: ops.BINARY_MULTIPLY,
    ast.Mod: ops.BINARY_MODULO,
    ast.Pow: ops.BINARY_POWER,
    ast.LShift: ops.BINARY_LSHIFT,
    ast.RShift: ops.BINARY_RSHIFT,
    ast.BitOr: ops.BINARY_OR,
    ast.BitAnd: ops.BINARY_AND,
    ast.BitXor: ops.BINARY_XOR,
    ast.FloorDiv: ops.BINARY_FLOOR_DIVIDE
})

inplace_operations = misc.dict_to_switch({
    ast.Add: ops.INPLACE_ADD,
    ast.Sub: ops.INPLACE_SUBTRACT,
    ast.Mult: ops.INPLACE_MULTIPLY,
    ast.Mod: ops.INPLACE_MODULO,
    ast.Pow: ops.INPLACE_POWER,
    ast.LShift: ops.INPLACE_LSHIFT,
    ast.RShift: ops.INPLACE_RSHIFT,
    ast.BitOr: ops.INPLACE_OR,
    ast.BitAnd: ops.INPLACE_AND,
    ast.BitXor: ops.INPLACE_XOR,
    ast.FloorDiv: ops.INPLACE_FLOOR_DIVIDE
})

compare_operations = misc.dict_to_switch({
    ast.Eq: 2,
    ast.NotEq: 3,
    ast.Lt: 0,
    ast.LtE: 1,
    ast.Gt: 4,
    ast.GtE: 5,
    ast.In: 6,
    ast.NotIn: 7,
    ast.Is: 8,
    ast.IsNot: 9
})

subscr_operations = misc.dict_to_switch({
    ast.AugLoad: ops.BINARY_SUBSCR,
    ast.Load: ops.BINARY_SUBSCR,
    ast.AugStore: ops.STORE_SUBSCR,
    ast.Store: ops.STORE_SUBSCR,
    ast.Del: ops.DELETE_SUBSCR
})

slice_operations = misc.dict_to_switch({
    ast.AugLoad: ops.SLICE,
    ast.Load: ops.SLICE,
    ast.AugStore: ops.STORE_SLICE,
    ast.Store: ops.STORE_SLICE,
    ast.Del: ops.DELETE_SLICE
})


class __extend__(ast.GeneratorExp):

    def build_container(self, codegen):
        pass

    def get_generators(self):
        return self.generators

    def accept_comp_iteration(self, codegen, index):
        self.elt.walkabout(codegen)
        codegen.emit_op(ops.YIELD_VALUE)
        codegen.emit_op(ops.POP_TOP)


class __extend__(ast.SetComp):

    def build_container(self, codegen):
        codegen.emit_op_arg(ops.BUILD_SET, 0)

    def get_generators(self):
        return self.generators

    def accept_comp_iteration(self, codegen, index):
        self.elt.walkabout(codegen)
        codegen.emit_op_arg(ops.SET_ADD, index + 1)


class __extend__(ast.DictComp):

    def build_container(self, codegen):
        codegen.emit_op_arg(ops.BUILD_MAP, 0)

    def get_generators(self):
        return self.generators

    def accept_comp_iteration(self, codegen, index):
        self.value.walkabout(codegen)
        self.key.walkabout(codegen)
        codegen.emit_op_arg(ops.MAP_ADD, index + 1)


# These are frame blocks.
F_BLOCK_LOOP = 0
F_BLOCK_EXCEPT = 1
F_BLOCK_FINALLY = 2
F_BLOCK_FINALLY_END = 3


class PythonCodeGenerator(assemble.PythonCodeMaker):
    """Base code generator.

    A subclass of this is created for every scope to be compiled.  It walks
    across the AST tree generating bytecode as needed.
    """

    def __init__(self, space, name, tree, lineno, symbols, compile_info):
        self.scope = symbols.find_scope(tree)
        assemble.PythonCodeMaker.__init__(self, space, name, lineno,
                                          self.scope, compile_info)
        self.symbols = symbols
        self.frame_blocks = []
        self.interactive = False
        self.temporary_name_counter = 1
        self._compile(tree)

    def _compile(self, tree):
        """Override in subclasses to compile a scope."""
        raise NotImplementedError

    def current_temporary_name(self):
        """Return the name of the current temporary variable.

        This must be in sync with the one during symbol table building.
        """
        name = "_[%d]" % (self.temporary_name_counter,)
        self.temporary_name_counter += 1
        assert self.scope.lookup(name) != symtable.SCOPE_UNKNOWN
        return name

    def sub_scope(self, kind, name, node, lineno):
        """Convenience function for compiling a sub scope."""
        generator = kind(self.space, name, node, lineno, self.symbols,
                         self.compile_info)
        return generator.assemble()

    def push_frame_block(self, kind, block):
        self.frame_blocks.append((kind, block))

    def pop_frame_block(self, kind, block):
        actual_kind, old_block = self.frame_blocks.pop()
        assert actual_kind == kind and old_block is block, \
            "mismatched frame blocks"

    def error(self, msg, node):
        raise SyntaxError(msg, node.lineno, node.col_offset,
                          filename=self.compile_info.filename)

    def name_op(self, identifier, ctx):
        """Generate an operation appropiate for the scope of the identifier."""
        scope = self.scope.lookup(identifier)
        op = ops.NOP
        container = self.names
        if scope == symtable.SCOPE_LOCAL:
            if self.scope.can_be_optimized:
                container = self.var_names
                op = name_ops_fast(ctx)
        elif scope == symtable.SCOPE_FREE:
            op = name_ops_deref(ctx)
            container = self.free_vars
        elif scope == symtable.SCOPE_CELL:
            try:
                op = name_ops_deref(ctx)
            except KeyError:
                assert ctx == ast.Del
                raise SyntaxError("Can't delete variable used in "
                                  "nested scopes: '%s'" % (identifier,))
            container = self.cell_vars
        elif scope == symtable.SCOPE_GLOBAL_IMPLICIT:
            if self.scope.locals_fully_known:
                op = name_ops_global(ctx)
        elif scope == symtable.SCOPE_GLOBAL_EXPLICIT:
            op = name_ops_global(ctx)
        if op == ops.NOP:
            op = name_ops_default(ctx)
        self.emit_op_arg(op, self.add_name(container, identifier))

    def possible_docstring(self, node):
        if isinstance(node, ast.Expr):
            expr_value = node.value
            if isinstance(expr_value, ast.Str):
                return expr_value
        return None

    def _get_code_flags(self):
        # Default for everything but module scopes.
        return consts.CO_NEWLOCALS

    def _handle_body(self, body):
        """Compile a list of statements, handling doc strings if needed."""
        if body:
            start = 0
            doc_expr = self.possible_docstring(body[0])
            if doc_expr is not None:
                start = 1
                doc_expr.walkabout(self)
                self.name_op("__doc__", ast.Store)
                self.scope.doc_removable = True
            for i in range(start, len(body)):
                body[i].walkabout(self)
            return True
        else:
            return False

    def visit_Module(self, mod):
        if not self._handle_body(mod.body):
            self.first_lineno = self.lineno = 1

    def visit_Interactive(self, mod):
        self.interactive = True
        self.visit_sequence(mod.body)

    def visit_Expression(self, mod):
        self.add_none_to_final_return = False
        mod.body.walkabout(self)

    def _make_function(self, code, num_defaults=0):
        """Emit the opcodes to turn a code object into a function."""
        code_index = self.add_const(code)
        if code.co_freevars:
            # Load cell and free vars to pass on.
            for free in code.co_freevars:
                free_scope = self.scope.lookup(free)
                if free_scope == symtable.SCOPE_CELL:
                    index = self.cell_vars[free]
                else:
                    index = self.free_vars[free]
                self.emit_op_arg(ops.LOAD_CLOSURE, index)
            self.emit_op_arg(ops.BUILD_TUPLE, len(code.co_freevars))
            self.emit_op_arg(ops.LOAD_CONST, code_index)
            self.emit_op_arg(ops.MAKE_CLOSURE, num_defaults)
        else:
            self.emit_op_arg(ops.LOAD_CONST, code_index)
            self.emit_op_arg(ops.MAKE_FUNCTION, num_defaults)

    def visit_FunctionDef(self, func):
        self.update_position(func.lineno, True)
        # Load decorators first, but apply them after the function is created.
        self.visit_sequence(func.decorator_list)
        args = func.args
        assert isinstance(args, ast.arguments)
        self.visit_sequence(args.defaults)
        num_defaults = len(args.defaults) if args.defaults is not None else 0
        code = self.sub_scope(FunctionCodeGenerator, func.name, func,
                              func.lineno)
        self._make_function(code, num_defaults)
        # Apply decorators.
        if func.decorator_list:
            for i in range(len(func.decorator_list)):
                self.emit_op_arg(ops.CALL_FUNCTION, 1)
        self.name_op(func.name, ast.Store)

    def visit_Lambda(self, lam):
        self.update_position(lam.lineno)
        args = lam.args
        assert isinstance(args, ast.arguments)
        self.visit_sequence(args.defaults)
        default_count = len(args.defaults) if args.defaults is not None else 0
        code = self.sub_scope(LambdaCodeGenerator, "<lambda>", lam, lam.lineno)
        self._make_function(code, default_count)

    def visit_ClassDef(self, cls):
        self.update_position(cls.lineno, True)
        self.visit_sequence(cls.decorator_list)
        self.load_const(self.space.newtext(cls.name))
        self.visit_sequence(cls.bases)
        bases_count = len(cls.bases) if cls.bases is not None else 0
        self.emit_op_arg(ops.BUILD_TUPLE, bases_count)
        code = self.sub_scope(ClassCodeGenerator, cls.name, cls, cls.lineno)
        self._make_function(code, 0)
        self.emit_op_arg(ops.CALL_FUNCTION, 0)
        self.emit_op(ops.BUILD_CLASS)
        if cls.decorator_list:
            for i in range(len(cls.decorator_list)):
                self.emit_op_arg(ops.CALL_FUNCTION, 1)
        self.name_op(cls.name, ast.Store)

    def _op_for_augassign(self, op):
        if op == ast.Div:
            if self.compile_info.flags & consts.CO_FUTURE_DIVISION:
                return ops.INPLACE_TRUE_DIVIDE
            else:
                return ops.INPLACE_DIVIDE
        return inplace_operations(op)

    def visit_AugAssign(self, assign):
        self.update_position(assign.lineno, True)
        target = assign.target
        if isinstance(target, ast.Attribute):
            attr = ast.Attribute(target.value, target.attr, ast.AugLoad,
                                 target.lineno, target.col_offset)
            attr.walkabout(self)
            assign.value.walkabout(self)
            self.emit_op(self._op_for_augassign(assign.op))
            attr.ctx = ast.AugStore
            attr.walkabout(self)
        elif isinstance(target, ast.Subscript):
            sub = ast.Subscript(target.value, target.slice, ast.AugLoad,
                                target.lineno, target.col_offset)
            sub.walkabout(self)
            assign.value.walkabout(self)
            self.emit_op(self._op_for_augassign(assign.op))
            sub.ctx = ast.AugStore
            sub.walkabout(self)
        elif isinstance(target, ast.Name):
            self.name_op(target.id, ast.Load)
            assign.value.walkabout(self)
            self.emit_op(self._op_for_augassign(assign.op))
            self.name_op(target.id, ast.Store)
        else:
            self.error("illegal expression for augmented assignment", assign)

    def visit_Assert(self, asrt):
        self.update_position(asrt.lineno)
        end = self.new_block()
        self.emit_jump(ops.JUMP_IF_NOT_DEBUG, end)
        asrt.test.accept_jump_if(self, True, end)
        self.emit_op_name(ops.LOAD_GLOBAL, self.names, "AssertionError")
        if asrt.msg:
            asrt.msg.walkabout(self)
            self.emit_op_arg(ops.CALL_FUNCTION, 1)
        self.emit_op_arg(ops.RAISE_VARARGS, 1)
        self.use_next_block(end)

    def _binop(self, op):
        if op == ast.Div:
            if self.compile_info.flags & consts.CO_FUTURE_DIVISION:
                return ops.BINARY_TRUE_DIVIDE
            else:
                return ops.BINARY_DIVIDE
        return binary_operations(op)

    def visit_BinOp(self, binop):
        self.update_position(binop.lineno)
        binop.left.walkabout(self)
        binop.right.walkabout(self)
        self.emit_op(self._binop(binop.op))

    def visit_Return(self, ret):
        self.update_position(ret.lineno, True)
        if ret.value:
            ret.value.walkabout(self)
        else:
            self.load_const(self.space.w_None)
        self.emit_op(ops.RETURN_VALUE)

    def visit_Print(self, pr):
        self.update_position(pr.lineno, True)
        have_dest = bool(pr.dest)
        if have_dest:
            pr.dest.walkabout(self)
        if pr.values:
            for value in pr.values:
                if have_dest:
                    self.emit_op(ops.DUP_TOP)
                    value.walkabout(self)
                    self.emit_op(ops.ROT_TWO)
                    self.emit_op(ops.PRINT_ITEM_TO)
                else:
                    value.walkabout(self)
                    self.emit_op(ops.PRINT_ITEM)
        if pr.nl:
            if have_dest:
                self.emit_op(ops.PRINT_NEWLINE_TO)
            else:
                self.emit_op(ops.PRINT_NEWLINE)
        elif have_dest:
            self.emit_op(ops.POP_TOP)

    def visit_Delete(self, delete):
        self.update_position(delete.lineno, True)
        self.visit_sequence(delete.targets)

    def visit_If(self, if_):
        self.update_position(if_.lineno, True)
        end = self.new_block()
        test_constant = if_.test.as_constant_truth(self.space)
        if test_constant == optimize.CONST_FALSE:
            self.visit_sequence(if_.orelse)
        elif test_constant == optimize.CONST_TRUE:
            self.visit_sequence(if_.body)
        else:
            if if_.orelse:
                otherwise = self.new_block()
            else:
                otherwise = end
            if_.test.accept_jump_if(self, False, otherwise)
            self.visit_sequence(if_.body)
            self.emit_jump(ops.JUMP_FORWARD, end)
            if if_.orelse:
                self.use_next_block(otherwise)
                self.visit_sequence(if_.orelse)
        self.use_next_block(end)

    def visit_Break(self, br):
        self.update_position(br.lineno, True)
        for f_block in self.frame_blocks:
            if f_block[0] == F_BLOCK_LOOP:
                break
        else:
            self.error("'break' outside loop", br)
        self.emit_op(ops.BREAK_LOOP)

    def visit_Continue(self, cont):
        self.update_position(cont.lineno, True)
        if not self.frame_blocks:
            self.error("'continue' not properly in loop", cont)
        current_block, block = self.frame_blocks[-1]
        # Continue cannot be in a finally block.
        if current_block == F_BLOCK_LOOP:
            self.emit_jump(ops.JUMP_ABSOLUTE, block, True)
        elif current_block == F_BLOCK_EXCEPT or \
                current_block == F_BLOCK_FINALLY:
            for i in range(len(self.frame_blocks) - 2, -1, -1):
                f_type, block = self.frame_blocks[i]
                if f_type == F_BLOCK_LOOP:
                    self.emit_jump(ops.CONTINUE_LOOP, block, True)
                    break
                if f_type == F_BLOCK_FINALLY_END:
                    self.error("'continue' not supported inside 'finally' "
                                   "clause", cont)
            else:
                self.error("'continue' not properly in loop", cont)
        elif current_block == F_BLOCK_FINALLY_END:
            self.error("'continue' not supported inside 'finally' clause", cont)

    def visit_For(self, fr):
        self.update_position(fr.lineno, True)
        start = self.new_block()
        cleanup = self.new_block()
        end = self.new_block()
        self.emit_jump(ops.SETUP_LOOP, end)
        self.push_frame_block(F_BLOCK_LOOP, start)
        fr.iter.walkabout(self)
        self.emit_op(ops.GET_ITER)
        self.use_next_block(start)
        # This adds another line, so each for iteration can be traced.
        self.lineno_set = False
        self.emit_jump(ops.FOR_ITER, cleanup)
        fr.target.walkabout(self)
        self.visit_sequence(fr.body)
        self.emit_jump(ops.JUMP_ABSOLUTE, start, True)
        self.use_next_block(cleanup)
        self.emit_op(ops.POP_BLOCK)
        self.pop_frame_block(F_BLOCK_LOOP, start)
        self.visit_sequence(fr.orelse)
        self.use_next_block(end)

    def visit_While(self, wh):
        self.update_position(wh.lineno, True)
        test_constant = wh.test.as_constant_truth(self.space)
        if test_constant == optimize.CONST_FALSE:
            self.visit_sequence(wh.orelse)
        else:
            end = self.new_block()
            anchor = None
            if test_constant == optimize.CONST_NOT_CONST:
                anchor = self.new_block()
            self.emit_jump(ops.SETUP_LOOP, end)
            loop = self.new_block()
            self.push_frame_block(F_BLOCK_LOOP, loop)
            self.use_next_block(loop)
            if test_constant == optimize.CONST_NOT_CONST:
                # Force another lineno to be set for tracing purposes.
                self.lineno_set = False
                wh.test.accept_jump_if(self, False, anchor)
            self.visit_sequence(wh.body)
            self.emit_jump(ops.JUMP_ABSOLUTE, loop, True)
            if test_constant == optimize.CONST_NOT_CONST:
                self.use_next_block(anchor)
            self.emit_op(ops.POP_BLOCK)
            self.pop_frame_block(F_BLOCK_LOOP, loop)
            self.visit_sequence(wh.orelse)
            self.use_next_block(end)

    def visit_TryExcept(self, te):
        self.update_position(te.lineno, True)
        exc = self.new_block()
        otherwise = self.new_block()
        end = self.new_block()
        self.emit_jump(ops.SETUP_EXCEPT, exc)
        body = self.use_next_block()
        self.push_frame_block(F_BLOCK_EXCEPT, body)
        self.visit_sequence(te.body)
        self.emit_op(ops.POP_BLOCK)
        self.pop_frame_block(F_BLOCK_EXCEPT, body)
        self.emit_jump(ops.JUMP_FORWARD, otherwise)
        self.use_next_block(exc)
        for i, handler in enumerate(te.handlers):
            assert isinstance(handler, ast.ExceptHandler)
            self.update_position(handler.lineno, True)
            next_except = self.new_block()
            if handler.type:
                self.emit_op(ops.DUP_TOP)
                handler.type.walkabout(self)
                self.emit_op_arg(ops.COMPARE_OP, 10)
                self.emit_jump(ops.POP_JUMP_IF_FALSE, next_except, True)
            else:
                if i != len(te.handlers) - 1:
                    self.error(
                        "bare 'except:' must be the last except block", handler)
            self.emit_op(ops.POP_TOP)
            if handler.name:
                handler.name.walkabout(self)
            else:
                self.emit_op(ops.POP_TOP)
            self.emit_op(ops.POP_TOP)
            self.visit_sequence(handler.body)
            self.emit_jump(ops.JUMP_FORWARD, end)
            self.use_next_block(next_except)
        self.emit_op(ops.END_FINALLY)   # this END_FINALLY will always re-raise
        self.use_next_block(otherwise)
        self.visit_sequence(te.orelse)
        self.use_next_block(end)

    def visit_TryFinally(self, tf):
        self.update_position(tf.lineno, True)
        end = self.new_block()
        self.emit_jump(ops.SETUP_FINALLY, end)
        body = self.use_next_block()
        self.push_frame_block(F_BLOCK_FINALLY, body)
        self.visit_sequence(tf.body)
        self.emit_op(ops.POP_BLOCK)
        self.pop_frame_block(F_BLOCK_FINALLY, body)
        # Indicates there was no exception.
        self.load_const(self.space.w_None)
        self.use_next_block(end)
        self.push_frame_block(F_BLOCK_FINALLY_END, end)
        self.visit_sequence(tf.finalbody)
        self.emit_op(ops.END_FINALLY)
        self.pop_frame_block(F_BLOCK_FINALLY_END, end)

    def _import_as(self, alias):
        source_name = alias.name
        dot = source_name.find(".")
        if dot > 0:
            while True:
                start = dot + 1
                dot = source_name.find(".", start)
                if dot < 0:
                    end = len(source_name)
                else:
                    end = dot
                attr = source_name[start:end]
                self.emit_op_name(ops.LOAD_ATTR, self.names, attr)
                if dot < 0:
                    break
        self.name_op(alias.asname, ast.Store)

    def visit_Import(self, imp):
        self.update_position(imp.lineno, True)
        for alias in imp.names:
            assert isinstance(alias, ast.alias)
            if self.compile_info.flags & consts.CO_FUTURE_ABSOLUTE_IMPORT:
                level = 0
            else:
                level = -1
            self.load_const(self.space.newint(level))
            self.load_const(self.space.w_None)
            self.emit_op_name(ops.IMPORT_NAME, self.names, alias.name)
            # If there's no asname then we store the root module.  If there is
            # an asname, _import_as stores the last module of the chain into it.
            if alias.asname:
                self._import_as(alias)
            else:
                dot = alias.name.find(".")
                if dot < 0:
                    store_name = alias.name
                else:
                    store_name = alias.name[:dot]
                self.name_op(store_name, ast.Store)

    def visit_ImportFrom(self, imp):
        self.update_position(imp.lineno, True)
        space = self.space
        first = imp.names[0]
        assert isinstance(first, ast.alias)
        star_import = len(imp.names) == 1 and first.name == "*"
        # Various error checking for future imports.
        if imp.module == "__future__":
            last_line, last_offset = self.compile_info.last_future_import
            if imp.lineno > last_line or \
                    imp.lineno == last_line and imp.col_offset > last_offset:
                self.error("__future__ statements must appear at beginning "
                               "of file", imp)
            if star_import:
                self.error("* not valid in __future__ imports", imp)
            compiler = space.createcompiler()
            for alias in imp.names:
                assert isinstance(alias, ast.alias)
                if alias.name not in compiler.future_flags.compiler_features:
                    if alias.name == "braces":
                        self.error("not a chance", imp)
                    self.error("future feature %s is not defined" %
                               (alias.name,), imp)
        if imp.level == 0 and \
                not self.compile_info.flags & consts.CO_FUTURE_ABSOLUTE_IMPORT:
            level = -1
        else:
            level = imp.level
        self.load_const(space.newint(level))
        names_w = [None]*len(imp.names)
        for i in range(len(imp.names)):
            alias = imp.names[i]
            assert isinstance(alias, ast.alias)
            names_w[i] = space.newtext(alias.name)
        self.load_const(space.newtuple(names_w))
        if imp.module:
            mod_name = imp.module
        else:
            # In the case of a relative import.
            mod_name = ""
        self.emit_op_name(ops.IMPORT_NAME, self.names, mod_name)
        if star_import:
            self.emit_op(ops.IMPORT_STAR)
        else:
            for alias in imp.names:
                assert isinstance(alias, ast.alias)
                self.emit_op_name(ops.IMPORT_FROM, self.names, alias.name)
                if alias.asname:
                    store_name = alias.asname
                else:
                    store_name = alias.name
                self.name_op(store_name, ast.Store)
            self.emit_op(ops.POP_TOP)

    def visit_Assign(self, assign):
        self.update_position(assign.lineno, True)
        if self._optimize_unpacking(assign):
            return
        assign.value.walkabout(self)
        duplications = len(assign.targets) - 1
        for i in range(len(assign.targets)):
            if i < duplications:
                self.emit_op(ops.DUP_TOP)
            assign.targets[i].walkabout(self)

    def _optimize_unpacking(self, assign):
        """Try to optimize out BUILD_TUPLE and UNPACK_SEQUENCE opcodes."""
        if len(assign.targets) != 1:
            return False
        targets = assign.targets[0].as_node_list(self.space)
        if targets is None:
            return False
        values = assign.value.as_node_list(self.space)
        if values is None:
            return False
        targets_count = len(targets)
        values_count = len(values)
        if targets_count != values_count:
            return False
        for target in targets:
            if not isinstance(target, ast.Name):
                break
        else:
            self.visit_sequence(values)
            seen_names = {}
            for i in range(targets_count - 1, -1, -1):
                target = targets[i]
                assert isinstance(target, ast.Name)
                if target.id not in seen_names:
                    seen_names[target.id] = True
                    self.name_op(target.id, ast.Store)
                else:
                    self.emit_op(ops.POP_TOP)
            return True
        if values_count > 3:
            return False
        self.visit_sequence(values)
        if values_count == 2:
            self.emit_op(ops.ROT_TWO)
        elif values_count == 3:
            self.emit_op(ops.ROT_THREE)
            self.emit_op(ops.ROT_TWO)
        self.visit_sequence(targets)
        return True

    def visit_With(self, wih):
        self.update_position(wih.lineno, True)
        body_block = self.new_block()
        cleanup = self.new_block()
        wih.context_expr.walkabout(self)
        self.emit_jump(ops.SETUP_WITH, cleanup)
        self.use_next_block(body_block)
        self.push_frame_block(F_BLOCK_FINALLY, body_block)
        if wih.optional_vars:
            wih.optional_vars.walkabout(self)
        else:
            self.emit_op(ops.POP_TOP)
        self.visit_sequence(wih.body)
        self.emit_op(ops.POP_BLOCK)
        self.pop_frame_block(F_BLOCK_FINALLY, body_block)
        self.load_const(self.space.w_None)
        self.use_next_block(cleanup)
        self.push_frame_block(F_BLOCK_FINALLY_END, cleanup)
        self.emit_op(ops.WITH_CLEANUP)
        self.emit_op(ops.END_FINALLY)
        self.pop_frame_block(F_BLOCK_FINALLY_END, cleanup)

    def visit_Raise(self, rais):
        self.update_position(rais.lineno, True)
        arg = 0
        if rais.type:
            rais.type.walkabout(self)
            arg += 1
            if rais.inst:
                rais.inst.walkabout(self)
                arg += 1
                if rais.tback:
                    rais.tback.walkabout(self)
                    arg += 1
        self.emit_op_arg(ops.RAISE_VARARGS, arg)

    def visit_Exec(self, exc):
        self.update_position(exc.lineno, True)
        exc.body.walkabout(self)
        if exc.globals:
            exc.globals.walkabout(self)
            if exc.locals:
                exc.locals.walkabout(self)
            else:
                self.emit_op(ops.DUP_TOP)
        else:
            self.load_const(self.space.w_None)
            self.emit_op(ops.DUP_TOP)
        self.emit_op(ops.EXEC_STMT)

    def visit_Global(self, glob):
        # Handled in symbol table building.
        pass

    def visit_Pass(self, pas):
        self.update_position(pas.lineno, True)

    def visit_Expr(self, expr):
        self.update_position(expr.lineno, True)
        if self.interactive:
            expr.value.walkabout(self)
            self.emit_op(ops.PRINT_EXPR)
        # Only compile if the expression isn't constant.
        elif not expr.value.constant:
            expr.value.walkabout(self)
            self.emit_op(ops.POP_TOP)

    def visit_Yield(self, yie):
        self.update_position(yie.lineno)
        if yie.value:
            yie.value.walkabout(self)
        else:
            self.load_const(self.space.w_None)
        self.emit_op(ops.YIELD_VALUE)

    def visit_Num(self, num):
        self.update_position(num.lineno)
        self.load_const(num.n)

    def visit_Str(self, string):
        self.update_position(string.lineno)
        self.load_const(string.s)

    def visit_Const(self, const):
        self.update_position(const.lineno)
        self.load_const(const.value)

    def visit_UnaryOp(self, op):
        self.update_position(op.lineno)
        op.operand.walkabout(self)
        self.emit_op(unary_operations(op.op))

    def visit_BoolOp(self, op):
        self.update_position(op.lineno)
        if op.op == ast.And:
            instr = ops.JUMP_IF_FALSE_OR_POP
        else:
            instr = ops.JUMP_IF_TRUE_OR_POP
        end = self.new_block()
        for value in op.values[:-1]:
            value.walkabout(self)
            self.emit_jump(instr, end, True)
        op.values[-1].walkabout(self)
        self.use_next_block(end)

    def visit_Compare(self, comp):
        self.update_position(comp.lineno)
        comp.left.walkabout(self)
        ops_count = len(comp.ops)
        cleanup = None
        if ops_count > 1:
            cleanup = self.new_block()
            comp.comparators[0].walkabout(self)
        for i in range(1, ops_count):
            self.emit_op(ops.DUP_TOP)
            self.emit_op(ops.ROT_THREE)
            op_kind = compare_operations(comp.ops[i - 1])
            self.emit_op_arg(ops.COMPARE_OP, op_kind)
            self.emit_jump(ops.JUMP_IF_FALSE_OR_POP, cleanup, True)
            if i < (ops_count - 1):
                comp.comparators[i].walkabout(self)
        last_op, last_comparator = comp.ops[-1], comp.comparators[-1]
        if not self._optimize_comparator(last_op, last_comparator):
            last_comparator.walkabout(self)
        self.emit_op_arg(ops.COMPARE_OP, compare_operations(last_op))
        if ops_count > 1:
            end = self.new_block()
            self.emit_jump(ops.JUMP_FORWARD, end)
            self.use_next_block(cleanup)
            self.emit_op(ops.ROT_TWO)
            self.emit_op(ops.POP_TOP)
            self.use_next_block(end)

    def _optimize_comparator(self, op, node):
        """Fold lists/sets of constants in the context of "in"/"not in".

        lists are folded into tuples, sets into frozensets, otherwise
        returns False
        """
        if op in (ast.In, ast.NotIn):
            is_list = isinstance(node, ast.List)
            if is_list or isinstance(node, ast.Set):
                w_const = self._tuple_of_consts(node.elts)
                if w_const is not None:
                    if not is_list:
                        from pypy.objspace.std.setobject import (
                            W_FrozensetObject)
                        w_const = W_FrozensetObject(self.space, w_const)
                    self.load_const(w_const)
                    return True
        return False

    def _tuple_of_consts(self, elts):
        """Return a tuple of consts from elts if possible, or None"""
        count = len(elts) if elts is not None else 0
        consts_w = [None] * count
        for i in range(count):
            w_value = elts[i].as_constant()
            if w_value is None:
                # Not all constants
                return None
            consts_w[i] = w_value
        return self.space.newtuple(consts_w)

    def visit_IfExp(self, ifexp):
        self.update_position(ifexp.lineno)
        end = self.new_block()
        otherwise = self.new_block()
        ifexp.test.accept_jump_if(self, False, otherwise)
        ifexp.body.walkabout(self)
        self.emit_jump(ops.JUMP_FORWARD, end)
        self.use_next_block(otherwise)
        ifexp.orelse.walkabout(self)
        self.use_next_block(end)

    def visit_Tuple(self, tup):
        self.update_position(tup.lineno)
        elt_count = len(tup.elts) if tup.elts is not None else 0
        if tup.ctx == ast.Store:
            self.emit_op_arg(ops.UNPACK_SEQUENCE, elt_count)
        if tup.ctx == ast.Load and elt_count > MAX_STACKDEPTH_CONTAINERS:
            # we need a complete hack to build a new tuple from the list
            # ().__class__(l)
            empty_index = self.add_const(self.space.newtuple([]))
            self.emit_op_arg(ops.LOAD_CONST, empty_index)
            self.emit_op_name(ops.LOAD_ATTR, self.names, '__class__')

            self.emit_op_arg(ops.BUILD_LIST, 0)
            for element in tup.elts:
                element.walkabout(self)
                self.emit_op_arg(ops.LIST_APPEND, 1)

            self.emit_op_arg(ops.CALL_FUNCTION, 1)
            return
        self.visit_sequence(tup.elts)
        if tup.ctx == ast.Load:
            self.emit_op_arg(ops.BUILD_TUPLE, elt_count)

    def visit_List(self, l):
        self.update_position(l.lineno)
        elt_count = len(l.elts) if l.elts is not None else 0
        if l.ctx == ast.Store:
            self.emit_op_arg(ops.UNPACK_SEQUENCE, elt_count)
        if elt_count > MAX_STACKDEPTH_CONTAINERS and l.ctx == ast.Load:
            # pushing all the elements would make the stack depth gigantic.
            # build the list incrementally instead
            self.emit_op_arg(ops.BUILD_LIST, 0)
            for element in l.elts:
                element.walkabout(self)
                self.emit_op_arg(ops.LIST_APPEND, 1)
        else:
            self.visit_sequence(l.elts)
            if l.ctx == ast.Load:
                self.emit_op_arg(ops.BUILD_LIST, elt_count)

    def visit_Dict(self, d):
        self.update_position(d.lineno)
        self.emit_op_arg(ops.BUILD_MAP, 0)
        if d.values:
            for i in range(len(d.values)):
                d.values[i].walkabout(self)
                d.keys[i].walkabout(self)
                self.emit_op(ops.STORE_MAP)

    def visit_Set(self, s):
        self.update_position(s.lineno)
        elt_count = len(s.elts) if s.elts is not None else 0
        if elt_count > MAX_STACKDEPTH_CONTAINERS:
            self.emit_op_arg(ops.BUILD_SET, 0)
            for element in s.elts:
                element.walkabout(self)
                self.emit_op_arg(ops.SET_ADD, 1)
        else:
            self.visit_sequence(s.elts)
            self.emit_op_arg(ops.BUILD_SET, elt_count)


    def visit_Name(self, name):
        self.update_position(name.lineno)
        self.name_op(name.id, name.ctx)

    def visit_keyword(self, keyword):
        self.load_const(self.space.newtext(keyword.arg))
        keyword.value.walkabout(self)

    def visit_Call(self, call):
        self.update_position(call.lineno)
        if self._optimize_method_call(call):
            return
        call.func.walkabout(self)
        arg = len(call.args) if call.args is not None else 0
        call_type = 0
        self.visit_sequence(call.args)
        if call.keywords:
            self.visit_sequence(call.keywords)
            arg |= len(call.keywords) << 8
        if call.starargs:
            call.starargs.walkabout(self)
            call_type |= 1
        if call.kwargs:
            call.kwargs.walkabout(self)
            call_type |= 2
        op = 0
        if call_type == 0:
            op = ops.CALL_FUNCTION
        elif call_type == 1:
            op = ops.CALL_FUNCTION_VAR
        elif call_type == 2:
            op = ops.CALL_FUNCTION_KW
        elif call_type == 3:
            op = ops.CALL_FUNCTION_VAR_KW
        self.emit_op_arg(op, arg)

    def _call_has_no_star_args(self, call):
        return not call.starargs and not call.kwargs

    def _call_has_simple_args(self, call):
        return self._call_has_no_star_args(call) and not call.keywords

    def _optimize_method_call(self, call):
        if not self._call_has_no_star_args(call) or \
           not isinstance(call.func, ast.Attribute):
            return False
        attr_lookup = call.func
        assert isinstance(attr_lookup, ast.Attribute)
        attr_lookup.value.walkabout(self)
        self.emit_op_name(ops.LOOKUP_METHOD, self.names, attr_lookup.attr)
        self.visit_sequence(call.args)
        arg_count = len(call.args) if call.args is not None else 0
        self.visit_sequence(call.keywords)
        kwarg_count = len(call.keywords) if call.keywords is not None else 0
        self.emit_op_arg(ops.CALL_METHOD, (kwarg_count << 8) | arg_count)
        return True

    def _listcomp_generator(self, gens, gen_index, elt, single=False):
        start = self.new_block()
        skip = self.new_block()
        if_cleanup = self.new_block()
        anchor = self.new_block()
        gen = gens[gen_index]
        assert isinstance(gen, ast.comprehension)
        gen.iter.walkabout(self)
        if single:
            self.emit_op_arg(ops.BUILD_LIST_FROM_ARG, 0)
        self.emit_op(ops.GET_ITER)
        self.use_next_block(start)
        self.emit_jump(ops.FOR_ITER, anchor)
        self.use_next_block()
        gen.target.walkabout(self)
        if gen.ifs:
            for if_ in gen.ifs:
                if_.accept_jump_if(self, False, if_cleanup)
                self.use_next_block()
        gen_index += 1
        if gen_index < len(gens):
            self._listcomp_generator(gens, gen_index, elt)
        else:
            elt.walkabout(self)
            self.emit_op_arg(ops.LIST_APPEND, gen_index + 1)
            self.use_next_block(skip)
        self.use_next_block(if_cleanup)
        self.emit_jump(ops.JUMP_ABSOLUTE, start, True)
        self.use_next_block(anchor)

    def visit_ListComp(self, lc):
        self.update_position(lc.lineno)
        if len(lc.generators) == 1:
            comp = lc.generators[0]
            assert isinstance(comp, ast.comprehension)
            if comp.ifs:
                single = False
                self.emit_op_arg(ops.BUILD_LIST, 0)
            else:
                single = True
        else:
            single = False
            self.emit_op_arg(ops.BUILD_LIST, 0)
        self._listcomp_generator(lc.generators, 0, lc.elt, single=single)

    def _comp_generator(self, node, generators, gen_index):
        start = self.new_block()
        if_cleanup = self.new_block()
        anchor = self.new_block()
        gen = generators[gen_index]
        assert isinstance(gen, ast.comprehension)
        if gen_index == 0:
            self.argcount = 1
            self.emit_op_arg(ops.LOAD_FAST, 0)
        else:
            gen.iter.walkabout(self)
            self.emit_op(ops.GET_ITER)
        self.use_next_block(start)
        self.emit_jump(ops.FOR_ITER, anchor)
        self.use_next_block()
        gen.target.walkabout(self)
        if gen.ifs:
            for if_ in gen.ifs:
                if_.accept_jump_if(self, False, if_cleanup)
                self.use_next_block()
        gen_index += 1
        if gen_index < len(generators):
            self._comp_generator(node, generators, gen_index)
        else:
            node.accept_comp_iteration(self, gen_index)
        self.use_next_block(if_cleanup)
        self.emit_jump(ops.JUMP_ABSOLUTE, start, True)
        self.use_next_block(anchor)

    def _compile_comprehension(self, node, name, sub_scope):
        code = self.sub_scope(sub_scope, name, node, node.lineno)
        self.update_position(node.lineno)
        self._make_function(code)
        first_comp = node.get_generators()[0]
        assert isinstance(first_comp, ast.comprehension)
        first_comp.iter.walkabout(self)
        self.emit_op(ops.GET_ITER)
        self.emit_op_arg(ops.CALL_FUNCTION, 1)

    def visit_GeneratorExp(self, genexp):
        self._compile_comprehension(genexp, "<genexpr>", GenExpCodeGenerator)

    def visit_SetComp(self, setcomp):
        self._compile_comprehension(setcomp, "<setcomp>",
                                    ComprehensionCodeGenerator)

    def visit_DictComp(self, dictcomp):
        self._compile_comprehension(dictcomp, "<dictcomp>",
                                    ComprehensionCodeGenerator)

    def visit_Repr(self, rep):
        self.update_position(rep.lineno)
        rep.value.walkabout(self)
        self.emit_op(ops.UNARY_CONVERT)

    def visit_Attribute(self, attr):
        self.update_position(attr.lineno)
        names = self.names
        ctx = attr.ctx
        if ctx != ast.AugStore:
            attr.value.walkabout(self)
        if ctx == ast.AugLoad:
            self.emit_op(ops.DUP_TOP)
            self.emit_op_name(ops.LOAD_ATTR, names, attr.attr)
        elif ctx == ast.Load:
            self.emit_op_name(ops.LOAD_ATTR, names, attr.attr)
        elif ctx == ast.AugStore:
            self.emit_op(ops.ROT_TWO)
            self.emit_op_name(ops.STORE_ATTR, names, attr.attr)
        elif ctx == ast.Store:
            self.emit_op_name(ops.STORE_ATTR, names, attr.attr)
        elif ctx == ast.Del:
            self.emit_op_name(ops.DELETE_ATTR, names, attr.attr)
        else:
            raise AssertionError("unknown context")

    def _simple_slice(self, slc, ctx):
        slice_offset = 0
        stack_count = 0
        if slc.lower:
            slice_offset += 1
            stack_count += 1
            if ctx != ast.AugStore:
                slc.lower.walkabout(self)
        if slc.upper:
            slice_offset += 2
            stack_count += 1
            if ctx != ast.AugStore:
                slc.upper.walkabout(self)
        if ctx == ast.AugLoad:
            if stack_count == 0:
                self.emit_op(ops.DUP_TOP)
            elif stack_count == 1:
                self.emit_op_arg(ops.DUP_TOPX, 2)
            elif stack_count == 2:
                self.emit_op_arg(ops.DUP_TOPX, 3)
        elif ctx == ast.AugStore:
            if stack_count == 0:
                self.emit_op(ops.ROT_TWO)
            elif stack_count == 1:
                self.emit_op(ops.ROT_THREE)
            elif stack_count == 2:
                self.emit_op(ops.ROT_FOUR)
        self.emit_op(slice_operations(ctx) + slice_offset)

    def _complex_slice(self, slc, ctx):
        if slc.lower:
            slc.lower.walkabout(self)
        else:
            self.load_const(self.space.w_None)
        if slc.upper:
            slc.upper.walkabout(self)
        else:
            self.load_const(self.space.w_None)
        arg = 2
        if slc.step:
            slc.step.walkabout(self)
            arg += 1
        self.emit_op_arg(ops.BUILD_SLICE, arg)

    def _nested_slice(self, slc, ctx):
        if isinstance(slc, ast.Ellipsis):
            self.load_const(self.space.w_Ellipsis)
        elif isinstance(slc, ast.Slice):
            self._complex_slice(slc, ctx)
        elif isinstance(slc, ast.Index):
            slc.value.walkabout(self)
        else:
            raise AssertionError("unknown nested slice type")

    def _compile_slice(self, slc, ctx):
        if isinstance(slc, ast.Index):
            if ctx != ast.AugStore:
                slc.value.walkabout(self)
        elif isinstance(slc, ast.Ellipsis):
            if ctx != ast.AugStore:
                self.load_const(self.space.w_Ellipsis)
        elif isinstance(slc, ast.Slice):
            if not slc.step:
                self._simple_slice(slc, ctx)
                return
            elif ctx != ast.AugStore:
                self._complex_slice(slc, ctx)
        elif isinstance(slc, ast.ExtSlice):
            if ctx != ast.AugStore:
                for dim in slc.dims:
                    self._nested_slice(dim, ctx)
                self.emit_op_arg(ops.BUILD_TUPLE, len(slc.dims))
        else:
            raise AssertionError("unknown slice type")
        if ctx == ast.AugLoad:
            self.emit_op_arg(ops.DUP_TOPX, 2)
        elif ctx == ast.AugStore:
            self.emit_op(ops.ROT_THREE)
        self.emit_op(subscr_operations(ctx))

    def visit_Subscript(self, sub):
        self.update_position(sub.lineno)
        if sub.ctx != ast.AugStore:
            sub.value.walkabout(self)
        self._compile_slice(sub.slice, sub.ctx)

    def _revdb_metavar(self, node):
        # moved in its own function for the import statement
        from pypy.interpreter.reverse_debugging import dbstate
        if not dbstate.standard_code:
            self.emit_op_arg(ops.LOAD_REVDB_VAR, node.metavar)
            return True
        return False

    def visit_RevDBMetaVar(self, node):
        if self.space.reverse_debugging and self._revdb_metavar(node):
            return
        self.error("Unknown character ('$NUM' is only valid in the "
                   "reverse-debugger)", node)


class TopLevelCodeGenerator(PythonCodeGenerator):

    def __init__(self, space, tree, symbols, compile_info):
        PythonCodeGenerator.__init__(self, space, "<module>", tree, -1,
                                     symbols, compile_info)

    def _compile(self, tree):
        tree.walkabout(self)

    def _get_code_flags(self):
        flags = 0
        if self.scope.doc_removable:
            flags |= consts.CO_KILL_DOCSTRING
        return flags


class AbstractFunctionCodeGenerator(PythonCodeGenerator):

    def _handle_nested_args(self, args):
        for i in range(len(args)):
            arg = args[i]
            if isinstance(arg, ast.Tuple):
                self.update_position(arg.lineno)
                self.name_op(".%d" % (i,), ast.Load)
                arg.walkabout(self)

    def _get_code_flags(self):
        scope = self.scope
        assert isinstance(scope, symtable.FunctionScope)
        flags = 0
        if scope.locals_fully_known:
            flags |= consts.CO_OPTIMIZED
        if scope.nested:
            flags |= consts.CO_NESTED
        if scope.is_generator:
            flags |= consts.CO_GENERATOR
        if scope.has_yield_inside_try:
            flags |= consts.CO_YIELD_INSIDE_TRY
        if scope.has_variable_arg:
            flags |= consts.CO_VARARGS
        if scope.has_keywords_arg:
            flags |= consts.CO_VARKEYWORDS
        if scope.doc_removable:
            flags |= consts.CO_KILL_DOCSTRING
        if not self.cell_vars and not self.free_vars:
            flags |= consts.CO_NOFREE
        return PythonCodeGenerator._get_code_flags(self) | flags


class FunctionCodeGenerator(AbstractFunctionCodeGenerator):

    def _compile(self, func):
        assert isinstance(func, ast.FunctionDef)
        # If there's a docstring, store it as the first constant.
        if func.body:
            doc_expr = self.possible_docstring(func.body[0])
        else:
            doc_expr = None
        if doc_expr is not None:
            self.add_const(doc_expr.s)
            self.scope.doc_removable = True
            start = 1
        else:
            self.add_const(self.space.w_None)
            start = 0
        args = func.args
        assert isinstance(args, ast.arguments)
        if args.args:
            self._handle_nested_args(args.args)
            self.argcount = len(args.args)
        if func.body:
            for i in range(start, len(func.body)):
                func.body[i].walkabout(self)


class LambdaCodeGenerator(AbstractFunctionCodeGenerator):

    def _compile(self, lam):
        assert isinstance(lam, ast.Lambda)
        args = lam.args
        assert isinstance(args, ast.arguments)
        if args.args:
            self._handle_nested_args(args.args)
            self.argcount = len(args.args)
        # Prevent a string from being the first constant and thus a docstring.
        self.add_const(self.space.w_None)
        lam.body.walkabout(self)
        self.emit_op(ops.RETURN_VALUE)


class ComprehensionCodeGenerator(AbstractFunctionCodeGenerator):

    def _compile(self, node):
        assert isinstance(node, ast.expr)
        self.update_position(node.lineno)
        node.build_container(self)
        self._comp_generator(node, node.get_generators(), 0)
        self._end_comp()

    def _end_comp(self):
        self.emit_op(ops.RETURN_VALUE)


class GenExpCodeGenerator(ComprehensionCodeGenerator):

    def _end_comp(self):
        pass

    def _get_code_flags(self):
        flags = ComprehensionCodeGenerator._get_code_flags(self)
        return flags | consts.CO_GENERATOR


class ClassCodeGenerator(PythonCodeGenerator):

    def _compile(self, cls):
        assert isinstance(cls, ast.ClassDef)
        self.lineno = self.first_lineno
        self.name_op("__name__", ast.Load)
        self.name_op("__module__", ast.Store)
        self._handle_body(cls.body)
        self.emit_op(ops.LOAD_LOCALS)
        self.emit_op(ops.RETURN_VALUE)

    def _get_code_flags(self):
        flags = 0
        if self.scope.doc_removable:
            flags |= consts.CO_KILL_DOCSTRING
        return PythonCodeGenerator._get_code_flags(self) | flags
