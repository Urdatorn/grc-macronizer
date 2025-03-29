import logging
import os
import re
import sqlite3

from tqdm import tqdm as original_tqdm

from ascii import ascii_macronizer
from barytone import replace_grave_with_acute, replace_acute_with_grave
from class_text import Text
from db.custom import custom_macronizer
from db.wiktionary_ambiguous import wiktionary_ambiguous_map
from db.wiktionary_singletons import wiktionary_singletons_map
from format_macrons import macron_integrate_markup, macron_markup_to_unicode, macron_unicode_to_markup, merge_or_overwrite_markup
from grc_utils import GRAVES, count_ambiguous_dichrona_in_open_syllables, count_dichrona_in_open_syllables, DICHRONA, long_acute, lower_grc, upper_grc, no_macrons, normalize_word, paroxytone, proparoxytone, properispomenon, short_vowel, syllabifier, vowel, word_with_real_dichrona
from greek_proper_names_cltk.proper_names import proper_names
from morph_disambiguator import morph_disambiguator
from verbal_forms import macronize_verbal_forms

class tqdm(original_tqdm):
    def __init__(self, *args, **kwargs):
        if 'position' not in kwargs:
            kwargs['position'] = 1  # Default to line 1 (0-based index)
        super().__init__(*args, **kwargs)

logging.basicConfig(
    level=logging.DEBUG, # INFO or DEBUG
    filename="diagnostics/macronizer.log",
    format="%(asctime)s - %(message)s"
)

logging.info("Starting new log...")
for line in ascii_macronizer:
    logging.info(line)

diphth_y = r'[αεηο][ὐὔυὑύὖῦὕὗὺὒὓ]'
diphth_i = r'[αεου][ἰίιῖἴἶἵἱἷὶἲἳ]'
adscr_i = r'[αηωἀἠὠἁἡὡάήώὰὴὼᾶῆῶὤὥὢὣἄἅἂἃἤἥἣἢἦἧἆἇὧὦ]ι'

combined_pattern = re.compile(f'(?:{diphth_y}|{diphth_i}|{adscr_i})[_^]')

