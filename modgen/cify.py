import sys, typing

def npe():
    print('Null Pointer Exception')

void = typing.TypeVar('ptr')



def read_stack(T, IDX, name ):
    if T in ['int','float']:
        return f'    if (argc>{IDX}) {name} = mp_obj_get_{T}(argv[{IDX}]);'

    if T=='str':
        return f'    if (argc>{IDX}) {name} = mp_obj_new_str_via_qstr(argv[{IDX}],strlen(argv[{IDX}]));'

    return f'// if (argc>{IDX}) {name} = mp_obj_get_<<<{T}>>>(argv[{IDX}]);'


def indent(n,t):
    lt = []
    for l in t.split('\n'):
        lt.append( ' '*n + l)
    return '\n'.join(lt)



def read_init(IDX, T, name, V):

    if T == void.__name__:
        if V in (None,npe,):
            return f"""
    void (*{name})(void);
    if (argc>{IDX})
        {name} = (void*)argv[{IDX}] ;
    else {name} = &null_pointer_exception;

"""

    if T in ['int','float']:
            return f"""
    int {name};
    if (argc>{IDX})
        {name} = mp_obj_get_{T}(argv[{IDX}]);
    else {name} = {V} ;

"""

    if T=='str':
        val = repr(V)
        if val[0]=="'":
            val = '"%s"' % val[1:-1]
        return f"""
    mp_obj_t {name};
    if (argc>{IDX})
        {name} = (mp_obj_t*)argv[{IDX}];
    else {name} =  mp_obj_new_str_via_qstr({val},{len(V)});

"""
    if T=='const char*':
        val = repr(V)
        if val[0]=="'":
            val = '"%s"' % val[1:-1]
        return f"""
    const char *{name};
    if (argc>{IDX})
        {name} = mp_obj_str_get_str(argv[{IDX}]);
    else
        {name} = mp_obj_new_str_via_qstr({val},{len(V)});
"""

    V = 'NULL';
    return f"""
    {T} {name};
    if (argc>{IDX})
        {name} = ({T})argv[{IDX}];
    else {name} = {V} ;

"""

def make_c_type(tc, default=None):

    if isinstance(tc,typing.TypeVar):
        tc=repr(tc)
    elif isinstance(tc, str):
        pass
    else:
        tc = tc.__name__

    if tc[0]=='~':
        tc = tc [1:]

    if tc.endswith('_p'):
        tc = tc[:-2]+' *'
        default = 'NULL'

    if tc=='ptr':
        tc='mp_obj_t'
        default = 'mp_const_none'

    return tc, default

def cvar_any(name, obj ):
    init_line = ''
    if isinstance(obj, str):
        decl = f'    {obj} {name};'
    else:
        if isinstance(obj, tuple):
            tc, defv = make_c_type( obj[0], obj[1] )
            decl = f'    {tc} {name};'
            init_line = f'    this->{name} = {defv};\n'
        else:
            decl=f'//?    {name} {repr(obj)};'
    return decl, init_line

def annotation_rt(ann):
    # ann.__name__
    prefix = 'STATIC mp_obj_t '

    tc, defv = make_c_type(ann)

    tp = tc

# TODO: use mp_types
    if tc in ('int','long','unsigned long'):
        tp = 'int'

    if tc in ('float','double'):
        tp = 'double'

    if tc in ('bytes',):
        tc = 'char *'
        tp = 'bytes'
        defv = '(char *)nullbytes'

    if tc in ('str',):
        tc = 'const char *'
        tp = 'qstr'
    return prefix, tc, tp, defv



def annotation_stack(ann):
    stack = []
    for vname, ctype in ann.items():
        tc, defv = make_c_type( str(ctype) )
        stack.append( f'{tc} {vname}')
    return ', '.join(stack)



def block_from_c_value(prefix, rtp):
    body = []
    if rtp == 'int':
        body.append(f'{prefix} mp_obj_new_int(__creturn__);')
    elif rtp == 'bytes':
        body.append(f'{prefix} PyBytes_FromString(__creturn__);')
    elif rtp == 'qstr':
        body.append(f'{prefix} MP_OBJ_NEW_QSTR(qstr_from_str(__creturn__));')
    else:
        body.append(f'{prefix} (mp_obj_t)__creturn__ ;')
    return body[-1]



