from ast import *
import meta
from meta.asttools import print_ast

from .helpers import *


def transform_function(func_tree):
    assert all(isinstance(t, If) for t in func_tree.body), \
        'Patterns function should only have if statements'

    # Adjust arglist and decorators
    func_tree.args.args.append(Name(ctx=Param(), id='value'))
    func_tree.decorator_list = []

    # print_ast(func_tree)

    # Transform tests to pattern matching
    for test in func_tree.body:
        cond = test.test

        if isinstance(cond, (Num, Str, List, Tuple)) and not has_vars(cond):
            test.test = make_eq(N('value'), cond)

        if isinstance(cond, (Num, Str, Name, Compare, List, Tuple, Dict, BinOp)):
            tests, assigns = destruct_to_tests_and_assigns(N('value'), cond)
            test.test = BoolOp(op=And(), values=tests) if tests else V(1)
            test.body = assigns + test.body

        else:
            raise TypeError("Don't know how to match %s" % meta.dump_python_source(cond).strip())

    func_tree.body = map(wrap_tail_expr, func_tree.body)
    func_tree.body.append(Raise(type=N('Mismatch'), inst=None, tback=None))

    # print_ast(func_tree)
    print meta.dump_python_source(func_tree)


def destruct_to_tests_and_assigns(topic, pattern):
    if isinstance(pattern, (Num, Str)):
        return [make_eq(topic, pattern)], []
    elif isinstance(pattern, Name):
        return [], [make_assign(pattern.id, topic)]
    elif isinstance(pattern, Compare) and len(pattern.ops) == 1 and isinstance(pattern.ops[0], Is):
        return [make_call('isinstance', topic, pattern.comparators[0])], \
               [make_assign(pattern.left.id, topic)]
    elif isinstance(pattern, (List, Tuple, Dict)):
        elts = getattr(pattern, 'elts', []) or getattr(pattern, 'values', [])
        coll_tests = [
            make_call('isinstance', topic, N(pattern.__class__.__name__.lower())),
            make_eq(make_call('len', topic), len(elts))
        ]
        tests, assigns = subscript_tests_and_assigns(topic, pattern)
        return coll_tests + tests, assigns
    elif isinstance(pattern, BinOp) and isinstance(pattern.op, Add) \
         and isinstance(pattern.left, (List, Tuple)) and isinstance(pattern.right, Name):
        coll_tests = [
            make_call('isinstance', topic, N(pattern.left.__class__.__name__.lower())),
            make_op(GtE, make_call('len', topic), len(pattern.left.elts)),
        ]
        coll_assigns = [
            make_assign(pattern.right.id,
                        Subscript(ctx=Load(),
                                  value=topic,
                                  slice=Slice(lower=V(len(pattern.left.elts)), upper=None, step=None)))
        ]
        tests, assigns = subscript_tests_and_assigns(topic, pattern.left)
        return coll_tests + tests, assigns + coll_assigns
    else:
        raise TypeError("Don't know how to match %s" % meta.dump_python_source(pattern).strip())


def subscript_tests_and_assigns(topic, pattern):
    tests = []
    assigns = []
    items = enumerate(pattern.elts) if hasattr(pattern, 'elts') else zip(pattern.keys, pattern.values)
    for key, elt in items:
        t, a = destruct_to_tests_and_assigns(make_subscript(topic, key), elt)
        tests.extend(t)
        assigns.extend(a)
    return tests, assigns


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
        return isinstance(expr, (Name, Compare))
