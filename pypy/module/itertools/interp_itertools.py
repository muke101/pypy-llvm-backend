from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.error import OperationError, oefmt
from pypy.interpreter.typedef import TypeDef, make_weakref_descr
from pypy.interpreter.gateway import interp2app, unwrap_spec, WrappedDefault
from rpython.rlib import jit


class W_Count(W_Root):
    def __init__(self, space, w_firstval, w_step):
        self.space = space
        self.w_c = w_firstval
        self.w_step = w_step

    def iter_w(self):
        return self

    def next_w(self):
        w_c = self.w_c
        self.w_c = self.space.add(w_c, self.w_step)
        return w_c

    def single_argument(self):
        space = self.space
        return (space.isinstance_w(self.w_step, space.w_int) and
                space.eq_w(self.w_step, space.newint(1)))

    def repr_w(self):
        space = self.space
        c = space.text_w(space.repr(self.w_c))
        if self.single_argument():
            s = 'count(%s)' % (c,)
        else:
            step = space.text_w(space.repr(self.w_step))
            s = 'count(%s, %s)' % (c, step)
        return self.space.newtext(s)

    def reduce_w(self):
        space = self.space
        if self.single_argument():
            args_w = [self.w_c]
        else:
            args_w = [self.w_c, self.w_step]
        return space.newtuple([space.gettypefor(W_Count),
                               space.newtuple(args_w)])

def check_number(space, w_obj):
    if (space.lookup(w_obj, '__int__') is None and
        space.lookup(w_obj, '__float__') is None):
        raise oefmt(space.w_TypeError, "expected a number")

@unwrap_spec(w_start=WrappedDefault(0), w_step=WrappedDefault(1))
def W_Count___new__(space, w_subtype, w_start, w_step):
    check_number(space, w_start)
    check_number(space, w_step)
    r = space.allocate_instance(W_Count, w_subtype)
    r.__init__(space, w_start, w_step)
    return r

W_Count.typedef = TypeDef(
        'itertools.count',
        __new__ = interp2app(W_Count___new__),
        __iter__ = interp2app(W_Count.iter_w),
        next = interp2app(W_Count.next_w),
        __reduce__ = interp2app(W_Count.reduce_w),
        __repr__ = interp2app(W_Count.repr_w),
        __doc__ = """Make an iterator that returns evenly spaced values starting
    with n.  If not specified n defaults to zero.  Often used as an
    argument to imap() to generate consecutive data points.  Also,
    used with izip() to add sequence numbers.

    Equivalent to:

    def count(start=0, step=1):
        n = start
        while True:
            yield n
            n += step
    """)


class W_Repeat(W_Root):
    def __init__(self, space, w_obj, w_times):
        self.space = space
        self.w_obj = w_obj

        if w_times is None:
            self.counting = False
            self.count = 0
        else:
            self.counting = True
            self.count = max(self.space.int_w(w_times), 0)

    def next_w(self):
        if self.counting:
            if self.count <= 0:
                raise OperationError(self.space.w_StopIteration, self.space.w_None)
            self.count -= 1
        return self.w_obj

    def iter_w(self):
        return self

    def length_w(self):
        if not self.counting:
            return self.space.w_NotImplemented
        return self.space.newint(self.count)

    def repr_w(self):
        objrepr = self.space.text_w(self.space.repr(self.w_obj))
        if self.counting:
            s = 'repeat(%s, %d)' % (objrepr, self.count)
        else:
            s = 'repeat(%s)' % (objrepr,)
        return self.space.newtext(s)

def W_Repeat___new__(space, w_subtype, w_object, w_times=None):
    r = space.allocate_instance(W_Repeat, w_subtype)
    r.__init__(space, w_object, w_times)
    return r

W_Repeat.typedef = TypeDef(
        'itertools.repeat',
        __new__          = interp2app(W_Repeat___new__),
        __iter__         = interp2app(W_Repeat.iter_w),
        __length_hint__  = interp2app(W_Repeat.length_w),
        next             = interp2app(W_Repeat.next_w),
        __repr__         = interp2app(W_Repeat.repr_w),
        __doc__  = """Make an iterator that returns object over and over again.
    Runs indefinitely unless the times argument is specified.  Used
    as argument to imap() for invariant parameters to the called
    function. Also used with izip() to create an invariant part of a
    tuple record.

    Equivalent to :

    def repeat(object, times=None):
        if times is None:
            while True:
                yield object
        else:
            for i in xrange(times):
                yield object
    """)


class W_TakeWhile(W_Root):
    def __init__(self, space, w_predicate, w_iterable):
        self.space = space
        self.w_predicate = w_predicate
        self.iterable = space.iter(w_iterable)
        self.stopped = False

    def iter_w(self):
        return self

    def next_w(self):
        if self.stopped:
            raise OperationError(self.space.w_StopIteration, self.space.w_None)

        w_obj = self.space.next(self.iterable)  # may raise a w_StopIteration
        w_bool = self.space.call_function(self.w_predicate, w_obj)
        if not self.space.is_true(w_bool):
            self.stopped = True
            raise OperationError(self.space.w_StopIteration, self.space.w_None)

        return w_obj

def W_TakeWhile___new__(space, w_subtype, w_predicate, w_iterable):
    r = space.allocate_instance(W_TakeWhile, w_subtype)
    r.__init__(space, w_predicate, w_iterable)
    return r


