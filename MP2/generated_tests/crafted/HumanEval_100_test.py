import pytest

from HumanEval_100 import *

def test_make_a_pile_odd():
    """
    Test the make_a_pile function with an odd number.
    """
    assert make_a_pile(3) == [3, 5, 7]

def test_make_a_pile_even():
    """
    Test the make_a_pile function with an even number.
    """
    assert make_a_pile(4) == [4, 6, 8, 10]

def test_make_a_pile_zero():
    """
    Test the make_a_pile function with zero.
    """
    assert make_a_pile(0) == []

def test_make_a_pile_negative():
    """
    Test the make_a_pile function with a negative number.
    """
    assert make_a_pile(-5) == []

def test_make_a_pile_single_element():
    """
    Test the make_a_pile function with a single element.
    """
    assert make_a_pile(1) == [1]

def test_make_a_pile_large_number():
    """
    Test the make_a_pile function with a large number.
    """
    assert make_a_pile(100) == [100, 102, 104, 106, 108, 110, 112, 114, 116, 118, 120]
