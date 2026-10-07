from HumanEval_38 import *

import pytest

def test_encode_cyclic():
    assert encode_cyclic('abc') == 'bca'
    assert encode_cyclic('defghi') == 'efgdai'
    assert encode_cyclic('1234567890') == '2341567890'
    assert encode_cyclic('') == ''

def test_decode_cyclic():
    assert decode_cyclic('bca') == 'abc'
    assert decode_cyclic('efgdai') == 'defghi'
    assert decode_cyclic('2341567890') == '1234567890'
    assert decode_cyclic('') == ''