W_TakeWhile.typedef = TypeDef(
        'itertools.takewhile',
        __new__  = interp2app(W_TakeWhile___new__),
        __iter__ = interp2app(W_TakeWhile.iter_w),
        next     = interp2app(W_TakeWhile.next_w),
        __doc__  = """Make an iterator that returns elements from the iterable as
    long as the predicate is true.

    Equivalent to :

    def takewhile(predicate, iterable):
        for x in iterable:
            if predicate(x):
                yield x
            else:
                break
    """)


class W_DropWhile(W_Root):
    def __init__(self, space, w_predicate, w_iterable):
        self.space = space
        self.w_predicate = w_predicate
        self.iterable = space.iter(w_iterable)
        self.started = False

    def iter_w(self):
        return self

    def next_w(self):
        if self.started:
            w_obj = self.space.next(self.iterable)  # may raise w_StopIteration
        else:
            while True:
                w_obj = self.space.next(self.iterable)  # may raise w_StopIter
                w_bool = self.space.call_function(self.w_predicate, w_obj)
                if not self.space.is_true(w_bool):
                    self.started = True
                    break

        return w_obj

def W_DropWhile___new__(space, w_subtype, w_predicate, w_iterable):
    r = space.allocate_instance(W_DropWhile, w_subtype)
    r.__init__(space, w_predicate, w_iterable)
    return r


W_DropWhile.typedef = TypeDef(
        'itertools.dropwhile',
        __new__  = interp2app(W_DropWhile___new__),
        __iter__ = interp2app(W_DropWhile.iter_w),
        next     = interp2app(W_DropWhile.next_w),
        __doc__  = """Make an iterator that drops elements from the iterable as long
    as the predicate is true; afterwards, returns every
    element. Note, the iterator does not produce any output until the
    predicate is true, so it may have a lengthy start-up time.

    Equivalent to :

    def dropwhile(predicate, iterable):
        iterable = iter(iterable)
        for x in iterable:
            if not predicate(x):
                yield x
                break
        for x in iterable:
            yield x
    """)


class _IFilterBase(W_Root):
    def __init__(self, space, w_predicate, w_iterable):
        self.space = space
        if space.is_w(w_predicate, space.w_None):
            self.no_predicate = True
        else:
            self.no_predicate = False
            self.w_predicate = w_predicate
        self.iterable = space.iter(w_iterable)

    def iter_w(self):
        return self

    def next_w(self):
        while True:
            w_obj = self.space.next(self.iterable)  # may raise w_StopIteration
            if self.no_predicate:
                pred = self.space.is_true(w_obj)
            else:
                w_pred = self.space.call_function(self.w_predicate, w_obj)
                pred = self.space.is_true(w_pred)
            if pred ^ self.reverse:
                return w_obj


class W_IFilter(_IFilterBase):
    reverse = False

def W_IFilter___new__(space, w_subtype, w_predicate, w_iterable):
    r = space.allocate_instance(W_IFilter, w_subtype)
    r.__init__(space, w_predicate, w_iterable)
    return r

W_IFilter.typedef = TypeDef(
        'itertools.ifilter',
        __new__  = interp2app(W_IFilter___new__),
        __iter__ = interp2app(W_IFilter.iter_w),
        next     = interp2app(W_IFilter.next_w),
        __doc__  = """Make an iterator that filters elements from iterable returning
    only those for which the predicate is True.  If predicate is
    None, return the items that are true.

    Equivalent to :

    def ifilter:
        if predicate is None:
            predicate = bool
        for x in iterable:
            if predicate(x):
                yield x
    """)

class W_IFilterFalse(_IFilterBase):
    reverse = True

def W_IFilterFalse___new__(space, w_subtype, w_predicate, w_iterable):
    r = space.allocate_instance(W_IFilterFalse, w_subtype)
    r.__init__(space, w_predicate, w_iterable)
    return r

W_IFilterFalse.typedef = TypeDef(
        'itertools.ifilterfalse',
        __new__  = interp2app(W_IFilterFalse___new__),
        __iter__ = interp2app(W_IFilterFalse.iter_w),
        next     = interp2app(W_IFilterFalse.next_w),
        __doc__  = """Make an iterator that filters elements from iterable returning
    only those for which the predicate is False.  If predicate is
    None, return the items that are false.

    Equivalent to :

    def ifilterfalse(predicate, iterable):
        if predicate is None:
            predicate = bool
        for x in iterable:
            if not predicate(x):
                yield x
    """)


def get_printable_location(greenkey):
    return "islice_ignore_items [%s]" % (greenkey.iterator_greenkey_printable(), )
islice_ignore_items_driver = jit.JitDriver(name='islice_ignore_items',
                                           greens=['greenkey'],
                                           reds='auto',
                                           get_printable_location=get_printable_location)

