from HumanEval_133 import *

import pytest
import math

def test_sum_squares_positive_numbers():
    assert sum_squares([1.1, 2.2, 3.3]) == 12

def test_sum_squares_negative_numbers():
    assert sum_squares([-1.1, -2.2, -3.3]) == 12

def test_sum_squares_mixed_numbers():
    assert sum_squares([-1.1, 2.2, 3.3]) == 12

def test_sum_squares_empty_list():
    assert sum_squares([]) == 0

def test_sum_squares_large_numbers():
    large_list = [i for i in range(1, 1001)]
    squared_sum = sum([math.ceil(i) ** 2 for i in large_list])
    assert sum_squares(large_list) == squared_sum
