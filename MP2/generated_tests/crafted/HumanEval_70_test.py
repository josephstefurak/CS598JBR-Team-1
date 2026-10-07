import pytest

from HumanEval_70 import *

def test_strange_sort_list_example1():
    assert strange_sort_list([1, 2, 3, 4]) == [1, 4, 2, 3]

def test_strange_sort_list_example2():
    assert strange_sort_list([5, 5, 5, 5]) == [5, 5, 5, 5]

def test_strange_sort_list_empty():
    assert strange_sort_list([]) == []

def test_strange_sort_list_single_element():
    assert strange_sort_list([1]) == [1]

def test_strange_sort_list_zero():
    assert strange_sort_list([0, 0, 0, 0]) == [0, 0, 0, 0]

def test_strange_sort_list_negative():
    assert strange_sort_list([-1, -2, -3, -4]) == [-1, -4, -2, -3]

def test_strange_sort_list_boundary():
    assert strange_sort_list([1000000, -1000000, 0]) == [1000000, 0, -1000000]