class W_ISlice(W_Root):
    def __init__(self, space, w_iterable, w_startstop, args_w):
        self.iterable = space.iter(w_iterable)
        self.space = space

        num_args = len(args_w)

        if num_args == 0:
            start = 0
            w_stop = w_startstop
        elif num_args <= 2:
            if space.is_w(w_startstop, space.w_None):
                start = 0
            else:
                start = self.arg_int_w(w_startstop, 0,
                 "Indicies for islice() must be None or non-negative integers")
            w_stop = args_w[0]
        else:
            raise oefmt(space.w_TypeError,
                        "islice() takes at most 4 arguments (%d given)",
                        num_args)

        if space.is_w(w_stop, space.w_None):
            stop = -1
        else:
            stop = self.arg_int_w(w_stop, 0,
                "Stop argument must be a non-negative integer or None.")
            stop = max(start, stop)    # for obscure CPython compatibility

        if num_args == 2:
            w_step = args_w[1]
            if space.is_w(w_step, space.w_None):
                step = 1
            else:
                step = self.arg_int_w(w_step, 1,
                    "Step for islice() must be a positive integer or None")
        else:
            step = 1

        self.ignore = step - 1
        self.start = start
        self.stop = stop

    def arg_int_w(self, w_obj, minimum, errormsg):
        space = self.space
        try:
            result = space.int_w(space.int(w_obj))    # CPython allows floats as parameters
        except OperationError as e:
            if e.async(space):
                raise
            result = -1
        if result < minimum:
            raise OperationError(space.w_ValueError, space.newtext(errormsg))
        return result

    def iter_w(self):
        return self

    def next_w(self):
        if self.start >= 0:               # first call only
            ignore = self.start
            self.start = -1
        else:                             # all following calls
            ignore = self.ignore
        stop = self.stop
        if stop >= 0:
            if stop <= ignore:
                self.stop = 0   # reset the state so that a following next_w()
                                # has no effect any more
                if stop > 0:
                    self._ignore_items(stop)
                self.iterable = None
                raise OperationError(self.space.w_StopIteration,
                                     self.space.w_None)
            self.stop = stop - (ignore + 1)
        if ignore > 0:
            self._ignore_items(ignore)
        if self.iterable is None:
            raise OperationError(self.space.w_StopIteration, self.space.w_None)
        try:
            return self.space.next(self.iterable)
        except OperationError as e:
            if e.match(self.space, self.space.w_StopIteration):
                self.iterable = None
            raise

    def _ignore_items(self, num):
        w_iterator = self.iterable
        if w_iterator is None:
            raise OperationError(self.space.w_StopIteration, self.space.w_None)

        greenkey = self.space.iterator_greenkey(w_iterator)
        while True:
            islice_ignore_items_driver.jit_merge_point(greenkey=greenkey)
            try:
                self.space.next(w_iterator)
            except OperationError as e:
                if e.match(self.space, self.space.w_StopIteration):
                    self.iterable = None
                raise
            num -= 1
            if num <= 0:
                break

def W_ISlice___new__(space, w_subtype, w_iterable, w_startstop, args_w):
    r = space.allocate_instance(W_ISlice, w_subtype)
    r.__init__(space, w_iterable, w_startstop, args_w)
    return r

W_ISlice.typedef = TypeDef(
        'itertools.islice',
        __new__  = interp2app(W_ISlice___new__),
        __iter__ = interp2app(W_ISlice.iter_w),
        next     = interp2app(W_ISlice.next_w),
        __doc__  = """Make an iterator that returns selected elements from the
    iterable.  If start is non-zero, then elements from the iterable
    are skipped until start is reached. Afterward, elements are
    returned consecutively unless step is set higher than one which
    results in items being skipped. If stop is None, then iteration
    continues until the iterator is exhausted, if at all; otherwise,
    it stops at the specified position. Unlike regular slicing,
    islice() does not support negative values for start, stop, or
    step. Can be used to extract related fields from data where the
    internal structure has been flattened (for example, a multi-line
    report may list a name field on every third line).
    """)


class W_Chain(W_Root):
    def __init__(self, space, w_iterables):
        self.space = space
        self.w_iterables = w_iterables
        self.w_it = None

    def iter_w(self):
        return self

    def _advance(self):
        self.w_it = self.space.iter(self.space.next(self.w_iterables))

    def next_w(self):
        if not self.w_it:
            self._advance()
        try:
            return self.space.next(self.w_it)
        except OperationError as e:
            return self._handle_error(e)

    def _handle_error(self, e):
        while True:
            if not e.match(self.space, self.space.w_StopIteration):
                raise e
            self._advance() # may raise StopIteration itself
            try:
                return self.space.next(self.w_it)
            except OperationError as e:
                pass # loop back to the start of _handle_error(e)

def W_Chain___new__(space, w_subtype, args_w):
    r = space.allocate_instance(W_Chain, w_subtype)
    w_args = space.newtuple(args_w)
    r.__init__(space, space.iter(w_args))
    return r

def chain_from_iterable(space, w_cls, w_arg):
    """chain.from_iterable(iterable) --> chain object

    Alternate chain() constructor taking a single iterable argument
    that evaluates lazily."""
    r = space.allocate_instance(W_Chain, w_cls)
    r.__init__(space, space.iter(w_arg))
    return r

W_Chain.typedef = TypeDef(
        'itertools.chain',
        __new__  = interp2app(W_Chain___new__),
        __iter__ = interp2app(W_Chain.iter_w),
        next     = interp2app(W_Chain.next_w),
        from_iterable = interp2app(chain_from_iterable, as_classmethod=True),
        __doc__  = """Make an iterator that returns elements from the first iterable
    until it is exhausted, then proceeds to the next iterable, until
    all of the iterables are exhausted. Used for treating consecutive
    sequences as a single sequence.

    Equivalent to :

    def chain(*iterables):
        for it in iterables:
            for element in it:
                yield element
    """)