def macronized_diphthong(word):
    '''
    Part of the sanity check. 
    >>> macronized_diphthong("χίλι^οι)
    False
    >>> macronized_diphthong("χίλιοι^")
    True
    '''
    return bool(re.search(combined_pattern, word))

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
            logging.info(f"Warning: Could not load hypotactic database: {e}")
            
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
            [custom] # finally, hardcode whatever macronizations you want to overwrite every other module
        Accent rules and (naturally) lemma-based generalization are the only modules that rely on the output of the other modules for optimal performance.
        My design goal is that it should be easy for the "power user" to change the order of the other modules, and to graft in new ones.
        """

        text_object = Text(text, genre, doc_from_file=True, debug=self.debug)
        token_lemma_pos_morph = text_object.token_lemma_pos_morph # format: [[orth, token.lemma_, token.pos_, token.morph], ...]
            
        def macronization_modules(token, lemma, pos, morph, recursion_depth=0, oxytonized_pass=False, capitalized_pass=False, decapitalized_pass=False, is_lemma=False):
            
            recursion_depth += 1
            if recursion_depth > 10:
                raise RecursionError("Maximum recursion depth exceeded in macronization_modules")
            
            if oxytonized_pass:
                logging.debug(f'🔄 Macronizing (oxytonized): {token} ({lemma}, {pos}, {morph})')
            elif capitalized_pass:
                logging.debug(f'🔄 Macronizing (capitalized): {token} ({lemma}, {pos}, {morph})')
            elif decapitalized_pass:
                logging.debug(f'🔄 Macronizing (decapitalized): {token} ({lemma}, {pos}, {morph})')
            elif is_lemma:
                logging.debug(f'🔄 Macronizing (lemma): {token} ({lemma}, {pos}, {morph})')
            else:
                logging.debug(f'🔄 Macronizing: {token} ({lemma}, {pos}, {morph})')

            wiktionary_token = self.wiktionary(token, lemma, pos, morph)
            if self.debug:
                logging.debug(f'\t✅ Wiktionary: {token} => {wiktionary_token}, with {count_dichrona_in_open_syllables(wiktionary_token)} left')

            if count_dichrona_in_open_syllables(wiktionary_token) == 0:
                return wiktionary_token

            hypotactic_token = self.hypotactic(token)
            if self.debug:
                logging.debug(f'\t✅ Hypotactic: {wiktionary_token} => {merge_or_overwrite_markup(hypotactic_token, wiktionary_token)}, with {count_dichrona_in_open_syllables(merge_or_overwrite_markup(hypotactic_token, wiktionary_token))} left')
            macronized_token = merge_or_overwrite_markup(hypotactic_token, wiktionary_token)

            if count_dichrona_in_open_syllables(macronized_token) == 0:
                return macronized_token

            nominal_forms_token = macronize_verbal_forms(token, lemma, pos, morph, debug=self.debug)
            if self.debug:
                logging.debug(f'\t✅ Nominal forms: {macronized_token} => {merge_or_overwrite_markup(nominal_forms_token, macronized_token)}, with {count_dichrona_in_open_syllables(merge_or_overwrite_markup(nominal_forms_token, macronized_token))} left')
            macronized_token = merge_or_overwrite_markup(nominal_forms_token, macronized_token)

            if count_dichrona_in_open_syllables(macronized_token) == 0:
                return macronized_token

            accent_rules_token = self.apply_accentuation_rules(macronized_token) # accent rules benefit from earlier macronization
            if self.debug:
                logging.debug(f'\t✅ Accent rules: {macronized_token} => {merge_or_overwrite_markup(accent_rules_token, macronized_token)}, with {count_dichrona_in_open_syllables(merge_or_overwrite_markup(accent_rules_token, macronized_token))} left')
            macronized_token = merge_or_overwrite_markup(accent_rules_token, macronized_token)

            custom_token = custom_macronizer(macronized_token)
            if self.debug and custom_token != macronized_token:
                logging.debug(f'\t✅ Custom: {macronized_token} => {merge_or_overwrite_markup(custom_token, macronized_token)}, with {count_dichrona_in_open_syllables(merge_or_overwrite_markup(custom_token, macronized_token))} left')
            elif self.debug:
                logging.debug(f'\t❌ Custom did not help')
            macronized_token = merge_or_overwrite_markup(custom_token, macronized_token)

            # ἴθε δή, let's recursively macronize remaining dichrona

            # TODO We should also try removing prefixes, e.g. ἀπο-κτενῶν => macronize κτενῶν, and then reattach the prefix
            
            # OXYTONIZING RECURSION
            if count_dichrona_in_open_syllables(macronized_token) > 0 and macronized_token[-1] in GRAVES:
                oxytonized_token = macronized_token[:-1] + replace_grave_with_acute(macronized_token[-1])
                if not oxytonized_pass and replace_acute_with_grave(macronized_token) != macronized_token: # only bother with actual barytones, obviously
                    rebarytonized_token = replace_acute_with_grave(macronization_modules(oxytonized_token, lemma, pos, morph, recursion_depth, oxytonized_pass=True, capitalized_pass=capitalized_pass, decapitalized_pass=decapitalized_pass, is_lemma=is_lemma))
                    macronized_token = merge_or_overwrite_markup(rebarytonized_token, macronized_token)
                    if self.debug and rebarytonized_token != macronized_token:
                        logging.debug(f'\t✅ Oxytonizing helped: : {count_dichrona_in_open_syllables(macronized_token)} left')
                    else:
                        logging.debug(f'\t❌ Oxytonizing did not help')

            # CAPITALIZING RECURSION
            if count_dichrona_in_open_syllables(macronized_token) > 0:
                capitalized_token = upper_grc(macronized_token[0]) + macronized_token[1:]
                if not capitalized_pass and not decapitalized_pass and pos == "PROPN" and macronized_token != capitalized_token: # if the token is an all lowercase proper noun, try capitalizing it
                    if self.debug:
                        logging.debug(f'\t Capitalizing {macronized_token} as {capitalized_token}')
                    old_macronized_token = macronized_token
                    capitalized_token = macronization_modules(capitalized_token, lemma, pos, morph, recursion_depth, oxytonized_pass=oxytonized_pass, capitalized_pass=True, decapitalized_pass=decapitalized_pass, is_lemma=is_lemma)
                    restored_token = old_macronized_token[0] + capitalized_token[1:] # restore the original first character
                    logging.debug(f'\t Restoring capitalized token: {capitalized_token} => {restored_token}')

                    macronized_token = merge_or_overwrite_markup(restored_token, macronized_token)
                    if self.debug and macronized_token != old_macronized_token:
                        logging.debug(f'\t✅ Capitalization helped: {count_dichrona_in_open_syllables(macronized_token)} left')
                    else:
                        logging.debug(f'\t❌ Capitalization did not help')

            # DECAPITALIZING RECURSION
            # if count_dichrona_in_open_syllables(macronized_token) > 0:
            #     decapitalized_token = lower_grc(macronized_token[0]) + macronized_token[1:]
            #     if not capitalized_pass and not decapitalized_pass and macronized_token != decapitalized_token: # without the capitalized_pass check, we get infinite recursion for capitalized tokens
            #         if self.debug:
            #             logging.debug(f'\t Decapitalizing {macronized_token} as {decapitalized_token}')
            #         old_macronized_token = macronized_token
            #         decapitalized_token = merge_or_overwrite_markup(macronization_modules(decapitalized_token, lemma, pos, morph, recursion_depth, oxytonized_pass=oxytonized_pass, capitalized_pass=capitalized_pass,  decapitalized_pass=True, is_lemma=is_lemma), macronized_token)
            #         if count_dichrona_in_open_syllables(decapitalized_token) < count_dichrona_in_open_syllables(old_macronized_token):
            #             macronized_token = decapitalized_token
            #             if self.debug:
            #                 logging.debug(f'\t✅ Decapitalization helped: {count_dichrona_in_open_syllables(macronized_token)} left')
            #         elif self.debug:
            #             logging.debug(f'\t❌ Decapitalization did not help')

            # LEMMA-BASED GENERALIZATION RECURSION
            if count_dichrona_in_open_syllables(macronized_token) > 0:
                decapitalized_token = lower_grc(token.replace('^', ''))
                if not is_lemma and not decapitalized_token == lemma: # if the token is capitalized and is the lemma itself, we get infinite recursion
                    lemma_token = macronization_modules(macronized_token, lemma, pos, morph, recursion_depth, oxytonized_pass=oxytonized_pass, capitalized_pass=capitalized_pass, decapitalized_pass=decapitalized_pass, is_lemma=True)
                    macronized_token = self.lemma_generalization(macronized_token, lemma_token)
                    if self.debug:
                        logging.debug(f'\t✅ Lemma generalization (placeholder): {count_dichrona_in_open_syllables(macronized_token)} left')

            assert not macronized_diphthong(macronized_token), f"Watch out! We just macronized a diphthong: {macronized_token}"

            return macronized_token

        macronized_tokens = []
        still_ambiguous = []
        for token, lemma, pos, morph in tqdm(token_lemma_pos_morph, desc="Macronizing tokens"):
            result = macronization_modules(token, lemma, pos, morph)
            if count_dichrona_in_open_syllables(result) > 0:
                still_ambiguous.append(result)
            macronized_tokens.append(result)

        text_object.macronized_words = macronized_tokens
        text_object.integrate() # creates the final .macronized_text

        if stats:
            self.macronization_ratio(text, text_object.macronized_text, count_all_dichrona=True, count_proper_names=True)
        
        file_version = 1
        file_stub = ''
        file_name = ''

        if len(macronized_tokens) > 0:
            if macronized_tokens[0]:
                file_stub = f'diagnostics/still_ambiguous_{macronized_tokens[0].replace("^", "").replace("_", "")}'
            else:
                file_stub = f'diagnostics/still_ambiguous'

            while True:
                file_version = str(file_version)
                file_name = file_stub + f'_{file_version}.py'
                if not os.path.exists(file_name):
                    break
                file_version = int(file_version)
                file_version += 1
        
            with open(file_name, 'w', encoding='utf-8') as f:
                f.write('still_ambiguous = [\n')
                for item in still_ambiguous:
                    f.write(f'    {repr(item)},\n')
                f.write(']\n')

        return text_object.macronized_text
    
    def macronization_ratio(self, text, macronized_text, count_all_dichrona=True, count_proper_names=True):
        def remove_proper_names(text):
            # Build a regex pattern that matches whole words from the set
            pattern = r'\b(?:' + '|'.join(re.escape(name) for name in tqdm(proper_names, desc="Building proper names pattern")) + r')\b'

            # Remove names, handling extra spaces that might appear
            cleaned_text = re.sub(pattern, '', text).strip()
            cleaned_text = re.sub(r'\s+', ' ', cleaned_text)

            return cleaned_text

        text = normalize_word(text)
        if not count_proper_names:
            logging.debug("\nRemoving proper names...")
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
            count_before = count_dichrona_in_open_syllables(text)
            count_after = count_dichrona_in_open_syllables(macronized_text)
            print(f"Dichrona in open syllables before: {count_before}")
            print(f"Unmacronized dichrona in open syllables left: {count_after}")
            
        difference = count_before - count_after

        print(f"{difference} dichrona macronized.")

        ratio = difference / count_before if count_before > 0 else 0

        print(f"Macronization ratio: {ratio:.2%}")

        return ratio
    
    def apply_accentuation_rules(self, old_version):
        if not old_version:
            return old_version
        old_version = normalize_word(old_version)

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
                    if vowel(syllable[i]) and word_with_real_dichrona(syllable):
                        modified_syllable = syllable[:i+1] + '^' + syllable[i+1:]
                        break
            elif position == -1 and paroxytone(new_version) and long_acute(penultima):
                # Find the last vowel in syllable and append '_' after it
                for i in range(len(syllable)-1, -1, -1):
                    if vowel(syllable[i]) and word_with_real_dichrona(syllable):
                        modified_syllable = syllable[:i+1] + '_' + syllable[i+1:]
                        break
            elif position == -1 and (properispomenon(new_version) or proparoxytone(new_version)):
                # Find the last vowel in syllable and append '^' after it
                for i in range(len(syllable)-1, -1, -1):
                    if vowel(syllable[i]) and word_with_real_dichrona(syllable):
                        modified_syllable = syllable[:i+1] + '^' + syllable[i+1:]
                        break
            modified_syllable_positions.append((position, modified_syllable))
            
        #print("Modified syllable positions:", modified_syllable_positions) # new debug print
        new_version = ''.join(syllable for _, syllable in modified_syllable_positions)
        #print("New version:", new_version) # debugging

        merged = merge_or_overwrite_markup(new_version, old_version)

        assert not macronized_diphthong(merged), f"Watch out! We just macronized a diphthong: {merged}"
        return merged
    
    def lemma_generalization(self, macronized_token, lemma_token):
        """
        Take a deep breath and focus. 
        This is probably the one module with the greatest potential for optimization, given enough ingenuity.
        """
        return macronized_token