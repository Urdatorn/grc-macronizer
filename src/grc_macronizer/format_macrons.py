'''
Tread carefully. This is a minefield of Unicode normalization and combining characters.
'''

import logging
import unicodedata

from grc_utils import macrons_map, normalize_word

SHORT = '̆'
LONG = '̄'

def macron_unicode_to_markup(text):
    '''
    >>> macron_unicode_to_markup('νεᾱνῐ́ᾱς')
    >>> νεα_νί^α_ς

    NB1: Sending markup through this is fine; it will do nothing.
    NB2: I grappled with a unicode bug for a LONG time! The solution came from Grok 3.
    '''
    #if not SHORT in text and not LONG in text:
    #    return text

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
                if mark == LONG:  # Macron
                    length_marker = '_'
                elif mark == SHORT:  # Breve
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
    return normalize_word(result)


def macron_markup_to_unicode(text):
    '''
    >>> assert macron_markup_to_unicode('νεα_νί^α_ς') == 'νεᾱνῐ́ᾱς'
    '''
    if not '_' in text and not '^' in text:
        return text

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


def merge_or_overwrite_markup(new_version, old_version, precedence='new'):
    '''
    Merges two versions of a string with markup (^ and _), following these rules:
    1. If one version has markup at position i and other doesn't, use the markup
    2. If versions disagree at position i, use the markup of whatever version takes precedence
    3. If versions agree, use that markup

    This boils down to:
    - If the version with precedence has markup, use it
    - but if only the other has markup, use that one
    
    >>> merge_or_overwrite_markup('st_ring^', 's_t^ring^')
    's_t_ring^'
    '''

    if not new_version:
        logging.debug('No new version, returning old version')
        return old_version
    if not old_version:
        logging.debug('No old version, returning new version')
        return new_version
    
    # assert normalize_word(new_version.replace('^', '').replace('_', '')) == normalize_word(old_version.replace('^', '').replace('_', '')), \
    #     f'Cannot merge markup on different words: {new_version} vs {old_version}'

    if normalize_word(new_version.replace('^', '').replace('_', '')) != normalize_word(old_version.replace('^', '').replace('_', '')):
        logging.debug('Words do not match, returning old version to be on the safe side')
        return old_version

    
    # First, get base string without markup
    base = ''.join(c for c in new_version if c not in '^_')
    
    # Create lists to track markup positions
    new_markup = [''] * len(base)
    old_markup = [''] * len(base)
    
    # Fill markup positions for new version
    pos = 0
    for i, c in enumerate(new_version):
        if c in '^_':
            new_markup[pos-1] = c
        else:
            pos += 1
            
    # Fill markup positions for old version
    pos = 0
    for i, c in enumerate(old_version):
        if c in '^_':
            old_markup[pos-1] = c
        else:
            pos += 1
    
    # Merge according to rules
    result = []
    pos = 0
    for i, c in enumerate(base):
        result.append(c)
        if precedence == 'new': 
            # If new has markup, use it
            if new_markup[i]:
                result.append(new_markup[i])
            # If only old has markup, use it
            elif old_markup[i]:
                result.append(old_markup[i])
        else:
            # If old has markup, use it
            if old_markup[i]:
                result.append(old_markup[i])
            # If only new has markup, use it
            elif new_markup[i]:
                result.append(new_markup[i])
            
    return ''.join(result)

assert merge_or_overwrite_markup('st_ring^', 's_t^ring^') == 's_t_ring^'