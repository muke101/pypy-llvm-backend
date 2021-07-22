from pypy.objspace.std.test.test_dictmultiobject import FakeSpace, W_DictObject
from pypy.objspace.std.mapdict import *

class Config:
    class objspace:
        class std:
            methodcachesizeexp = 11
            withmethodcachecounter = False

space = FakeSpace()
space.config = Config

class Class(object):
    def __init__(self, hasdict=True):
        self.hasdict = hasdict
        if hasdict:
            self.terminator = DictTerminator(space, self)
        else:
            self.terminator = NoDictTerminator(space, self)

    def instantiate(self, sp=None):
        if sp is None:
            sp = space
        if self.hasdict:
            result = Object()
        else:
            result = ObjectWithoutDict()
        result.user_setup(sp, self)
        return result

class ObjectWithoutDict(ObjectWithoutDict):
    class typedef:
        hasdict = False

class Object(Object):
    class typedef:
        hasdict = False

def test_plain_attribute():
    w_cls = "class"
    aa = PlainAttribute("b", DICT,
                        PlainAttribute("a", DICT,
                                       Terminator(space, w_cls)))
    assert aa.space is space
    assert aa.terminator.w_cls is w_cls
    assert aa.get_terminator() is aa.terminator

    obj = Object()
    obj.map, obj.storage = aa, [10, 20]
    assert obj.getdictvalue(space, "a") == 10
    assert obj.getdictvalue(space, "b") == 20
    assert obj.getdictvalue(space, "c") is None

    obj = Object()
    obj.map, obj.storage = aa, [30, 40]
    obj.setdictvalue(space, "a", 50)
    assert obj.storage == [50, 40]
    assert obj.getdictvalue(space, "a") == 50
    obj.setdictvalue(space, "b", 60)
    assert obj.storage == [50, 60]
    assert obj.getdictvalue(space, "b") == 60

    assert aa.length() == 2

    assert aa.get_terminator() is aa.back.back

def test_huge_chain():
    current = Terminator(space, "cls")
    for i in range(20000):
        current = PlainAttribute(str(i), DICT, current)
    assert current.find_map_attr("0", DICT).storageindex == 0


def test_search():
    aa = PlainAttribute("b", DICT, PlainAttribute("a", DICT, Terminator(None, None)))
    assert aa.search(DICT) is aa
    assert aa.search(SLOTS_STARTING_FROM) is None
    assert aa.search(SPECIAL) is None
    bb = PlainAttribute("C", SPECIAL, PlainAttribute("A", SLOTS_STARTING_FROM, aa))
    assert bb.search(DICT) is aa
    assert bb.search(SLOTS_STARTING_FROM) is bb.back
    assert bb.search(SPECIAL) is bb

def test_add_attribute():
    cls = Class()
    obj = cls.instantiate()
    obj.setdictvalue(space, "a", 10)
    assert obj.storage == [10]
    assert obj.getdictvalue(space, "a") == 10
    assert obj.getdictvalue(space, "b") is None
    assert obj.getdictvalue(space, "c") is None
    obj.setdictvalue(space, "a", 20)
    assert obj.getdictvalue(space, "a") == 20
    assert obj.getdictvalue(space, "b") is None
    assert obj.getdictvalue(space, "c") is None

    obj.setdictvalue(space, "b", 30)
    assert obj.storage == [20, 30]
    assert obj.getdictvalue(space, "a") == 20
    assert obj.getdictvalue(space, "b") == 30
    assert obj.getdictvalue(space, "c") is None
    obj.setdictvalue(space, "b", 40)
    assert obj.getdictvalue(space, "a") == 20
    assert obj.getdictvalue(space, "b") == 40
    assert obj.getdictvalue(space, "c") is None

    obj2 = cls.instantiate()
    obj2.setdictvalue(space, "a", 50)
    obj2.setdictvalue(space, "b", 60)
    assert obj2.getdictvalue(space, "a") == 50
    assert obj2.getdictvalue(space, "b") == 60
    assert obj2.map is obj.map

def test_add_attribute_limit():
    for numslots in [0, 10, 100]:
        cls = Class()
        obj = cls.instantiate()
        for i in range(numslots):
            obj.setslotvalue(i, i) # some extra slots too, sometimes
        # test that eventually attributes are really just stored in a dictionary
        for i in range(1000):
            obj.setdictvalue(space, str(i), i)
        # moved to dict (which is the remaining non-slot item)
        assert len(obj.storage) == 1 + numslots

        for i in range(1000):
            assert obj.getdictvalue(space, str(i)) == i
        for i in range(numslots):
            assert obj.getslotvalue(i) == i # check extra slots

    # this doesn't happen with slots
    cls = Class()
    obj = cls.instantiate()
    for i in range(1000):
        obj.setslotvalue(i, i)
    assert len(obj.storage) == 1000

    for i in range(1000):
        assert obj.getslotvalue(i) == i

def test_insert_different_orders():
    cls = Class()
    obj = cls.instantiate()
    obj.setdictvalue(space, "a", 10)
    obj.setdictvalue(space, "b", 20)

    obj2 = cls.instantiate()
    obj2.setdictvalue(space, "b", 30)
    obj2.setdictvalue(space, "a", 40)

    assert obj.map is obj2.map

