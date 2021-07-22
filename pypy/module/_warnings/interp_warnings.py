
from rpython.rlib import rutf8

from pypy.interpreter.gateway import unwrap_spec, WrappedDefault
from pypy.interpreter.error import OperationError, oefmt

def create_filter(space, w_category, action):
    return space.newtuple([
        space.newtext(action), space.w_None, w_category,
        space.w_None, space.newint(0)])

class State:
    def __init__(self, space):
        self.init_filters(space)
        self.w_once_registry = space.newdict()
        self.w_default_action = space.newtext("default")

    def init_filters(self, space):
        filters_w = []

        if (not space.sys.get_flag('py3k_warning') and
            not space.sys.get_flag('division_warning')):
            filters_w.append(create_filter(
                space, space.w_DeprecationWarning, "ignore"))

        filters_w.append(create_filter(
            space, space.w_PendingDeprecationWarning, "ignore"))
        filters_w.append(create_filter(
            space, space.w_ImportWarning, "ignore"))

        bytes_warning = space.sys.get_flag('bytes_warning')
        if bytes_warning > 1:
            action = "error"
        elif bytes_warning == 0:
            action = "ignore"
        else:
            action = "default"
        filters_w.append(create_filter(
            space, space.w_BytesWarning, action))

        self.w_filters = space.newlist(filters_w)

def get_warnings_attr(space, name):
    try:
        w_module = space.getitem(space.sys.get('modules'),
                                 space.newtext('warnings'))
    except OperationError as e:
        if not e.match(space, space.w_KeyError):
            raise
        return None

    try:
        return space.getattr(w_module, space.newtext(name))
    except OperationError as e:
        if not e.match(space, space.w_AttributeError):
            raise
    return None

def get_category(space, w_message, w_category):
    # Get category
    if space.isinstance_w(w_message, space.w_Warning):
        w_category = space.type(w_message)
    elif space.is_none(w_category):
        w_category = space.w_UserWarning

    # Validate category
    if not space.abstract_issubclass_w(w_category, space.w_Warning):
        raise oefmt(space.w_ValueError,
                    "category is not a subclass of Warning")

    return w_category

def setup_context(space, stacklevel):
    # Setup globals and lineno
    ec = space.getexecutioncontext()
    frame = ec.gettopframe_nohidden()
    while frame and stacklevel > 1:
        frame = ec.getnextframe_nohidden(frame)
        stacklevel -= 1
    if frame:
        w_globals = frame.get_w_globals()
        lineno = frame.get_last_lineno()
    else:
        w_globals = space.sys.w_dict
        lineno = 1

    # setup registry
    try:
        w_registry = space.getitem(w_globals, space.newtext("__warningregistry__"))
    except OperationError as e:
        if not e.match(space, space.w_KeyError):
            raise
        w_registry = space.newdict()
        space.setitem(w_globals, space.newtext("__warningregistry__"), w_registry)

    # setup module
    try:
        w_module = space.getitem(w_globals, space.newtext("__name__"))
    except OperationError as e:
        if not e.match(space, space.w_KeyError):
            raise
        w_module = space.newtext("<string>")

    # setup filename
    try:
        w_filename = space.getitem(w_globals, space.newtext("__file__"))
        filename = space.text_w(w_filename)
    except OperationError as e:
        if space.text_w(w_module) == '__main__':
            w_argv = space.sys.getdictvalue(space, 'argv')
            if w_argv and space.len_w(w_argv) > 0:
                w_filename = space.getitem(w_argv, space.newint(0))
                if not space.is_true(w_filename):
                    w_filename = space.newtext('__main__')
            else:
                # embedded interpreters don't have sys.argv
                w_filename = space.newtext('__main__')
        else:
            w_filename = w_module
    else:
        lc_filename = filename.lower()
        if (lc_filename.endswith(".pyc") or
            lc_filename.endswith(".pyo")):
            # strip last character
            w_filename = space.newtext(filename[:-1])

    return (w_filename, lineno, w_module, w_registry)

def check_matched(space, w_obj, w_arg):
    if space.is_w(w_obj, space.w_None):
        return True
    return space.is_true(space.call_method(w_obj, "match", w_arg))

