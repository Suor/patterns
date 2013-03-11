import pytest
from patterns import *


def test_const():
    @patterns
    def const():
        if 1: 'int'
        if 'hi': 'str'
        if [1, 2]: 'list'
        if (1, 2): 'tuple'

    assert const(1) == 'int'
    assert const('hi') == 'str'
    assert const([1, 2]) == 'list'
    assert const((1, 2)) == 'tuple'
    with pytest.raises(Mismatch): const(2)
    with pytest.raises(Mismatch): const(True)


def test_global_ref():
    @patterns
    def _global():
        if '': test_global_ref

    assert _global('') is test_global_ref


def test_local_ref():
    local_var = object()

    @patterns
    def _local():
        if '': local_var

    assert _local('') is local_var
    local_var = object()
    assert _local('') is local_var