def test_insert_different_orders_2():
    cls = Class()
    obj = cls.instantiate()
    obj2 = cls.instantiate()

    obj.setdictvalue(space, "a", 10)

    obj2.setdictvalue(space, "b", 20)
    obj2.setdictvalue(space, "a", 30)

    obj.setdictvalue(space, "b", 40)
    assert obj.map is obj2.map

def test_insert_different_orders_3():
    cls = Class()
    obj = cls.instantiate()
    obj2 = cls.instantiate()
    obj3 = cls.instantiate()
    obj4 = cls.instantiate()
    obj5 = cls.instantiate()
    obj6 = cls.instantiate()

    obj.setdictvalue(space, "a", 10)
    obj.setdictvalue(space, "b", 20)
    obj.setdictvalue(space, "c", 30)

    obj2.setdictvalue(space, "a", 30)
    obj2.setdictvalue(space, "c", 40)
    obj2.setdictvalue(space, "b", 50)

    obj3.setdictvalue(space, "c", 30)
    obj3.setdictvalue(space, "a", 40)
    obj3.setdictvalue(space, "b", 50)

    obj4.setdictvalue(space, "c", 30)
    obj4.setdictvalue(space, "b", 40)
    obj4.setdictvalue(space, "a", 50)

    obj5.setdictvalue(space, "b", 30)
    obj5.setdictvalue(space, "a", 40)
    obj5.setdictvalue(space, "c", 50)

    obj6.setdictvalue(space, "b", 30)
    obj6.setdictvalue(space, "c", 40)
    obj6.setdictvalue(space, "a", 50)

    assert obj.map is obj2.map
    assert obj.map is obj3.map
    assert obj.map is obj4.map
    assert obj.map is obj5.map
    assert obj.map is obj6.map


def test_insert_different_orders_4():
    cls = Class()
    obj = cls.instantiate()
    obj2 = cls.instantiate()

    obj.setdictvalue(space, "a", 10)
    obj.setdictvalue(space, "b", 20)
    obj.setdictvalue(space, "c", 30)
    obj.setdictvalue(space, "d", 40)

    obj2.setdictvalue(space, "d", 50)
    obj2.setdictvalue(space, "c", 50)
    obj2.setdictvalue(space, "b", 50)
    obj2.setdictvalue(space, "a", 50)

    assert obj.map is obj2.map

def test_insert_different_orders_5():
    cls = Class()
    obj = cls.instantiate()
    obj2 = cls.instantiate()

    obj.setdictvalue(space, "a", 10)
    obj.setdictvalue(space, "b", 20)
    obj.setdictvalue(space, "c", 30)
    obj.setdictvalue(space, "d", 40)

    obj2.setdictvalue(space, "d", 50)
    obj2.setdictvalue(space, "c", 50)
    obj2.setdictvalue(space, "b", 50)
    obj2.setdictvalue(space, "a", 50)

    obj3 = cls.instantiate()
    obj3.setdictvalue(space, "d", 50)
    obj3.setdictvalue(space, "c", 50)
    obj3.setdictvalue(space, "b", 50)
    obj3.setdictvalue(space, "a", 50)

    assert obj.map is obj3.map


def test_bug_stack_overflow_insert_attributes():
    cls = Class()
    obj = cls.instantiate()

    for i in range(1000):
        obj.setdictvalue(space, str(i), i)


def test_insert_different_orders_perm():
    from itertools import permutations
    cls = Class()
    seen_maps = {}
    for preexisting in ['', 'x', 'xy']:
        for i, attributes in enumerate(permutations("abcdef")):
            obj = cls.instantiate()
            for i, attr in enumerate(preexisting):
                obj.setdictvalue(space, attr, i*1000)
            key = preexisting
            for j, attr in enumerate(attributes):
                obj.setdictvalue(space, attr, i*10+j)
                key = "".join(sorted(key+attr))
                if key in seen_maps:
                    assert obj.map is seen_maps[key]
                else:
                    seen_maps[key] = obj.map

    print len(seen_maps)


def test_bug_infinite_loop():
    cls = Class()
    obj = cls.instantiate()
    obj.setdictvalue(space, "e", 1)
    obj2 = cls.instantiate()
    obj2.setdictvalue(space, "f", 2)
    obj3 = cls.instantiate()
    obj3.setdictvalue(space, "a", 3)
    obj3.setdictvalue(space, "e", 4)
    obj3.setdictvalue(space, "f", 5)


def test_attr_immutability(monkeypatch):
    cls = Class()
    obj = cls.instantiate()
    obj.setdictvalue(space, "a", 10)
    obj.setdictvalue(space, "b", 20)
    obj.setdictvalue(space, "b", 30)
    assert obj.storage == [10, 30]
    assert obj.map.ever_mutated == True
    assert obj.map.back.ever_mutated == False

    indices = []

    def _pure_mapdict_read_storage(obj, storageindex):
        assert storageindex == 0
        indices.append(storageindex)
        return obj._mapdict_read_storage(storageindex)

    obj.map._pure_mapdict_read_storage = _pure_mapdict_read_storage
    monkeypatch.setattr(jit, "isconstant", lambda c: True)

    assert obj.getdictvalue(space, "a") == 10
    assert obj.getdictvalue(space, "b") == 30
    assert obj.getdictvalue(space, "a") == 10
    assert indices == [0, 0]

    obj2 = cls.instantiate()
    obj2.setdictvalue(space, "a", 15)
    obj2.setdictvalue(space, "b", 25)
    assert obj2.map is obj.map
    assert obj2.map.ever_mutated == True
    assert obj2.map.back.ever_mutated == False

    # mutating obj2 changes the map
    obj2.setdictvalue(space, "a", 50)
    assert obj2.map.back.ever_mutated == True
    assert obj2.map is obj.map

