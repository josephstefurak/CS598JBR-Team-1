from HumanEval_151 import *

import pytest

def test_double_the_difference():
    assert double_the_difference([1, 2, 3, 4, 5]) == 11
    assert double_the_difference([2, 3, 4, 5, 6]) == 0
    assert double_the_difference([1.1, 2, 3, 4, 5]) == 11
    assert double_the_difference([1, 2, 3, 4.4, 5]) == 11
    assert double_the_difference([1, 2, 3, 4, 5.5]) == 11
    assert double_the_difference([-1, 2, 3, 4, 5]) == 11
    assert double_the_difference([1, -2, 3, 4, 5]) == 11
    assert double_the_difference([1, 2, -3, 4, 5]) == 11
    assert double_the_difference([1, 2, 3, -4, 5]) == 11
    assert double_the_difference([1, 2, 3, 4, -5]) == 11
    assert double_the_difference([]) == 0
