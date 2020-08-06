# opiniated decision to make sys/time/aio available everywhere to reduce scripting bloat / repl overhead
# if you don't agree, continue to write all your imports as usual :)

import sys
import builtins

builtins.LOGS = []


builtins.sys = sys
builtins.builtins = builtins

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


# force use a fixed, tested version of uasyncio to avoid non-determinism
from . import uasyncio
sys.modules['uasyncio'] = uasyncio


from . import fixes

# aio is a vital component make sure it is wide access.
import pythons.aio

from .python3 import *

# order last : this is expected to be a patched module
import time
builtins.time = time

if __UPY__:
    import embed

    core_argv = []
    core_kw = {}
    pycore = {'':undef}

    def reg(fn):
        pycore[fn.__name__] = fn

    @reg
    def pouet(*argv, **kw):
        print('Je suis "pouet", écrite en python et je suis chouette !')
        print('ma pile : ', argv)
        print('mes motclefs : ', kw)
        print('bye')

    @reg
    def pyc_excepthook(type, value, tb, **kw):
        print("pyc_excepthook",type, value, tb)

    def core_py(fn):
        global pycore, core_argv, core_kw
        fnex = pycore.get(fn, undef)
        print("(CorePy)%s(*%r,**%r) Calls" % (fn, core_argv, core_kw), fnex )
        try:
            return fnex(*core_argv, **core_kw)
        except:
            return undef
        finally:
            core_kw.clear()
            core_argv.clear()

    def core_pyv(v):
        #print('(CorePy)added', v)
        core_argv.append(v)

    embed.set_ffpy(core_py)
    embed.set_ffpy_add(core_pyv)