def test_attr_immutability_delete():
    cls = Class()
    obj = cls.instantiate()
    obj.setdictvalue(space, "a", 10)
    map1 = obj.map
    obj.deldictvalue(space, "a")
    obj.setdictvalue(space, "a", 20)
    assert obj.map.ever_mutated == True
    assert obj.map is map1

def test_delete():
    for i, dattr in enumerate(["a", "b", "c"]):
        c = Class()
        obj = c.instantiate()
        obj.setdictvalue(space, "a", 50)
        obj.setdictvalue(space, "b", 60)
        obj.setdictvalue(space, "c", 70)
        assert obj.storage == [50, 60, 70]
        res = obj.deldictvalue(space, dattr)
        assert res
        s = [50, 60, 70]
        del s[i]
        assert obj.storage == s

    obj = c.instantiate()
    obj.setdictvalue(space, "a", 50)
    obj.setdictvalue(space, "b", 60)
    obj.setdictvalue(space, "c", 70)
    assert not obj.deldictvalue(space, "d")


def test_class():
    c = Class()
    obj = c.instantiate()
    assert obj.getclass(space) is c
    obj.setdictvalue(space, "a", 50)
    assert obj.getclass(space) is c
    obj.setdictvalue(space, "b", 60)
    assert obj.getclass(space) is c
    obj.setdictvalue(space, "c", 70)
    assert obj.getclass(space) is c

    c2 = Class()
    obj.setclass(space, c2)
    assert obj.getclass(space) is c2
    assert obj.storage == [50, 60, 70]

def test_special():
    from pypy.module._weakref.interp__weakref import WeakrefLifeline
    lifeline1 = WeakrefLifeline(space)
    lifeline2 = WeakrefLifeline(space)
    c = Class()
    obj = c.instantiate()
    assert obj.getweakref() is None
    obj.setdictvalue(space, "a", 50)
    obj.setdictvalue(space, "b", 60)
    obj.setdictvalue(space, "c", 70)
    obj.setweakref(space, lifeline1)
    assert obj.getdictvalue(space, "a") == 50
    assert obj.getdictvalue(space, "b") == 60
    assert obj.getdictvalue(space, "c") == 70
    assert obj.storage == [50, 60, 70, lifeline1]
    assert obj.getweakref() is lifeline1

    obj2 = c.instantiate()
    obj2.setdictvalue(space, "a", 150)
    obj2.setdictvalue(space, "b", 160)
    obj2.setdictvalue(space, "c", 170)
    obj2.setweakref(space, lifeline2)
    assert obj2.storage == [150, 160, 170, lifeline2]
    assert obj2.getweakref() is lifeline2

    assert obj2.map is obj.map

    assert obj.getdictvalue(space, "weakref") is None
    obj.setdictvalue(space, "weakref", 41)
    assert obj.getweakref() is lifeline1
    assert obj.getdictvalue(space, "weakref") == 41

    lifeline1 = WeakrefLifeline(space)
    obj = c.instantiate()
    assert obj.getweakref() is None
    obj.setweakref(space, lifeline1)
    obj.delweakref()



def test_slots():
    cls = Class()
    obj = cls.instantiate()
    a =  0
    b =  1
    c =  2
    obj.setslotvalue(a, 50)
    obj.setslotvalue(b, 60)
    obj.setslotvalue(c, 70)
    assert obj.getslotvalue(a) == 50
    assert obj.getslotvalue(b) == 60
    assert obj.getslotvalue(c) == 70
    assert obj.storage == [50, 60, 70]

    obj.setdictvalue(space, "a", 5)
    obj.setdictvalue(space, "b", 6)
    obj.setdictvalue(space, "c", 7)
    assert obj.getdictvalue(space, "a") == 5
    assert obj.getdictvalue(space, "b") == 6
    assert obj.getdictvalue(space, "c") == 7
    assert obj.getslotvalue(a) == 50
    assert obj.getslotvalue(b) == 60
    assert obj.getslotvalue(c) == 70
    assert obj.storage == [50, 60, 70, 5, 6, 7]

    obj2 = cls.instantiate()
    obj2.setslotvalue(a, 501)
    obj2.setslotvalue(b, 601)
    obj2.setslotvalue(c, 701)
    obj2.setdictvalue(space, "a", 51)
    obj2.setdictvalue(space, "b", 61)
    obj2.setdictvalue(space, "c", 71)
    assert obj2.storage == [501, 601, 701, 51, 61, 71]
    assert obj.map is obj2.map

    assert obj2.getslotvalue(b) == 601
    assert obj2.delslotvalue(b)
    assert obj2.getslotvalue(b) is None
    assert obj2.storage == [501, 701, 51, 61, 71]
    assert not obj2.delslotvalue(b)


