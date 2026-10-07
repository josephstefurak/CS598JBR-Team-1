from HumanEval_150 import *

import pytest

def test_x_or_y():
    assert x_or_y(1, 'x', 'y') == 'y'
    assert x_or_y(2, 'x', 'y') == 'x'
    assert x_or_y(3, 'x', 'y') == 'x'
    assert x_or_y(4, 'x', 'y') == 'y'
    assert x_or_y(5, 'x', 'y') == 'x'
    assert x_or_y(6, 'x', 'y') == 'y'
    assert x_or_y(7, 'x', 'y') == 'x'
    assert x_or_y(8, 'x', 'y') == 'y'
    assert x_or_y(9, 'x', 'y') == 'y'
    assert x_or_y(10, 'x', 'y') == 'y'
