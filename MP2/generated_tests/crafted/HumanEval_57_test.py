import pytest

from HumanEval_57 import *

def test_monotonic_increasing():
    assert monotonic([1, 2, 4, 20]) == True

def test_monotonic_decreasing():
    assert monotonic([4, 3, 2, 1]) == True

def test_monotonic_false():
    assert monotonic([1, 20, 4, 10]) == False

def test_monotonic_negative():
    assert monotonic([4, 1, 0, -10]) == True

def test_monotonic_empty():
    assert monotonic([]) == True

def test_monotonic_single_element():
    assert monotonic([1]) == True

def test_monotonic_zero():
    assert monotonic([0, 0, 0, 0]) == True

def test_monotonic_negative_increasing():
    assert monotonic([-1, -2, -4, -20]) == True

def test_monotonic_negative_decreasing():
    assert monotonic([-4, -3, -2, -1]) == True

def test_monotonic_negative_false():
    assert monotonic([-1, -20, -4, -10]) == False