class W_IMap(W_Root):
    _error_name = "imap"
    _immutable_fields_ = ["w_fun", "iterators_w"]

    def __init__(self, space, w_fun, args_w):
        self.space = space
        if self.space.is_w(w_fun, space.w_None):
            self.w_fun = None
        else:
            self.w_fun = w_fun

        iterators_w = []
        i = 0
        for iterable_w in args_w:
            try:
                iterator_w = space.iter(iterable_w)
            except OperationError as e:
                if e.match(self.space, self.space.w_TypeError):
                    raise oefmt(space.w_TypeError,
                                "%s argument #%d must support iteration",
                                self._error_name, i + 1)
                else:
                    raise
            else:
                iterators_w.append(iterator_w)

            i += 1

        self.iterators_w = iterators_w

    def iter_w(self):
        return self

    def next_w(self):
        # common case: 1 or 2 arguments
        iterators_w = self.iterators_w
        length = len(iterators_w)
        if length == 1:
            objects = [self.space.next(iterators_w[0])]
        elif length == 2:
            objects = [self.space.next(iterators_w[0]),
                       self.space.next(iterators_w[1])]
        else:
            objects = self._get_objects()
        w_objects = self.space.newtuple(objects)
        if self.w_fun is None:
            return w_objects
        else:
            return self.space.call(self.w_fun, w_objects)

    def _get_objects(self):
        # the loop is out of the way of the JIT
        return [self.space.next(w_elem) for w_elem in self.iterators_w]


def W_IMap___new__(space, w_subtype, w_fun, args_w):
    if len(args_w) == 0:
        raise oefmt(space.w_TypeError,
                    "imap() must have at least two arguments")
    r = space.allocate_instance(W_IMap, w_subtype)
    r.__init__(space, w_fun, args_w)
    return r

W_IMap.typedef = TypeDef(
        'itertools.imap',
        __new__  = interp2app(W_IMap___new__),
        __iter__ = interp2app(W_IMap.iter_w),
        next     = interp2app(W_IMap.next_w),
        __doc__  = """Make an iterator that computes the function using arguments
    from each of the iterables. If function is set to None, then
    imap() returns the arguments as a tuple. Like map() but stops
    when the shortest iterable is exhausted instead of filling in
    None for shorter iterables. The reason for the difference is that
    infinite iterator arguments are typically an error for map()
    (because the output is fully evaluated) but represent a common
    and useful way of supplying arguments to imap().

    Equivalent to :

    def imap(function, *iterables):
        iterables = map(iter, iterables)
        while True:
            args = [i.next() for i in iterables]
            if function is None:
                yield tuple(args)
            else:
                yield function(*args)

    """)


class W_IZip(W_IMap):
    _error_name = "izip"

    def next_w(self):
        # argh.  izip(*args) is almost like imap(None, *args) except
        # that the former needs a special case for len(args)==0
        # while the latter just raises a TypeError in this situation.
        if len(self.iterators_w) == 0:
            raise OperationError(self.space.w_StopIteration, self.space.w_None)
        return W_IMap.next_w(self)

def W_IZip___new__(space, w_subtype, args_w):
    r = space.allocate_instance(W_IZip, w_subtype)
    r.__init__(space, space.w_None, args_w)
    return r

W_IZip.typedef = TypeDef(
        'itertools.izip',
        __new__  = interp2app(W_IZip___new__),
        __iter__ = interp2app(W_IZip.iter_w),
        next     = interp2app(W_IZip.next_w),
        __doc__  = """Make an iterator that aggregates elements from each of the
    iterables.  Like zip() except that it returns an iterator instead
    of a list. Used for lock-step iteration over several iterables at
    a time.

    Equivalent to :

    def izip(*iterables):
        iterables = map(iter, iterables)
        while iterables:
            result = [i.next() for i in iterables]
            yield tuple(result)
    """)


class W_IZipLongest(W_IMap):
    _error_name = "izip_longest"
    _immutable_fields_ = ["w_fillvalue"]

    def _fetch(self, index):
        w_iter = self.iterators_w[index]
        if w_iter is not None:
            space = self.space
            try:
                return space.next(w_iter)
            except OperationError as e:
                if not e.match(space, space.w_StopIteration):
                    raise
                self.active -= 1
                if self.active <= 0:
                    # It was the last active iterator
                    raise
                self.iterators_w[index] = None
        return self.w_fillvalue

    def next_w(self):
        # common case: 2 arguments
        if len(self.iterators_w) == 2:
            objects = [self._fetch(0), self._fetch(1)]
        else:
            objects = self._get_objects()
        return self.space.newtuple(objects)

    def _get_objects(self):
        # the loop is out of the way of the JIT
        nb = len(self.iterators_w)
        if nb == 0:
            raise OperationError(self.space.w_StopIteration, self.space.w_None)
        return [self._fetch(index) for index in range(nb)]

def W_IZipLongest___new__(space, w_subtype, __args__):
    arguments_w, kwds_w = __args__.unpack()
    w_fillvalue = space.w_None
    if kwds_w:
        if "fillvalue" in kwds_w:
            w_fillvalue = kwds_w["fillvalue"]
            del kwds_w["fillvalue"]
        if kwds_w:
            raise oefmt(space.w_TypeError,
                        "izip_longest() got unexpected keyword argument(s)")

    self = space.allocate_instance(W_IZipLongest, w_subtype)
    self.__init__(space, space.w_None, arguments_w)
    self.w_fillvalue = w_fillvalue
    self.active = len(self.iterators_w)

    return self

