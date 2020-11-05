# pythons android support for flavours that implement sys.getandroidapilevel

if not __UPY__:
    import sys

    todel = []
    for i, elem in enumerate(sys.path):
        if elem.startswith('/data/data/'):
            todel.append(i)
    while len(todel):
        sys.path.pop( todel.pop() )


    # may only works for root shell access
    # sys.path.insert(0,"/data/data/{{ cookiecutter.bundle }}.{{ cookiecutter.module_name }}/usr/lib/python3.8/lib-dynload")

    # so use importlib

    import importlib
    import importlib.abc
    import importlib.machinery

    class ApkLibFinder(importlib.abc.MetaPathFinder):
        @classmethod
        def find_spec(cls, name, path=None, target=None):
            try:
                lib = f"{os.environ['DYLD']}/lib.{name}.so"
                os.stat(lib)
                pdb(f"ApkLibFinder found : {lib}")
                loader = importlib.machinery.ExtensionFileLoader(name, path)
                return importlib.machinery.ModuleSpec(name=name, loader=loader, origin=lib)

            except FileNotFoundError:
                return None

    sys.meta_path.append(ApkLibFinder)
