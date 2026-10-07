import pytest

from HumanEval_18 import *

def test_empty_string():
    assert how_many_times('', 'a') == 0

def test_single_character_match():
    assert how_many_times('aaa', 'a') == 3

def test_multiple_character_match():
    assert how_many_times('aaaa', 'aa') == 3

def test_no_match():
    assert how_many_times('abcd', 'ef') == 0

def test_overlapping_match():
    assert how_many_times('ababa', 'aba') == 2

def test_substring_at_start():
    assert how_many_times('aaab', 'aa') == 2

def test_substring_at_end():
    assert how_many_times('abab', 'ab') == 2

def test_substring_not_in_string():
    assert how_many_times('abcd', 'xyz') == 0

def test_substring_is_empty():
    assert how_many_times('abcd', '') == 0

def test_string_is_empty():
    assert how_many_times('', 'ab') == 0
