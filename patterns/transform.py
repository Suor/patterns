import copy
from ast import *
from meta.asttools import print_ast

from .helpers import make_call, make_assign, make_compare, make_raise


def transform_function(func_tree):
    assert all(isinstance(t, If) for t in func_tree.body), \
        'Patterns function should only have if statements'

    def destruct_to_tests_and_assigns(cond):
        def build_subscript_for_index(indexes):
            def _build_subscript_for_index(indexes):
                if len(indexes) == 0:
                    return Name(ctx=Load(), id='value')
                index = indexes.pop()
                return Subscript(ctx=Load(), slice=Index(value=Num(n=index)),
                                 value=_build_subscript_for_index(indexes))
            return _build_subscript_for_index(copy.copy(indexes))

        def build_tests(indexes):
            def _build_tests(indexes):
                if len(indexes) == 0:
                    return [Name(ctx=Load(), id='value')]
                item = build_subscript_for_index(indexes)
                indexes.pop()
                return  _build_tests(indexes) + [item]
            return map(lambda v: make_call('isinstance', v, 'tuple'), _build_tests(copy.copy(indexes[:-1])))

        def _destruct_to_tests_and_assigns(expr, indexes):
            if isinstance(expr, Name):
                return build_tests(indexes), [make_assign(expr.id, build_subscript_for_index(indexes))]
            if isinstance(expr, (Num, Str)):
                return build_tests(indexes) + [make_compare(build_subscript_for_index(copy.copy(indexes)), '==', expr)], []
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
            tests.insert(0, make_compare(len(cond.elts), '==', make_call('len', 'value')))
            tests.insert(0, make_call('isinstance', 'value', 'tuple'))
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
    func_tree.body.append(make_raise('Mismatch'))

    # print_ast(func_tree)


def wrap_tail_expr(if_expr):
    """
    Wrap last expression in if body with return
    """
    if isinstance(if_expr.body[-1], Expr):
        if_expr.body[-1] = Return(value=if_expr.body[-1].value)
    return if_expr

def has_vars(expr):
    if isinstance(expr, Tuple):
        return any(has_vars(el) for el in expr.elts)
    else:
        return isinstance(expr, Name)
