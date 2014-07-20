import sys, inspect, ast, re
from ast import *

from .cross import *
from .helpers import *
from .transform import transform_function


__all__ = ('patterns', 'Mismatch')


class Mismatch(Exception):
    pass


def patterns(func):
    empty_argspec = inspect.ArgSpec(args=[], varargs=None, keywords=None, defaults=None)
    assert inspect.getargspec(func) == empty_argspec, 'Pattern function should not have arguments'

    # TODO: make it not as weird and dirty
    func.__globals__['Mismatch'] = Mismatch

    tree = get_ast(func)
    transform_function(tree.body[0])
    return compile_func(func, tree)


# TODO: wrap referenced globals somehow to prevent name conflicts with global/local vars
def compile_func(func, tree):
    def wrap_func(func_tree, arg_names):
        return FunctionDef(
            name = func_tree.name + '__wrapped',
            args = make_arguments(lmap(A, arg_names)),
            decorator_list = [],
            body = [
                func_tree,
                Return(value=N(func_tree.name))
            ]
        )

    context = sys._getframe(2).f_locals
    if getattr(func, '__closure__', None) or getattr(func, 'func_closure', None):
        kwargs = context.copy()
        tree.body[0] = wrap_func(tree.body[0], kwargs.keys())
        _compile_func(func, tree, context)
        func.__code__ = context[func.__name__ + '__wrapped'](**kwargs).__code__
        return func
    else:
        _compile_func(func, tree, context)
        return context[func.__name__]

def _compile_func(func, tree, context):
    ast.fix_missing_locations(tree)
    code = compile(tree, func_file(func), 'single')
    exec(code, func.__globals__, context)


def get_ast(func):
    # Get function source
    source = inspect.getsource(func)

    # Fix extra indent if present
    spaces = re.search(r'^\s*', source).group()
    if spaces:
        source = re.sub(r'(^|\n)' + spaces, '\n', source)

    # Preserve line numbers
    source = '\n' * (func.__code__.co_firstlineno - 2) + source

    return ast.parse(source, func_file(func), 'single')


def func_file(func):
    return getattr(sys.modules[func.__module__], '__file__', '<nofile>')
