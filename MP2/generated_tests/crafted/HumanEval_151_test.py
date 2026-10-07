import pytest

from HumanEval_151 import *

def test_empty_list():
    assert double_the_difference([]) == 0

def test_single_element():
    assert double_the_difference([1]) == 1
    assert double_the_difference([0]) == 0
    assert double_the_difference([-1]) == 0

def test_zero():
    assert double_the_difference([0, 2, 3]) == 9

def test_negative_numbers():
    assert double_the_difference([-1, -2, 3]) == 0

def test_boundary_values():
    assert double_the_difference([1, 2, 3]) == 10
    assert double_the_difference([2, 3, 4]) == 18

def test_large_numbers():
    assert double_the_difference([100, 200, 300]) == 10000

def test_negative_large_numbers():
    assert double_the_difference([-100, -200, -300]) == 0

def test_float_numbers():
    assert double_the_difference([1.5, 2.5, 3.5]) == 0

def test_negative_float_numbers():
    assert double_the_difference([-1.5, -2.5, -3.5]) == 0

def test_mixed_numbers():
    assert double_the_difference([1, -2, 3]) == 10
    assert double_the_difference([-1, 2, -3]) == 10
