'''
Tread carefully. This is a minefield of Unicode normalization and combining characters.
'''

import unicodedata

from grc_utils import macrons_map, normalize_word

SHORT = '̆'
LONG = '̄'


def strip_length_string(string):
    '''
    Strips the input string of all length diacritics using the macrons_map dictionary.
    >>> strip_length_string('ᾰᾸᾱᾹῐῘῑῙῠῨῡῩᾰ̓Ᾰ̓ᾰ̔Ᾰ̔ᾰ́ᾰ̀ᾱ̓Ᾱ̓ᾱ̔Ᾱ̔ᾱ́ᾱ̀ᾱͅῐ̓Ῐ̓ῐ̔Ῐ̔ῐ́ῐ̀ῐ̈ῑ̓Ῑ̓ῑ̔Ῑ̔ῑ́ῑ̈ῠ̓ῠ̔Ῠ̔ῠ́ῠ̀ῠ͂ῠ̈ῠ̒ῡ̔Ῡ̔ῡ́ῡ̈')
    >>> αΑαΑιΙιΙυΥυΥἀἈἁἉάὰἀἈἁἉάὰᾳἰἸἱἹίὶϊἰἸἱἹίϊὐὑὙύὺῦϋυ̒ὑὙύϋ
    '''
    for composite, replacement in macrons_map.items():
        string = string.replace(composite, replacement)
    return string


def macron_unicode_to_markup(text):
    '''
    >>> macron_unicode_to_markup('νεᾱνῐ́ᾱς')
    >>> νεα_νί^α_ς

    (I grappled with a unicode bug for a LONG time! The solution came from Grok 3)
    '''
    # Step 1: Decompose into base characters and combining marks
    decomposed = unicodedata.normalize('NFD', text)
    
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
    
    # Most Greek punctuation decomposes to Latin punctuation, so we need to revert that
    # middle dot (U+00B7) -> ano teleia (U+0387)
    # semicolon (U+003B) -> Greek question mark (U+037E)
    result = result.replace('\u00b7', '\u0387')
    result = result.replace('\u003b', '\u037e')
    return result


def macron_markup_to_unicode(text):
    '''
    >>> assert macron_markup_to_unicode('νεα_νί^α_ς') == 'νεᾱνῐ́ᾱς'
    '''
    result = ''
    i = 0
    while i < len(text):
        char = text[i]
        if unicodedata.category(char).startswith('L'):
            # Collect diacritics
            diacritics = ''
            i += 1
            while i < len(text) and unicodedata.category(text[i]).startswith('M'):
                diacritics += text[i]
                i += 1
            # Check for length marker
            length_combining = ''
            if i < len(text) and text[i] in '_^':
                if text[i] == '_':
                    length_combining = '̄'  # Macron
                elif text[i] == '^':
                    length_combining = '̆'  # Breve
                i += 1
            # Construct sequence: base + length_combining + diacritics
            sequence = char + length_combining + diacritics
            # Normalize to NFC
            composed = unicodedata.normalize('NFC', sequence)
            result += composed
        else:
            # Non-letter, append as is
            result += char
            i += 1
    
    # Most Greek punctuation decomposes to Latin punctuation, so we need to revert that
    # middle dot (U+00B7) -> ano teleia (U+0387)
    # semicolon (U+003B) -> Greek question mark (U+037E)
    result = result.replace('\u00b7', '\u0387')
    result = result.replace('\u003b', '\u037e')
    return result


anabasis_unicode_test = '''Δαρείου καὶ Παρυσάτιδος γίγνονται παῖδες δῠ́ο, πρεσβῠ́τερος μὲν Ἀρταξέρξης, νεώτερος δὲ Κῦρος· ἐπεὶ δὲ ἠσθένει Δαρεῖος καὶ ῠ̔πώπτευε τελευτὴν τοῦ βῐ́ου, ἐβούλετο τὼ παῖδε ᾰ̓μφοτέρω πᾰρεῖναι. ὁ μὲν οὖν πρεσβῠ́τερος πᾰρὼν ἐτύγχᾰνε· Κῦρον δὲ μετᾰπέμπεται ἀπὸ τῆς ἀρχῆς ἧς αὐτὸν σατράπην ἐποίησε, καὶ στρατηγὸν δὲ αὐτὸν ἀπέδειξε πᾰ́ντων ὅσοι ἐς Καστωλοῦ πεδίον ἁθροίζονται. ᾰ̓νᾰβαίνει οὖν ὁ Κῦρος λᾰβὼν Τισσαφέρνην ὡς φῐ́λον, καὶ τῶν Ἑλλήνων ἔχων ὁπλῑ́τᾱς ᾰ̓νέβη τρῐᾱκοσῐ́ους, ᾰ̓́ρχοντᾰ δὲ αὐτῶν Ξενίαν Παρράσιον. ἐπεὶ δὲ ἐτελεύτησε Δαρεῖος καὶ κᾰτέστη εἰς τὴν βᾰσῐλείᾱν Ἀρταξέρξης, Τισσαφέρνης διαβάλλει τὸν Κῦρον πρὸς τὸν ᾰ̓δελφὸν ὡς ἐπῐβουλεύοι αὐτῷ. ὁ δὲ πείθεται καὶ σῠλλᾰμβᾰ́νει Κῦρον ὡς ἀποκτενῶν·'''
anabasis_markup_test = macron_unicode_to_markup(anabasis_unicode_test)
assert macron_markup_to_unicode(anabasis_markup_test) == anabasis_unicode_test


def macron_integrate_markup(word, macrons):
    '''    
    >>> macron_integrate_markup('νεανίας', '_3,^5,_6')
    'νεα_νί^α_ς'
    '''
    # Parse the macrons string into a list of (marker, position) tuples
    if not macrons:
        return word
    
    markup_list = []
    for mark in macrons.split(','):
        mark = mark.strip()
        if mark:
            marker = mark[0]  # _ or ^
            position = int(mark[1:])  # Convert position to integer
            markup_list.append((marker, position))
    
    # Sort markup by position (highest first) to avoid shifting issues
    markup_list.sort(key=lambda x: x[1], reverse=True)
    
    # Decompose the word into NFD to handle combining characters
    decomposed = unicodedata.normalize('NFD', word)
    
    # Build the result by inserting markup at specified positions
    result = ''
    char_pos = 0  # Tracks position of base characters (letters)
    i = 0  # Index in decomposed string
    
    while i < len(decomposed):
        char = decomposed[i]
        if unicodedata.category(char).startswith('L'):
            char_pos += 1  # Increment for each base letter
            # Collect diacritics for this character
            diacritics = ''
            i += 1
            while i < len(decomposed) and unicodedata.category(decomposed[i]).startswith('M'):
                diacritics += decomposed[i]
                i += 1
            # Check if this position has a length marker
            length_marker = ''
            for marker, pos in markup_list:
                if pos == char_pos:
                    length_marker = marker
                    break
            result += char + diacritics + length_marker
        else:
            # Non-letter character (e.g., punctuation)
            result += char
            i += 1

    return normalize_word(result)

# Test the function
if __name__ == "__main__":
    test_word = 'νεανίας'
    test_macrons = '_3,^5,_6'
    result = macron_integrate_markup(test_word, test_macrons)
    print(f"Input: {test_word}, {test_macrons}")
    print(f"Output: {result}")
    assert result == 'νεα_νί^α_ς'

