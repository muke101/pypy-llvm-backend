from pytest import raises
import sys

def test_simple():
    co = compile('1+2', '?', 'eval')
    assert eval(co) == 3
    co = compile(buffer('1+2'), '?', 'eval')
    assert eval(co) == 3
    exc = raises(TypeError, compile, chr(0), '?', 'eval')
    assert str(exc.value) == "compile() expected string without null bytes"
    exc = raises(TypeError, compile, unichr(0), '?', 'eval')
    assert str(exc.value) == "compile() expected string without null bytes"

    if '__pypy__' in sys.modules:
        co = compile(memoryview('1+2'), '?', 'eval')
        assert eval(co) == 3
    compile("from __future__ import with_statement", "<test>", "exec")
    raises(SyntaxError, compile, '-', '?', 'eval')
    raises(ValueError, compile, '"\\xt"', '?', 'eval')
    raises(ValueError, compile, '1+2', '?', 'maybenot')
    raises(ValueError, compile, "\n", "<string>", "exec", 0xff)
    raises(TypeError, compile, '1+2', 12, 34)

def test_error_message():
    import re
    compile('# -*- coding: iso-8859-15 -*-\n', 'dummy', 'exec')
    compile(b'\xef\xbb\xbf\n', 'dummy', 'exec')
    compile(b'\xef\xbb\xbf# -*- coding: utf-8 -*-\n', 'dummy', 'exec')
    exc = raises(SyntaxError, compile,
        b'# -*- coding: fake -*-\n', 'dummy', 'exec')
    assert 'fake' in str(exc.value)
    exc = raises(SyntaxError, compile,
        b'\xef\xbb\xbf# -*- coding: iso-8859-15 -*-\n', 'dummy', 'exec')
    assert 'iso-8859-15' in str(exc.value)
    assert 'BOM' in str(exc.value)
    exc = raises(SyntaxError, compile,
        b'\xef\xbb\xbf# -*- coding: fake -*-\n', 'dummy', 'exec')
    assert 'fake' in str(exc.value)
    assert 'BOM' in str(exc.value)

def test_unicode():
    try:
        compile(u'-', '?', 'eval')
    except SyntaxError as e:
        assert e.lineno == 1

def test_unicode_encoding():
    code = u"# -*- coding: utf-8 -*-\npass\n"
    raises(SyntaxError, compile, code, "tmp", "exec")

def test_recompile_ast():
    import _ast
    # raise exception when node type doesn't match with compile mode
    co1 = compile('print 1', '<string>', 'exec', _ast.PyCF_ONLY_AST)
    raises(TypeError, compile, co1, '<ast>', 'eval')
    co2 = compile('1+1', '<string>', 'eval', _ast.PyCF_ONLY_AST)
    tree = compile(co2, '<ast>', 'eval')
    assert compile(co2, '<ast>', 'eval', _ast.PyCF_ONLY_AST) is co2

def test_leading_newlines():
    src = """
def fn(): pass
"""
    co = compile(src, 'mymod', 'exec')
    firstlineno = co.co_firstlineno
    assert firstlineno == 2

def test_null_bytes():
    raises(TypeError, compile, '\x00', 'mymod', 'exec', 0)
    src = "#abc\x00def\n"
    raises(TypeError, compile, src, 'mymod', 'exec')
    raises(TypeError, compile, src, 'mymod', 'exec', 0)

def test_null_bytes_flag():
    try:
        from _ast import PyCF_ACCEPT_NULL_BYTES
    except ImportError:
        skip('PyPy only (requires _ast.PyCF_ACCEPT_NULL_BYTES)')
    raises(SyntaxError, compile, '\x00', 'mymod', 'exec',
            PyCF_ACCEPT_NULL_BYTES)
    src = "#abc\x00def\n"
    compile(src, 'mymod', 'exec', PyCF_ACCEPT_NULL_BYTES)  # works
