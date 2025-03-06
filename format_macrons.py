'''
Takes a list of polytonic Greek tokens such as 

νεᾱνῐ́ᾱς
νεᾱνῐ́ᾳ
νεᾱνῐείᾱ
νεᾱνῐεύομαι

and separates the tokens from the vowel-lengths, turning it into a two-column TSV, such as

νεανίας	_3^5_6
'''
import re
import unicodedata

from greek_accentuation.characters import length
from grc_utils import macrons_map, base_alphabet, base, normalize_word

SHORT = '̆'
LONG = '̄'

# Define length_count as a global dictionary
length_count = {'long': 0, 'short': 0}


def strip_length_string(string):
    '''
    Strips the input string of all length diacritics using the macrons_map dictionary.
    >>> strip_length_string('ᾰᾸᾱᾹῐῘῑῙῠῨῡῩᾰ̓Ᾰ̓ᾰ̔Ᾰ̔ᾰ́ᾰ̀ᾱ̓Ᾱ̓ᾱ̔Ᾱ̔ᾱ́ᾱ̀ᾱͅῐ̓Ῐ̓ῐ̔Ῐ̔ῐ́ῐ̀ῐ̈ῑ̓Ῑ̓ῑ̔Ῑ̔ῑ́ῑ̈ῠ̓ῠ̔Ῠ̔ῠ́ῠ̀ῠ͂ῠ̈ῠ̒ῡ̔Ῡ̔ῡ́ῡ̈')
    >>> αΑαΑιΙιΙυΥυΥἀἈἁἉάὰἀἈἁἉάὰᾳἰἸἱἹίὶϊἰἸἱἹίϊὐὑὙύὺῦϋυ̒ὑὙύϋ
    '''
    for composite, replacement in macrons_map.items():
        string = string.replace(composite, replacement)
    return string


def macron_unicode_to_markup(word):
    # Step 1: Decompose into base characters and combining marks
    decomposed = unicodedata.normalize('NFD', word)
    
    result = ''
    i = 0
    while i < len(decomposed):
        char = decomposed[i]
        # Step 2: Check if this is a letter
        if unicodedata.category(char).startswith('L'):
            # Collect all combining marks for this base character
            diacritics = ''
            length_marker = ''
            i += 1
            # Step 3: Process combining marks
            while i < len(decomposed) and unicodedata.category(decomposed[i]).startswith('M'):
                mark = decomposed[i]
                # Step 4: Classify the mark
                if mark == '̄':  # Macron (long)
                    length_marker = '_'
                elif mark == '̆':  # Breve (short)
                    length_marker = '^'
                else:
                    diacritics += mark  # Keep other diacritics (e.g., acute)
                i += 1
            # Step 5: Rebuild: base + diacritics + length marker
            result += char + diacritics + length_marker
        else:
            # Non-letter (e.g., punctuation), append as is
            result += char
            i += 1
    
    return result


def batch_macron_unicode_to_markup(text):
    def get_words(text):
        return re.findall(r'\w+', text)
    
    for word in get_words(text):
        yield macron_unicode_to_markup(word)


print(macron_unicode_to_markup('νεᾱνῐ́ᾱς'))

if __name__ == '__main__':
    from anabasis import anabasis
    from anabasis_macronized import anabasis_macronized

    #assert anabasis == 
