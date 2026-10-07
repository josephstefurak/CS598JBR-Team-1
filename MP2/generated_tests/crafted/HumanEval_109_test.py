import pytest

from HumanEval_109 import *

def test_empty_array():
    assert move_one_ball([]) == True

def test_sorted_array():
    assert move_one_ball([1, 2, 3, 4, 5]) == True

def test_shifted_array():
    assert move_one_ball([3, 4, 5, 1, 2]) == True

def test_unsorted_array():
    assert move_one_ball([3, 5, 4, 1, 2]) == False

def test_single_element_array():
    assert move_one_ball([1]) == True

def test_zero_array():
    assert move_one_ball([0, 0, 0, 0]) == True

def test_negative_numbers():
    assert move_one_ball([-1, -2, -3, -4, -5]) == True

def test_boundary_values():
    assert move_one_ball([1000000, 2000000, 3000000, 4000000]) == True

def test_duplicate_values():
    assert move_one_ball([1, 1, 1, 1]) == True

def test_large_array():
    arr = list(range(1, 1000000))
    arr.reverse()
    assert move_one_ball(arr) == True
