'''
ALGORITHMIC MACRONIZING PART 1

We put brevia on the ultimas of tokens which pass:
    properispomenon_with_dichronon_in_ultima or
    proparoxytone_with_dichronon_in_ultima

Position in general algorithmic process: 
==> (i) macronize all accentually-determined "free" macrons that were not filtered out by filter_dichrona.py because the token also contained one or more "true dichrona"
    (ii) generalize the already macronized tokens by rule-bound inferences
    (iii) generalize whatever endings are left over algorithmically

Test file:
    lemma	tag	token	macron	source
    χαρακτήρ	n-s---mn-	χαρακτήρ	^2	wiktionary
    λήμματα	n-s---fa-	σφραγίς	^7	ifthimos
    λήμματα	n-s---fa-	σφραγίς	_4^6	ifthimos
    σφραγῖδα	n-s---fa-	σφραγίς	_4	
Result:
    lemma	tag	token	macron	source
    χαρακτήρ	n-s---mn-	χαρακτήρ	^2	wiktionary
    λήμματα	n-s---fa-	σφραγίς	^7	ifthimos
    λήμματα	n-s---fa-	σφραγίς	_4^6^7	ifthimos,breve_ultima
    σφραγῖδα	n-s---fa-	σφραγίς	_4^8	breve_ultima
'''

import re
import csv
import unicodedata

from grc_utils import Colors, DICHRONA, only_bases, all_vowels
from grc_utils import patterns
from grc_utils import ultima, properispomenon, proparoxytone
from grc_utils import paroxytone_short_ultima_with_dichronon_only_in_penultima, paroxytone_long_penultima_with_dichronon_only_in_ultima, properispomenon_with_dichronon_only_in_ultima, proparoxytone_with_dichronon_only_in_ultima

### AUXILIARY FUNCTIONS ###
#   is_diphthong
#   has_iota_adscriptum
#   word_with_real_dichrona
#   properispomenon_with_dichronon_in_ultima
#   proparoxytone_with_dichronon_in_ultima


def is_diphthong(chars):
    ''' Expects two characters '''
    for pattern in ['diphth_y', 'diphth_i']:
        if re.match(patterns[pattern], chars):
            return True
    return False


def has_iota_adscriptum(chars):
    ''' Expects two characters '''
    adscr_i_pattern = re.compile(patterns['adscr_i'])

    if adscr_i_pattern.match(chars):
        return True
    return False


def word_with_real_dichrona(s):
    """
    Determines if a given string contains at least one character from the DICHRONA set 
    that does not form a diphthong with its neighboring character and does not have an adscriptum.
    """
    for i, char in enumerate(s):
        if char in DICHRONA:

            # Form pairs to check for diphthongs and adscriptum
            prev_pair = s[i-1:i+1] if i > 0 else ''
            next_pair = s[i:i+2] if i < len(s) - 1 else ''

            # Check if the character is part of a diphthong or has adscriptum
            if (prev_pair and (is_diphthong(prev_pair) or has_iota_adscriptum(prev_pair))) or \
               (next_pair and (is_diphthong(next_pair) or has_iota_adscriptum(next_pair))):
                continue  # Skip if any of these conditions are true

            return True

    return False


def properispomenon_with_dichronon_in_ultima(word):
    """
    Determines if a given word satisfies the following criteria for "free macron":
    - The accent type is classified as properispomenon.
    - The ultima is recognized by `word_with_real_dichrona`.
    """

    if not properispomenon(word):
        return False
    
    ultima_str = ultima(word)

    if not word_with_real_dichrona(ultima_str):
        return False

    return True


def proparoxytone_with_dichronon_in_ultima(string):
    """
    Determines if a given word satisfies the following criteria for "free macron":
    - The accent type of the string is classified as proparoxytone.
    - The ultima of the string is recognized by `word_with_real_dichrona`.
    """

    if not proparoxytone(string):
        return False
    
    ultima_str = ultima(string)

    if not word_with_real_dichrona(ultima_str):
        return False

    return True


### MAIN FUNCTIONS ###


def ordinal_last_vowel(word):
    """
    Returns the ordinal index of the last vowel in the word, ignoring non-vowel characters.
    The index is based on the position in the base-only version of the word.
    >>> ordinal_last_vowel('ἄγαν')
    >>> 3
    """
    base_word = only_bases(word)
    ordinal = len(base_word)
    for char in reversed(word):  # Iterate through the word backwards
        if re.search(all_vowels, char):
            return ordinal
        ordinal -= 1
    return None  # In case there are no vowels


def breve_ultima(word):
    '''
    Returns a formatted breve entry for prosodically determined ultimae 
    >>> breve_ultima('αἷμα')
    >>> ^4
    >>> breve_ultima('λήμματα')
    >>> ^7
    >>> breve_ultima('ἄγαν')
    >>> None
    '''
    if word:
        if properispomenon_with_dichronon_in_ultima(word) or proparoxytone_with_dichronon_in_ultima(word):
            breve = f"^{ordinal_last_vowel(word)}"
            return breve
    return None


def brevize_ultimae_in_tsv(input_tsv, output_tsv):
    updated_source_count = 0
    first_line = True  # Flag to identify the header

    with open(input_tsv, mode='r', encoding='utf-8', newline='') as infile, \
         open(output_tsv, mode='w', encoding='utf-8', newline='') as outfile:
        reader = csv.reader(infile, delimiter='\t')
        writer = csv.writer(outfile, delimiter='\t')

        for row in reader:
            if first_line:
                # Write the header unchanged
                writer.writerow(row)
                first_line = False
                continue

            if row and len(row) >= 4:
                token_in, tag_in, lemma_in, macron_in = row[:4]
                source_in = row[4] if len(row) > 4 else ''

                normalized_token = unicodedata.normalize('NFC', token_in)
                new_macron = breve_ultima(normalized_token)
                
                if new_macron:
                    macron_out = collate_macrons(macron_in, new_macron)
                    # Check if the collated macron differs from the input
                    if macron_out != macron_in:
                        source_out = f"{source_in},breve_ultima" if source_in else "breve_ultima"
                        updated_source_count += 1
                    else:
                        source_out = source_in
                else:
                    macron_out = macron_in
                    source_out = source_in
                
                output_row = [token_in, tag_in, lemma_in, macron_out, source_out]
                writer.writerow(output_row)

    print(f"{Colors.GREEN}Total sources updated due to breve ultima: {updated_source_count}{Colors.ENDC}")


if __name__ == '__main__':
    input_tsv = 'macrons_wiki_hypo_ifth_lsj.tsv'
    output_tsv = 'macrons_alg1_ultima.tsv'
    brevize_ultimae_in_tsv(input_tsv, output_tsv)