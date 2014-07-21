Patterns |Build Status|
========

Pattern matching for python.


Installation
-------------

::

    pip install patterns


Usage
-----

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

    factorial('hello') # raises Mismatch

See tests for more examples.


TODO
----

- docs
- better handling of None, True, False matching
- matching to ``_`` should not capture
- name parameter
- better handling of ``Mismatch`` passing to function env
- non-strict dict matching


.. |Build Status| image:: https://travis-ci.org/Suor/patterns.svg?branch=master
   :target: https://travis-ci.org/Suor/patterns