def get_filter(space, w_category, w_text, lineno, w_module):
    w_filters = get_warnings_attr(space, "filters")
    if w_filters:
        space.fromcache(State).w_filters = w_filters
    else:
        w_filters = space.fromcache(State).w_filters

    # filters could change while we are iterating over it
    for w_item in space.fixedview(w_filters):
        w_action, w_msg, w_cat, w_mod, w_lineno = space.fixedview(
            w_item, 5)
        ln = space.int_w(w_lineno)

        if (check_matched(space, w_msg, w_text) and
            check_matched(space, w_mod, w_module) and
            space.abstract_issubclass_w(w_category, w_cat) and
            (ln == 0 or ln == lineno)):
            return space.text_w(w_action), w_item

    action = get_default_action(space)
    if not action:
        raise oefmt(space.w_ValueError, "warnings.defaultaction not found")
    return action, None

def get_default_action(space):
    w_action = get_warnings_attr(space, "defaultaction");
    if w_action is None:
        return space.text_w(space.fromcache(State).w_default_action)

    space.fromcache(State).w_default_action = w_action
    return space.text_w(w_action)

def get_once_registry(space):
    w_registry = get_warnings_attr(space, "onceregistry");
    if w_registry is None:
        return space.fromcache(State).w_once_registry

    space.fromcache(State).w_once_registry = w_registry
    return w_registry

def update_registry(space, w_registry, w_text, w_category):
    w_key = space.newtuple([w_text, w_category])
    return already_warned(space, w_registry, w_key, should_set=True)

def already_warned(space, w_registry, w_key, should_set=False):
    try:
        w_warned = space.getitem(w_registry, w_key)
    except OperationError as e:
        if not e.match(space, space.w_KeyError):
            raise
        if should_set:
            space.setitem(w_registry, w_key, space.w_True)
        return False
    else:
        return space.is_true(w_warned)

def normalize_module(space, w_filename):
    if not space.is_true(w_filename):
        return space.newtext("<unknown>")

    filename = space.text_w(w_filename)
    if filename.endswith(".py"):
        n = len(filename) - 3
        assert n >= 0
        filename = filename[:n]
    return space.newtext(filename)

def show_warning(space, w_filename, lineno, w_text, w_category,
                 w_sourceline=None):
    w_name = space.getattr(w_category, space.newtext("__name__"))
    w_stderr = space.sys.get("stderr")

    # Print "filename:lineno: category: text\n"
    try:
        message = "%s:%d: %s: %s\n" % (space.text_w(w_filename), lineno,
                                       space.text_w(w_name),
                                       space.text_w(w_text))
    except OperationError as e:
        if e.async(space):
            raise
        message = "%s:%d: %s: %s\n" % (space.utf8_w(w_filename), lineno,
                                        space.utf8_w(w_name),
                                        space.utf8_w(w_text))
        lgt = rutf8.check_utf8(message, True)
        w_message = space.newutf8(message, lgt)
    else:
        w_message = space.newtext(message)
    space.call_method(w_stderr, "write", w_message)

    # Print "  source_line\n"
    if not w_sourceline:
        try:
            # sourceline = linecache.getline(filename, lineno).strip()
            w_builtins = space.getbuiltinmodule('__builtin__')
            w_linecachemodule = space.call_method(w_builtins, '__import__',
                                                  space.newtext("linecache"))
            w_sourceline = space.call_method(w_linecachemodule, "getline",
                                             w_filename, space.newint(lineno))
            w_sourceline = space.call_method(w_sourceline, "strip")
        except OperationError:
            w_sourceline = None

    if not w_sourceline:
        return
    line = space.text_w(w_sourceline)
    if not line:
        return

    message = "\n"
    for i in range(len(line)):
        c = line[i]
        if c not in ' \t\014':
            message = "  %s\n" % (line[i:],)
            break
    space.call_method(w_stderr, "write", space.newtext(message))

def do_warn(space, w_message, w_category, stacklevel):
    context_w = setup_context(space, stacklevel)
    do_warn_explicit(space, w_category, w_message, context_w)