def test_slots_no_dict():
    cls = Class(hasdict=False)
    obj = cls.instantiate()
    a = 0
    b = 1
    obj.setslotvalue(a, 50)
    obj.setslotvalue(b, 60)
    assert obj.getslotvalue(a) == 50
    assert obj.getslotvalue(b) == 60
    assert obj.storage == [50, 60]
    assert not obj.setdictvalue(space, "a", 70)
    assert obj.getdict(space) is None
    assert obj.getdictvalue(space, "a") is None


def test_getdict():
    cls = Class()
    obj = cls.instantiate()
    obj.setdictvalue(space, "a", 51)
    obj.setdictvalue(space, "b", 61)
    obj.setdictvalue(space, "c", 71)
    assert obj.getdict(space) is obj.getdict(space)
    assert obj.getdict(space).length() == 3


def test_materialize_r_dict():
    cls = Class()
    obj = cls.instantiate()
    a = 0
    b = 1
    c = 2
    obj.setslotvalue(a, 50)
    obj.setslotvalue(b, 60)
    obj.setslotvalue(c, 70)
    obj.setdictvalue(space, "a", 5)
    obj.setdictvalue(space, "b", 6)
    obj.setdictvalue(space, "c", 7)
    assert obj.storage == [50, 60, 70, 5, 6, 7]

    class FakeDict(W_DictObject):
        def __init__(self, d):
            self.dstorage = d

        class strategy:
            def unerase(self, x):
                return d
        strategy = strategy()

    d = {}
    w_d = FakeDict(d)
    flag = obj.map.write(obj, "dict", SPECIAL, w_d)
    assert flag
    materialize_r_dict(space, obj, d)
    assert d == {"a": 5, "b": 6, "c": 7}
    assert obj.storage == [50, 60, 70, w_d]


