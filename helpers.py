from ast import *

__author__ = 'ir4y'


def make_call(func_name, *args):
    def wrap(item):
        if isinstance(item, int): return Num(n=item)
        elif isinstance(item, str): return Name(ctx=Load(), id='value')
        else: return item
    return Call(args=map(wrap, args),
                func=Name(ctx=Load(), id=func_name),
                keywords=[],
                kwargs=None,
                starargs=None)


def make_assign(left, right):
    return Assign(targets=[Name(ctx=Store(), id=left)],
                  value=Name(ctx=Load(), id=right))
