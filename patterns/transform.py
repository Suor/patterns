import copy
from ast import *
import meta
from meta.asttools import print_ast

from .helpers import *


def transform_function(func_tree):
    assert all(isinstance(t, If) for t in func_tree.body), \
        'Patterns function should only have if statements'

    def destruct_to_tests_and_assigns(cond):
        def build_tests(indexes):
            def _build_tests(indexes):
                if len(indexes) == 0:
                    return [N('value')]
                item = make_subscript(N('value'), indexes)
                indexes.pop()
                return  _build_tests(indexes) + [item]
            return map(lambda v: make_call('isinstance', v, N('tuple')), _build_tests(copy.copy(indexes[:-1])))

        def _destruct_to_tests_and_assigns(expr, indexes):
            if isinstance(expr, Name):
                return build_tests(indexes), [make_assign(expr.id, make_subscript(N('value'), indexes))]
            if isinstance(expr, (Num, Str)):
                return build_tests(indexes) + [make_eq(make_subscript(N('value'), indexes), expr)], []
            elif isinstance(expr, Tuple):
                tests = []
                assigns = []
                for index, el in enumerate(expr.elts):
                    new_tests, new_assigns = _destruct_to_tests_and_assigns(el, indexes + [index])
                    tests.extend(new_tests)
                    assigns.extend(new_assigns)
                return tests, assigns
        return _destruct_to_tests_and_assigns(cond, [])


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
            tests.insert(0, make_eq(len(cond.elts), make_call('len', N('value'))))
            tests.insert(0, make_call('isinstance', N('value'), N('tuple')))
            test.test = BoolOp(op=And(), values=tests)
            assigns.append(test.body[0])
            test.body = assigns

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
    # print meta.dump_python_source(func_tree)


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
