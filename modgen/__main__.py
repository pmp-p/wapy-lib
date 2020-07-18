import sys
import os
import glob



def print_exception(e, out, **kw):
    kw['file'] = out
    __import__('traceback').print_exc(**kw)


sys.print_exception = print_exception

from . import *


USER_C_MODULES = os.environ.get('USER_C_MODULES','cmod')

for pym in glob.glob( os.path.join(USER_C_MODULES,'*.pym')):

    clines=["""/* http://github.com/pmp-p */"""]

    namespace = os.path.basename(pym)[:-4]

    with open(pym,'r') as source:
        pylines, codemap, cbodies = py2c( namespace, source, clines)


        print(f"Begin:====================== transpiling [{pym}] ========================")
        for l in pylines:
            print(l)


        code = '\n'.join(pylines)
        try:
            bytecode = compile( code, '<modgen>', 'exec')
        except Exception as e:
            print("================ %s ================" % pym)
            print(code)
            print("================================")
            sys.print_exception(e, sys.stderr)
            raise SystemExit(1)

        exec(bytecode,  __import__('__main__').__dict__, globals())

        cmod = module()
        cmod.__code__ = cbodies

        cmap = cify( cmod, namespace)

        table = cmap.pop(-1)

        print("== code map ==")
        while len(codemap):
            defname, prepend, append = codemap.pop()
            if defname in cmap:
                code,rti = cmap.pop( defname )
                print(defname,'pre=', prepend,'post=', append, len( code) )
                clines.insert(append, rti )
                clines.insert(prepend, code )
            else:
                print("error",defname)

        mod_dir = f"{USER_C_MODULES}/{namespace}"
        os.makedirs(mod_dir, exist_ok=True)
        with open(f"{mod_dir}/micropython.mk","w") as makefile:
            makefile.write(f"""
{namespace.upper()}_MOD_DIR := $(USERMOD_DIR)

# Add all C files to SRC_USERMOD.
SRC_USERMOD += $(wildcard $({namespace.upper()}_MOD_DIR)/*.c)

# add module folder to include paths if needed
CFLAGS_USERMOD += -I$({namespace.upper()}_MOD_DIR)
""")



        ctarget = f"{mod_dir}/mod{namespace}.c"
        print(f"End:====================== transpiled [{ctarget}] ========================")
        print()
        print()
        clines.append( table )

        with open(ctarget,'w') as code:
            for l in clines:
                print(l, file=code)




sys.exit(0)
