import ast
from ast import *

from .cross import *


__all__ = ['V', 'N', 'A',
           'make_call', 'make_arguments', 'make_raise',
           'make_assign', 'make_op', 'make_eq', 'make_subscript']


def V(value):
    if isinstance(value, int):
        return Num(n=value)
    else:
        raise TypeError("Don't know how to make AST value from %s" % repr(value))

def N(id):
    return Name(ctx=Load(), id=id)

if PY3:
    def A(id):
        return arg(arg=id, annotation=None)
else:
    def A(id):
        return Name(ctx=Param(), id=id)


def wrap_carefully(value):
    if isinstance(value, ast.expr):
        return value
    else:
        return V(value)


def make_call(func_name, *args):
    return Call(
        func=N(func_name), args=lmap(wrap_carefully, args),
        keywords=[], kwargs=None, starargs=None
    )

def make_arguments(args):
    # Some fields are only needed for python 3,
    # but we pass them always as they are safely ignored by python 2
    return arguments(
        args=args,
        defaults=[], kw_defaults=[],
        kwarg=None, kwargannotation=None, kwonlyargs=[],
        vararg=None, varargannotation=None
    )

if PY3:
    def make_raise(expr):
        return Raise(exc=expr, cause=None)
else:
    def make_raise(expr):
        return Raise(type=expr, inst=None, tback=None)


def make_assign(left, right):
    return Assign(
        targets = [Name(ctx=Store(), id=left)],
        value   = wrap_carefully(right)
    )

def make_op(op_class, left, right):
    return Compare(
        ops         = [op_class()],
        left        = wrap_carefully(left),
        comparators = [wrap_carefully(right)],
    )

def make_eq(left, right):
    return make_op(Eq, left, right)

def make_subscript(expr, index):
    return Subscript(
        value = expr,
        slice = Index(value=wrap_carefully(index)),
        ctx   = Load(),
    )
