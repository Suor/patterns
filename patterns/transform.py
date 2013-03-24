import copy
from ast import *
import meta
from meta.asttools import print_ast

from .helpers import *


def transform_function(func_tree):
    assert all(isinstance(t, If) for t in func_tree.body), \
        'Patterns function should only have if statements'

    def destruct_to_tests_and_assigns(topic, pattern):
        if isinstance(pattern, (Num, Str)):
            return [make_eq(topic, pattern)], []
        elif isinstance(pattern, Name):
            return [], [make_assign(pattern.id, topic)]
        elif isinstance(pattern, Tuple):
            tests = [
                make_call('isinstance', topic, N('tuple')),
                make_eq(make_call('len', topic), len(pattern.elts))
            ]
            assigns = []
            for i, elt in enumerate(pattern.elts):
                t, a = destruct_to_tests_and_assigns(make_subscript(topic, i), elt)
                tests.extend(t)
                assigns.extend(a)
            return tests, assigns

    # Adjust arglist and decorators
    func_tree.args.args.append(Name(ctx=Param(), id='value'))
    func_tree.decorator_list = []

    # print_ast(func_tree)

    # Transform tests to pattern matching
    for test in func_tree.body:
        cond = test.test

        if isinstance(cond, Tuple) and has_vars(cond):
            tests, assigns = destruct_to_tests_and_assigns(N('value'), cond)
            test.test = BoolOp(op=And(), values=tests)
            test.body = assigns + test.body

        elif isinstance(cond, (Num, Str, List, Tuple)):
            test.test = make_eq(N('value'), cond)

        elif isinstance(cond, Name):
            test.test = V(1)
            test.body.insert(0, make_assign(cond.id, N('value')))

        elif isinstance(cond, Compare) and isinstance(cond.ops[0], Is):
            assert len(cond.ops) == 1
            test.test = make_call('isinstance', N('value'), cond.comparators[0])
            test.body.insert(0, make_assign(cond.left.id, N('value')))

    func_tree.body = map(wrap_tail_expr, func_tree.body)
    func_tree.body.append(Raise(type=N('Mismatch'), inst=None, tback=None))

    # print_ast(func_tree)
    print meta.dump_python_source(func_tree)


def wrap_tail_expr(if_expr):
    """
    Wrap last expression in if body with Return node
    """
    if isinstance(if_expr.body[-1], Expr):
        if_expr.body[-1] = Return(value=if_expr.body[-1].value)
    return if_expr

def has_vars(expr):
    if isinstance(expr, Tuple):
        return any(has_vars(el) for el in expr.elts)
    else:
        return isinstance(expr, Name)
