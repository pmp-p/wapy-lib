# ❯❯❯


# still to solve :

# Python on android must use ashmem instead of shmem : https://bugs.python.org/issue31039

# https://github.com/pelya/android-shmem/issues/8

# Cross-build _curses failed if host ncurses headers and target ncurses headers have different layouts
# https://bugs.python.org/issue28190


import embed
import sys, os, builtins, time

import json


builtins.sys = sys
builtins.os = os
builtins.embed = embed
builtins.builtins = builtins


python3 = sys.modules[__name__]


# no dll/so hook when in host "emulator"
if not __UPY__:

    # setup exception display with same syntax as upy
    import traceback

    def print_exception(e, out=sys.stderr, **kw):
        kw["file"] = out
        traceback.print_exc(**kw)

    sys.print_exception = print_exception
    del print_exception

    # test for this implementation ctytpes support

    try:
        import ctypes
    except Exception as e:
        ctypes = None
        sys.print_exception(e)

    if hasattr(sys, "getandroidapilevel"):
        builtins.__EMU__ = False
        from .aosp import *
    else:
        print("running in host emulator or wasm")
        builtins.__EMU__ = True
        builtins.__ANDROID__ = not __EMSCRIPTEN__

    try:

        # javascript stdio
        if __EMSCRIPTEN__:
            import binascii

            original_stderr_fd = sys.stderr.fileno()
            original_stdout_fd = sys.stdout.fileno()

            class Redir(object):
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
                        self.flush()

                def flush(self):
                    s = "".join(self.buf)
                    #s = s.replace("\n", "↲")  # ¶
                    #s = s.replace("\n", "↲\r\n")
                    s = s.replace("\n", "\r\n")
                    if len(s):
                        #embed.cout(f'"sys.{self.channel}" : "{s}"')
                        value = binascii.hexlify(s.encode('utf-8')).decode('utf-8')
                        sys.__stdout__.write( json.dumps( { 1 : value } ) )
                        sys.__stdout__.write( "\n" )
                        sys.__stdout__.flush()
                    self.buf.clear()


                def __getattr__(self, attr):
                    if attr[0] == "_":
                        return object.__getattribute__(self, attr)
                    return getattr(self._file, attr)

            sys.stdout = Redir("1", sys.stdout)
            sys.stderr = Redir("2", sys.stderr)

        # android stdio
        elif not __EMU__:
            if ctypes:
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
            try:
                import Applications
                Applications.onCreate(Applications, python3)
            except:
                pass

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
        embed.log("190: %r" % e )



# =====================================================================



OneSec = time.Lapse(1)
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
