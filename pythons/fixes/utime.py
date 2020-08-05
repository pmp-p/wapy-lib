


if sys.version_info[0:2]>(3,7):
    MICROPY_PY_UTIME_TICKS_PERIOD = 2**30
    import time as _time
    attr = ("time", "sleep", "process_time", "localtime")
    def clock():
        return _time.process_time()
    sleep = _time.sleep

else:
    MICROPY_PY_UTIME_TICKS_PERIOD = const(2**30)
    import embed
    import utime as _time

    if embed.WAPY():
        attr = ("time", "clock", "localtime")
        def sleep(t):
            print("No Sleep till Brooklyn")
    else:
        attr = ("time", "sleep", "clock", "localtime")

for f in attr:
    globals()[f] = getattr(_time, f)


def sleep_ms(t):
    sleep(t / 1000)

def sleep_us(t):
    sleep(t / 1000000)

def ticks_ms():
    return int(_time.time() * 1000) & (MICROPY_PY_UTIME_TICKS_PERIOD - 1)

def ticks_us():
    return int(_time.time() * 1000000) & (MICROPY_PY_UTIME_TICKS_PERIOD - 1)

ticks_cpu = ticks_us

def ticks_add(t, delta):
    return (t + delta) & (MICROPY_PY_UTIME_TICKS_PERIOD - 1)

def ticks_diff(a, b):
    return ((a - b + MICROPY_PY_UTIME_TICKS_PERIOD // 2) & (MICROPY_PY_UTIME_TICKS_PERIOD - 1)) - MICROPY_PY_UTIME_TICKS_PERIOD // 2

del f, attr


class Lapse:
    def __init__(self, intv=1.0, oneshot=None):
        self.intv = int(intv * 1000000)
        self.next = self.intv
        self.last = _time.time() * 1000000
        if oneshot:
            self.shot = False
            return
        self.shot = None

    # FIXME: pause / resume(reset)

    def __bool__(self):
        if self.shot is True:
            return False

        t = _time.time() * 1000000
        self.next -= t - self.last
        self.last = t
        if self.next <= 0:
            if self.shot is False:
                self.shot = True
            self.next = self.intv
            return True

        return False
