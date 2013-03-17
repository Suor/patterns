import sys, inspect, ast, re
from inspect import getargspec, ArgSpec, getsource
from ast import *
import copy
from meta.asttools import print_ast
import dis
from funcy import re_find, zipdict


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
    # R: No point in having this function, it's not hiding complexity
    #    Besides it's inconsistent - one function for two diffrent puporses
    def get_final_operator(expr):
        if isinstance(expr, Expr):
            return Return(value=expr.value)
        # R: elif would be better style
        if isinstance(expr, Raise):
            return expr
        # R: No else fallback, asking for trouble,
        #    doesn't really matter since function should be trashed anyway )

    def has_vars(expr):
        if isinstance(expr, Expr):
            return has_vars(expr.value)
        elif isinstance(expr, Tuple):
            return any(has_vars(el) for el in expr.elts)
        else:
            return isinstance(expr, Name)

    # R: strange function with mutable (!!!) arguments, just asking for trouble again,
    #    really should be rewritten completely as pure function.
    def build_tuple_destruct_ast(result, expr, indexes):
        def build_subscript_for_index(indexes):
            if len(indexes) == 0:
                return Name(ctx=Load(), id='value')
            index = indexes.pop()
            return Subscript(ctx=Load(), slice=Index(value=Num(n=index)),
                             value=build_subscript_for_index(indexes))

        if isinstance(expr, Expr):
            # R: Going for stack overflow, luckily there can't be Exprs in If tests
            build_tuple_destruct_ast(result, expr, indexes)
        elif isinstance(expr, Name):
            result['assigns'].append(Assign(targets=[Name(ctx=Store(), id=expr.id)],
                                            value=build_subscript_for_index(copy.copy(indexes))))
        elif isinstance(expr, (Num, Str)):
            result['tests'].append(Compare(comparators=[expr],
                                           left=build_subscript_for_index(copy.copy(indexes)),
                                           ops=[Eq()]))
        elif isinstance(expr, Tuple):
            # TODO: refactor
            jndex = 0 # R: jndex?
            for el in expr.elts:
                new_indexes = []
                new_indexes.extend(indexes)
                new_indexes.append(jndex)
                build_tuple_destruct_ast(result, el, new_indexes)
                jndex += 1

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
            # R: lines too long, logic unclear:
            #    constructing some half-backed result and then mutating it with a function
            # R: should also test if value is a tuple
            # R: use helper for making calls, like make_call('len', 'value')
            # R: also len variable could be overwritten in function def scope,
            #    need to handle that
            tests_and_assign = {'tests': [Compare(comparators=[Call(args=[Name(ctx=Load(), id='value')],
                                                                    func=Name(ctx=Load(), id='len'),
                                                                    keywords=[],
                                                                    kwargs=None,
                                                                    starargs=None)],
                                                  left=Num(n=len(cond.elts)),
                                                  ops=[Eq()])],
                                'assigns': []}
            build_tuple_destruct_ast(tests_and_assign, cond, [])


            # Wrap if statment with
            # try:
            #   if_statment
            # except TypeError:
            #   pass
            realtest = copy.copy(test)
            # R: should not alter elements list we iterate.
            #    Should not wrap arbitrary (library user supplied code) with try ... except.
            #    This will lead to unwanted exception capturing.
            func_tree.body[func_tree.body.index(test)] = TryExcept(body=[realtest],
                                                                   handlers=[ExceptHandler(body=[Pass()],
                                                                                           name=None,
                                                                                           type=Name(ctx=Load(),
                                                                                                     id='TypeError'))],
                                                                   orelse=[])
            if len(tests_and_assign['tests']) == 1:
                realtest.test = tests_and_assign['tests'][0]
            else:
                #For multiple tests use And operator
                realtest.test = BoolOp(op=And(), values=tests_and_assign['tests'])

            tests_and_assign['assigns'].append(get_final_operator(realtest.body[0]))
            realtest.body = tests_and_assign['assigns']

        elif isinstance(cond, (Num, Str, List, Tuple)):
            test.test = Compare(comparators=[cond],
                                left=Name(ctx=Load(), id='value'),
                                ops=[Eq()])
            test.body = [get_final_operator(test.body[0])]

        elif isinstance(cond, Name):
            var_name = cond.id
            test.test = Name(ctx=Load(),
                               id='True')
            test.body = [Assign(targets=[Name(ctx=Store(), id=var_name)],
                                value=Name(ctx=Load(), id='value')),
                         get_final_operator(test.body[0])]

        elif isinstance(cond, Compare) and isinstance(cond.ops[0], Is):
            assert len(cond.ops) == 1

            var_name = cond.left.id
            test.test = Call(
                func     = Name(ctx=Load(), id='isinstance'),
                args     = [Name(ctx=Load(), id='value'), cond.comparators[0]],
                keywords = [],
                kwargs   = None,
                starargs = None
            )
            test.body = [
                Assign(targets=[Name(ctx=Store(), id=var_name)],
                       value=Name(ctx=Load(), id='value')),
                get_final_operator(test.body[0])
            ]

    func_tree.body.append(Raise(inst=None,
                                tback=None,
                                type=Name(ctx=Load(),
                                          id='Mismatch')))
    print_ast(func_tree)


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
