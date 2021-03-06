Pure-Python ``ast`` module
==========================

This is a pure-Python implementation of "ast" module as described in
CPython documentation. It is written for the 
`Pycopy <https://github.com/pfalcon/pycopy>`_ project and is a part
of its standard library, `pycopy-lib <https://github.com/pfalcon/pycopy-lib>`_.

Implementation-wise, it's laid out as a package, with following submodules:

* ``ast.types``, with AST node types auto-generated from CPython's ASDL
  description.
* ``ast.parser``, implementing hand-written parser for Python 3.5,
  utilizing recursive descent to parse statements, and Pratt operator
  precedence parser to parse expressions.
* ``ast``, the main package, integrating submodules above, and exposing
  CPython-compatible API with corresponding additional functions and
  classes to process AST trees.

At the time of writing, parsers support Python 3.5 syntax with
future-looking cleanups, e.g. ``async`` is treated as a keyword. Updates
for the next versions of Python syntax are expected to follow.

The package has small builtin test corpus to check that the AST trees
match the ones generated by CPython, and can also use entire CPython
standard library as a test corpus, which it can parse similarly
correctly (but with some discrepancies, e.g. this module is optimized
for minimal size and doesn't support Unicode named escape sequences
(in the same way as Pycopy doesn't support them)).

Pycopy's ``ast`` module is written by Paul Sokolovsky and provided
under the MIT license.