W_IZipLongest.typedef = TypeDef(
        'itertools.izip_longest',
        __new__  = interp2app(W_IZipLongest___new__),
        __iter__ = interp2app(W_IZipLongest.iter_w),
        next     = interp2app(W_IZipLongest.next_w),
        __doc__  = """Return an izip_longest object whose .next() method returns a tuple where
    the i-th element comes from the i-th iterable argument.  The .next()
    method continues until the longest iterable in the argument sequence
    is exhausted and then it raises StopIteration.  When the shorter iterables
    are exhausted, the fillvalue is substituted in their place.  The fillvalue
    defaults to None or can be specified by a keyword argument.
    """)


class W_Cycle(W_Root):
    def __init__(self, space, w_iterable):
        self.space = space
        self.saved_w = []
        self.w_iterable = space.iter(w_iterable)
        self.index = 0    # 0 during the first iteration; > 0 afterwards

    def iter_w(self):
        return self

    def next_w(self):
        if self.index > 0:
            if not self.saved_w:
                raise OperationError(self.space.w_StopIteration, self.space.w_None)
            try:
                w_obj = self.saved_w[self.index]
            except IndexError:
                self.index = 1
                w_obj = self.saved_w[0]
            else:
                self.index += 1
        else:
            try:
                w_obj = self.space.next(self.w_iterable)
            except OperationError as e:
                if e.match(self.space, self.space.w_StopIteration):
                    self.index = 1
                    if not self.saved_w:
                        raise
                    w_obj = self.saved_w[0]
                else:
                    raise
            else:
                self.saved_w.append(w_obj)
        return w_obj

def W_Cycle___new__(space, w_subtype, w_iterable):
    r = space.allocate_instance(W_Cycle, w_subtype)
    r.__init__(space, w_iterable)
    return r

W_Cycle.typedef = TypeDef(
        'itertools.cycle',
        __new__  = interp2app(W_Cycle___new__),
        __iter__ = interp2app(W_Cycle.iter_w),
        next     = interp2app(W_Cycle.next_w),
        __doc__  = """Make an iterator returning elements from the iterable and
    saving a copy of each. When the iterable is exhausted, return
    elements from the saved copy. Repeats indefinitely.

    Equivalent to :

    def cycle(iterable):
        saved = []
        for element in iterable:
            yield element
            saved.append(element)
        while saved:
            for element in saved:
                yield element
    """)


class W_StarMap(W_Root):
    def __init__(self, space, w_fun, w_iterable):
        self.space = space
        self.w_fun = w_fun
        self.w_iterable = self.space.iter(w_iterable)

    def iter_w(self):
        return self

    def next_w(self):
        w_obj = self.space.next(self.w_iterable)
        return self.space.call(self.w_fun, w_obj)

def W_StarMap___new__(space, w_subtype, w_fun, w_iterable):
    r = space.allocate_instance(W_StarMap, w_subtype)
    r.__init__(space, w_fun, w_iterable)
    return r

W_StarMap.typedef = TypeDef(
        'itertools.starmap',
        __new__  = interp2app(W_StarMap___new__),
        __iter__ = interp2app(W_StarMap.iter_w),
        next     = interp2app(W_StarMap.next_w),
        __doc__  = """Make an iterator that computes the function using arguments
    tuples obtained from the iterable. Used instead of imap() when
    argument parameters are already grouped in tuples from a single
    iterable (the data has been ``pre-zipped''). The difference
    between imap() and starmap() parallels the distinction between
    function(a,b) and function(*c).

    Equivalent to :

    def starmap(function, iterable):
        iterable = iter(iterable)
        while True:
            yield function(*iterable.next())
    """)


@unwrap_spec(n=int)
def tee(space, w_iterable, n=2):
    """Return n independent iterators from a single iterable.
    Note : once tee() has made a split, the original iterable
    should not be used anywhere else; otherwise, the iterable could get
    advanced without the tee objects being informed.

    Note : this member of the toolkit may require significant auxiliary
    storage (depending on how much temporary data needs to be stored).
    In general, if one iterator is going to use most or all of the
    data before the other iterator, it is faster to use list() instead
    of tee()

    If iter(iterable) has no method __copy__(), this is equivalent to:

    def tee(iterable, n=2):
        def gen(next, data={}, cnt=[0]):
            for i in count():
                if i == cnt[0]:
                    item = data[i] = next()
                    cnt[0] += 1
                else:
                    item = data[i]   # data.pop(i) if it's the last one
                yield item
        it = iter(iterable)
        return tuple([gen(it.next) for i in range(n)])

    If iter(iterable) has a __copy__ method, though, we just return
    a tuple t = (iterable, t[0].__copy__(), t[1].__copy__(), ...).
    """
    if n < 0:
        raise oefmt(space.w_ValueError, "n must be >= 0")

    if space.findattr(w_iterable, space.newtext("__copy__")) is not None:
        # In this case, we don't instantiate any W_TeeIterable.
        # We just rely on doing repeated __copy__().  This case
        # includes the situation where w_iterable is already
        # a W_TeeIterable itself.
        iterators_w = [w_iterable] * n
        for i in range(1, n):
            w_iterable = space.call_method(w_iterable, "__copy__")
            iterators_w[i] = w_iterable
    else:
        w_iterator = space.iter(w_iterable)
        chained_list = TeeChainedListNode()
        iterators_w = [W_TeeIterable(space, w_iterator, chained_list)
                       for x in range(n)]
    return space.newtuple(iterators_w)

class TeeChainedListNode(object):
    w_obj = None
    running = False


