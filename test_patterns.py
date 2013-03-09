import pytest
from patterns import patterns


global_var = 'global'

def test_value():
    local_var = 'local'

    @patterns
    def exact():
        if 1: 'int'
        if 'hi': 'str'
        # if [1, 2]: 'list'
        # if (1, 2): 'tuple'
        if 'local': local_var
        if 'global': global_var

    assert exact(1) == 'int'
    assert exact('hi') == 'str'
    # assert exact([1, 2]) == 'list'
    # assert exact((1, 2)) == 'tuple'
    # with pytest.raises(NotImplementedError): exact(2)
    # with pytest.raises(NotImplementedError): exact(True)

    # assert exact('local') == 'local'
    assert exact('global') == 'global'


def test_global():
    @patterns
    def _global():
        if '': test_global

    assert _global('') is test_global


def test_local():
    local_var = object()

    @patterns
    def _local():
        if '': local_var

    assert _local('') is local_var
    local_var = object()
    assert _local('') is local_var
