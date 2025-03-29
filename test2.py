import re
import unicodedata
from grc_utils import has_ambiguous_dichrona, oxia_to_tonos, word_with_real_dichrona, open_syllable_in_word, syllabifier, vowel

def count_dichrona_in_open_syllables(string):
    count = 0
    
    if not string:
        return count

    string = unicodedata.normalize('NFC', oxia_to_tonos(string))
    
    words = re.findall(r'[\w_^]+', string)
    words = [word for word in words if any(vowel(char) for char in word)]
    print(words)
    for word in words:
        list_of_syllables = syllabifier(word)
        print(list_of_syllables)
        for syllable in list_of_syllables:
            if word_with_real_dichrona(syllable) and open_syllable_in_word(syllable, list_of_syllables) and not any(char in '^_' for char in syllable): # = unmacronized open dichronon
                count += 1

    return count

count = count_dichrona_in_open_syllables('ἐνταῦθα')

print(count)