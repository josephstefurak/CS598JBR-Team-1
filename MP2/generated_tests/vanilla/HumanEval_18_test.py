from HumanEval_18 import *

import pytest

def test_how_many_times():
    assert how_many_times('hello world', 'lo') == 2
    assert how_many_times('aaaaa', 'aa') == 3
    assert how_many_times('abcabcabc', 'abc') == 3
    assert how_many_times('abc', 'd') == 0
    assert how_many_times('aabaa', 'aa') == 2
    assert how_many_times('', 'a') == 0
    assert how_many_times('a', '') == 0
    assert how_many_times('', '') == 0
