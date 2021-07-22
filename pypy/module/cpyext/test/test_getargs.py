
from pypy.module.cpyext.test.test_api import BaseApiTest
from pypy.module.cpyext.test.test_cpyext import AppTestCpythonExtensionBase

class AppTestGetargs(AppTestCpythonExtensionBase):
    def w_import_parser(self, implementation, argstyle='METH_VARARGS',
                        PY_SSIZE_T_CLEAN=False):
        mod = self.import_extension(
            'modname', [('funcname', argstyle, implementation)],
            PY_SSIZE_T_CLEAN=PY_SSIZE_T_CLEAN)
        return mod.funcname

    def test_pyarg_parse_int(self):
        """
        The `i` format specifier can be used to parse an integer.
        """
        oneargint = self.import_parser(
            '''
            int l;
            if (!PyArg_ParseTuple(args, "i", &l)) {
                return NULL;
            }
            return PyInt_FromLong(l);
            ''')
        assert oneargint(1) == 1
        raises(TypeError, oneargint, None)
        raises(TypeError, oneargint)


    def test_pyarg_parse_fromname(self):
        """
        The name of the function parsing the arguments can be given after a `:`
        in the argument format string.
        """
        oneargandform = self.import_parser(
            '''
            int l;
            if (!PyArg_ParseTuple(args, "i:oneargandstuff", &l)) {
                return NULL;
            }
            return PyInt_FromLong(l);
            ''')
        assert oneargandform(1) == 1


    def test_pyarg_parse_object(self):
        """
        The `O` format specifier can be used to parse an arbitrary object.
        """
        oneargobject = self.import_parser(
            '''
            PyObject *obj;
            if (!PyArg_ParseTuple(args, "O", &obj)) {
                return NULL;
            }
            Py_INCREF(obj);
            return obj;
            ''')
        sentinel = object()
        res = oneargobject(sentinel)
        assert res is sentinel

    def test_pyarg_parse_restricted_object_type(self):
        """
        The `O!` format specifier can be used to parse an object of a particular
        type.
        """
        oneargobjectandlisttype = self.import_parser(
            '''
            PyObject *obj;
            if (!PyArg_ParseTuple(args, "O!", &PyList_Type, &obj)) {
                return NULL;
            }
            Py_INCREF(obj);
            return obj;
            ''')
        sentinel = object()
        raises(TypeError, "oneargobjectandlisttype(sentinel)")
        sentinel = []
        res = oneargobjectandlisttype(sentinel)
        assert res is sentinel


    def test_pyarg_parse_one_optional(self):
        """
        An object corresponding to a format specifier after a `|` in the
        argument format string is optional and may be passed or not.
        """
        twoopt = self.import_parser(
            '''
            PyObject *a;
            PyObject *b = NULL;
            if (!PyArg_ParseTuple(args, "O|O", &a, &b)) {
                return NULL;
            }
            if (b)
                Py_INCREF(b);
            else
                b = PyInt_FromLong(42);
            /* return an owned reference */
            return b;
            ''')
        assert twoopt(1) == 42
        assert twoopt(1, 2) == 2
        raises(TypeError, twoopt, 1, 2, 3)


    def test_pyarg_parse_string_py_buffer(self):
        """
        The `s*` format specifier can be used to parse a str into a Py_buffer
        structure containing a pointer to the string data and the length of the
        string data.
        """
        pybuffer = self.import_parser(
            '''
            Py_buffer buf;
            PyObject *result;
            if (!PyArg_ParseTuple(args, "s*", &buf)) {
                return NULL;
            }
            result = PyString_FromStringAndSize(buf.buf, buf.len);
            PyBuffer_Release(&buf);
            return result;
            ''')
        assert 'foo\0bar\0baz' == pybuffer('foo\0bar\0baz')
        assert 'foo\0bar\0baz' == pybuffer(bytearray('foo\0bar\0baz'))


    def test_pyarg_parse_string_old_buffer(self):
        pybuffer = self.import_parser(
            '''
            Py_buffer buf;
            PyObject *result;
            if (!PyArg_ParseTuple(args, "s*", &buf)) {
                return NULL;
            }
            result = PyString_FromStringAndSize(buf.buf, buf.len);
            PyBuffer_Release(&buf);
            return result;
            ''')
        assert 'foo\0bar\0baz' == pybuffer(buffer('foo\0bar\0baz'))

    def test_pyarg_parse_string_fails(self):
        """
        Test the failing case of PyArg_ParseTuple(): it must not keep
        a reference on the PyObject passed in.
        """
        pybuffer = self.import_parser(
            '''
            Py_buffer buf1, buf2, buf3;
            if (!PyArg_ParseTuple(args, "s*s*s*", &buf1, &buf2, &buf3)) {
                return NULL;
            }
            Py_FatalError("should not get there");
            return NULL;
            ''')
        freed = []
        class freestring(str):
            def __del__(self):
                freed.append('x')
        raises(TypeError, pybuffer,
               freestring("string"), freestring("other string"), 42)
        self.debug_collect()    # gc.collect() is not enough in this test:
                                # we need to check and free the PyObject
                                # linked to the freestring object as well
        assert freed == ['x', 'x']


    def test_pyarg_parse_charbuf_and_length(self):
        """
        The `t#` format specifier can be used to parse a read-only 8-bit
        character buffer into a char* and int giving its length in bytes.
        """
        charbuf = self.import_parser(
            '''
            char *buf;
            int len;
            if (!PyArg_ParseTuple(args, "t#", &buf, &len)) {
                return NULL;
            }
            return PyString_FromStringAndSize(buf, len);
            ''')
        raises(TypeError, "charbuf(10)")
        assert 'foo\0bar\0baz' == charbuf('foo\0bar\0baz')

    def test_pyarg_parse_without_py_ssize_t(self):
        import sys
        charbuf = self.import_parser(
            '''
            char *buf;
            Py_ssize_t y = -1;
            if (!PyArg_ParseTuple(args, "s#", &buf, &y)) {
                return NULL;
            }
            return PyInt_FromSsize_t(y);
            ''')
        if sys.maxsize < 2**32:
            expected = 5
        elif sys.byteorder == 'little':
            expected = -0xfffffffb
        else:
            expected = 0x5ffffffff
        assert charbuf('12345') == expected

    def test_pyarg_parse_with_py_ssize_t(self):
        charbuf = self.import_parser(
            '''
            char *buf;
            Py_ssize_t y = -1;
            if (!PyArg_ParseTuple(args, "s#", &buf, &y)) {
                return NULL;
            }
            return PyInt_FromSsize_t(y);
            ''', PY_SSIZE_T_CLEAN=True)
        assert charbuf('12345') == 5
