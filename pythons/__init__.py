# ❯❯❯

# opiniated decision to make sys/time/aio available everywhere to reduce scripting bloat / repl overhead
# if you don't agree, continue to write all your imports as usual :)

# be carefull order matter a lot in this file



import sys
import builtins
builtins.sys = sys
builtins.builtins = builtins

builtins.LOGS = []


def pdb(*argv, **kw):
    kw["file"] = sys.stderr
    print("\033[31mPYDEBUG>\033[0m ", *argv, **kw)

builtins.pdb = pdb


# those  __dunder__ are usually the same used in C conventions.

try:
    __UPY__
except:
    builtins.__UPY__ =  hasattr(sys.implementation,'mpy')

try:
    __EMSCRIPTEN__
except:
    builtins.__EMSCRIPTEN__ = sys.platform in ("asm.js", "wasm", "wasi")

try:
    __WASM__
except:
    builtins.__WASM__ = sys.platform in ("wasm", "wasi")

try:
    __ANDROID__
except:
    # this *is* the cpython way
    builtins.__ANDROID__ = hasattr(sys, "getandroidapilevel")




# this should be done in site.py / main.c but that's not easy for cpython.
# last chance to do it since required by aio.*
try:
    undefined
except:
    class sentinel:
        def __bool__(self):
            return False

        def __repr__(self):
            return '∅'

        def __nonzero__(self):
            return 0

        def __call__(self, *argv, **kw):
            if len(argv) and argv[0] is self:
                return True
            print('Null Pointer Exception')

    sentinel = sentinel()
    builtins.undefined = sentinel
    del sentinel



# force use a fixed, tested version of uasyncio to avoid non-determinism
if __UPY__:

    sys.modules['sys'] = sys
    sys.modules['builtins'] = builtins
    from . import uasyncio
else:
    from . import uasyncio_cpy as uasyncio

sys.modules['uasyncio'] = uasyncio



# check for embedding support or use an emulation from host script __main__ .

try:
    import embed
except:
    print("WARNING: embed module not found, using __main__ for it", file=sys.stderr)
    embed = __import__('__main__')

    try:
        embed.log
    except:
        pdb("CRITICAL: embed functions not found in __main__")
        embed.CLI = print
        embed.STI = print
        embed.log = print


sys.modules['embed'] = embed


# import possible fixes leveraring various python implementations.

from . import fixes




# aio is a vital component make sure it is wide access.
import pythons.aio

from .python3 import *

# order last : this is expected to be a patched module
import time
builtins.time = time


# allows to call from C, pyv(elem) adds elements to call stack
# eg from main.c:
#    pyv( mp_obj_get_type(ex) );
#    pyv( MP_OBJ_FROM_PTR(ex) );
#    pyv( MP_ROM_NONE );
#    mp_obj_t result = pycore("pyc_excepthook");
#


pyc_jump = {'':undefined}

def pycore(fn):
    global pyc_jump
    pyc_jump[fn.__name__] = fn

builtins.pycore = pycore


if __UPY__:
    import io
    sys.modules['io'] = io

    core_argv = []
    core_kw = {}

    format_list = []

    def __excepthook__(type, exc, tb, **kw):
        format_list = kw.get('format_list',[])
        fn = kw.get('file')
        ln = kw.get('line')

        print("_"*45)
        print('Traceback, most recent call : %s:%s' %( fn , ln ))
        while len(format_list):
            print(format_list.pop(0),end='')
        print("_"*45)

    excepthook = __excepthook__

    @pycore
    def pyc_test(*argv, **kw):
        print('pyc_test (pythons.__init__:103):')
        print('argv : ', argv)
        print('kw : ', kw)
        print('done')


    # should be set only interactive mode and moved into traceback module
#    last_type = None
#    last_value = None
#    last_traceback = None

    @pycore
    def pyc_excepthook(etype, exc, tb, **kw):
        # https://docs.python.org/3.8/library/traceback.html
#        last_value = exc
#        last_type = etype
        try:
            # FIXME: extracting that way may trips on inlined '\n'
            # ideally: make a list from C in "tb"
            buf = io.StringIO()
            sys.print_exception(exc, buf)
            buf.seek(0)
            fn = '<stdin>'
            ln = 1
            for line in buf.read().split('\n'):
                ls = line.strip()
                if not ls.startswith('Traceback '):
                    format_list.append(line+'\r\n')
                if ls and ls.startswith('File "'):
                    try:
                        fn,ln = ls.split('", line ',1)
                        ln = int(ln.split(',',1)[0])
                        fn = fn[7:-1]
                    except:
                        fn = '<stdin>'
                        ln = 1
            excepthook(etype, exc, tb, file=fn, line=ln, format_list=format_list)

        except Exception as e:
            print("_"*45)
            sys.print_exception(exc)
            print()
            print("Got another exception while printing exception:")
            print("_"*45)
            sys.print_exception(e)
            print("_"*45)
        finally:
            format_list.clear()

    # TODO check "undefined" from C to allow a default C handler to be used
    # when function is not found in jump table

    def core_py(fn):
        global pyc_jump, core_argv, core_kw
        fnex = pyc_jump.get(fn, undefined)
        #print("(CorePy)%s(*%r,**%r) Calls" % (fn, core_argv, core_kw), fnex )
        try:
            return fnex(*core_argv, **core_kw)
        except:
            return undefined
        finally:
            core_kw.clear()
            core_argv.clear()

    def core_pyv(v):
        #print('(CorePy)added', v)
        core_argv.append(v)

    embed.set_ffpy(core_py)
    embed.set_ffpy_add(core_pyv)
