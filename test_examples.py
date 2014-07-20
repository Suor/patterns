import pytest
from patterns import patterns, Mismatch


def test_factorial():
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


def test_depth():
    def make_node(v, l=None, r=None):
        return ('Tree', v, l, r)

    @patterns
    def depth():
        if ('Tree', _, l, r): 1 + max(depth(l), depth(r))
        if None: 0

    n1 = make_node(1)
    n2 = make_node(2, n1)
    n3 = make_node(3, n1, n1)
    n4 = make_node(4, n2, n3)

    # TODO: make test distingishing between Name and NameConstant
    assert depth(None) == 0
    assert depth(n1) == 1
    assert depth(n2) == 2
    assert depth(n3) == 2
    assert depth(n4) == 3


def test_chatter():
    botname = "Chatty"

    @patterns
    def answer():
        if ['hello']: "Hello, my name is %s" % botname
        if ['hello', 'my', 'name', 'is', name]: "Hello, %s!" % name.capitalize()
        if ['how', 'much', 'is'] + expr: "It is %d" % eval(' '.join(expr))
        if ['bye']: "Good bye!"

    @patterns
    def chatterbot():
        if l is list: answer([s.lower() for s in l])
        if s is str: chatterbot(s.split())

    assert chatterbot("hello") == "Hello, my name is Chatty"
    assert chatterbot("how much is 5 * 10") == "It is 50"
    assert chatterbot("how much is 5 - 10") == "It is -5"
    assert chatterbot("how much is 5 + 10 - 1") == "It is 14"
    assert chatterbot("how much is 5 + 10 - 1") == "It is 14"
    assert chatterbot("hello my name is alice") == "Hello, Alice!"