class W_TeeIterable(W_Root):
    def __init__(self, space, w_iterator, chained_list):
        self.space = space
        self.w_iterator = w_iterator
        assert chained_list is not None
        self.chained_list = chained_list

    def iter_w(self):
        return self

    def next_w(self):
        chained_list = self.chained_list
        if chained_list.running:
            raise oefmt(self.space.w_RuntimeError,
                        "cannot re-enter the tee iterator")
        w_obj = chained_list.w_obj
        if w_obj is None:
            chained_list.running = True
            try:
                w_obj = self.space.next(self.w_iterator)
            finally:
                chained_list.running = False
            chained_list.next = TeeChainedListNode()
            chained_list.w_obj = w_obj
        self.chained_list = chained_list.next
        return w_obj

    def copy_w(self):
        space = self.space
        tee_iter = W_TeeIterable(space, self.w_iterator, self.chained_list)
        return tee_iter

def W_TeeIterable___new__(space, w_subtype, w_iterable):
    # Obscure and undocumented function.  PyPy only supports w_iterable
    # being a W_TeeIterable, because the case where it is a general
    # iterable is useless and confusing as far as I can tell (as the
    # semantics are then slightly different; see the XXX in lib-python's
    # test_itertools).
    myiter = space.interp_w(W_TeeIterable, w_iterable)
    return W_TeeIterable(space, myiter.w_iterator, myiter.chained_list)

W_TeeIterable.typedef = TypeDef(
        'itertools._tee',
        __new__ = interp2app(W_TeeIterable___new__),
        __iter__ = interp2app(W_TeeIterable.iter_w),
        next     = interp2app(W_TeeIterable.next_w),
        __copy__ = interp2app(W_TeeIterable.copy_w),
        __weakref__ = make_weakref_descr(W_TeeIterable),
        )
W_TeeIterable.typedef.acceptable_as_base_class = False


class W_GroupBy(W_Root):
    def __init__(self, space, w_iterable, w_fun):
        self.space = space
        self.w_iterator = self.space.iter(w_iterable)
        if w_fun is None:
            w_fun = space.w_None
        self.w_keyfunc = w_fun
        self.w_tgtkey = None
        self.w_currkey = None
        self.w_currvalue = None

    def iter_w(self):
        return self

    def next_w(self):
        self._skip_to_next_iteration_group()
        w_key = self.w_tgtkey = self.w_currkey
        w_grouper = W_GroupByIterator(self, w_key)
        return self.space.newtuple([w_key, w_grouper])

    def _skip_to_next_iteration_group(self):
        space = self.space
        while True:
            if self.w_currkey is None:
                pass
            elif self.w_tgtkey is None:
                break
            else:
                if not space.eq_w(self.w_tgtkey, self.w_currkey):
                    break

            w_newvalue = space.next(self.w_iterator)
            if space.is_w(self.w_keyfunc, space.w_None):
                w_newkey = w_newvalue
            else:
                w_newkey = space.call_function(self.w_keyfunc, w_newvalue)

            self.w_currkey = w_newkey
            self.w_currvalue = w_newvalue

def W_GroupBy___new__(space, w_subtype, w_iterable, w_key=None):
    r = space.allocate_instance(W_GroupBy, w_subtype)
    r.__init__(space, w_iterable, w_key)
    return r

W_GroupBy.typedef = TypeDef(
        'itertools.groupby',
        __new__  = interp2app(W_GroupBy___new__),
        __iter__ = interp2app(W_GroupBy.iter_w),
        next     = interp2app(W_GroupBy.next_w),
        __doc__  = """Make an iterator that returns consecutive keys and groups from the
    iterable. The key is a function computing a key value for each
    element. If not specified or is None, key defaults to an identity
    function and returns the element unchanged. Generally, the
    iterable needs to already be sorted on the same key function.

    The returned group is itself an iterator that shares the
    underlying iterable with groupby(). Because the source is shared,
    when the groupby object is advanced, the previous group is no
    longer visible. So, if that data is needed later, it should be
    stored as a list:

       groups = []
       uniquekeys = []
       for k, g in groupby(data, keyfunc):
           groups.append(list(g))      # Store group iterator as a list
           uniquekeys.append(k)
    """)


class W_GroupByIterator(W_Root):
    def __init__(self, groupby, w_tgtkey):
        self.groupby = groupby
        self.w_tgtkey = w_tgtkey

    def iter_w(self):
        return self

    def next_w(self):
        groupby = self.groupby
        space = groupby.space
        if groupby.w_currvalue is None:
            w_newvalue = space.next(groupby.w_iterator)
            if space.is_w(groupby.w_keyfunc, space.w_None):
                w_newkey = w_newvalue
            else:
                w_newkey = space.call_function(groupby.w_keyfunc, w_newvalue)
            #assert groupby.w_currvalue is None
            # ^^^ check disabled, see http://bugs.python.org/issue30347
            groupby.w_currkey = w_newkey
            groupby.w_currvalue = w_newvalue

        assert groupby.w_currkey is not None
        if not space.eq_w(self.w_tgtkey, groupby.w_currkey):
            raise OperationError(space.w_StopIteration, space.w_None)
        w_result = groupby.w_currvalue
        groupby.w_currvalue = None
        groupby.w_currkey = None
        return w_result

W_GroupByIterator.typedef = TypeDef(
        'itertools._groupby',
        __iter__ = interp2app(W_GroupByIterator.iter_w),
        next     = interp2app(W_GroupByIterator.next_w))
W_GroupByIterator.typedef.acceptable_as_base_class = False