def comment_blocks(in_comment, body, cls, clr, cline):
    # /* */ comments block
    while 1:
        if in_comment:
            if cls.endswith('*/'):
                in_comment = False
                body.append( cline  )
            else:
                body.append("# " + cline)
                break

        if not cls:
            body.append('')
            break

        if cls.startswith('/*'):
            in_comment = True
            body.append( cline  )
            break

        # single line comment
        if cls.startswith('//'):
            body.append( cline  )
            break

        if cls.startswith('#'):
            body.append( '//' + cline[1:]  )

        break

    return in_comment

# TODO: use a proper parser
def self_line(cline):
    #return cline.replace('self.','(*self).')
    return cline.replace('self.','self->')


def cify(instance, namespace=None):


    def build_method_block(nscname, cname, cdef):
        meth = []
        meth_table = ([],[])

        while len(cdef):
            name, func = cdef.pop(0)
            ann = dict( **func.__annotations__ )
            rt_ann = ann.pop('return',None)
            rt_prefix, rtc, rtp, rt_default = annotation_rt(rt_ann)
            stack_ann = annotation_stack(ann)

            cfunc = [ f'''
{rt_prefix} // {stack_ann or "()"} -> {rt_ann}
{namespace}_{name}(size_t argc, const mp_obj_t *argv) {{ '''
            ]

            fname = name[len(cname):] # _funcname


            if rt_default is not None:
                cfunc.append(f'    {rtc} __creturn__ = {rt_default};')
            else:
                cfunc.append(f'    {rtc} __creturn__;')

# TODO: optim creturn blocks when no finally
            opt_preturn = len(cfunc);
            cfunc.append(f'    mp_obj_t __preturn__;')

            fnextra = instance.__code__.pop(name)

            cfunc.append(f'''
    {nscname}_obj_t *self = ({nscname}_obj_t *)MP_OBJ_TO_PTR(argv[0]);
    (void)self;
''')

            if fnextra['sync']:
                pass
            else:
                cfunc.append('    // TODO: async : resume with go after last yield ')



            argv = []

            item_pos = 0

# 1+ len(argv), self is implicit : this allow simpler conversion from module code to class code.
# TODO: what about classmethod 1+len(argv) /staticmethod len(argv) ?
            decal_stack = 1
            for item_pos,(k,v) in enumerate( ann.items()):
                if not item_pos:
                    cfunc.append('\n    // extract c-stack / set default values')
                cfunc.append( indent(4, read_init(decal_stack+item_pos, v.__name__, k, func.__defaults__[item_pos])) )
                argv.append(v.__name__)


            meth_table[0].append(f'''
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN({namespace}_{name}_obj,
    0, {decal_stack+len(argv)}, {namespace}_{name});
''')
            meth_table[1].append(f'''
    {{ MP_OBJ_NEW_QSTR(MP_QSTR{fname}), (mp_obj_t)&{namespace}_{name}_obj }},
''')

            lblname = 'lreturn__'

            in_comment = False
            in_try = False
            in_return = False
            in_finally = False
            last_indent = 0
            cur_indent = 0
            brace_close = []
            body = ['\n    // ------- method body --------']

            for cline in fnextra.pop('code'):


                cline = self_line(cline)

                cls = cline.lstrip()
                clr = cline.rstrip()
                clstrip = cline.strip().replace('  ',' ').replace(' :',':')
                was_comment = in_comment
                in_comment = comment_blocks(in_comment, body, cls, clr, cline)
                if was_comment or in_comment:
                    continue


                # code handling

                cur_indent= len(cline) - len(cls)
                if not last_indent:
                    last_indent = cur_indent

# TODO: check for comments after ':'
                if clstrip.endswith(':'):
                    # TODO: add missing () for  if/while
                    for x in ('if','while'):
                        if clstrip.startswith(f'{x} '):
                            if not clstrip.startswith(f'{x} ('):
                                cline = cline[:-1].replace(f'{x} ',f'{x} (',1)+'):'

                    # transform self. into (*self).  or self->
                    # cline = self_line(cline)

                    last_indent = cur_indent
                    if clstrip =='try:':
                        cline = ' ' * cur_indent + '{ //try:'
                        in_try = True
                    elif clstrip =='finally:':
                        # finally blocks are dedents too
                        if len(brace_close):
                            body.append(brace_close.pop() )
                            last_indent = cur_indent

                        cline = ' ' * cur_indent + '{ //finally:\n'
                        cline += ' ' * cur_indent + block_from_c_value("    __preturn__ = ", rtp)
                        in_try = False
                        in_finally = True
                    else:
                        cline = cline[:-1] + ' {'
                    brace_close.append(  f"{' '*last_indent}}}" )

                else:
                    # transform self. into (*self).  or self->
                    # cline = self_line(cline)
                    if cur_indent > last_indent:
                        # indenting, memorize the new block indentation
                        last_indent = cur_indent
                    elif cur_indent < last_indent:
                        # we dedent : close the last block
                        if len(brace_close):
                            body.append(brace_close.pop() )
                            last_indent = cur_indent
                    else:
                        # we are in same indent block
                        #TODO: raise if finally
                        pass

