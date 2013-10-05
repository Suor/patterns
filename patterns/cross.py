import sys


PY2 = sys.version_info.major == 2
PY3 = sys.version_info.major == 3

# Getting back our simple and useful list-returing map in python 3
if map(int, []) == []:
    lmap = map
else:
    lmap = lambda f, seq: list(map(f, seq))
