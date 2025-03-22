import re
import sqlite3
import time
from tqdm import tqdm

from barytone import grave_to_acute, replace_grave_with_acute, replace_acute_with_grave
from class_text import Text
from epic_stop_words import epic_stop_words
from format_macrons import macron_integrate_markup, macron_markup_to_unicode, macron_unicode_to_markup, merge_or_overwrite_markup
from grc_utils import count_ambiguous_dichrona_in_open_syllables, count_dichrona_in_open_syllables, DICHRONA, has_ambiguous_dichrona_in_open_syllables, long_acute, no_macrons, normalize_word, paroxytone, proparoxytone, properispomenon, short_vowel, syllabifier, vowel
from greek_proper_names_cltk.proper_names import proper_names
from nominal_forms import macronize_nominal_forms
from db.wiktionary import wiktionary_map

def check_word(word):
    return not has_ambiguous_dichrona_in_open_syllables(word)

def get_words(text):
            text = normalize_word(text) # combining diacritics will cause splits without this
            words = re.findall(r'[\w^_]+', text) # remember that we are now acting on integrated markup with carets and underscores
            return [word for word in words if any(vowel(char) for char in word)] # extra precaution: all grc words have vowels

class Macronizer:
    def __init__(self, 
                 macronize_everything=True,
                 unicode=False,
                 ifeellucky=True,
                 hypotactic_db_file='db/hypotactic.db', 
                 aristophanes_db_file=None, 
                 custom_db_file=None,
                 debug=False):

        self.macronize_everything = macronize_everything
        self.unicode = unicode
        self.ifeellucky = ifeellucky
        self.hypotactic_db_file = hypotactic_db_file
        self.aristophanes_db_file = aristophanes_db_file
        self.custom_db_file = custom_db_file
        self.debug = debug

        self.wiktionary_map = wiktionary_map

        self.hypotactic_map = {}
        try:
            conn = sqlite3.connect(self.hypotactic_db_file)
            cursor = conn.cursor()
            cursor.execute("SELECT token, macrons FROM annotated_tokens")
            rows = cursor.fetchall()
            conn.close()
            
            for token, macrons in rows:
                self.hypotactic_map[token] = macrons
        except sqlite3.Error as e:
            print(f"Warning: Could not load hypotactic database: {e}")
            
    def wiktionary(self, word):
        """
        Should return with macron_unicode_to_markup
        """
        word = normalize_word(no_macrons(word.replace('^', '').replace('_', '')))
        
        matches = self.wiktionary_map.get(word, [])
        if len(matches) == 1:
            return matches[0]
        elif len(matches) > 1:
            if self.ifeellucky:
                return matches[0]
            else:
                return matches # work in progress; this should pipe to a POS disambiguator
        return None
    
    def hypotactic(self, word):
        '''
        >>> hypotactic('ἀγαθῆς')
        >>> ἀ^γα^θῆς
        '''
        macrons = self.hypotactic_map.get(word)
        if macrons:
            return macron_integrate_markup(word, macrons)
        return word

    def macronize(self, text, genre='prose'):
        """
        Macronization is a modular and recursive process comprised of the following operations: 
            [wiktionary]
            [hypotactic]
            [nominal forms]
            [accent rules]
            [lemma-based generalization]
        Accent rules and (naturally) lemma-based generalization are the only modules that rely on the output of the other modules for optimal performance.
        My design goal is that it should be easy for the "power user" to change the order of the other modules, and to graft in new ones.
        """

        text = Text(text, genre, doc_from_file=True, debug=self.debug)
        token_lemma_pos_morph = text.token_lemma_pos_morph # format: [[orth, token.lemma_, token.pos_, token.morph], ...]
            
        def macronization_modules(token, lemma, pos, morph, is_lemma=False):
            second_pass = False

            wiktionary_token = self.wiktionary(token, lemma, pos, morph)
            hypotactic_token = self.hypotactic(token)

            macronized_token = merge_or_overwrite_markup(hypotactic_token, wiktionary_token)
            accent_rules_token = self.apply_accentuation_rules(macronized_token)
            
            macronized_token = merge_or_overwrite_markup(accent_rules_token, macronized_token)

            # ἴθε δή, let's recursively macronize remaining dichrona
            dichrona_remaining = 0
            if count_dichrona_in_open_syllables(macronized_token) > 0:
                if not second_pass:
                    second_pass = True
                    oxytonized_token = replace_grave_with_acute(macronized_token)
                    oxytonized_token = macronization_modules(oxytonized_token, lemma, pos, morph)
                    macronized_token = merge_or_overwrite_markup(oxytonized_token, macronized_token)
                    
                if not is_lemma:
                    lemma_token = macronization_modules(macronized_token, lemma, pos, morph, is_lemma=True)
                    macronized_token = self.lemma_generalization(macronized_token, lemma_token)

            return macronized_token

        macronized_tokens = []
        for token, lemma, pos, morph in token_lemma_pos_morph:
            macronized_tokens.append(macronization_modules(token, lemma, pos, morph))

        text.macronized_words = macronized_tokens
        text.integrate()

        return text.macronized_text
    
    def macronization_ratio(self, text, macronized_text, count_all_dichrona=True, count_proper_names=True):
        def remove_proper_names(text):
            # Build a regex pattern that matches whole words from the set
            pattern = r'\b(?:' + '|'.join(re.escape(name) for name in tqdm(proper_names, desc="Building proper names pattern")) + r')\b'

            # Remove names, handling extra spaces that might appear
            cleaned_text = re.sub(pattern, '', text).strip()
            cleaned_text = re.sub(r'\s+', ' ', cleaned_text)

            return cleaned_text
        start_time = time.perf_counter()

        text = normalize_word(text)
        if not count_proper_names:
            print("\nRemoving proper names...")
            text = remove_proper_names(text)

        count_before = 0
        count_after = 0

        if not count_all_dichrona:
            print("\nCounting ambiguous dichrona...")
            count_before = count_ambiguous_dichrona_in_open_syllables(text)
            count_after = count_ambiguous_dichrona_in_open_syllables(macronized_text)
            print(f"Dichrona in open syllables not covered by accent rules before: {count_before}")
            print(f"Dichrona in open syllables not covered by accent rules after: {count_after}")
        else:
            print("\nCounting all dichrona...")
            count_before = count_dichrona_in_open_syllables(text)
            count_after = count_dichrona_in_open_syllables(macronized_text)
            print(f"Dichrona in open syllables before: {count_before}")
            print(f"Unmacronized dichrona in open syllables left: {count_after}")
            
        difference = count_before - count_after

        end_time = time.perf_counter()
        print(f"\nEvaluation took {end_time - start_time:.2f} seconds")

        print(f"Difference: {difference}")

        ratio = difference / count_before if count_before > 0 else 0
        return ratio
    
    def apply_accentuation_rules(self, old_version):
        if not old_version:
            return old_version
        old_version = normalize_word(old_version)
        old_version = macron_unicode_to_markup(old_version)
        new_version = old_version.replace('_', '').replace('^', '') # this will be updated later

        list_of_syllables = syllabifier(old_version) # important: needs to use old_version, for markup to potentially decide short_vowel and long_acute
        total_syllables = len(list_of_syllables)

        syllable_positions = [ # can't filter out sylls here because I want to join them later
            (-(total_syllables - i), syllable)  # Position from the end
            for i, syllable in enumerate(list_of_syllables)
        ]

        if not syllable_positions:
            return old_version
        
        ultima = list_of_syllables[-1]
        penultima = list_of_syllables[-2] if len(list_of_syllables) > 1 else None

        modified_syllable_positions = []
        for position, syllable in syllable_positions:
            modified_syllable = syllable.replace('_', '').replace('^', '')  # Create a new variable to store modifications
            if position == -2 and paroxytone(new_version) and short_vowel(ultima):
                # Find the last vowel in syllable and append '^' after it
                for i in range(len(syllable)-1, -1, -1): # NB: len(syllable)-1 is the index of the last character (0-indexed); -1 is to go backwards
                    if vowel(syllable[i]) and i in DICHRONA:
                        modified_syllable = syllable[:i+1] + '^' + syllable[i+1:]
                        break
            elif position == -1 and paroxytone(new_version) and long_acute(penultima):
                # Find the last vowel in syllable and append '_' after it
                for i in range(len(syllable)-1, -1, -1):
                    if vowel(syllable[i]) and i in DICHRONA:
                        modified_syllable = syllable[:i+1] + '_' + syllable[i+1:]
                        break
            elif position == -1 and (properispomenon(new_version) or proparoxytone(new_version)):
                # Find the last vowel in syllable and append '^' after it
                for i in range(len(syllable)-1, -1, -1):
                    if vowel(syllable[i]) and i in DICHRONA:
                        modified_syllable = syllable[:i+1] + '^' + syllable[i+1:]
                        break
            modified_syllable_positions.append((position, modified_syllable))
            
        #print("Modified syllable positions:", modified_syllable_positions) # new debug print
        new_version = ''.join(syllable for _, syllable in modified_syllable_positions)
        #print("New version:", new_version) # debugging

        merged = merge_or_overwrite_markup(new_version, old_version)
        return merged
    

    def lemma_generalization(macronized_token, lemma_token):
        """
        Take a deep breath and focus. 
        This is probably the one module with the greatest potential for optimization, given enough ingenuity.
        """
        pass