class W_Compress(W_Root):
    def __init__(self, space, w_data, w_selectors):
        self.space = space
        self.w_data = space.iter(w_data)
        self.w_selectors = space.iter(w_selectors)

    def iter_w(self):
        return self

    def next_w(self):
        # No need to check for StopIteration since either w_data
        # or w_selectors will raise this. The shortest one stops first.
        while True:
            w_next_item = self.space.next(self.w_data)
            w_next_selector = self.space.next(self.w_selectors)
            if self.space.is_true(w_next_selector):
                return w_next_item


def W_Compress__new__(space, w_subtype, w_data, w_selectors):
    r = space.allocate_instance(W_Compress, w_subtype)
    r.__init__(space, w_data, w_selectors)
    return r

W_Compress.typedef = TypeDef(
    'itertools.compress',
    __new__ = interp2app(W_Compress__new__),
    __iter__ = interp2app(W_Compress.iter_w),
    next     = interp2app(W_Compress.next_w),
    __doc__ = """Make an iterator that filters elements from *data* returning
   only those that have a corresponding element in *selectors* that evaluates to
   ``True``.  Stops when either the *data* or *selectors* iterables has been
   exhausted.
   Equivalent to::

       def compress(data, selectors):
           # compress('ABCDEF', [1,0,1,0,1,1]) --> A C E F
           return (d for d, s in izip(data, selectors) if s)
""")


class W_Product(W_Root):
    def __init__(self, space, args_w, w_repeat):
        self.gears = [
            space.unpackiterable(arg_w) for arg_w in args_w
        ] * space.int_w(w_repeat)
        #
        for gear in self.gears:
            if len(gear) == 0:
                self.lst = None
                break
        else:
            self.indices = [0] * len(self.gears)
            self.lst = [gear[0] for gear in self.gears]

    def _rotate_previous_gears(self):
        lst = self.lst
        x = len(self.gears) - 1
        lst[x] = self.gears[x][0]
        self.indices[x] = 0
        x -= 1
        # the outer loop runs as long as a we have a carry
        while x >= 0:
            gear = self.gears[x]
            index = self.indices[x] + 1
            if index < len(gear):
                # no carry: done
                lst[x] = gear[index]
                self.indices[x] = index
                return
            lst[x] = gear[0]
            self.indices[x] = 0
            x -= 1
        else:
            self.lst = None

    def fill_next_result(self):
        # the last gear is done here, in a function with no loop,
        # to allow the JIT to look inside
        lst = self.lst
        x = len(self.gears) - 1
        if x >= 0:
            gear = self.gears[x]
            index = self.indices[x] + 1
            if index < len(gear):
                # no carry: done
                lst[x] = gear[index]
                self.indices[x] = index
            else:
                self._rotate_previous_gears()
        else:
            self.lst = None

    def iter_w(self, space):
        return self

    def next_w(self, space):
        if self.lst is None:
            raise OperationError(space.w_StopIteration, space.w_None)
        w_result = space.newtuple(self.lst[:])
        self.fill_next_result()
        return w_result


def W_Product__new__(space, w_subtype, __args__):
    arguments_w, kwds_w = __args__.unpack()
    w_repeat = space.newint(1)
    if kwds_w:
        if 'repeat' in kwds_w:
            w_repeat = kwds_w['repeat']
            del kwds_w['repeat']
        if kwds_w:
            raise oefmt(space.w_TypeError,
                        "product() got unexpected keyword argument(s)")

    r = space.allocate_instance(W_Product, w_subtype)
    r.__init__(space, arguments_w, w_repeat)
    return r

W_Product.typedef = TypeDef(
    'itertools.product',
    __new__ = interp2app(W_Product__new__),
    __iter__ = interp2app(W_Product.iter_w),
    next = interp2app(W_Product.next_w),
    __doc__ = """
   Cartesian product of input iterables.

   Equivalent to nested for-loops in a generator expression. For example,
   ``product(A, B)`` returns the same as ``((x,y) for x in A for y in B)``.

   The nested loops cycle like an odometer with the rightmost element advancing
   on every iteration.  This pattern creates a lexicographic ordering so that if
   the input's iterables are sorted, the product tuples are emitted in sorted
   order.

   To compute the product of an iterable with itself, specify the number of
   repetitions with the optional *repeat* keyword argument.  For example,
   ``product(A, repeat=4)`` means the same as ``product(A, A, A, A)``.

   This function is equivalent to the following code, except that the
   actual implementation does not build up intermediate results in memory::

       def product(*args, **kwds):
           # product('ABCD', 'xy') --> Ax Ay Bx By Cx Cy Dx Dy
           # product(range(2), repeat=3) --> 000 001 010 011 100 101 110 111
           pools = map(tuple, args) * kwds.get('repeat', 1)
           result = [[]]
           for pool in pools:
               result = [x+[y] for x in result for y in pool]
           for prod in result:
               yield tuple(prod)
""")


