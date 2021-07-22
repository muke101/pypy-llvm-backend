import py
from pypy.module.pypyjit.test_pypy_c.test_00_model import BaseTestPyPyC

class TestInstance(BaseTestPyPyC):

    def test_virtual_instance(self):
        def main(n):
            class A(object):
                pass
            #
            i = 0
            while i < n:
                a = A()
                assert isinstance(a, A)
                assert not isinstance(a, int)
                a.x = 2
                i = i + a.x
            return i
        #
        log = self.run(main, [1000], threshold = 400)
        assert log.result == 1000
        loop, = log.loops_by_filename(self.filepath)
        assert loop.match("""
            i7 = int_lt(i5, i6)
            guard_true(i7, descr=...)
            guard_not_invalidated(descr=...)
            i9 = int_add_ovf(i5, 2)
            guard_no_overflow(descr=...)
            --TICK--
            jump(..., descr=...)
        """)

    def test_load_attr(self):
        src = '''
            class A(object):
                pass
            a = A()
            a.x = 1
            def main(n):
                i = 0
                while i < n:
                    i = i + a.x
                return i
        '''
        log = self.run(src, [1000])
        assert log.result == 1000
        loop, = log.loops_by_filename(self.filepath)
        assert loop.match("""
            i9 = int_lt(i5, i6)
            guard_true(i9, descr=...)
            guard_not_invalidated(descr=...)
            i10 = int_add(i5, 1)
            --TICK--
            jump(..., descr=...)
        """)

    def test_getattr_with_dynamic_attribute(self):
        src = """
        class A(object):
            pass

        l = ["x", "y"]

        def main():
            sum = 0
            a = A()
            a.a1 = 0
            a.a2 = 0
            a.a3 = 0
            a.a4 = 0
            a.a5 = 0 # workaround, because the first five attributes need a promotion
            a.x = 1
            a.y = 2
            i = 0
            while i < 500:
                name = l[i % 2]
                sum += getattr(a, name)
                i += 1
            return sum
        """
        log = self.run(src, [])
        assert log.result == 250 + 250*2
        loops = log.loops_by_filename(self.filepath)
        assert len(loops) == 1

    def test_mutate_class_int(self):
        def fn(n):
            class A(object):
                count = 1
                def __init__(self, a):
                    self.a = a
                def f(self):
                    return self.count
            i = 0
            a = A(1)
            while i < n:
                A.count += 1 # ID: mutate
                i = a.f()    # ID: meth1
            return i
        #
        log = self.run(fn, [1000], threshold=10)
        assert log.result == 1000
        #
        # first, we test the entry bridge
        # -------------------------------
        entry_bridge, = log.loops_by_filename(self.filepath, is_entry_bridge=True)
        ops = entry_bridge.ops_by_id('mutate', opcode='LOAD_ATTR')
        assert log.opnames(ops) == ['guard_value', 'guard_not_invalidated',
                                    'getfield_gc_i']
        # the STORE_ATTR is folded away
        assert list(entry_bridge.ops_by_id('meth1', opcode='STORE_ATTR')) == []
        #
        # then, the actual loop
        # ----------------------
        loop, = log.loops_by_filename(self.filepath)
        assert loop.match("""
            i58 = int_lt(i38, i31)
            guard_true(i58, descr=...)
            guard_not_invalidated(descr=...)
            i59 = int_add_ovf(i57, 1)
            guard_no_overflow(descr=...)
            p60 = force_token()
            i61 = getfield_raw_i(..., descr=...)
            setfield_gc(ConstPtr(ptr39), i59, descr=...)
            i62 = int_lt(i61, 0)
            guard_false(i62, descr=...)
            jump(..., descr=...)
        """)

    def test_mutate_class(self):
        def fn(n):
            class LL(object):
                def __init__(self, n):
                    self.n = n
            class A(object):
                count = None
                def __init__(self, a):
                    self.a = a
                def f(self):
                    return self.count
            i = 0
            a = A(1)
            while i < n:
                A.count = LL(A.count) # ID: mutate
                a.f()    # ID: meth1
                i += 1
            return i
        #
        log = self.run(fn, [1000], threshold=10)
        assert log.result == 1000
        #
        # first, we test the entry bridge
        # -------------------------------
        entry_bridge, = log.loops_by_filename(self.filepath, is_entry_bridge=True)
        ops = entry_bridge.ops_by_id('mutate', opcode='LOAD_ATTR')
        assert log.opnames(ops) == ['guard_value', 'guard_not_invalidated',
                                    'getfield_gc_r', 'guard_nonnull_class',
                                    'getfield_gc_r', 'guard_value', # type check on the attribute
                                    ]
        # the STORE_ATTR is folded away
        assert list(entry_bridge.ops_by_id('meth1', opcode='STORE_ATTR')) == []
        #
        # then, the actual loop
        # ----------------------
        loop, = log.loops_by_filename(self.filepath)
        assert loop.match("""
            i70 = int_lt(i58, i33)
            guard_true(i70, descr=...)
            guard_not_invalidated(descr=...)
            p71 = getfield_gc_r(p64, descr=...)
            guard_value(p71, ConstPtr(ptr42), descr=...)
            p72 = force_token()
            p73 = force_token()
            i74 = int_add(i58, 1)
            i75 = getfield_raw_i(..., descr=...)
            i76 = int_lt(i75, 0)
            guard_false(i76, descr=...)
            p77 = new_with_vtable(descr=...)
            setfield_gc(p77, p64, descr=...)
            setfield_gc(p77, ConstPtr(null), descr=...)
            setfield_gc(p77, ConstPtr(null), descr=...)
            setfield_gc(p77, ConstPtr(null), descr=...)
            setfield_gc(p77, ConstPtr(null), descr=...)
            setfield_gc(p77, ConstPtr(ptr42), descr=...)
            setfield_gc(ConstPtr(ptr69), p77, descr=...)
            jump(..., descr=...)

        """)

    def test_oldstyle_methcall(self):
        def main():
            def g(): pass
            class A:
                def f(self):
                    return self.x + 1
            class I(A):
                pass
            class J(I):
                pass


            class B(J):
                def __init__(self, x):
                    self.x = x

            i = 0
            b = B(1)
            while i < 1000:
                g()
                v = b.f() # ID: meth
                i += v
            return i

        log = self.run(main, [], threshold=80)
        loop, = log.loops_by_filename(self.filepath, is_entry_bridge=True)
        assert loop.match_by_id('meth',
        '''
    guard_nonnull_class(p18, ..., descr=...)
    p52 = getfield_gc_r(p18, descr=...) # read map
    guard_value(p52, ConstPtr(ptr53), descr=...)
    p54 = getfield_gc_r(p18, descr=...) # read class
    guard_value(p54, ConstPtr(ptr55), descr=...)
    p56 = force_token() # done
        ''')


    def test_oldstyle_newstyle_mix(self):
        def main():
            class A:
                pass

            class B(object, A):
                def __init__(self, x):
                    self.x = x

            i = 0
            b = B(1)
            while i < 100:
                v = b.x # ID: loadattr1
                v = b.x # ID: loadattr2
                i += v
            return i

        log = self.run(main, [], threshold=80)
        loop, = log.loops_by_filename(self.filepath)
        assert loop.match_by_id('loadattr1',
        '''
        guard_not_invalidated(descr=...)
        i19 = call_i(ConstClass(ll_call_lookup_function), _, _, _, 0, descr=...)
        guard_no_exception(descr=...)
        i22 = int_lt(i19, 0)
        guard_true(i22, descr=...)
        i26 = call_i(ConstClass(ll_call_lookup_function), _, _, _, 0, descr=...)
        guard_no_exception(descr=...)
        i29 = int_lt(i26, 0)
        guard_true(i29, descr=...)
        guard_nonnull_class(p58, ConstClass(W_IntObject), descr=...)
        ''')
        assert loop.match_by_id('loadattr2', "")   # completely folded away

    def test_python_contains(self):
        def main():
            class A(object):
                def __contains__(self, v):
                    return True

            i = 0
            a = A()
            while i < 100:
                i += i in a # ID: contains
                b = 0       # to make sure that JUMP_ABSOLUTE is not part of the ID

        log = self.run(main, [], threshold=80)
        loop, = log.loops_by_filename(self.filepath)
        assert loop.match_by_id("contains", """
            guard_not_invalidated(descr=...)
            i11 = force_token()
            i12 = int_add(i5, 1)
        """)

    def test_id_compare_optimization(self):
        def main():
            class A(object):
                pass
            #
            i = 0
            a = A()
            while i < 300:
                new_a = A()
                if new_a != a:  # ID: compare
                    pass
                i += 1
            return i
        #
        log = self.run(main, [])
        loop, = log.loops_by_filename(self.filepath)
        assert loop.match_by_id("compare", "") # optimized away

    def test_super(self):
        def main():
            class A(object):
                def m(self, x):
                    return x + 1
            class B(A):
                def m(self, x):
                    return super(B, self).m(x)
            i = 0
            while i < 300:
                i = B().m(i)
            return i

        log = self.run(main, [])
        loop, = log.loops_by_filename(self.filepath)
        assert loop.match("""
            i78 = int_lt(i72, 300)
            guard_true(i78, descr=...)
            guard_not_invalidated(descr=...)
            i79 = force_token()
            i80 = force_token()
            i81 = int_add(i72, 1)
            --TICK--
            jump(..., descr=...)
        """)
