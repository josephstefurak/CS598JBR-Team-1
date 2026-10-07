import pytest

from HumanEval_76 import *

def test_is_simple_power_1():
    assert is_simple_power(1, 1) == True

def test_is_simple_power_2():
    assert is_simple_power(4, 2) == True

def test_is_simple_power_3():
    assert is_simple_power(8, 2) == True

def test_is_simple_power_4():
    assert is_simple_power(27, 3) == True

def test_is_simple_power_5():
    assert is_simple_power(16, 2) == True

def test_is_simple_power_6():
    assert is_simple_power(32, 2) == True

def test_is_simple_power_7():
    assert is_simple_power(64, 2) == True

def test_is_simple_power_8():
    assert is_simple_power(5, 2) == False

def test_is_simple_power_9():
    assert is_simple_power(10, 2) == False

def test_is_simple_power_10():
    assert is_simple_power(15, 2) == False

def test_is_simple_power_11():
    assert is_simple_power(20, 2) == False

def test_is_simple_power_12():
    assert is_simple_power(25, 2) == False

def test_is_simple_power_13():
    assert is_simple_power(30, 2) == False

def test_is_simple_power_14():
    assert is_simple_power(31, 2) == False

def test_is_simple_power_15():
    assert is_simple_power(32, 2) == False

def test_is_simple_power_16():
    assert is_simple_power(33, 2) == False

def test_is_simple_power_17():
    assert is_simple_power(34, 2) == False

def test_is_simple_power_18():
    assert is_simple_power(35, 2) == False

def test_is_simple_power_19():
    assert is_simple_power(36, 2) == False

def test_is_simple_power_20():
    assert is_simple_power(37, 2) == False

def test_is_simple_power_21():
    assert is_simple_power(38, 2) == False

def test_is_simple_power_22():
    assert is_simple_power(39, 2) == False

def test_is_simple_power_23():
    assert is_simple_power(40, 2) == False

def test_is_simple_power_24():
    assert is_simple_power(41, 2) == False

def test_is_simple_power_25():
    assert is_simple_power(42, 2) == False

def test_is_simple_power_26():
    assert is_simple_power(43, 2) == False

def test_is_simple_power_27():
    assert is_simple_power(44, 2) == False

def test_is_simple_power_28():
    assert is_simple_power(45, 2) == False

def test_is_simple_power_29():
    assert is_simple_power(46, 2) == False

def test_is_simple_power_30():
    assert is_simple_power(47, 2) == False

def test_is_simple_power_31():
    assert is_simple_power(48, 2) == False

def test_is_simple_power_32():
    assert is_simple_power(49, 2) == False

def test_is_simple_power_33():
    assert is_simple_power(50, 2) == False
