import sys,typing

def npe():
    print('Null Pointer Exception')

void = typing.TypeVar('void')
mp_raw_code_t = typing.TypeVar('mp_raw_code_t*')
const_char_p = typing.TypeVar('const char*')
mp_obj_t = typing.TypeVar('mp_obj_t*')


class empty:pass

instance = empty()


def py2c(modname, source, clines):
    global namespace, instance
    header = len(clines)
    append = 0
    prepend = 0
    namespace = modname
    pylines = ["class module:"]

    defs = []
    defcount = 0
    isdef = ''
    defmap = []

    cbody = {}


    cls = []
    clscount = 0
    iscls = ''
    clsmap = []
    ancestor = ''

    def annotation_var(l):
        if '=' in l:
            head, tail = l.split('=',1)
        else:
            head = l
            tail = 'TODO_DEF_INIT'

        head = head.replace(' ','')
        tail = tail.strip()

        vname, vtype = head.split(':')
        return vname, vtype, tail



    def end_def():
        nonlocal isdef
        nonlocal iscls
        nonlocal cbody
        nonlocal append

        if isdef!='':
            trail = []
            while (not len(clines[-1].strip())) or (clines[-1].strip().startswith('//')):
                trail.insert(0,clines.pop() )

            if iscls:
                # record the whole function body for instrumentation in build_as_class()
                #cbody[isdef]['code'].append('//} end_def, generating return value\n')
                pass
            else:
                clines.append('} /* end_def-nocls %s */' % isdef)
                append = len(clines)
                clines.extend( trail )
                defmap.append( [ isdef, prepend,  append ] )
                print(defmap[-1])
            isdef = ''


    def end_class():
        nonlocal iscls
        if iscls != '':
            trail = []
            while (not len(clines[-1].strip())) or (clines[-1].strip().startswith('//')):
                trail.insert(0, clines.pop() )

            clines.append('/* end_class %s */' % iscls)
            append = len(clines)

            clines.extend( trail )

            clsmap.append( [ iscls, prepend, append ] )
            print(clsmap[-1])

            pylines.append(f"    {iscls} = {iscls}")

            iscls = ''

    def begin_def(defstart, pylines):
        nonlocal iscls
        nonlocal isdef
        nonlocal defcount
        nonlocal clines
        nonlocal cbody
        nonlocal l

        if l[:defstart].find('async ')>=0:
            tdef = 'async def'
        else:
            tdef = 'def'



        isdef, thedef = l[defstart:-1].split('(',1)

        isdef = isdef.strip()
        thedef = thedef.strip()


        pylines.append('')

        if iscls:
            pylines.append(f"        {tdef} {iscls}_{isdef}({thedef}: pass #{isdef}")
            isdef = iscls + '_' + isdef
            cbody.setdefault(isdef, { 'code' : [] , 'sync' : tdef == 'def' } )
        else:
            pylines.append(f"    {l} pass #{isdef}")
        pylines.append('')


        defcount+=1

        clines.append("/* begin_def #%s@%s %s  */" % (defcount, len(clines), isdef ))

        prepend = 1+len(clines)


    for l in source.readlines():
        l = l.rstrip()
        ls = l.strip()
        if len(ls) and ls[0] == "#":
            if ls.startswith('#include '):
                pass
            elif ls.startswith('#define '):
                pass
            elif ls.startswith('#error '):
                pass
            elif ls.startswith('#warning '):
                pass
            elif ls.startswith('#pragma '):
                pass
            elif ls.startswith('#define '):
                pass
            elif ls.startswith('#if'):
                pass
            elif ls.startswith('#else'):
                pass
            elif ls.startswith('#endif'):
                pass
            else:
                clines.append('//'+l[1:])
                continue

        if not len(ls):
            clines.append("")
            continue


        # no support for toplevel async, we need alloc for ctx state.

        if l.startswith('def ') or l.startswith('class '):
            end_def()
            end_class()

            if l.startswith('class '):

                iscls = l[6:].rsplit(':',1)[0].strip()


                if iscls.find('(')<=0:
                    iscls= iscls+'(object)'
                iscls, ancestor = iscls.split('(',1)
                ancestor = ancestor.rsplit(')')[0]



                pylines.append(f"    class {iscls}:")
                pylines.append(f"        __base__ = '{ancestor}'")
                pylines.append(f"        __ancestor__ = '{ancestor}'")

                clscount += 1
                clines.append("/* #%s@%s %s  */" % (clscount,len(clines),l[6:-1].strip() ))
                prepend = 1+len(clines)
                continue

            if l.startswith('def '):
                begin_def(len('def '), pylines)
                continue


        if iscls=='':
            clines.append(l)
            continue

        # we are inside a class definition => dataclasses / methods

        defsize = 0

        if ls.startswith('def '):
            defsize = len('def ')

        if ls.startswith('async def '):
            defsize = len('async def ')

        if defsize:
            end_def()
            begin_def(4+defsize, pylines)
            continue

        # a function body
        if iscls and isdef :
            pylines.append(f'#    {l}')
            cbody[isdef]['code'].append(l)
            continue

        #var annotations
        try:
            vname, vtype, vdef = annotation_var(l)
            pylines.append(f'        {vname}=("{vtype}", "{vdef}")')
            clines.append(f'// {iscls} -> {vname}=("{vtype}", "{vdef}")')
            continue
        # var with c type as strings or raw int
        except:
            pylines.append(f'    {l}')

    end_def()
    end_class()



    clines.insert(header, """/*
  %(namespace)s AUTO-GENERATED by %(name)s
*/


#include <string.h>
#include <stdio.h>
#include <stdlib.h> // for free()

#include "py/obj.h"
#include "py/runtime.h"

static void print(mp_obj_t str) {
    mp_obj_print(str, PRINT_STR);
    mp_obj_print(mp_obj_new_str_via_qstr("\\n",1), PRINT_STR);
}

static void null_pointer_exception(void){
    fprintf(stderr, "null pointer exception in function pointer call\\n");
}

STATIC mp_obj_t PyBytes_FromString(char *string){
    vstr_t vstr;
    vstr_init_len(&vstr, strlen(string));
    strcpy(vstr.buf, string);
    return mp_obj_new_str_from_vstr(&mp_type_bytes, &vstr);
}

#define None mp_const_none
#define bytes(cstr) PyBytes_FromString(cstr)
#define PyMethodDef const mp_map_elem_t
#define PyModuleDef const mp_obj_module_t

const char *nullbytes = "";
//static int orem_id = 0;

    """  % {'namespace': namespace, 'name': sys.argv[0]} )

    defmap.extend( clsmap )
    return pylines, defmap, cbody


