from HumanEval_109 import *

import pytest

def test_move_one_ball_empty_array():
    assert move_one_ball([]) == True

def test_move_one_ball_single_element():
    assert move_one_ball([1]) == True

def test_move_one_ball_sorted_array():
    assert move_one_ball([1, 2, 3, 4, 5]) == True

def test_move_one_ball_unsorted_array():
    assert move_one_ball([2, 1, 3, 4, 5]) == False

def test_move_one_ball_negative_numbers():
    assert move_one_ball([-1, -2, -3, -4, -5]) == True

def test_move_one_ball_mixed_positive_negative_numbers():
    assert move_one_ball([-1, 2, -3, 4, -5]) == False
