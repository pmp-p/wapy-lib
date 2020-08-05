# ❯❯❯

import sys
from ujson import loads, dumps
import uasyncio
from uasyncio import *

loop = get_event_loop()

q = {}
req = []
lio_listio = []
lio = {}
fds = {}


try:
    DBG = 'aio' in DBG
except:
    DBG = 0

WARNED = 0

IOCTL = []

# prevent running run_once in step at startup
error = True

def finalize():
    global q,req
    okdel = []
    for key in q:
        if not key in req:
            okdel.append( key )

    while len(okdel):
        key = okdel.pop()
        q.pop(key)

class Event(dict):
    def __getattr__(self,attr):
        return self[attr]

# BEWARE : THIS IS NOT AN ASYNC FUNCTION
def step(jsdata):
    global q,IOCTL, error, loop, fds

    #if len(jsdata)!=12:
    #    print("step",aio.error,jsdata)

    if not aio.error:
        try:
            jsdata =  loads(jsdata)
            try:
                q.update( jsdata )
                ioctl = q.get('ioctl',())
                if len(ioctl):
                    print("IOCTL",ioctl)
                    IOCTL.extend( ioctl )
            except Exception as e :
                sys.print_exception(e, sys.stderr)
                aio.error = True

            fdio = []
            for k,v in q.items():
                if k.startswith('#'):
                    fdio.append(k)

            while len(fdio):
                fdk = fdio.pop(0)
                ts, origin, data = q.pop(fdk)
                node = fds[fdk[1:]]
                # raw msg
                if isinstance(data, str):
                    data = [ fds.get(fdk,''), data ]
                    fds[fdk] = ''.join( data )
                    node.peek = len( fds[fdk] )
                # json
                else :
                    for client in node.clients.get('message',()):
                        client( Event({'source':node, 'data':data, 'origin':origin} ) )

            # try to prevent leaks with unconsummed data left
            if len(q)>30:
                finalize()
            # or fail
            if not WARNED and len(q) > 50:
                pdb("65:aio","q","big","discard")
                aio.error = True
        except Exception as e :
            aio.error = repr(e)
            embed.log("81: %s" % aio.error)
            embed.log("82:aio.step.error(%r)" % jsdata)
            sys.print_exception(e, sys.stderr)
            jsdata = {}

        # no ctx, call just set the async context
        with aio.ctx:
            loop.run_once()
    return None

# TODO: use nanoseconds
async def ctl(file, ev, tmout):
    global IOCTL
    fd = file.fileno()
    ioctl = "{}:{}".format((fd), (ev))
    print("94:AWAIT IOCTL", ioctl )
    stop_at = int(Time.time()*1_000 + tmout)
    while True:
        if ioctl in IOCTL:
            print("97:GOT IOCTL",ioctl)
            return True
        if int(Time.time()*1_000)>stop_at:
            break
        await aio.sleep_ms(16)
    return Exception('IOCTL.timeout')


def network():
    from aio.network import StreamReader, StreamWriter, start_server
    aio.StreamReader = StreamReader
    aio.StreamWriter = StreamWriter
    aio.start_server = start_server


async def Future(fildes, coro):
    aio.lio[fildes] = await coro

def await_for(coro, tmout):
    global loop
    embed.CLI()
    stop_at = int(Time.time() + tmout)
    fildes = id(coro)
    loop.create_task( Future(fildes, coro) )
    lio[fildes] = undef
    while lio.get(fildes) is undef:
        import aio_suspend
        if int(Time.time())>stop_at:
            print("136:await_for tmout")
            break
    embed.STI()
    return lio.pop(fildes)

def fsync(owner, coro, tmout ):
    global loop, lio, fds
    embed.CLI()
    fildes = id(owner)

    # TODO: use a io handler queue that can be rewritten in C
    loop.create_task( Future(fildes,coro) )

    stop_at = int(Time.time() + tmout)
    while lio.get( fildes, undef) is undef:
        import aio_suspend
        if int(Time.time())>stop_at:
            pdb("116:aio_fsync tmout")
            break

    embed.STI()
    result = lio.pop(fildes)
    if isinstance(result, Exception):
        raise result
    return result


class _:

    def __enter__(self):
        embed.CLI()

    def __exit__(self, type, value, traceback):
        embed.STI()

aio.block = _()

class _:
    def __enter__(self):
        embed.os_hideloop()

    def __exit__(self, type, value, traceback):
        embed.os_showloop()

aio.hide = _()


class _:
    def __enter__(self):
        embed.os_showloop()

    def __exit__(self, type, value, traceback):
        embed.os_hideloop()
aio.show = _()

class aioctx:
    def __init__(self, delta, coro):
        self.coro = coro
        self.tnext = Time.time() + delta
        self.tmout = 0

class _(list):
    current = None

    async def __aenter__(self):
        if self.__class__.current is None:
            self.__class__.current = aioctx(0, None)
        self.append(  self.__class__.current )
        self.__class__.current = None
        if self[-1].coro is not None:
            print("__aenter__ awaiting", self[-1].coro)
            return await self[-1].coro
        else:
            print('__aenter__ no coro')
            self.__class__.current = None
            return self

    async def __aexit__(self, type, value, traceback):
        len(self) and self.pop()

    def __enter__(self):
        self.append(0)

    def __exit__(self, type, value, traceback):
        len(self) and self.pop()

    def __bool__(self):
        if self.__class__.current:
            return True
        if len(self) and self[-1]:
            return True
        return False

    def __call__(self, frametime):
        print('__call__', len(self), frametime )
        self.__class__.current = aioctx(frametime, None)
        return self

    def call(self, coro) :
        print('.call', len(self), coro )
        if self.__class__.current is None:
            self.__class__.current = aioctx(0, coro)
        else:
            self.__class__.current.coro = coro
        #self.__class__.current.tmout = tmout
        return self

aio.ctx = _()


