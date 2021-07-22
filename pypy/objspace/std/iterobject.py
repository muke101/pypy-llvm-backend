"""Generic iterator implementations"""

from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.gateway import interp2app, interpindirect2app
from pypy.interpreter.error import OperationError
from pypy.interpreter.typedef import TypeDef


class W_AbstractSeqIterObject(W_Root):
    def __init__(self, w_seq, index=0):
        if index < 0:
            index = 0
        self.w_seq = w_seq
        self.index = index

    def getlength(self, space):
        if self.w_seq is None:
            return space.newint(0)
        index = self.index
        w_length = space.len(self.w_seq)
        w_len = space.sub(w_length, space.newint(index))
        if space.is_true(space.lt(w_len, space.newint(0))):
            w_len = space.newint(0)
        return w_len

    def descr_iter(self, space):
        return self

    def descr_next(self, space):
        raise NotImplementedError

    def descr_reduce(self, space):
        from pypy.interpreter.mixedmodule import MixedModule
        w_mod = space.getbuiltinmodule('_pickle_support')
        mod = space.interp_w(MixedModule, w_mod)
        new_inst = mod.get('seqiter_new')
        tup = [self.w_seq, space.newint(self.index)]
        return space.newtuple([new_inst, space.newtuple(tup)])

    def descr_length_hint(self, space):
        return self.getlength(space)

W_AbstractSeqIterObject.typedef = TypeDef(
    "sequenceiterator",
    __doc__ = '''iter(collection) -> iterator
iter(callable, sentinel) -> iterator

Get an iterator from an object.  In the first form, the argument must
supply its own iterator, or be a sequence.
In the second form, the callable is called until it returns the sentinel.''',
    __iter__ = interp2app(W_AbstractSeqIterObject.descr_iter),
    next = interpindirect2app(W_AbstractSeqIterObject.descr_next),
    __reduce__ = interp2app(W_AbstractSeqIterObject.descr_reduce),
    __length_hint__ = interp2app(W_AbstractSeqIterObject.descr_length_hint),
)
W_AbstractSeqIterObject.typedef.acceptable_as_base_class = False


class W_SeqIterObject(W_AbstractSeqIterObject):
    """Sequence iterator implementation for general sequences."""

    def descr_next(self, space):
        if self.w_seq is None:
            raise OperationError(space.w_StopIteration, space.w_None)
        try:
            w_item = space.getitem(self.w_seq, space.newint(self.index))
        except OperationError as e:
            self.w_seq = None
            if not e.match(space, space.w_IndexError):
                raise
            raise OperationError(space.w_StopIteration, space.w_None)
        self.index += 1
        return w_item


class W_FastListIterObject(W_AbstractSeqIterObject):
    """Sequence iterator specialized for lists."""

    def descr_next(self, space):
        from pypy.objspace.std.listobject import W_ListObject
        w_seq = self.w_seq
        if w_seq is None:
            raise OperationError(space.w_StopIteration, space.w_None)
        assert isinstance(w_seq, W_ListObject)
        index = self.index
        try:
            w_item = w_seq.getitem(index)
        except IndexError:
            self.w_seq = None
            raise OperationError(space.w_StopIteration, space.w_None)
        self.index = index + 1
        return w_item


class W_FastUnicodeIterObject(W_AbstractSeqIterObject):
    """Sequence iterator specialized for unicode objects."""

    def __init__(self, w_seq):
        from pypy.objspace.std.unicodeobject import W_UnicodeObject
        W_AbstractSeqIterObject.__init__(self, w_seq)
        assert isinstance(w_seq, W_UnicodeObject)
        self.byteindex = 0

    def descr_next(self, space):
        from pypy.objspace.std.unicodeobject import W_UnicodeObject
        w_seq = self.w_seq
        if w_seq is None:
            raise OperationError(space.w_StopIteration, space.w_None)
        assert isinstance(w_seq, W_UnicodeObject)
        index = self.index
        if index == w_seq._length:
            self.w_seq = None
            raise OperationError(space.w_StopIteration, space.w_None)
        start = self.byteindex
        end = w_seq.next_codepoint_pos_dont_look_inside(start)
        w_res = W_UnicodeObject(w_seq._utf8[start:end], 1)
        self.byteindex = end
        self.index += 1
        return w_res


class W_FastTupleIterObject(W_AbstractSeqIterObject):
    """Sequence iterator specialized for tuples, accessing directly
    their RPython-level list of wrapped objects.
    """
    def __init__(self, w_seq, wrappeditems):
        W_AbstractSeqIterObject.__init__(self, w_seq)
        self.tupleitems = wrappeditems

    def descr_next(self, space):
        if self.tupleitems is None:
            raise OperationError(space.w_StopIteration, space.w_None)
        index = self.index
        try:
            w_item = self.tupleitems[index]
        except IndexError:
            self.tupleitems = None
            self.w_seq = None
            raise OperationError(space.w_StopIteration, space.w_None)
        self.index = index + 1
        return w_item


class W_ReverseSeqIterObject(W_Root):
    def __init__(self, space, w_seq, index=-1):
        self.w_seq = w_seq
        self.index = space.len_w(w_seq) + index

    def descr_reduce(self, space):
        from pypy.interpreter.mixedmodule import MixedModule
        w_mod = space.getbuiltinmodule('_pickle_support')
        mod = space.interp_w(MixedModule, w_mod)
        new_inst = mod.get('reverseseqiter_new')
        w_seq = space.w_None if self.w_seq is None else self.w_seq
        tup = [w_seq, space.newint(self.index)]
        return space.newtuple([new_inst, space.newtuple(tup)])

    def descr_length_hint(self, space):
        length = self.index + 1
        if self.w_seq is None or space.len_w(self.w_seq) < length:
            length = 0
        return space.newint(length)

    def descr_iter(self, space):
        return self

    def descr_next(self, space):
        if self.index >= 0:
            w_index = space.newint(self.index)
            try:
                w_item = space.getitem(self.w_seq, w_index)
            except OperationError as e:
                # Done
                self.index = -1
                self.w_seq = None
                if not e.match(space, space.w_IndexError):
                    raise
                raise OperationError(space.w_StopIteration, space.w_None)
            else:
                self.index -= 1
                return w_item

        # Done
        self.index = -1
        self.w_seq = None
        raise OperationError(space.w_StopIteration, space.w_None)

W_ReverseSeqIterObject.typedef = TypeDef(
    "reversesequenceiterator",
    __iter__ = interp2app(W_ReverseSeqIterObject.descr_iter),
    next = interp2app(W_ReverseSeqIterObject.descr_next),
    __reduce__ = interp2app(W_ReverseSeqIterObject.descr_reduce),
    __length_hint__ = interp2app(W_ReverseSeqIterObject.descr_length_hint),
)
W_ReverseSeqIterObject.typedef.acceptable_as_base_class = False