# TODO: check for end line comments what would be after missing ';'
                    if not clr.endswith('([{,"\''):
                        cline = clr.rstrip(';').rstrip()

                        if cls.startswith('return '):

                            if in_try:
                                cline = cline.replace('return ',f'__creturn__ = ({rtc})')
                            else:
                                cline = cline.replace('return ',f'{{ __creturn__ = ({rtc})')
                                cline += '; goto lreturn__; }';

                        cline = cline + ';'

                body.append( cline  )

            while len( brace_close ):
                body.append(brace_close.pop())

            if in_finally:
                # late return final type
                body.append("return __preturn__;")
            else:
                #remove the useless Py type pointer conversion.
                cfunc.pop(opt_preturn)
                body.append( block_from_c_value(f'{lblname}: return', rtp) )

# TODO: remove __creturn__ for (void) that always return mp_const_none

            body.append('}')

            cfunc.extend( body )

            meth.append( '\n'.join(cfunc) )


        return '\n'.join( meth ), ''.join(meth_table[0]),''.join(meth_table[1])








    def build_as_class(clsdef):
        nonlocal class_table
        nonlocal cmap

        cstruct = clsdef()
        cname = clsdef.__name__

        nscname = f'{namespace}_{cname}'

        class_table.append(f"""// {cname} class""")
        class_table.append(f"""    {{MP_OBJ_NEW_QSTR(MP_QSTR_{cname}), (mp_obj_t)&{nscname}_type }},""")

        proto = [f"""typedef struct _{nscname}_obj_t {{"""]
        proto.append('    mp_obj_base_t base;')

        cvar = []
        cdef = []
        init_lines = []

        for name in dir(cstruct):
            if name[0]!='_':
                cobj = getattr( cstruct, name )
                if isinstance(cobj, (list, tuple,str,int) ):
                    cvar.append( [name,cobj] )
                else:
                    cdef.append( [name, cobj] )

        while len(cvar):
            name,obj = cvar.pop(0)
            decl, init_line = cvar_any(name,obj)
            proto.append( decl )
            init_lines.append(init_line)

        proto.append(f"""}} {nscname}_obj_t;""")


        proto.append(f"""
""")

        # forward decl of type + ctor

        # m_new_obj_with_finaliser could be used too

