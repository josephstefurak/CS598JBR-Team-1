import pytest

from HumanEval_118 import *

def test_get_closest_vowel_yogurt():
    assert get_closest_vowel('yogurt') == 'u'

def test_get_closest_vowel_FULL():
    assert get_closest_vowel('FULL') == 'U'

def test_get_closest_vowel_quick():
    assert get_closest_vowel('quick') == ''

def test_get_closest_vowel_ab():
    assert get_closest_vowel('ab') == ''

def test_get_closest_vowel_empty_string():
    assert get_closest_vowel('') == ''

def test_get_closest_vowel_single_character():
    assert get_closest_vowel('a') == ''

def test_get_closest_vowel_zero():
    assert get_closest_vowel('0') == ''

def test_get_closest_vowel_negative_numbers():
    assert get_closest_vowel('-1') == ''

def test_get_closest_vowel_boundary_values():
    assert get_closest_vowel('aaa') == ''
    assert get_closest_vowel('eee') == ''
    assert get_closest_vowel('iii') == ''
    assert get_closest_vowel('ooo') == ''
    assert get_closest_vowel('uuu') == ''
