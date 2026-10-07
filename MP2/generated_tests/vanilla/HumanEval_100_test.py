from HumanEval_100 import *

import pytest

def test_make_a_pile():
    assert make_a_pile(5) == [5, 7, 9, 11, 13]
    assert make_a_pile(10) == [10, 12, 14, 16, 18, 20, 22, 24, 26, 28]
    assert make_a_pile(0) == []
    assert make_a_pile(1) == [1]
    assert make_a_pile(2) == [2, 4]