# TODO: decl of __init__
# STATIC mp_obj_t object___init__(mp_obj_t self) {
#    (void)self;
#    return mp_const_none;
# }
# STATIC MP_DEFINE_CONST_FUN_OBJ_1(object___init___obj, object___init__);


        proto.append(f"""
const mp_obj_type_t {nscname}_type;  //forward decl at 344

mp_obj_t {nscname}_make_new( const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args ) {{

    mp_arg_check_num(n_args, n_kw, {0}, {0}, true);

    {nscname}_obj_t *this = m_new_obj({nscname}_obj_t);

    this->base.type = &{nscname}_type;

    //this->hash = object_id++;
    //printf("Object serial #%d\\n", this->hash );
{''.join(init_lines)}
    return MP_OBJ_FROM_PTR(this);
}}
""")


        # default __repr__ and locals() table
        proto.append(f"""

void {nscname}_print( const mp_print_t *print, mp_obj_t self_in, mp_print_kind_t kind ) {{
    // get a ptr to the C-struct of the object
    {nscname}_obj_t *self = MP_OBJ_TO_PTR(self_in);

    // print the number
    mp_printf (print, "<{namespace}.{cname} at 0x%p>", self);
}}
""")


        meth_defs, meth_map, meth_table = build_method_block(nscname, cname, cdef)

        proto.append( meth_defs  )

        # declare the locals() dict of the above struct.
        proto.append(f"""
{meth_map}

STATIC const mp_rom_map_elem_t {nscname}_locals_dict_table[] = {{
{meth_table}
}};

STATIC MP_DEFINE_CONST_DICT({nscname}_locals_dict, {nscname}_locals_dict_table);

const mp_obj_type_t zipfile_ZipFile_type = {{

    // "inherit" the type "{clsdef.__ancestor__}"
    {{ &mp_type_{clsdef.__ancestor__} }},

     // give it a name
    .name = MP_QSTR_{cname},

     // give it a print-function
    .print = zipfile_ZipFile_print,

     // give it a constructor
    .make_new = zipfile_ZipFile_make_new,

     // and its locals members
    .locals_dict = (mp_obj_dict_t*)&zipfile_ZipFile_locals_dict,
}};
""")



        cmap[cname] = ( '\n'.join(proto), f'// {namespace}_{cname}')




    if namespace is None:
        namespace = instance.__class__.__name__

    defcount = 0
    cmap = {}

    module_table = []
    class_table = []

    print()

    table = ["\n\n/***************************** MODULE INTERFACE ***************************/"]
    for function_name in dir(instance):

        if function_name.startswith('_'):
            continue

        func = getattr(instance, function_name)

        if not hasattr(func,'__annotations__'):
            print(func.__name__,'is a class/struct definition')
            build_as_class(func)
            continue

        argv = []
        item_pos = 0
        clines = ['']
        proto = len(clines)
        clines.append('<proto>')

        rti = None
        function_type = "void"


        for item_pos,(k,v) in enumerate( func.__annotations__.items()):

            if k=='return':
                function_type = v.__name__
                rti = v.__name__
                continue

            clines.append( read_init(item_pos, v.__name__, k, func.__defaults__[item_pos]) )
            argv.append(v.__name__)

        clines[proto] = f"STATIC mp_obj_t //{function_type}\n"
        clines[proto] += f"{namespace}_{function_name}(size_t argc, const mp_obj_t *argv) {{"


        if rti and rti!='ptr':
            rti_stmt = f"    //return {rti}()"
        else:
            rti_stmt = "    return None;"

        try:
            clines = '\n'.join(clines)
        except:
            for cl in clines:
                print(cl)
            #raise SystemExit
            raise


        cmap[function_name]=[ clines , rti_stmt ]

        table.append('')
        table.append(f"STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN({namespace}_{function_name}_obj,")
        table.append(f"    0, {len(argv)}, {namespace}_{function_name});")

        module_table.append(f"    {{MP_OBJ_NEW_QSTR(MP_QSTR_{function_name}), (mp_obj_t)&{namespace}_{function_name}_obj }},")

    class_table = '\n'.join( class_table )
    module_table='\n'.join( module_table )

    if namespace == 'embed':
        del_hook = '{MP_OBJ_NEW_QSTR(MP_QSTR_on_del), MP_ROM_PTR(&mp_type_on_del) },'
    else:
        del_hook = ''

    table.append(f"""
STATIC PyMethodDef mod_{namespace}_globals_table[] = {{
    {{MP_OBJ_NEW_QSTR(MP_QSTR___name__), MP_OBJ_NEW_QSTR(MP_QSTR_{namespace}) }},
    {{MP_OBJ_NEW_QSTR(MP_QSTR___file__), MP_OBJ_NEW_QSTR(MP_QSTR_flashrom) }},
    {del_hook}
{class_table}
{module_table}
//  {{NULL, NULL, 0, NULL}} // cpython
}};

STATIC MP_DEFINE_CONST_DICT(mp_mod_{namespace}_globals, mod_{namespace}_globals_table);

//const mp_obj_module_t STATIC
PyModuleDef mp_module_{namespace} = {{
    .base = {{ &mp_type_module }},
    .globals = (mp_obj_dict_t*)&mp_mod_{namespace}_globals,
}};

// Register the module to make it available
MP_REGISTER_MODULE(MP_QSTR_{namespace}, mp_module_{namespace}, MODULE_{namespace.upper()}_ENABLED);
""" )
    cmap[-1] = "\n".join(table)
    return cmap


if __name__=='__main__':

    #=================== what a .pym file would produce ===============

    class module:

        def os_read() -> bytes: pass

        def echoint(num : int=0) -> int: pass

        def callsome(fn : void=npe) -> void: pass

        def somecall(s:str='pouet') : pass

    #====================================================================

    instance = module()

    for k,v in cify( module()).items():
        print(v)

    sys.exit(1)
