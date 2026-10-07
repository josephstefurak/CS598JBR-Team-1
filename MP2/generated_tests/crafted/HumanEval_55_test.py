import pytest

from HumanEval_55 import *

def test_fib_zero():
    assert fib(0) == 0

def test_fib_one():
    assert fib(1) == 1

def test_fib_eight():
    assert fib(8) == 21

def test_fib_ten():
    assert fib(10) == 55

def test_fib_negative():
    assert fib(-1) == 0

def test_fib_negative_two():
    assert fib(-2) == 0

def test_fib_large_number():
    assert fib(50) == 12586269025
