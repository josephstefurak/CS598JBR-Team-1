from HumanEval_36 import *

import pytest

def test_fizz_buzz():
    assert fizz_buzz(0) == 0
    assert fizz_buzz(1) == 0
    assert fizz_buzz(10) == 0
    assert fizz_buzz(11) == 0
    assert fizz_buzz(13) == 0
    assert fizz_buzz(14) == 0
    assert fizz_buzz(100) == 0
    assert fizz_buzz(110) == 1
    assert fizz_buzz(130) == 1
    assert fizz_buzz(140) == 1
    assert fizz_buzz(1000) == 2
