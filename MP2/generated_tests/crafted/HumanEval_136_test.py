import pytest

from HumanEval_136 import *

def test_largest_smallest_integers():
    assert largest_smallest_integers([2, 4, 1, 3, 5, 7]) == (None, 1)
    assert largest_smallest_integers([]) == (None, None)
    assert largest_smallest_integers([0]) == (None, None)
    assert largest_smallest_integers([-2, -4, -1, -3, -5, -7]) == (-1, None)
    assert largest_smallest_integers([2, 4, 1, 3, 5, 7]) == (None, 1)
    assert largest_smallest_integers([-2, 4, -1, 3, -5, 7]) == (-2, 3)
    assert largest_smallest_integers([-2, 0, 4, -1, 3, 0, 7]) == (-1, 3)
    assert largest_smallest_integers([-2147483648, 4, -1, 3, -5, 7]) == (-2147483648, 3)
    assert largest_smallest_integers([2147483647, 4, -1, 3, -5, 7]) == (None, 1)
