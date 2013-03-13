import sys, inspect, ast, re
from inspect import getargspec, ArgSpec, getsource
from ast import *

from meta.asttools import print_ast
import dis
from funcy import re_find, zipdict


__all__ = ('Mismatch', 'patterns')


class Mismatch(Exception):
    pass


def patterns(func):
    empty_argspec = inspect.ArgSpec(args=[], varargs=None, keywords=None, defaults=None)
    assert inspect.getargspec(func) == empty_argspec, 'Pattern function should not have arguments'

    tree = get_ast(func)
    transform_function(tree.body[0])
    return compile_func(func, tree)


def transform_function(func_tree):
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


def compile_func(func, tree):
    def _compile_func():
        ast.fix_missing_locations(tree)
        code = compile(tree, func_file(func), 'single')
        exec code in func.__globals__, context

    def wrap_func(func_tree, arg_names):
        args = [Name(ctx=Param(), id=name) for name in arg_names]
        return FunctionDef(
            name = func_tree.name + '__wrapped',
            args = arguments(args=args, defaults=[], vararg=None, kwarg=None),
            decorator_list = [],
             body = [
                func_tree,
                Return(value=Name(ctx=Load(), id=func_tree.name))
            ]
        )

    context = sys._getframe(2).f_locals
    if func.__closure__:
        kwargs = context.copy()
        tree.body[0] = wrap_func(tree.body[0], kwargs.keys())
        _compile_func()
        func.__code__ = context[func.__name__ + '__wrapped'](**kwargs).__code__
        return func
    else:
        _compile_func()
        return context[func.__name__]


def get_ast(func):
    # Get function source
    source = inspect.getsource(func)

    # Fix extra indent if present
    spaces = re_find(r'^\s+', source)
    if spaces:
        source = re.sub(r'(^|\n)' + spaces, '\n', source)

    return ast.parse(source, func_file(func), 'single')


def func_file(func):
    return sys.modules[func.__module__].__file__
