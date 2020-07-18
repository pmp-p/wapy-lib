# still to solve :

# Python on android must use ashmem instead of shmem : https://bugs.python.org/issue31039

# https://github.com/pelya/android-shmem/issues/8

# Cross-build _curses failed if host ncurses headers and target ncurses headers have different layouts
# https://bugs.python.org/issue28190


import embed
import sys, os, builtins

import json


builtins.sys = sys
builtins.os = os
builtins.embed = embed
builtins.builtins = builtins

builtins.__UPY__ =  (sys.implementation.name != 'cpython')
#TODO: use embed.platform later to tell platform
builtins.__EMSCRIPTEN__ = sys.platform in ('emscripten','wasm')
builtins.__WASM__ = sys.platform in ('wasi')

if not __UPY__:
    import traceback

builtins.use = sys.modules[__name__]
lives = True

def pdb(*argv, **kw):
    kw["file"] = sys.stderr
    print("\033[31mPYDEBUG>\033[0m ", *argv, **kw)

builtins.pdb = pdb
python3 = sys.modules[__name__]


# no dll/so hook when in host "emulator"
if not __UPY__:

    if hasattr(sys, "getandroidapilevel"):
        builtins.__EMU__ = False
        builtins.__ANDROID__ = True
        # would only works for root
        # sys.path.insert(0,"/data/data/{{ cookiecutter.bundle }}.{{ cookiecutter.module_name }}/usr/lib/pythons.7/lib-dynload")

        # so use importlib

        import importlib
        import importlib.abc
        import importlib.machinery

        class ApkLibFinder(importlib.abc.MetaPathFinder):
            @classmethod
            def find_spec(cls, name, path=None, target=None):
                try:
                    lib = f"{os.environ['DYLD']}/lib{name}.so"
                    os.stat(lib)
                    pdb(f"ApkLibFinder found : {lib}")
                    loader = importlib.machinery.ExtensionFileLoader(name, path)
                    return importlib.machinery.ModuleSpec(name=name, loader=loader, origin=lib)

                except FileNotFoundError:
                    return None

        sys.meta_path.append(ApkLibFinder)
    else:
        print("running in host emulator or wasm")
        builtins.__EMU__ = True
        builtins.__ANDROID__ = not __EMSCRIPTEN__

    try:
        import ctypes


        import os

        if not __EMU__:

            try:
                builtins.libc = ctypes.CDLL("libc.so")
            except OSError:
                pass

            original_stderr_fd = sys.stderr.fileno()
            original_stdout_fd = sys.stdout.fileno()

            class LogFile(object):
                def __init__(self, channel, file):
                    self.channel = channel
                    self._file = file  # no = fileno
                    self.buf = []

                def write(self, s):
                    self.buf.append(s)
                    # classic buffers behaviour
                    # if self.buf[-1].find('\n')>=0:

                    # wanted behaviour
                    if self.buf[-1].endswith("\n"):
                        s = "".join(self.buf)
                        s = s.replace("\n", "↲")  # ¶
                        if len(s):
                            embed.cout(f"sys.{self.channel}: {s}")
                        self.buf.clear()

                def flush(self):
                    return

                def __getattr__(self, attr):
                    if attr[0] == "_":
                        return object.__getattribute__(self, attr)
                    return getattr(self._file, attr)

            sys.stdout = LogFile("stdout", sys.stdout)
            sys.stderr = LogFile("stderr", sys.stderr)

        def print_exception(e, out=sys.stderr, **kw):
            kw["file"] = out
            traceback.print_exc(**kw)

        sys.print_exception = print_exception
        del print_exception

        try:
            # add the pip packages folder or in-apk
            addsys = []
            ipos = 0
            for pos, syspath in enumerate(sys.path):
                if syspath.endswith("/assets"):
                    addsys.append(f"{syspath}/packages")
                    if not ipos:
                        ipos = pos

            print("sys.path=", sys.path)
            while len(addsys):
                sys.path.insert(ipos + 1, addsys.pop(0))
                print(f" -> added {sys.path[ipos+1]}")
            del addsys

            import Applications
            Applications.onCreate(Applications, python3)

            if not __EMU__:
                for k in os.environ:
                    print(f"    {k} = '{os.environ[k]}'")

        except Exception as e:


            embed.log(f"FATAL: {__file__.split('assets/')[-1]} {e}")
            sys.print_exception(e)

    except Exception as e:
        try:
            sys.print_exception(e)
        except:
            embed.log("161: %r" % e )

    import time as Time
else:

    import utime as Time

import pythons.aio
import pythons.aio.plink

# TODO: in case of failure to create "Application" load a safe template
# that could display the previous tracebacks

