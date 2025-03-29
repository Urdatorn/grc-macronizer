import re

import re

# Use character classes for single-character choices
diphth_y = r'[αεηο][ὐὔυὑύὖῦὕὗὺὒὓ]'
diphth_i = r'[αεου][ἰίιῖἴἶἵἱἷὶἲἳ]'
adscr_i = r'[αηωἀἠὠἁἡὡάήώὰὴὼᾶῆῶὤὥὢὣἄἅἂἃἤἥἣἢἦἧἆἇὧὦ]ι'

# Combine all patterns and ensure [_^] follows
combined_pattern = re.compile(f'(?:{diphth_y}|{diphth_i}|{adscr_i})[_^]')

def macronized_diphthong(word):
    '''
    >>> macronized_diphthong("χίλι^οι)
    False
    >>> macronized_diphthong("χίλιοι^")
    True
    '''
    return bool(re.search(combined_pattern, word))

# Test cases
print(macronized_diphthong("αι_"))  # True
print(macronized_diphthong("αι"))   # False
print(macronized_diphthong("ξξξαιξξξ"))  # False
print(macronized_diphthong("ξξξαι_ξξξ"))  # True

test_words = ["χίλι^οι"]
for word in test_words:
    print(f"{word}: {macronized_diphthong(word)}")

