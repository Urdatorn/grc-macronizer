import re
import sqlite3
import time
from tqdm import tqdm
from greek_accentuation.syllabify import add_necessary_breathing

from barytone import replace_grave_with_acute, replace_acute_with_grave
from class_text import Text
from epic_stop_words import epic_stop_words
from format_macrons import macron_integrate_markup, macron_markup_to_unicode, macron_unicode_to_markup, merge_or_overwrite_markup
from grc_utils import count_ambiguous_dichrona_in_open_syllables, count_dichrona_in_open_syllables, DICHRONA, long_acute, no_macrons, normalize_word, paroxytone, proparoxytone, properispomenon, short_vowel, syllabifier, vowel
from greek_proper_names_cltk.proper_names import proper_names
from morph_disambiguator import morph_disambiguator
from verbal_forms import macronize_verbal_forms
from db.wiktionary_ambiguous import wiktionary_ambiguous_map
from db.wiktionary_singletons import wiktionary_singletons_map

class Macronizer:
    def __init__(self, 
                 macronize_everything=True,
                 unicode=False,
                 hypotactic_db_file='db/hypotactic.db', 
                 aristophanes_db_file=None, 
                 custom_db_file='db/custom.py',
                 debug=False):

        self.macronize_everything = macronize_everything
        self.unicode = unicode
        self.hypotactic_db_file = hypotactic_db_file
        self.aristophanes_db_file = aristophanes_db_file
        self.custom_db_file = custom_db_file
        self.debug = debug

        

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
            
    def wiktionary(self, word, lemma, pos, morph):
        """
        Should return with macron_unicode_to_markup
        """
        word = normalize_word(no_macrons(word.replace('^', '').replace('_', '')))
        
        if word in wiktionary_singletons_map:
            disambiguated = wiktionary_singletons_map[word][0][0] # get the db_word singleton content
            return macron_unicode_to_markup(disambiguated)
        elif word in wiktionary_ambiguous_map: # format: [[unnormalized tokens with macrons], [table names], [row headers 1], row headers 2], [column header 1], [column header 2]]
            match = wiktionary_ambiguous_map[word]
            disambiguated = morph_disambiguator(word, lemma, pos, morph, token=match[0], tense=match[1], case_voice=match[2], mode=match[3], person=match[4], number=match[5])
            return macron_unicode_to_markup(disambiguated)
        else:
            return word
    
    def hypotactic(self, word):
        '''
        >>> hypotactic('ἀγαθῆς')
        >>> ἀ^γα^θῆς
        '''
        macrons = self.hypotactic_map.get(word)
        if macrons:
            return macron_integrate_markup(word, macrons)
        return word

    def macronize(self, text, genre='prose', stats=True):
        """
        Macronization is a modular and recursive process comprised of the following operations, 
        where later entries are considered more reliable and thus overwrite earlier ones in case of disagreement:
            [wiktionary]
            [hypotactic]
            [nominal forms] # needs to be moved here from Text
            [verbal forms]
            [accent rules]
            [lemma-based generalization]
        Accent rules and (naturally) lemma-based generalization are the only modules that rely on the output of the other modules for optimal performance.
        My design goal is that it should be easy for the "power user" to change the order of the other modules, and to graft in new ones.
        """

        text_object = Text(text, genre, doc_from_file=True, debug=self.debug)
        token_lemma_pos_morph = text_object.token_lemma_pos_morph # format: [[orth, token.lemma_, token.pos_, token.morph], ...]
            
        def macronization_modules(token, lemma, pos, morph, second_pass=False, is_lemma=False):
            wiktionary_token = self.wiktionary(token, lemma, pos, morph)

            if count_dichrona_in_open_syllables(wiktionary_token) == 0:
                return wiktionary_token

            hypotactic_token = self.hypotactic(token)
            macronized_token = merge_or_overwrite_markup(hypotactic_token, wiktionary_token)

            if count_dichrona_in_open_syllables(macronized_token) == 0:
                return macronized_token

            nominal_forms_token = macronize_verbal_forms(token, lemma, pos, morph, debug=self.debug)
            macronized_token = merge_or_overwrite_markup(nominal_forms_token, macronized_token)

            if count_dichrona_in_open_syllables(macronized_token) == 0:
                return macronized_token

            accent_rules_token = self.apply_accentuation_rules(macronized_token) # accent rules benefit from earlier macronization
            macronized_token = merge_or_overwrite_markup(accent_rules_token, macronized_token)

            # ἴθε δή, let's recursively macronize remaining dichrona
            dichrona_remaining = 0
            if count_dichrona_in_open_syllables(macronized_token) > 0:
                if not second_pass and replace_acute_with_grave(macronized_token) != macronized_token: # only bother with actual barytones, obviously
                    oxytonized_token = replace_grave_with_acute(macronized_token)
                    rebarytonized_token = replace_acute_with_grave(macronization_modules(oxytonized_token, lemma, pos, morph, second_pass=True))
                    macronized_token = merge_or_overwrite_markup(rebarytonized_token, macronized_token)
                    
            if not is_lemma and count_dichrona_in_open_syllables(macronized_token) > 0:
                lemma_token = macronization_modules(macronized_token, lemma, pos, morph, is_lemma=True)
                macronized_token = self.lemma_generalization(macronized_token, lemma_token)

            return macronized_token

        macronized_tokens = []
        for token, lemma, pos, morph in token_lemma_pos_morph:
            macronized_tokens.append(macronization_modules(token, lemma, pos, morph))

        text_object.macronized_words = macronized_tokens
        text_object.integrate() # creates the final .macronized_text

        if stats:
            self.macronization_ratio(text, text_object.macronized_text, count_all_dichrona=True, count_proper_names=True)
        return text_object.macronized_text
    
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