from HumanEval_9 import *

import pytest

def test_rolling_max_empty():
    assert rolling_max([]) == [], 'Empty list should return an empty list'

def test_rolling_max_single_element():
    assert rolling_max([5]) == [5], 'Single element list should return the same list'

def test_rolling_max_multiple_elements():
    assert rolling_max([1, 2, 3, 2, 1]) == [1, 2, 3, 3, 3], 'List with multiple elements should return correct rolling max'

def test_rolling_max_negative_numbers():
    assert rolling_max([-1, -2, -3, -2, -1]) == [-1, -1, -1, -1, -1], 'List with negative numbers should return correct rolling max'

def test_rolling_max_mixed_positive_negative_numbers():
    assert rolling_max([1, -2, 3, -2, 1]) == [1, 1, 3, 3, 3], 'List with mixed positive and negative numbers should return correct rolling max'
