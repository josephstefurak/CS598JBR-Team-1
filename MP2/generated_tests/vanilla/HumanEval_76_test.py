from HumanEval_76 import *

import pytest

def test_is_simple_power_with_simple_numbers():
    assert is_simple_power(1, 1) == True
    assert is_simple_power(8, 2) == True
    assert is_simple_power(27, 3) == True
    assert is_simple_power(64, 4) == True
    assert is_simple_power(125, 5) == True

def test_is_simple_power_with_complex_numbers():
    assert is_simple_power(16, 2) == True
    assert is_simple_power(243, 3) == True
    assert is_simple_power(128, 4) == True
    assert is_simple_power(343, 5) == False

def test_is_simple_power_with_zero():
    assert is_simple_power(0, 0) == True
    assert is_simple_power(0, 1) == False
    assert is_simple_power(0, 2) == False

def test_is_simple_power_with_negative_numbers():
    assert is_simple_power(-1, 1) == False
    assert is_simple_power(-8, 2) == False
    assert is_simple_power(-27, 3) == False
    assert is_simple_power(-64, 4) == False
    assert is_simple_power(-125, 5) == False
