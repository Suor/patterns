a = Mismatch

def wrapper(_Mismatch_1966):
    def const(value):
        Mismatch = ' miss match'
        if value == 1: return 'int'
        if value == 'hi': return 'str'
        if value == [1, 2]: return 'list'
        if value == (1, 2): return 'tuple' + Mismatch
        raise _Mismatch_1966
    return const

return f(Mismatch)

def const(value):
    from patterns import Mismatch as _Mismatch_1966
    Mismatch = ' miss match'
    if value == 1: return 'int'
    if value == 'hi': return 'str'
    if value == [1, 2]: return 'list'
    if value == (1, 2): return 'tuple' + Mismatch
    raise _Mismatch_1966
