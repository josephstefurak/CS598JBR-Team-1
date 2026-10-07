import pytest

from HumanEval_140 import *

def test_fix_spaces_example():
    assert fix_spaces('Example') == 'Example'

def test_fix_spaces_one_space():
    assert fix_spaces('Example 1') == 'Example_1'

def test_fix_spaces_leading_space():
    assert fix_spaces(' Example 2') == '_Example_2'

def test_fix_spaces_multiple_spaces():
    assert fix_spaces(' Example   3') == '_Example-3'

def test_fix_spaces_empty_string():
    assert fix_spaces('') == ''

def test_fix_spaces_single_character():
    assert fix_spaces('E') == 'E'

def test_fix_spaces_zero():
    assert fix_spaces('0') == '0'

def test_fix_spaces_negative_numbers():
    assert fix_spaces('-1') == '-1'

def test_fix_spaces_boundary_values():
    assert fix_spaces(' ' * 100) == '-'