try:
    Applications
    try:
        from Applications import MainActivity
        State = MainActivity.plink.CallPath.proxy
    except Exception as e:
        try:
            sys.print_exception(e)
        except:
            embed.log("182: %r" % e )

except:

    class Applications:
        @staticmethod
        def onCreate(self, pyvm):
            print("onCreate", pyvm)
        @staticmethod
        def onStart(self, pyvm):
            print("onStart", pyvm)
        @staticmethod
        def onPause(self, pyvm):
            print("onPause", pyvm)
        @staticmethod
        def onResume(self, pyvm):
            print("onResume", pyvm)
        @staticmethod
        def onStop(self, pyvm):
            print("onStop", pyvm)
        @staticmethod
        def onDestroy(self, pyvm):
            print("onDestroy", pyvm)

    builtins.Applications = Applications

try:
    State = pythons.aio.plink.CallPath.proxy
except Exception as e:
    try:
        sys.print_exception(e)
    except:
        embed.log("214: %r" % e )




import pythons.aio as aio

# aio is a vital component make sure it is wide access.
builtins.aio = aio
# =====================================================================


class Lapse:
    def __init__(self, intv=1.0, oneshot=None):
        self.intv = int(intv * 1000000)
        self.next = self.intv
        self.last = Time.time() * 1000000
        if oneshot:
            self.shot = False
            return
        self.shot = None

    # FIXME: pause / resume(reset)

    def __bool__(self):
        if self.shot is True:
            return False

        t = Time.time() * 1000000
        self.next -= t - self.last
        self.last = t
        if self.next <= 0:
            if self.shot is False:
                self.shot = True
            self.next = self.intv
            return True

        return False


class GenClass:
    def __init__(self, cn, ip):
        self.cn = cn
        self.ip = ip


OneSec = Lapse(1)
lastc = 0
wall_s = 0
tested = False
jcount = 0
errored = []

def error(self, *msg):
    pdb(*msg)


def dispatch(jsonargs):
    global errored

    if isinstance(jsonargs, str):
        method, argv = json.loads(jsonargs)
    else:
        method = jsonargs.pop(0)
        argv = jsonargs

    callstack = []

    if isinstance(method, str):
        if not method in errored:
            rv = None
            if hasattr(Applications, method):
                try:
                    rv = getattr(Applications, method)(Applications, python3, *argv)
                except Exception as e:
                    errored = True
                    try:
                        sys.print_exception(e)
                    except:
                        embed.log("292: %r" % e )

                # maybe use rv to select ui/non ui
                # if rv is not None:
                #    callstack.append( rv )

            else:
                errored.append( method )
                print("300: *************** FAIL: dispatch '{}'".format(method), jsonargs)
    else:
        print("303: RPC garbage")

    try:
        # normal calls can go on all threads
        callstack.extend(State.q_sync)
        if State.ui:
            callstack.extend(State.q_async)
        embed.run(json.dumps(callstack))

    finally:
        State.q_sync.clear()
        if State.ui:
            State.q_async.clear()
            # State.ui = False


def on_event(apps, p3, evid):
    evh = MainActivity.Events.ld.get(evid, None)
    if evh is None:
        print("event ignored : ", evid)
        return
    sender, target, handler, hint = evh
    # aio.task( handler, MainActivity, sender, target, hint )
    # aio.loop.create_task( handler(MainActivity, sender, target, hint) )
    aio.loop.create_task(handler(sender, target, hint))


def onui(apps, p3, *in_queue):
    State.ui = True
    if len(State.q_ui):
        print("onui", State.q_ui)

def onmouse(apps, p3, *in_queue ):
    print(in_queue)


def on_step(apps, p3):
    global OneSec, wall_s, lastc, tested, jcount
    jcount += 1

    if OneSec:
        wall_s += 1
        if wall_s == 3 and not tested:
            if os.path.isdir(f"assets/python{sys.version_info.major}.{sys.version_info.minor}/test"):
                print("starting testsuite")
                import test.__main__
            else:
                embed.log("============= THE TEST : Begin =================")
                aio.loop.create_task(MainActivity.__main__())
                tested = True

        if wall_s == 10:
            print("FPS ", (jcount - lastc) / wall_s)
            lastc = jcount + 1
            wall_s = 0
            libc.puts(b"c.status = %d" % jcount)
            print(f"step {jcount}")
    try:
        aio.step()
    except Exception as e:
        print("Error:", e)
        sys.print_exception(e)

try:
    # bind default handler to applications framework if not overridden
    for attr in ('onui','onmouse','on_event','on_step'):
        if not hasattr(Applications, attr):
            setattr(Applications, attr, getattr(python3,attr) )

except:
    builtins.Applications = python3