def do_warn_explicit(space, w_category, w_message, context_w,
                     w_sourceline=None):
    w_filename, lineno, w_module, w_registry = context_w

    # normalize module
    if space.is_w(w_module, space.w_None):
        w_module = normalize_module(space, w_filename)

    # normalize message
    if space.isinstance_w(w_message, space.w_Warning):
        w_text = space.str(w_message)
        w_category = space.type(w_message)
    elif (not space.isinstance_w(w_message, space.w_unicode) and
          not space.isinstance_w(w_message, space.w_bytes)):
        w_text = space.str(w_message)
        w_message = space.call_function(w_category, w_message)
    else:
        w_text = w_message
        w_message = space.call_function(w_category, w_message)

    w_lineno = space.newint(lineno)

    # create key
    w_key = space.newtuple([w_text, w_category, w_lineno])

    if not space.is_w(w_registry, space.w_None):
        if already_warned(space, w_registry, w_key):
            return
        # else this warning hasn't been generated before

    action, w_item = get_filter(space, w_category, w_text, lineno, w_module)

    if action == "error":
        raise OperationError(w_category, w_message)

    # Store in the registry that we've been here, *except* when the action is
    # "always".
    warned = False
    if action != 'always':
        if not space.is_w(w_registry, space.w_None):
            space.setitem(w_registry, w_key, space.w_True)
        if action == 'ignore':
            return
        elif action == 'once':
            if space.is_w(w_registry, space.w_None):
                w_registry = get_once_registry(space)
            warned = update_registry(space, w_registry, w_text, w_category)
        elif action == 'module':
            if not space.is_w(w_registry, space.w_None):
                warned = update_registry(space, w_registry, w_text, w_category)
        elif action != 'default':
            try:
                err = space.text_w(space.str(w_item))
            except OperationError:
                err = "???"
            raise oefmt(space.w_RuntimeError,
                        "Unrecognized action (%s) in warnings.filters:\n %s",
                        action, err)

    if warned:
        # Already warned for this module
        return
    w_show_fxn = get_warnings_attr(space, "showwarning")
    if w_show_fxn is None:
        show_warning(space, w_filename, lineno, w_text, w_category,
                     w_sourceline)
    else:
        space.call_function(
            w_show_fxn, w_message, w_category, w_filename, w_lineno)

@unwrap_spec(stacklevel=int)
def warn(space, w_message, w_category=None, stacklevel=1):
    w_category = get_category(space, w_message, w_category);
    do_warn(space, w_message, w_category, stacklevel)


def get_source_line(space, w_globals, lineno):
    if space.is_none(w_globals):
        return None

    # Check/get the requisite pieces needed for the loader.
    try:
        w_loader = space.getitem(w_globals, space.newtext("__loader__"))
        w_module_name = space.getitem(w_globals, space.newtext("__name__"))
    except OperationError as e:
        if not e.match(space, space.w_KeyError):
            raise
        return None

    # Make sure the loader implements the optional get_source() method.
    try:
        w_get_source = space.getattr(w_loader, space.newtext("get_source"))
    except OperationError as e:
        if not e.match(space, space.w_AttributeError):
            raise
        return None

    # Call get_source() to get the source code.
    w_source = space.call_function(w_get_source, w_module_name)
    if space.is_w(w_source, space.w_None):
        return None

    # Split the source into lines.
    w_source_list = space.call_method(space.w_text, "splitlines", w_source)

    # Get the source line.
    w_source_line = space.getitem(w_source_list, space.newint(lineno - 1))
    return w_source_line

@unwrap_spec(lineno=int, w_module = WrappedDefault(None),
             w_registry = WrappedDefault(None),
             w_module_globals = WrappedDefault(None))
def warn_explicit(space, w_message, w_category, w_filename, lineno,
                  w_module=None, w_registry=None, w_module_globals=None):

    w_source_line = get_source_line(space, w_module_globals, lineno)

    do_warn_explicit(space, w_category, w_message,
                     (w_filename, lineno, w_module, w_registry),
                     w_source_line)
