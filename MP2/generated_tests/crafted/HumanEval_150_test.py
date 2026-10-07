import pytest

from HumanEval_150 import *

def test_x_or_y_prime():
    """Test x_or_y with a prime number"""
    assert x_or_y(7, 34, 12) == 34

def test_x_or_y_not_prime():
    """Test x_or_y with a non-prime number"""
    assert x_or_y(15, 8, 5) == 5

def test_x_or_y_1():
    """Test x_or_y with 1"""
    assert x_or_y(1, 34, 12) == 12

def test_x_or_y_negative():
    """Test x_or_y with negative number"""
    assert x_or_y(-3, 34, 12) == 12

def test_x_or_y_0():
    """Test x_or_y with 0"""
    assert x_or_y(0, 34, 12) == 12

def test_x_or_y_2():
    """Test x_or_y with 2"""
    assert x_or_y(2, 34, 12) == 34

def test_x_or_y_negative_x():
    """Test x_or_y with negative x"""
    assert x_or_y(7, -34, 12) == -34

def test_x_or_y_negative_y():
    """Test x_or_y with negative y"""
    assert x_or_y(7, 34, -12) == 34
