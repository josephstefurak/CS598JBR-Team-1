
from HumanEval_133 import *
import math
import pytest

def test_sum_squares_empty():
    """Test the sum_squares function with an empty list"""
    assert sum_squares([]) == 0

def test_sum_squares_single_element():
    """Test the sum_squares function with a single element"""
    assert sum_squares([1]) == 1

def test_sum_squares_zero():
    """Test the sum_squares function with a zero"""
    assert sum_squares([0]) == 0

def test_sum_squares_negative_numbers():
    """Test the sum_squares function with negative numbers"""
    assert sum_squares([-1, -2, -3]) == 14

def test_sum_squares_boundary_values():
    """Test the sum_squares function with boundary values"""
    assert sum_squares([1.4, 4.2, 0]) == 29

def test_sum_squares_large_numbers():
    """Test the sum_squares function with large numbers"""
    assert sum_squares([1000000.0, 2000000.0, 3000000.0]) == 1000000000000.0

def test_sum_squares_negative_large_numbers():
    """Test the sum_squares function with negative large numbers"""
    assert sumsum_squares([-1000000.0, -2000000.0, -3000000.0]) == 1000000000000.0

def test_sum_squares_negative_boundary_values():
    """Test the sum_squares function with negative boundary values"""
    assert sum_squares([-1.4, -4.2, 0]) == 29

def test_sum_squares_negative_small_numbers():
    """Test the sum_squares function with negative small numbers"""
    assert sum_squares([-1, -2, -3]) == 14

def test_sum_squares_small_numbers():
    """Test the sum_squares function with small numbers"""
    assert sum_squares([1, 2, 3]) == 14
