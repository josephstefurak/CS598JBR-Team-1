import pytest

from HumanEval_123 import *

def test_get_odd_collatz_even_start():
    """
    Test the function with an even starting number.
    """
    assert get_odd_collatz(10) == [1, 5, 11, 23]

def test_get_odd_collatz_odd_start():
    """
    Test the function with an odd starting number.
    """
    assert get_odd_collatz(7) == [7, 22, 111]

def test_get_odd_collatz_1():
    """
    Test the function with 1.
    """
    assert get_odd_collatz(1) == [1]

def test_get_odd_collatz_zero():
    """
    Test the function with 0.
    """
    assert get_odd_collatz(0) == []

def test_get_odd_collatz_negative():
    """
    Test the function with a negative number.
    """
    assert get_odd_collatz(-5) == []

def test_get_odd_collatz_large_number():
    """
    Test the function with a large number.
    """
    assert get_odd_collatz(1000000) == [1, 5, 11, 23, 47, 142, 407, 1221, 3665, 11081, 33245, 100731, 302195, 906571, 2720715]