def test_size_prediction():
    for i in range(10):
        c = Class()
        assert c.terminator.size_estimate() == 0
        for j in range(1000):
            obj = c.instantiate()
            for a in "abcdefghij"[:i]:
                obj.setdictvalue(space, a, 50)
        assert c.terminator.size_estimate() == i
    for i in range(1, 10):
        c = Class()
        assert c.terminator.size_estimate() == 0
        for j in range(1000):
            obj = c.instantiate()
            for a in "abcdefghij"[:i]:
                obj.setdictvalue(space, a, 50)
            obj = c.instantiate()
            for a in "klmnopqars":
                obj.setdictvalue(space, a, 50)
        assert c.terminator.size_estimate() in [(i + 10) // 2, (i + 11) // 2]

# ___________________________________________________________
# dict tests

from pypy.objspace.std.test.test_dictmultiobject import BaseTestRDictImplementation, BaseTestDevolvedDictImplementation
def get_impl(self):
    cls = Class()
    w_obj = cls.instantiate(self.fakespace)
    return w_obj.getdict(self.fakespace)
class TestMapDictImplementation(BaseTestRDictImplementation):
    StrategyClass = MapDictStrategy
    get_impl = get_impl
    def test_setdefault_fast(self):
        # mapdict can't pass this, which is fine
        pass
class TestDevolvedMapDictImplementation(BaseTestDevolvedDictImplementation):
    get_impl = get_impl
    StrategyClass = MapDictStrategy
    def test_setdefault_fast(self):
        # mapdict can't pass this, which is fine
        pass

# ___________________________________________________________
# tests that check the obj interface after the dict has devolved

def devolve_dict(space, obj):
    w_d = obj.getdict(space)
    w_d.get_strategy().switch_to_object_strategy(w_d)

def test_get_setdictvalue_after_devolve():
    cls = Class()
    obj = cls.instantiate()
    a = 0
    b = 1
    c = 2
    obj.setslotvalue(a, 50)
    obj.setslotvalue(b, 60)
    obj.setslotvalue(c, 70)
    obj.setdictvalue(space, "a", 5)
    obj.setdictvalue(space, "b", 6)
    obj.setdictvalue(space, "c", 7)
    obj.setdictvalue(space, "weakref", 42)
    devolve_dict(space, obj)
    assert obj.getdictvalue(space, "a") == 5
    assert obj.getdictvalue(space, "b") == 6
    assert obj.getdictvalue(space, "c") == 7
    assert obj.getslotvalue(a) == 50
    assert obj.getslotvalue(b) == 60
    assert obj.getslotvalue(c) == 70
    assert obj.getdictvalue(space, "weakref") == 42
    assert obj.getweakref() is None

    obj.setslotvalue(a, 501)
    obj.setslotvalue(b, 601)
    obj.setslotvalue(c, 701)
    res = obj.setdictvalue(space, "a", 51)
    assert res
    obj.setdictvalue(space, "b", 61)
    obj.setdictvalue(space, "c", 71)
    assert obj.getdictvalue(space, "a") == 51
    assert obj.getdictvalue(space, "b") == 61
    assert obj.getdictvalue(space, "c") == 71
    assert obj.getslotvalue(a) == 501
    assert obj.getslotvalue(b) == 601
    assert obj.getslotvalue(c) == 701
    res = obj.deldictvalue(space, "a")
    assert res
    assert obj.getdictvalue(space, "a") is None
    assert obj.getdictvalue(space, "b") == 61
    assert obj.getdictvalue(space, "c") == 71
    assert obj.getslotvalue(a) == 501
    assert obj.getslotvalue(b) == 601
    assert obj.getslotvalue(c) == 701

def test_setdict():
    cls = Class()
    obj = cls.instantiate()
    obj.setdictvalue(space, "a", 5)
    obj.setdictvalue(space, "b", 6)
    obj.setdictvalue(space, "c", 7)
    w_d = obj.getdict(space)
    obj2 = cls.instantiate()
    obj2.setdictvalue(space, "d", 8)
    obj.setdict(space, obj2.getdict(space))
    assert obj.getdictvalue(space, "a") is None
    assert obj.getdictvalue(space, "b") is None
    assert obj.getdictvalue(space, "c") is None
    assert obj.getdictvalue(space, "d") == 8
    assert w_d.getitem_str("a") == 5
    assert w_d.getitem_str("b") == 6
    assert w_d.getitem_str("c") == 7

# ___________________________________________________________
# check specialized classes


def test_specialized_class():
    from pypy.objspace.std.mapdict import _make_storage_mixin_size_n
    from pypy.objspace.std.objectobject import W_ObjectObject
    classes = [_make_storage_mixin_size_n(i) for i in range(2, 10)]
    w1 = W_Root()
    w2 = W_Root()
    w3 = W_Root()
    w4 = W_Root()
    w5 = W_Root()
    w6 = W_Root()
    for mixin in classes:
        class objectcls(W_ObjectObject):
            objectmodel.import_from_mixin(BaseUserClassMapdict)
            objectmodel.import_from_mixin(MapdictDictSupport)
            objectmodel.import_from_mixin(mixin)
        cls = Class()
        obj = objectcls()
        obj.user_setup(space, cls)
        obj.setdictvalue(space, "a", w1)
        assert obj._value0 is w1
        assert obj.getdictvalue(space, "a") is w1
        assert obj.getdictvalue(space, "b") is None
        assert obj.getdictvalue(space, "c") is None
        obj.setdictvalue(space, "a", w2)
        assert obj._value0 is w2
        assert obj.getdictvalue(space, "a") == w2
        assert obj.getdictvalue(space, "b") is None
        assert obj.getdictvalue(space, "c") is None

        obj.setdictvalue(space, "b", w3)
        #== [20, 30]
        assert obj.getdictvalue(space, "a") is w2
        assert obj.getdictvalue(space, "b") is w3
        assert obj.getdictvalue(space, "c") is None
        obj.setdictvalue(space, "b", w4)
        assert obj.getdictvalue(space, "a") is w2
        assert obj.getdictvalue(space, "b") is w4
        assert obj.getdictvalue(space, "c") is None
        abmap = obj.map

        res = obj.deldictvalue(space, "a")
        assert res
        assert obj._value0 is w4
        assert obj.getdictvalue(space, "a") is None
        assert obj.getdictvalue(space, "b") is w4
        assert obj.getdictvalue(space, "c") is None

        obj2 = objectcls()
        obj2.user_setup(space, cls)
        obj2.setdictvalue(space, "a", w5)
        obj2.setdictvalue(space, "b", w6)
        assert obj2.getdictvalue(space, "a") is w5
        assert obj2.getdictvalue(space, "b") is w6
        assert obj2.map is abmap

# ___________________________________________________________
# integration tests

# XXX write more

class AppTestWithMapDict(object):

    def test_simple(self):
        class A(object):
            pass
        a = A()
        a.x = 5
        a.y = 6
        a.zz = 7
        assert a.x == 5
        assert a.y == 6
        assert a.zz == 7

    def test_read_write_dict(self):
        class A(object):
            pass
        a = A()
        a.x = 5
        a.y = 6
        a.zz = 7
        d = a.__dict__
        assert d == {"x": 5, "y": 6, "zz": 7}
        d['dd'] = 41
        assert a.dd == 41
        del a.x
        assert d == {"y": 6, "zz": 7, 'dd': 41}
        d2 = d.copy()
        d2[1] = 2
        a.__dict__ = d2
        assert a.y == 6
        assert a.zz == 7
        assert a.dd == 41
        d['dd'] = 43
        assert a.dd == 41

    def test_popitem(self):
        class A(object):
            pass
        a = A()
        a.x = 5
        a.y = 6
        it1 = a.__dict__.popitem()
        assert it1 == ("y", 6)
        it2 = a.__dict__.popitem()
        assert it2 == ("x", 5)
        assert a.__dict__ == {}
        raises(KeyError, a.__dict__.popitem)



    def test_slot_name_conflict(self):
        class A(object):
            __slots__ = 'slot1'
        class B(A):
            __slots__ = 'slot1'
        x = B()
        x.slot1 = 'child'             # using B.slot1
        A.slot1.__set__(x, 'parent')  # using A.slot1
        assert x.slot1 == 'child'     # B.slot1 should still have its old value
        assert A.slot1.__get__(x) == 'parent'

    def test_change_class(self):
        class A(object):
            pass
        class B(object):
            pass
        a = A()
        a.x = 1
        a.y = 2
        assert a.x == 1
        assert a.y == 2
        a.__class__ = B
        assert a.x == 1
        assert a.y == 2
        assert isinstance(a, B)

        # dict accessed:
        a = A()
        a.x = 1
        a.y = 2
        assert a.x == 1
        assert a.y == 2
        d = a.__dict__
        assert d == {"x": 1, "y": 2}
        a.__class__ = B
        assert a.x == 1
        assert a.y == 2
        assert a.__dict__ is d
        assert d == {"x": 1, "y": 2}
        assert isinstance(a, B)

        # dict devolved:
        a = A()
        a.x = 1
        a.y = 2
        assert a.x == 1
        assert a.y == 2
        d = a.__dict__
        d[1] = 3
        assert d == {"x": 1, "y": 2, 1:3}
        a.__class__ = B
        assert a.x == 1
        assert a.y == 2
        assert a.__dict__ is d
        assert isinstance(a, B)

    def test_dict_devolved_bug(self):
        class A(object):
            pass
        a = A()
        a.x = 1
        d = a.__dict__
        d[1] = 3
        a.__dict__ = {}

    def test_dict_clear_bug(self):
        class A(object):
            pass
        a = A()
        a.x1 = 1
        a.x2 = 1
        a.x3 = 1
        a.x4 = 1
        a.x5 = 1
        for i in range(100): # change _size_estimate of w_A.terminator
            a1 = A()
            a1.x1 = 1
            a1.x2 = 1
            a1.x3 = 1
            a1.x4 = 1
            a1.x5 = 1
        d = a.__dict__
        d.clear()
        a.__dict__ = {1: 1}
        assert d == {}

    def test_change_class_slots(self):
        class A(object):
            __slots__ = ["x", "y"]

        class B(object):
            __slots__ = ["x", "y"]

        a = A()
        a.x = 1
        a.y = 2
        assert a.x == 1
        assert a.y == 2
        a.__class__ = B
        assert a.x == 1
        assert a.y == 2
        assert isinstance(a, B)

    def test_change_class_slots_dict(self):
        class A(object):
            __slots__ = ["x", "__dict__"]
        class B(object):
            __slots__ = ["x", "__dict__"]
        # dict accessed:
        a = A()
        a.x = 1
        a.y = 2
        assert a.x == 1
        assert a.y == 2
        d = a.__dict__
        assert d == {"y": 2}
        a.__class__ = B
        assert a.x == 1
        assert a.y == 2
        assert a.__dict__ is d
        assert d == {"y": 2}
        assert isinstance(a, B)

        # dict devolved:
        a = A()
        a.x = 1
        a.y = 2
        assert a.x == 1
        assert a.y == 2
        d = a.__dict__
        d[1] = 3
        assert d == {"y": 2, 1: 3}
        a.__class__ = B
        assert a.x == 1
        assert a.y == 2
        assert a.__dict__ is d
        assert isinstance(a, B)

    def test_setdict(self):
        class A(object):
            pass

        a = A()
        a.__dict__ = {}
        a.__dict__ = {}

    def test_delete_slot(self):
        class A(object):
            __slots__ = ['x']

        a = A()
        a.x = 42
        del a.x
        raises(AttributeError, "a.x")

    def test_reversed_dict(self):
        import __pypy__
        class X(object):
            pass
        x = X(); x.a = 10; x.b = 20; x.c = 30
        d = x.__dict__
        assert list(__pypy__.reversed_dict(d)) == d.keys()[::-1]

    def test_bug_materialize_huge_dict(self):
        import __pypy__
        d = __pypy__.newdict("instance")
        for i in range(100):
            d[str(i)] = i
        assert len(d) == 100

        for key in d:
            assert d[key] == int(key)



class AppTestWithMapDictAndCounters(object):
    spaceconfig = {"objspace.std.withmethodcachecounter": True}

    def setup_class(cls):
        from pypy.interpreter import gateway
        #
        def check(space, w_func, name):
            w_code = space.getattr(w_func, space.wrap('func_code'))
            nameindex = map(space.str_w, w_code.co_names_w).index(name)
            entry = w_code._mapdict_caches[nameindex]
            entry.failure_counter = 0
            entry.success_counter = 0
            INVALID_CACHE_ENTRY.failure_counter = 0
            #
            w_res = space.call_function(w_func)
            assert space.eq_w(w_res, space.wrap(42))
            #
            entry = w_code._mapdict_caches[nameindex]
            if entry is INVALID_CACHE_ENTRY:
                failures = successes = 0
            else:
                failures = entry.failure_counter
                successes = entry.success_counter
            globalfailures = INVALID_CACHE_ENTRY.failure_counter
            return space.wrap((failures, successes, globalfailures))
        check.unwrap_spec = [gateway.ObjSpace, gateway.W_Root, 'text']
        cls.w_check = cls.space.wrap(gateway.interp2app(check))

    def test_simple(self):
        class A(object):
            pass
        a = A()
        a.x = 42
        def f():
            return a.x
        #
        res = self.check(f, 'x')
        assert res == (1, 0, 0)
        res = self.check(f, 'x')
        assert res == (0, 1, 0)
        res = self.check(f, 'x')
        assert res == (0, 1, 0)
        res = self.check(f, 'x')
        assert res == (0, 1, 0)
        #
        A.y = 5     # unrelated, but changes the version_tag
        res = self.check(f, 'x')
        assert res == (1, 0, 0)
        res = self.check(f, 'x')
        assert res == (0, 1, 0)
        res = self.check(f, 'x')
        assert res == (0, 1, 0)
        res = self.check(f, 'x')
        assert res == (0, 1, 0)
        #
        A.x = 8     # but shadowed by 'a.x'
        res = self.check(f, 'x')
        assert res == (1, 0, 0)
        res = self.check(f, 'x')
        assert res == (0, 1, 0)
        res = self.check(f, 'x')
        assert res == (0, 1, 0)
        res = self.check(f, 'x')
        assert res == (0, 1, 0)

    def test_property(self):
        class A(object):
            x = property(lambda self: 42)
        a = A()
        def f():
            return a.x
        #
        res = self.check(f, 'x')
        assert res == (0, 0, 1)
        res = self.check(f, 'x')
        assert res == (0, 0, 1)
        res = self.check(f, 'x')
        assert res == (0, 0, 1)

    def test_slots(self):
        class A(object):
            __slots__ = ['x']
        a = A()
        a.x = 42
        def f():
            return a.x
        #
        res = self.check(f, 'x')
        assert res == (1, 0, 0)
        res = self.check(f, 'x')
        assert res == (0, 1, 0)
        res = self.check(f, 'x')
        assert res == (0, 1, 0)
        res = self.check(f, 'x')
        assert res == (0, 1, 0)

    def test_two_attributes(self):
        class A(object):
            pass
        a = A()
        a.x = 40
        a.y = -2
        def f():
            return a.x - a.y
        #
        res = self.check(f, 'x')
        assert res == (1, 0, 0)
        res = self.check(f, 'x')
        assert res == (0, 1, 0)
        res = self.check(f, 'x')
        assert res == (0, 1, 0)
        #
        res = self.check(f, 'y')
        assert res == (0, 1, 0)
        res = self.check(f, 'y')
        assert res == (0, 1, 0)
        res = self.check(f, 'y')
        assert res == (0, 1, 0)

    def test_two_maps(self):
        class A(object):
            pass
        a = A()
        a.x = 42
        def f():
            return a.x
        #
        res = self.check(f, 'x')
        assert res == (1, 0, 0)
        res = self.check(f, 'x')
        assert res == (0, 1, 0)
        res = self.check(f, 'x')
        assert res == (0, 1, 0)
        #
        a.y = "foo"      # changes the map
        res = self.check(f, 'x')
        assert res == (1, 0, 0)
        res = self.check(f, 'x')
        assert res == (0, 1, 0)
        res = self.check(f, 'x')
        assert res == (0, 1, 0)
        #
        a.y = "bar"      # does not change the map any more
        res = self.check(f, 'x')
        assert res == (0, 1, 0)
        res = self.check(f, 'x')
        assert res == (0, 1, 0)
        res = self.check(f, 'x')
        assert res == (0, 1, 0)

    def test_custom_metaclass(self):
        class A(object):
            class __metaclass__(type):
                pass
        a = A()
        a.x = 42
        def f():
            return a.x
        #
        res = self.check(f, 'x')
        assert res == (1, 0, 0)
        res = self.check(f, 'x')
        assert res == (0, 1, 0)
        res = self.check(f, 'x')
        assert res == (0, 1, 0)

    def test_old_style_base(self):
        class B:
            pass
        class C(object):
            pass
        class A(C, B):
            pass
        a = A()
        a.x = 42
        def f():
            return a.x
        #
        res = self.check(f, 'x')
        assert res == (0, 0, 1)
        res = self.check(f, 'x')
        assert res == (0, 0, 1)
        res = self.check(f, 'x')
        assert res == (0, 0, 1)

    def test_call_method_uses_cache(self):
        # bit sucky
        global C

        class C(object):
            def m(*args):
                return args
        C.sm = staticmethod(C.m.im_func)
        C.cm = classmethod(C.m.im_func)

        exec """if 1:

            def f():
                c = C()
                res = c.m(1)
                assert res == (c, 1)
                return 42

            def g():
                c = C()
                res = c.sm(1)
                assert res == (1, )
                return 42

            def h():
                c = C()
                res = c.cm(1)
                assert res == (C, 1)
                return 42
        """
        res = self.check(f, 'm')
        assert res == (1, 0, 0)
        res = self.check(f, 'm')
        assert res == (0, 1, 0)
        res = self.check(f, 'm')
        assert res == (0, 1, 0)
        res = self.check(f, 'm')
        assert res == (0, 1, 0)

        # static methods are not cached
        res = self.check(g, 'sm')
        assert res == (0, 0, 0)
        res = self.check(g, 'sm')
        assert res == (0, 0, 0)

        # neither are class methods
        res = self.check(h, 'cm')
        assert res == (0, 0, 0)
        res = self.check(h, 'cm')
        assert res == (0, 0, 0)

    def test_mix_cache_bug(self):
        # bit sucky
        global C

        class C(object):
            def m(*args):
                return args

        exec """if 1:

            def f():
                c = C()
                res = c.m(1)
                assert res == (c, 1)
                bm = c.m
                res = bm(1)
                assert res == (c, 1)
                return 42

        """
        res = self.check(f, 'm')
        assert res == (1, 1, 1)
        res = self.check(f, 'm')
        assert res == (0, 2, 1)
        res = self.check(f, 'm')
        assert res == (0, 2, 1)
        res = self.check(f, 'm')
        assert res == (0, 2, 1)

    def test_dont_keep_class_alive(self):
        import weakref
        import gc
        def f():
            class C(object):
                def m(self):
                    pass
            r = weakref.ref(C)
            # Trigger cache.
            C().m()
            del C
            gc.collect(); gc.collect(); gc.collect()
            assert r() is None
            return 42
        f()

    def test_instance_keeps_class_alive(self):
        import weakref
        import gc
        def f():
            class C(object):
                def m(self):
                    return 42
            r = weakref.ref(C)
            c = C()
            del C
            gc.collect(); gc.collect(); gc.collect()
            return c.m()
        val = f()
        assert val == 42
        f()

    def test_bug_lookup_method_devolved_dict_caching(self):
        class A(object):
            def method(self):
                return 42
        a = A()
        a.__dict__[1] = 'foo'
        got = a.method()
        assert got == 42
        a.__dict__['method'] = lambda: 43
        got = a.method()
        assert got == 43

    def test_dict_order(self):
        # the __dict__ order is not strictly enforced, but in
        # simple cases like that, we want to follow the order of
        # creation of the attributes
        class A(object):
            pass
        a = A()
        a.x = 5
        a.z = 6
        a.y = 7
        assert list(a.__dict__) == ['x', 'z', 'y']
        assert a.__dict__.values() == [5, 6, 7]
        assert list(a.__dict__.iteritems()) == [('x', 5), ('z', 6), ('y', 7)]

    def test_bug_method_change(self):
        class A(object):
            def method(self):
                return 42
        a = A()
        got = a.method()
        assert got == 42
        A.method = lambda self: 43
        got = a.method()
        assert got == 43
        A.method = lambda self: 44
        got = a.method()
        assert got == 44

    def test_bug_slot_via_changing_member_descr(self):
        class A(object):
            __slots__ = ['a', 'b', 'c', 'd']
        x = A()
        x.a = 'a'
        x.b = 'b'
        x.c = 'c'
        x.d = 'd'
        got = x.a
        assert got == 'a'
        A.a = A.b
        got = x.a
        assert got == 'b'
        A.a = A.c
        got = x.a
        assert got == 'c'
        A.a = A.d
        got = x.a
        assert got == 'd'

    def test_bug_builtin_types_callmethod(self):
        import sys
        class D(type(sys)):
            def mymethod(self):
                return "mymethod"

        def foobar():
            return "foobar"

        d = D('d')
        res1 = d.mymethod()
        d.mymethod = foobar
        res2 = d.mymethod()
        assert res1 == "mymethod"
        assert res2 == "foobar"

    def test_bug_builtin_types_load_attr(self):
        import sys
        class D(type(sys)):
            def mymethod(self):
                return "mymethod"

        def foobar():
            return "foobar"

        d = D('d')
        m = d.mymethod
        res1 = m()
        d.mymethod = foobar
        m = d.mymethod
        res2 = m()
        assert res1 == "mymethod"
        assert res2 == "foobar"



class AppTestGlobalCaching(AppTestWithMapDict):
    spaceconfig = {"objspace.std.withmethodcachecounter": True}

    def test_mix_classes(self):
        import __pypy__
        seen = []
        for i in range(20):
            class A(object):
                def f(self):
                    return 42
            class B(object):
                def f(self):
                    return 43
            class C(object):
                def f(self):
                    return 44
            l = [A(), B(), C()] * 10
            __pypy__.reset_method_cache_counter()
            # 'exec' to make sure that a.f() is compiled with CALL_METHOD
            exec """for i, a in enumerate(l):
                        assert a.f() == 42 + i % 3
            """ in locals()
            cache_counter = __pypy__.mapdict_cache_counter("f")
            if cache_counter == (27, 3):
                break
            # keep them alive, to make sure that on the
            # next try they have difference addresses
            seen.append((l, cache_counter))
        else:
            assert 0, "failed: got %r" % ([got[1] for got in seen],)

    def test_mix_classes_attribute(self):
        import __pypy__
        seen = []
        for i in range(20):
            class A(object):
                def __init__(self):
                    self.x = 42
            class B(object):
                def __init__(self):
                    self.x = 43
            class C(object):
                def __init__(self):
                    self.x = 44
            l = [A(), B(), C()] * 10
            __pypy__.reset_method_cache_counter()
            for i, a in enumerate(l):
                assert a.x == 42 + i % 3
            cache_counter = __pypy__.mapdict_cache_counter("x")
            if cache_counter == (27, 3):
                break
            # keep them alive, to make sure that on the
            # next try they have difference addresses
            seen.append((l, cache_counter))
        else:
            assert 0, "failed: got %r" % ([got[1] for got in seen],)

class TestDictSubclassShortcutBug(object):
    spaceconfig = {"objspace.std.withmethodcachecounter": True}

    def test_bug(self):
        w_dict = self.space.appexec([], """():
                class A(dict):
                    def __getitem__(self, key):
                        return 1
                assert eval("a", globals(), A()) == 1
                return A()
                """)
        assert w_dict.user_overridden_class

def test_newdict_instance():
    w_dict = space.newdict(instance=True)
    assert type(w_dict.get_strategy()) is MapDictStrategy

class TestMapDictImplementationUsingnewdict(BaseTestRDictImplementation):
    StrategyClass = MapDictStrategy
    # NB: the get_impl method is not overwritten here, as opposed to above

    def test_setdefault_fast(self):
        # mapdict can't pass this, which is fine
        pass
