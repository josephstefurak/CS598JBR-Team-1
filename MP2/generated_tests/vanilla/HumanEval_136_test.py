from HumanEval_136 import *

import pytest

def test_largest_smallest_integers():
    assert largest_smallest_integers([1, 2, 3, -4, -5, 6]) == (6, -4)
    assert largest_smallest_integers([1, 2, 3, 4, 5, 6]) == (6, 1)
    assert largest_smallest_integers([-1, -2, -3, -4, -5, -6]) == (-1, -6)
    assert largest_smallest_integers([]) == (None, None)
    assert largest_smallest_integers([1, -2, 3, -4, 5, -6]) == (-2, 1)
