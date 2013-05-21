Patterns
========

Pattern matching for python.

.. code:: python

    from patterns import patterns, Mismatch

    @patterns
    def factorial():
        if 0: 1
        if n is int: n * factorial(n-1)
        if []: []
        if [x] + xs: [factorial(x)] + factorial(xs)
        if {'n': n, 'f': f}: f(factorial(n))

    assert factorial(0) == 1
    assert factorial(5) == 120
    assert factorial([3,4,2]) == [6, 24, 2]
    assert factorial({'n': [5, 1], 'f': sum}) == 121
