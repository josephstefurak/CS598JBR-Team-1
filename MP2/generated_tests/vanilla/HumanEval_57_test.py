from HumanEval_57 import *

import pytest

def test_monotonic_increasing():
    assert monotonic([1, 2, 3, 4, 5])

def test_monotonic_decreasing():
    assert monotonic([5, 4, 3, 2, 1])

def test_monotonic_neither():
    assert not monotonic([1, 2, 5, 4, 3])

def test_monotonic_empty():
    assert monotonic([])

def test_monotonic_single_element():
    assert monotonic([4])
