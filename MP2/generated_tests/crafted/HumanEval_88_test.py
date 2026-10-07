import pytest

from HumanEval_88 import *

def test_empty_array():
    assert sort_array([]) == []

def test_single_element_array():
    assert sort_array([5]) == [5]

def test_even_sum_array():
    assert sort_array([2, 4, 3, 0, 1, 5]) == [0, 1, 2, 3, 4, 5]

def test_odd_sum_array():
    assert sort_array([2, 4, 3, 0, 1, 5, 6]) == [6, 5, 4, 3, 2, 1, 0]

def test_negative_numbers():
    assert sort_array([-2, -4, -3, -1, -5]) == [-5, -4, -3, -2, -1]

def test_zero():
    assert sort_array([0, 2, 4, 3, 1, 5]) == [0, 1, 2, 3, 4, 5]

def test_boundary_values():
    assert sort_array([10, 20, 30, 40, 50]) == [10, 20, 30, 40, 50]
    assert sort_array([50, 40, 30, 20, 10]) == [10, 20, 30, 40, 50]
