import pytest

from HumanEval_9 import *

def test_empty_input():
    assert rolling_max([]) == []

def test_single_element():
    assert rolling_max([5]) == [5]

def test_zero():
    assert rolling_max([0, 1, 2, 3, 0, 1]) == [0, 1, 2, 3, 3, 3]

def test_negative_numbers():
    assert rolling_max([-1, -2, -3, -2, -3, -4, -2]) == [-1, -1, -2, -2, -2, -2, -2]

def test_boundary_values():
    assert rolling_max([1000000, -1000000, 0, 1000000, -1000000, 0]) == [1000000, 1000000, 1000000, 1000000, 1000000, 1000000]

def test_normal_case():
    assert rolling_max([1, 2, 3, 2, 3, 4, 2]) == [1, 2, 3, 3, 3, 4, 4]
