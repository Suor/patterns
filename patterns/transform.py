from itertools import chain
from ast import *
# A new thing in Python 3.4
try:
    NameConstant
except NameError:
    NameConstant = Name

import codegen

from .helpers import *
from .cross import *


def transform_function(func_tree):
    assert all(isinstance(t, If) for t in func_tree.body), \
        'Patterns function should only have if statements'

    # Adjust arglist and decorators
    func_tree.args.args.append(A('value'))
    func_tree.decorator_list = []

    # Transform tests to pattern matching
    for test in func_tree.body:
        cond = test.test

        if isinstance(cond, (Num, Str, List, Tuple, Dict)) and not has_vars(cond):
            test.test = make_eq(N('value'), cond)

        elif isinstance(cond, (Num, Str, Name, NameConstant, Compare, List, Tuple, Dict, BinOp)):
            tests, assigns = destruct_to_tests_and_assigns(N('value'), cond)
            test.test = BoolOp(op=And(), values=tests) if len(tests) > 1 else \
                                              tests[0] if tests else V(1)
            test.body = assigns + test.body

        else:
            raise TypeError("Don't know how to match %s"
                            % (codegen.to_source(cond).strip() or cond))

    func_tree.body = lmap(wrap_tail_expr, func_tree.body)
    func_tree.body.append(make_raise(N('Mismatch')))

    # Set raise Mismatch lineno just after function end
    func_tree.body[-1].lineno = last_lineno(func_tree) + 1

    # print(dump(func_tree))
    # print(codegen.to_source(func_tree))


NAMED_CONSTS = {'None': None, 'True': True, 'False': False}

def destruct_to_tests_and_assigns(topic, pattern, names=None):
    if names is None:
        names = {}

    if isinstance(pattern, (Num, Str)):
        return [make_eq(topic, pattern)], []
    elif isinstance(pattern, Name):
        if pattern.id in NAMED_CONSTS:
            return [make_op(Is, topic, pattern)], []
        elif pattern.id == '_':
            return [], []
        else:
            if pattern.id in names:
                return [make_eq(topic, names[pattern.id])], []
            else:
                names[pattern.id] = topic
                return [], [make_assign(pattern.id, topic)]
    elif isinstance(pattern, NameConstant):
        return [make_op(Is, topic, pattern)], []
    elif isinstance(pattern, Compare) and len(pattern.ops) == 1 and isinstance(pattern.ops[0], Is):
        left_tests, left_assigns = destruct_to_tests_and_assigns(topic, pattern.left, names)
        test = make_call('isinstance', topic, pattern.comparators[0])
        return left_tests + [test], left_assigns
    elif isinstance(pattern, (List, Tuple, Dict)):
        elts = getattr(pattern, 'elts', []) or getattr(pattern, 'values', [])
        coll_tests = [
            make_call('isinstance', topic, N(pattern.__class__.__name__.lower())),
            make_eq(make_call('len', topic), len(elts))
        ]
        tests, assigns = subscript_tests_and_assigns(topic, pattern, names)
        return coll_tests + tests, assigns
    elif isinstance(pattern, BinOp) and isinstance(pattern.op, Add) \
         and isinstance(pattern.left, (List, Tuple)) and isinstance(pattern.right, Name):
        coll_tests = [
            make_call('isinstance', topic, N(pattern.left.__class__.__name__.lower())),
            make_op(GtE, make_call('len', topic), len(pattern.left.elts)),
        ]
        coll_assigns = [
            make_assign(
                pattern.right.id,
                Subscript(
                    ctx   = Load(),
                    value = topic,
                    slice = Slice(lower=V(len(pattern.left.elts)), upper=None, step=None)
                )
            )
        ]
        tests, assigns = subscript_tests_and_assigns(topic, pattern.left, names)
        return coll_tests + tests, assigns + coll_assigns
    else:
        raise TypeError("Don't know how to match %s"
                        % (codegen.to_source(pattern).strip() or pattern))


def subscript_tests_and_assigns(topic, pattern, names):
    tests = []
    assigns = []
    items = enumerate(pattern.elts) if hasattr(pattern, 'elts') else \
            zip(pattern.keys, pattern.values)
    for key, elt in items:
        t, a = destruct_to_tests_and_assigns(make_subscript(topic, key), elt, names)
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
    if isinstance(expr, (Tuple, List)):
        return any(has_vars(el) for el in expr.elts)
    elif isinstance(expr, Dict):
        return any(has_vars(e) for e in chain(expr.values, expr.keys))
    elif isinstance(expr, (Name, Compare)):
        return True
    elif isinstance(expr, (Num, Str)):
        return False
    else:
        raise TypeError("Don't know how to handle %s" % expr)


def last_lineno(node):
    lineno = getattr(node, 'lineno', None)
    if hasattr(node, 'body'):
        linenos = (last_lineno(n) for n in reversed(node.body))
        return next((n for n in linenos if n is not None), lineno)
    else:
        return lineno
