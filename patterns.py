import sys, inspect, ast, re
from inspect import getargspec, ArgSpec, getsource
from ast import Num, Str, List, Tuple, Name, Param, Compare, Load, Eq, Return, Expr

from meta.asttools import print_ast
import dis
from funcy import re_find, zipdict


__all__ = ('Mismatch', 'patterns')


class Mismatch(Exception):
    pass


def patterns(func):
    empty_argspec = inspect.ArgSpec(args=[], varargs=None, keywords=None, defaults=None)
    assert inspect.getargspec(func) == empty_argspec, 'Pattern function should not have arguments'

    tree = _ast(func)
    print_ast(tree)

    _transform_function(tree.body[0])

    ast.fix_missing_locations(tree)

    return _compile(func, tree)


def _transform_function(func_tree):
    assert all(isinstance(t, ast.If) for t in func_tree.body), \
        'Patterns function should only have if statements'

    # Adjust arglist and decorators
    func_tree.args.args.append(Name(ctx=Param(), id='value'))
    func_tree.decorator_list = []

    # Transform tests to pattern matching
    for test in func_tree.body:
        if isinstance(test.test, (Num, Str, List, Tuple)):
            test.test = Compare(comparators=[test.test],
                                left=Name(ctx=Load(), id='value'),
                                ops=[Eq()])
        assert len(test.body) == 1
        assert isinstance(test.body[0], Expr)
        test.body = [Return(value=test.body[0].value)]

    # print_ast(tree)


def _compile(func, tree):
    code = compile(tree, sys.modules[func.__module__].__file__, 'exec')
    context = locals()#_locals(func)
    context.update(_locals(func))
    print context
    exec code in func.__globals__, context
    # exec code in context
    # context[func.__name__].__closure__ = func.__closure__
    # print context[func.__name__].__closure__
    dis.dis(context[func.__name__])
    return context[func.__name__]


def _ast(func):
    return ast.parse(_source(func))

def _source(func):
    # Get function source
    source = inspect.getsource(func)

    # Fix extra indent if present
    spaces = re_find(r'^\s+', source)
    if spaces:
        source = re.sub(r'(^|\n)' + spaces, '\n', source)

    return source


def _locals(func):
    if func.__closure__:
        names = func.__code__.co_freevars
        values = [cell.cell_contents for cell in func.__closure__]
        return zipdict(names, values)
    else:
        return {}
