from HumanEval_88 import *

import pytest

def test_sort_array_empty():
    assert sort_array([]) == []

def test_sort_array_one_element():
    assert sort_array([5]) == [5]

def test_sort_array_two_elements():
    assert sort_array([5, 1]) == [1, 5]

def test_sort_array_odd_sum():
    assert sort_array([5, 1, 9, 3]) == [1, 3, 5, 9]

def test_sort_array_even_sum():
    assert sort_array([5, 1, 9, 2]) == [9, 5, 1, 2]

def test_sort_array_negative_numbers():
    assert sort_array([-5, -1, 9, 3]) == [-5, -1, 3, 9]

def test_sort_array_negative_and_positive():
    assert sort_array([-5, 1, 9, -3]) == [-5, -3, 1, 9]
