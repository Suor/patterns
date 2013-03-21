from ast import *

__author__ = 'ir4y'


def _wrap(item):
    if isinstance(item, int): return Num(n=item)
    elif isinstance(item, str): return Name(ctx=Load(), id=item)
    else: return item


def make_call(func_name, *args):
    return Call(args=map(_wrap, args),
                func=Name(ctx=Load(), id=func_name),
                keywords=[],
                kwargs=None,
                starargs=None)


def make_assign(left, right):
    return Assign(targets=[Name(ctx=Store(), id=left)],
                  value=_wrap(right))


def make_compare(left, operation, right):
    op_map = {'==': Eq(),
              '!=': NotEq(),
              'is': Is(),
              '<': Lt(),
              '<=': LtE(),
              '>': Gt(),
              '>=': GtE()}
    return Compare(comparators=[_wrap(right)], left=_wrap(left), ops=[op_map[operation]])


