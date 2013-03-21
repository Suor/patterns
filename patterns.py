from ast import *
import sys, inspect, ast, re, copy
from meta.asttools import print_ast
from funcy import re_find
from helpers import make_call, make_assign, make_compare

__all__ = ('Mismatch', 'patterns')


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


def transform_function(func_tree):
    def wrap_tail_expr(if_expr):
        """
        Wrap last expression in if body with return
        """
        if isinstance(if_expr.body[-1], Expr):
            if_expr.body[-1] = Return(value=if_expr.body[-1].value)
        return if_expr

    def has_vars(expr):
        if isinstance(expr, Expr):
            return has_vars(expr.value)
        elif isinstance(expr, Tuple):
            return any(has_vars(el) for el in expr.elts)
        else:
            return isinstance(expr, Name)

    def destruct_to_tests_and_assigns(cond):
        def build_subscript_for_index(indexes):
            def _build_subscript_for_index(indexes):
                if len(indexes) == 0:
                    return Name(ctx=Load(), id='value')
                index = indexes.pop()
                return Subscript(ctx=Load(), slice=Index(value=Num(n=index)),
                                 value=_build_subscript_for_index(indexes))
            return _build_subscript_for_index(copy.copy(indexes))

        def _destruct_to_tests_and_assigns(expr, indexes):
            if isinstance(expr, Name):
                return [], [make_assign(expr.id, build_subscript_for_index(indexes))]
            if isinstance(expr, (Num, Str)):
                return [make_compare(build_subscript_for_index(copy.copy(indexes)), '==', expr)], []
            elif isinstance(expr, Tuple):
                tests = []
                assigns = []
                for index, el in enumerate(expr.elts):
                    new_tests, new_assigns = _destruct_to_tests_and_assigns(el, indexes + [index])
                    tests.extend(new_tests)
                    assigns.extend(new_assigns)
                return tests, assigns
        return _destruct_to_tests_and_assigns(cond, [])

    assert all(isinstance(t, ast.If) for t in func_tree.body), \
        'Patterns function should only have if statements'

    # Adjust arglist and decorators
    func_tree.args.args.append(Name(ctx=Param(), id='value'))
    func_tree.decorator_list = []

    # print_ast(func_tree)

    # Transform tests to pattern matching
    for test in func_tree.body:
        assert len(test.body) == 1
        assert isinstance(test.body[0], (Expr, Raise))

        cond = test.test

        if isinstance(cond, Tuple) and has_vars(cond):
            tests, assigns = destruct_to_tests_and_assigns(cond)
            tests.append(make_compare(len(cond.elts), '==', make_call('len','value')))
            test.test = BoolOp(op=And(), values=tests)
            assigns.append(test.body[0])
            test.body = assigns

        elif isinstance(cond, (Num, Str, List, Tuple)):
            test.test = Compare(comparators=[cond],
                                left=Name(ctx=Load(), id='value'),
                                ops=[Eq()])

        elif isinstance(cond, Name):
            test.test = Name(ctx=Load(), id='True')
            test.body.insert(0, make_assign(cond.id, 'value'))

        elif isinstance(cond, Compare) and isinstance(cond.ops[0], Is):
            assert len(cond.ops) == 1
            test.test = make_call('isinstance', Name(ctx=Load(), id='value'), cond.comparators[0])
            test.body.insert(0, make_assign(cond.left.id, 'value'))

    func_tree.body = map(wrap_tail_expr, func_tree.body)
    func_tree.body.append(Raise(inst=None,
                                tback=None,
                                type=Name(ctx=Load(),
                                          id='Mismatch')))
    # print_ast(func_tree)


def compile_func(func, tree):
    def _compile_func():
        # TODO: this one doesn't work quite well, handle it
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
        # dis.dis(context[func.__name__])
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
