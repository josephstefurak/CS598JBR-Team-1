from HumanEval_122 import *

import pytest

def test_add_elements():
    assert add_elements([1, 2, 3, 4, 5], 3) == 6
    assert add_elements([10, 20, 30, 40, 50], 4) == 70
    assert add_elements([100, 200, 300, 400, 500], 5) == 1500
    assert add_elements([1000, 2000, 3000, 4000, 5000], 1) == 1000
    assert add_elements([10000, 20000, 30000, 4000, 50000], 2) == 30000
