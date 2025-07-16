'''
Here we define what the output should never be, withot exception:
- Diphthongs should never be macronized.
- Closed syllables should not have macrons.
'''

import re

from grc_utils import patterns, syllabifier, vowel, is_open_syllable_in_word_in_synapheia

diphth_i = patterns['diphth_i']
diphth_y = patterns['diphth_y']

adscr_i = patterns['adscr_i']
subscr_i = patterns['subscr_i']

split_diphth_i = re.compile(r'(?:α|ε|υ|ο|Α|Ε|Υ|Ο)[_^](?:ἰ|ί|ι|ῖ|ἴ|ἶ|ἵ|ἱ|ἷ|ὶ|ἲ|ἳ)')
split_diphth_y = re.compile(r'(?:α|ε|η|ο|Α|Ε|Η|Ο)[_^](?:ὐ|ὔ|υ|ὑ|ύ|ὖ|ῦ|ὕ|ὗ|ὺ|ὒ|ὓ)')

diphthong_plus_markup = re.compile(fr'(?:{diphth_y}|{diphth_i}|{adscr_i})[_^]')

def closed_syllable(syll: str) -> bool:
    return not vowel(syll[-1])

def macronized_diphthong(word: str) -> bool:
    '''
    Makes sure diphthongs are never in any way macronzied.
    Part of the sanity check.

        >>> macronized_diphthong("χίλι^οι)
        False
        >>> macronized_diphthong("χίλιοι^")
        True

    Should also pick up on erroneously split diphthongs:
        >>> macronized_diphthong("δα^ιμων")
        True

        >>> macronized_diphthong("δα^ϊμων")
        False
    '''
    syllable_list = syllabifier(word)

    for syllable in syllable_list:
        if re.search(diphthong_plus_markup, syllable) or re.search(subscr_i, syllable) or re.search(split_diphth_i, syllable) or re.search(split_diphth_y, syllable):
            return True
    return False

def demacronize_diphthong(word: str) -> str:
    '''
    Demacronizes diphthongs in a word.
    '''
    syllable_list = syllabifier(word)
    
    for idx, syllable in enumerate(syllable_list):
        if macronized_diphthong(syllable):
            syllable = syllable.replace("^", "").replace("_", "")
            syllable_list[idx] = syllable

    return ''.join(syllable_list)

def macronized_closed_syllable():
    pass

if __name__ == "__main__":
    print(macronized_diphthong("χίλιοι^"))  # Should return True
    print(macronized_diphthong("χίλι^οι"))  # Should return False
    print(macronized_diphthong("δα^ίμων"))  # Should return True
    print(macronized_diphthong("δαίμων"))  # Should return True
    print(macronized_diphthong("δα^ϊμων"))  # Should return False

    print("\n")

    print("δα^ίμων", "=>", demacronize_diphthong("δα^ίμων"))  # Should return "δαίμων"
    print("χίλιοι^", "=>", demacronize_diphthong("χίλιοι^"))  # Should return "χίλιοι"

    print("\n")

    print(closed_syllable("ἀνθ"))  # Should return False
    print(closed_syllable("ἀ"))  # Should return True

    print("\n")

    print(is_open_syllable_in_word_in_synapheia("πὶς", ["ἐλ", "πὶς"], "ἀνθρώπου"))
    print(is_open_syllable_in_word_in_synapheia("πὶς", ["ἐλ", "πὶς"], ""))