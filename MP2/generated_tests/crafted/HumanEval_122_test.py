import pytest

from HumanEval_122 import *

def test_add_elements_with_multiple_elements():
    assert add_elements([111, 21, 3, 4000, 5, 6, 7, 8, 9], 4) == 24

def test_add_elements_with_single_element():
    assert add_elements([1], 1) == 1

def test_add_elements_with_zero():
    assert addadd_elements([0, 1, 2, 3, 4], 5) == 10

def test_add_elements_with_negative_numbers():
    assert add_elements([-1, -2, 3, 4], 4) == 5

def test_add_elements_with_boundary_values():
    assert add_elements([100, 200, 300, 400], 4) == 1000

def test_add_elements_with_large_numbers():
    assert add_elements([1111, 2222, 3333, 4444], 4) == 10000

def test_add_elements_with_no_elements():
    assert add_elements([], 0) == 0
