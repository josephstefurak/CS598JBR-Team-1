from HumanEval_70 import *

import pytest

def test_strange_sort_list():
    assert strange_sort_list([]) == []
    assert strange_sort_list([5]) == [5]
    assert strange_sort_list([3, 2, 1, 4, 5]) == [1, 5, 2, 4, 3]
    assert strange_sort_list([1, 2, 3, 4, 5]) == [1, 5, 2, 4, 3]
    assert strange_sort_list([5, 4, 3, 2, 1]) == [1, 5, 2, 4, 3]
    assert strange_sort_list([1, 1, 1, 1]) == [1, 1, 1, 1]
    assert strange_sort_list([2, 2, 2, 1]) == [1, 2, 2, 2]
    assert strange_sort_list([-1, -2, -3, -4, -5]) == [-1, -5, -2, -4, -3]
    assert strange_sort_list([-5, -4, -3, -2, -1]) == [-1, -5, -2, -4, -3]
