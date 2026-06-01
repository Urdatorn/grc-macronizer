import re
import unicodedata

from format_macrons import macron_unicode_to_markup
from grc_utils import all_vowels_lowercase, has_ambiguous_dichrona, no_macrons, oxia_to_tonos, only_bases, word_with_real_dichrona, open_syllable_in_word, syllabifier, vowel, count_dichrona_in_open_syllables

from bailly_vowels import bailly

def mark_dichrona_in_open_syllables(string):
    if not string:
        return string

    # Normalize and convert oxia to tonos
    string = unicodedata.normalize('NFC', oxia_to_tonos(string))
    
    # Split into words and filter for those with vowels
    words = re.findall(r'[\w_^]+', string)
    words = [word for word in words if any(vowel(char) for char in word)]
    
    # Process each word and build the colored output
    result = []
    last_end = 0
    
    for word in words:
        # Find the word's position in the original string
        start = string.index(word, last_end)
        end = start + len(word)
        
        # Add any non-word characters before this word
        result.append(string[last_end:start])
        
        # Syllabify the word
        list_of_syllables = syllabifier(word)
        colored_word = ""
        
        # Process each character with look-ahead for _ or ^
        for i, char in enumerate(word):
            # Check if this char is followed by _ or ^
            is_green = (i + 1 < len(word) and word[i + 1] in '_^')
            
            # Check if this char is part of a dichrona in an open syllable
            is_red = False
            if not is_green and not (char in '_^'):  # Skip if it's _ or ^ itself
                # Find which syllable this char belongs to
                char_pos = 0
                for syllable in list_of_syllables:
                    syllable_len = len(syllable)
                    if char_pos <= i < char_pos + syllable_len:
                        if (word_with_real_dichrona(syllable) and 
                            open_syllable_in_word(syllable, list_of_syllables) and 
                            not any(c in '^_' for c in syllable) and 
                            vowel(char)):
                            is_red = True
                        break
                    char_pos += syllable_len
            
            # Apply markup
            if is_red:
                colored_word += f'%{char}%'
            elif is_green:
                colored_word += f'%{char}%'
            else:
                colored_word += char
        
        result.append(colored_word)
        last_end = end
    
    # Add any remaining characters after the last word
    result.append(string[last_end:])
    
    return "".join(result)

bailly = {
    "ἀφροσιβόμβαξ": "ῐᾰκ", # 3D, dichronon in oblique case only
    "ἡμιβάρβαρος": "ῐᾰρο",
    "ἰδιόφυτον": "ῐδῠ",
}

for key in bailly:
    
    key = mark_dichrona_in_open_syllables(key)

    pattern = r"%(.+?)%"
    matches = re.finditer(pattern, key)

    for match in matches:
        print(key + ":" + match.group())



# for key, value in bailly.items():
#     #value = macron_unicode_to_markup(value)
    
#     list_key = list(key)
#     list_value = list(value)
#     list_value_bases = [only_bases(char) for char in value]

#     new_list_value = []
#     value_index = len(value) - 1

#     for char in reversed(list_key):
#         if char in list_value_bases:
#             new_list_value.append(list_value[value_index])
#             value_index =+ 1
#         else:
#             new_list_value.append(char)
    
#     new_value = "".join(new_list_value)

#     bailly[key] = new_value

#     print(f"{key}: {new_value}")



