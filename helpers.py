from ast import Call, Name, Num, Load

__author__ = 'ir4y'


def make_call(func_name, *args):
    def wrap(item):
        if isinstance(item, int): return Num(n=item)
        elif isinstance(item, str): return Name(ctx=Load(), id='value')
    return Call(args=map(wrap,args),
               func=Name(ctx=Load(), id=func_name),
               keywords=[],
               kwargs=None,
               starargs=None)
