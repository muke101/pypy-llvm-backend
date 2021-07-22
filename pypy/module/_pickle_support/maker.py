from pypy.interpreter.error import oefmt
from pypy.interpreter.nestedscope import Cell
from pypy.interpreter.pycode import PyCode
from pypy.interpreter.function import Function, Method
from pypy.interpreter.module import Module
from pypy.interpreter.pytraceback import PyTraceback
from pypy.interpreter.generator import GeneratorIterator
from rpython.rlib.objectmodel import instantiate
from pypy.interpreter.gateway import unwrap_spec
from pypy.objspace.std.iterobject import W_SeqIterObject, W_ReverseSeqIterObject


#note: for now we don't use the actual value when creating the Cell.
#      (i.e. we assume it will be handled by __setstate__)
#      Stackless does use this so it might be needed here as well.

def cell_new(space):
    return instantiate(Cell)

def code_new(space, __args__):
    w_type = space.gettypeobject(PyCode.typedef)
    return space.call_args(w_type, __args__)

def func_new(space):
    fu = instantiate(Function)
    fu.w_func_dict = space.newdict()
    return fu

def module_new(space, w_name, w_dict):
    new_mod = Module(space, w_name, w_dict, add_package=False)
    return new_mod

def method_new(space, __args__):
    w_type = space.gettypeobject(Method.typedef)
    return space.call_args(w_type, __args__)

def builtin_method_new(space, w_instance, w_name):
    return space.getattr(w_instance, w_name)

def dictiter_surrogate_new(space, w_lis):
    # we got a listobject.
    # simply create an iterator and that's it.
    return space.iter(w_lis)

def seqiter_new(space, w_seq, w_index):
    return W_SeqIterObject(w_seq, space.int_w(w_index))

def reverseseqiter_new(space, w_seq, w_index):
    w_rev = instantiate(W_ReverseSeqIterObject)
    if space.is_w(w_seq, space.w_None):
        w_rev.w_seq = None
        w_rev.index = -1
    else:
        w_rev.w_seq = w_seq
        w_rev.index = space.int_w(w_index)
    return w_rev

def frame_new(space):
    new_frame = instantiate(space.FrameClass)   # XXX fish
    return new_frame

def traceback_new(space):
    tb = instantiate(PyTraceback)
    return tb

def generator_new(space):
    new_generator = instantiate(GeneratorIterator)
    return new_generator

@unwrap_spec(current=int, remaining=int, step=int)
def xrangeiter_new(space, current, remaining, step):
    from pypy.module.__builtin__.functional import W_XRangeIterator
    new_iter = W_XRangeIterator(space, current, remaining, step)
    return new_iter

@unwrap_spec(identifier='text')
def builtin_code(space, identifier):
    from pypy.interpreter import gateway
    try:
        return gateway.BuiltinCode.find(space, identifier)
    except KeyError:
        raise oefmt(space.w_RuntimeError,
                    "cannot unpickle builtin code: %s", identifier)

@unwrap_spec(identifier='text')
def builtin_function(space, identifier):
    from pypy.interpreter import function
    try:
        return function.Function.find(space, identifier)
    except KeyError:
        raise oefmt(space.w_RuntimeError,
                    "cannot unpickle builtin function: %s", identifier)


def enumerate_new(space, w_iter, w_index):
    from pypy.module.__builtin__.functional import _make_enumerate
    return _make_enumerate(space, w_iter, w_index)

def reversed_new(space, w_seq, w_remaining):
    from pypy.module.__builtin__.functional import _make_reversed
    return _make_reversed(space, w_seq, w_remaining)


# ___________________________________________________________________
# Helper functions for internal use

# adopted from prickelpit.c  (but almost completely different)

def slp_into_tuple_with_nulls(space, seq_w):
    """
    create a tuple with the object and store
    a tuple with the positions of NULLs as first element.
    """
    tup = [None] * (len(seq_w) + 1)
    num = 1
    nulls = [None for i in seq_w if i is None]
    null_num = 0
    for w_obj in seq_w:
        if w_obj is None:
            nulls[null_num] = space.newint(num - 1)
            null_num += 1
            w_obj = space.w_None
        tup[num] = w_obj
        num += 1
    tup[0] = space.newtuple(nulls)
    return space.newtuple(tup)

def slp_from_tuple_with_nulls(space, w_tup):
    tup_w = space.unpackiterable(w_tup)
    nulls = space.unpackiterable(tup_w[0])
    tup_w = tup_w[1:]
    for w_p in nulls:
        p = space.int_w(w_p)
        tup_w[p] = None
    return tup_w
