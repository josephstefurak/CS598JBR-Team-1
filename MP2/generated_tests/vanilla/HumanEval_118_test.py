from HumanEval_118 import *

import pytest

def test_get_closest_vowel():
    assert get_closest_vowel('') == ''
    assert get_closest_vowel('b') == ''
    assert get_closest_vowel('bcd') == ''
    assert get_closest_vowel('bcdfgh') == ''
    assert get_closest_vowel('bcdfghi') == 'i'
    assert get_closest_vowel('bcdfghie') == 'e'
    assert get_closest_vowel('bcdfghiea') == 'a'
    assert get_closest_vowel('bcdfghieai') == ''
    assert get_closest_vowel('bcdfghieaI') == 'I'
    assert get_closest_vowel('bcdfghieaIb') == ''
    assert get_closest_vowel('bcdfghieaIbcd') == ''
    assert get_closest_vowel('bcdfghieaIbcdfgh') == ''
    assert get_closest_vowel('bcdfghieaIbcdfghi') == 'i'
    assert get_closest_vowel('bcdfghieaIbcdfghie') == 'e'
    assert get_closest_vowel('bcdfghieaIbcdfghiea') == 'a'
    assert get_closest_vowel('bcdfghieaIbcdfghieai') == ''
    assert get_closest_vowel('bcdfghieaIbcdfghieaIb') == ''
    assert get_closest_vowel('bcdfghieaIbcdfghieaIbcd') == ''
    assert get_closest_vowel('bcdfghieaIbcdfghieaIbcdfgh') == ''
    assert get_closest_vowel('bcdfghieaIbcdfghieaIbcdfghi') == 'i'
    assert get_closest_vowel('bcdfghieaIbcdfghieaIbcdfghie') == 'e'
    assert get_closest_vowel('bcdfghieaIbcdfghieaIbcdfghiea') == 'a'