class W_Combinations(W_Root):
    def __init__(self, space, pool_w, indices, r):
        self.pool_w = pool_w
        self.indices = indices
        self.r = r
        self.last_result_w = None
        self.stopped = r > len(pool_w)

    def get_maximum(self, i):
        return i + len(self.pool_w) - self.r

    def max_index(self, j):
        return self.indices[j - 1] + 1

    def descr__iter__(self, space):
        return self

    def descr_next(self, space):
        if self.stopped:
            raise OperationError(space.w_StopIteration, space.w_None)
        if self.last_result_w is None:
            # On the first pass, initialize result tuple using the indices
            result_w = [None] * self.r
            for i in xrange(self.r):
                index = self.indices[i]
                result_w[i] = self.pool_w[index]
        else:
            # Copy the previous result
            result_w = self.last_result_w[:]
            # Scan indices right-to-left until finding one that is not at its
            # maximum
            i = self.r - 1
            while i >= 0 and self.indices[i] == self.get_maximum(i):
                i -= 1

            # If i is negative, then the indices are all at their maximum value
            # and we're done
            if i < 0:
                self.stopped = True
                raise OperationError(space.w_StopIteration, space.w_None)

            # Increment the current index which we know is not at its maximum.
            # Then move back to the right setting each index to its lowest
            # possible value
            self.indices[i] += 1
            for j in xrange(i + 1, self.r):
                self.indices[j] = self.max_index(j)

            # Update the result for the new indices starting with i, the
            # leftmost index that changed
            for i in xrange(i, self.r):
                index = self.indices[i]
                w_elem = self.pool_w[index]
                result_w[i] = w_elem
        self.last_result_w = result_w
        return space.newtuple(result_w)

@unwrap_spec(r=int)
def W_Combinations__new__(space, w_subtype, w_iterable, r):
    pool_w = space.fixedview(w_iterable)
    if r < 0:
        raise oefmt(space.w_ValueError, "r must be non-negative")
    indices = range(len(pool_w))
    res = space.allocate_instance(W_Combinations, w_subtype)
    res.__init__(space, pool_w, indices, r)
    return res

W_Combinations.typedef = TypeDef("itertools.combinations",
    __new__ = interp2app(W_Combinations__new__),
    __iter__ = interp2app(W_Combinations.descr__iter__),
    next = interp2app(W_Combinations.descr_next),
    __doc__ = """\
combinations(iterable, r) --> combinations object

Return successive r-length combinations of elements in the iterable.

combinations(range(4), 3) --> (0,1,2), (0,1,3), (0,2,3), (1,2,3)""",
)

class W_CombinationsWithReplacement(W_Combinations):
    def __init__(self, space, pool_w, indices, r):
        W_Combinations.__init__(self, space, pool_w, indices, r)
        self.stopped = len(pool_w) == 0 and r > 0

    def get_maximum(self, i):
        return len(self.pool_w) - 1

    def max_index(self, j):
        return self.indices[j - 1]

@unwrap_spec(r=int)
def W_CombinationsWithReplacement__new__(space, w_subtype, w_iterable, r):
    pool_w = space.fixedview(w_iterable)
    if r < 0:
        raise oefmt(space.w_ValueError, "r must be non-negative")
    indices = [0] * r
    res = space.allocate_instance(W_CombinationsWithReplacement, w_subtype)
    res.__init__(space, pool_w, indices, r)
    return res

W_CombinationsWithReplacement.typedef = TypeDef(
    "itertools.combinations_with_replacement",
    __new__ = interp2app(W_CombinationsWithReplacement__new__),
    __iter__ = interp2app(W_CombinationsWithReplacement.descr__iter__),
    next = interp2app(W_CombinationsWithReplacement.descr_next),
    __doc__ = """\
combinations_with_replacement(iterable, r) --> combinations_with_replacement object

Return successive r-length combinations of elements in the iterable
allowing individual elements to have successive repeats.
combinations_with_replacement('ABC', 2) --> AA AB AC BB BC CC""",
)


class W_Permutations(W_Root):
    def __init__(self, space, pool_w, r):
        self.pool_w = pool_w
        self.r = r
        n = len(pool_w)
        n_minus_r = n - r
        if n_minus_r < 0:
            self.stopped = True
        else:
            self.stopped = False
            self.indices = range(n)
            self.cycles = range(n, n_minus_r, -1)

    def descr__iter__(self, space):
        return self

    def descr_next(self, space):
        if self.stopped:
            raise OperationError(space.w_StopIteration, space.w_None)
        r = self.r
        indices = self.indices
        w_result = space.newtuple([self.pool_w[indices[i]]
                                   for i in range(r)])
        cycles = self.cycles
        i = r - 1
        while i >= 0:
            j = cycles[i] - 1
            if j > 0:
                cycles[i] = j
                indices[i], indices[-j] = indices[-j], indices[i]
                return w_result
            cycles[i] = len(indices) - i
            n1 = len(indices) - 1
            assert n1 >= 0
            num = indices[i]
            for k in range(i, n1):
                indices[k] = indices[k+1]
            indices[n1] = num
            i -= 1
        self.stopped = True
        return w_result

def W_Permutations__new__(space, w_subtype, w_iterable, w_r=None):
    pool_w = space.fixedview(w_iterable)
    if space.is_none(w_r):
        r = len(pool_w)
    else:
        r = space.gateway_nonnegint_w(w_r)
    res = space.allocate_instance(W_Permutations, w_subtype)
    res.__init__(space, pool_w, r)
    return res

W_Permutations.typedef = TypeDef("itertools.permutations",
    __new__ = interp2app(W_Permutations__new__),
    __iter__ = interp2app(W_Permutations.descr__iter__),
    next = interp2app(W_Permutations.descr_next),
    __doc__ = """\
permutations(iterable[, r]) --> permutations object

Return successive r-length permutations of elements in the iterable.

permutations(range(3), 2) --> (0,1), (0,2), (1,0), (1,2), (2,0), (2,1)""",
)
