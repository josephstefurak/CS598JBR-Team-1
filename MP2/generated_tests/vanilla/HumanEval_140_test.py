from HumanEval_140 import *

import pytest

def test_fix_spaces():
    assert fix_spaces('') == ''
    assert fix_spaces('a') == 'a'
    assert fix_spaces('hi') == 'hi'
    assert fix_spaces('two words') == 'two-words'
    assert fix_spaces('three   words') == 'three-words'
    assert fix_spaces('four    spaces') == 'four-spaces'
    assert fix_spaces('five     spaces  ') == 'five-spaces-'
    assert fix_spaces('one_space ') == 'one_space'
    assert fix_spaces('multiple   tabs   and   spaces') == 'multiple-tabs-and-spaces'
