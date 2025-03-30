from datetime import datetime
import logging
import os
import re
import sqlite3

from tqdm import tqdm as tqdm

from ascii import ascii_macronizer
from barytone import replace_grave_with_acute, replace_acute_with_grave
from class_text import Text
from db.custom import custom_macronizer
from db.wiktionary_ambiguous import wiktionary_ambiguous_map
from db.wiktionary_singletons import wiktionary_singletons_map
from format_macrons import macron_integrate_markup, macron_markup_to_unicode, macron_unicode_to_markup, merge_or_overwrite_markup
from grc_utils import only_bases, count_ambiguous_dichrona_in_open_syllables, count_dichrona_in_open_syllables, DICHRONA, GRAVES, long_acute, lower_grc, no_macrons, normalize_word, paroxytone, proparoxytone, properispomenon, short_vowel, syllabifier, upper_grc, vowel, VOWELS_LOWER_TO_UPPER, word_with_real_dichrona
from greek_proper_names_cltk.proper_names import proper_names
from morph_disambiguator import morph_disambiguator
from verbal_forms import macronize_verbal_forms

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")  # e.g., 20250329_120059
log_filename = f"diagnostics/macronizer_{timestamp}.log"

logging.basicConfig(
    level=logging.DEBUG,
    filename=log_filename,
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
                 debug=False):

        self.macronize_everything = macronize_everything
        self.unicode = unicode
        self.hypotactic_db_file = 'db/hypotactic.db'
        self.aristophanes_db_file = None
        self.custom_db_file = 'db/custom.py'
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
        word = word.replace('^', '').replace('_', '')

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

        # lists to keep track of module efficacy
        case_ending_recursion_results = []
            
        def macronization_modules(token, lemma, pos, morph, recursion_depth=0, oxytonized_pass=False, capitalized_pass=False, decapitalized_pass=False, different_ending_pass=False, is_lemma=False):
            '''
            I aim to have quite a lot of symmetry here, so it should be possible to change the order of modules without having to rewrite too many lines. 
            '''
            
            recursion_depth += 1
            if recursion_depth > 10:
                raise RecursionError("Maximum recursion depth exceeded in macronization_modules")
            
            if oxytonized_pass:
                logging.debug(f'🔄 Macronizing (oxytonized): {token} ({lemma}, {pos}, {morph})')
            elif capitalized_pass:
                logging.debug(f'🔄 Macronizing (capitalized): {token} ({lemma}, {pos}, {morph})')
            elif decapitalized_pass:
                logging.debug(f'🔄 Macronizing (decapitalized): {token} ({lemma}, {pos}, {morph})')
            elif different_ending_pass:
                logging.debug(f'🔄 Macronizing (different-ending): {token} ({lemma}, {pos}, {morph})')
            elif is_lemma:
                logging.debug(f'🔄 Macronizing (lemma): {token} ({lemma}, {pos}, {morph})')
            else:
                logging.debug(f'🔄 Macronizing: {token} ({lemma}, {pos}, {morph})')

            macronized_token = token

            custom_token = custom_macronizer(macronized_token)
            if self.debug and custom_token != macronized_token:
                logging.debug(f'\t✅ Custom: {macronized_token} => {merge_or_overwrite_markup(custom_token, macronized_token)}, with {count_dichrona_in_open_syllables(merge_or_overwrite_markup(custom_token, macronized_token))} left')
            elif self.debug:
                logging.debug(f'\t❌ Custom did not help')
            macronized_token = merge_or_overwrite_markup(custom_token, macronized_token)

            if count_dichrona_in_open_syllables(macronized_token) == 0:
                return macronized_token

            wiktionary_token = self.wiktionary(macronized_token, lemma, pos, morph)
            if self.debug:
                logging.debug(f'\t✅ Wiktionary: {token} => {wiktionary_token}, with {count_dichrona_in_open_syllables(wiktionary_token)} left')
            macronized_token = merge_or_overwrite_markup(wiktionary_token, macronized_token)

            if count_dichrona_in_open_syllables(macronized_token) == 0:
                return macronized_token

            hypotactic_token = self.hypotactic(macronized_token)
            if self.debug:
                logging.debug(f'\t✅ Hypotactic: {wiktionary_token} => {merge_or_overwrite_markup(hypotactic_token, wiktionary_token)}, with {count_dichrona_in_open_syllables(merge_or_overwrite_markup(hypotactic_token, wiktionary_token))} left')
            macronized_token = merge_or_overwrite_markup(hypotactic_token, macronized_token)

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

            if count_dichrona_in_open_syllables(macronized_token) == 0:
                return macronized_token
            
            # TODO PREFIXES
            # We should also try macronizing prefixes by checking if what's left of them is still a word, e.g. ἀπο-κτενῶν => κτενῶν

            # ἴθι δή, now let's *recursively* try to macronize the remaining dichrona!

            # Example of working two-level recursion:
                # 2025-03-30 11:39:44,565 - 🔄 Macronizing: Διὰ (διά, ADP, )
                # 2025-03-30 11:39:44,565 - 	❌ Custom did not help
                # 2025-03-30 11:39:44,565 - 	✅ Wiktionary: Διὰ => Διὰ, with 2 left
                # 2025-03-30 11:39:44,565 - 	✅ Hypotactic: Διὰ => Διὰ, with 2 left
                # 2025-03-30 11:39:44,565 - 	✅ Nominal forms: Διὰ => Διὰ, with 2 left
                # 2025-03-30 11:39:44,565 - 	✅ Accent rules: Διὰ => Διὰ, with 2 left
                # 2025-03-30 11:39:44,565 - 🔄 Macronizing (oxytonized): Διά (διά, ADP, )
                # 2025-03-30 11:39:44,565 - 	❌ Custom did not help
                # 2025-03-30 11:39:44,566 - 	✅ Wiktionary: Διά => Διά, with 2 left
                # 2025-03-30 11:39:44,566 - 	✅ Hypotactic: Διά => Διά, with 2 left
                # 2025-03-30 11:39:44,566 - 	✅ Nominal forms: Διά => Διά, with 2 left
                # 2025-03-30 11:39:44,566 - 	✅ Accent rules: Διά => Διά, with 2 left
                # 2025-03-30 11:39:44,566 - 	 Decapitalizing Διά as διά
                # 2025-03-30 11:39:44,566 - 🔄 Macronizing (oxytonized): διά (διά, ADP, )
                # 2025-03-30 11:39:44,566 - 	✅ Custom: διά => δι^ά^, with 0 left
                # 2025-03-30 11:39:44,566 - 	✅ Decapitalization helped: 0 left
                # 2025-03-30 11:39:44,567 - 	✅ Oxytonizing helped: : 0 left

            ### WRONG-CASE-ENDING RECURSION ### e.g. πόλιν should go through πόλις

            # 2nd declension
            ''' 
            Confirmed to yield στρα^τηγόν when having only "στρα^τηγός" in the db
            '''
            if not different_ending_pass and len(token) > 2 and only_bases(lemma[-2:]) == 'ος': # we enforce length for the last two chars to really be an ending (and for there to be dichrona)
                logging.debug(f'\t Testing for 2D wrong-case-ending recursion: {macronized_token} ({lemma})')
                old_macronized_token = macronized_token
                restored_token = ''

                # cases only differing wrt the last char: gen and acc sing, and nom plur
                if (only_bases(macronized_token[-2:]) == 'ου' and 'Gen' in morph.get("Case")) or (only_bases(macronized_token[-2:]) == 'ον' and 'Acc' in morph.get("Case")) or (only_bases(macronized_token[-2:]) == 'οι' and 'Nom' in morph.get("Case")):
                    nominative_token = token[:-1] + 'ς'
                    nominative_token = macronization_modules(nominative_token, lemma, pos, morph, recursion_depth, oxytonized_pass=oxytonized_pass, capitalized_pass=capitalized_pass, decapitalized_pass=decapitalized_pass, different_ending_pass=True, is_lemma=is_lemma)
                    restored_token = nominative_token[:-1] + token[-1]

                # non-oxytone dative
                elif token[-1] == 'ῳ' and 'Dat' in morph.get("Case"):
                    nominative_token = token[:-1] + 'ος'
                    nominative_token = macronization_modules(nominative_token, lemma, pos, morph, recursion_depth, oxytonized_pass=oxytonized_pass, capitalized_pass=capitalized_pass, decapitalized_pass=decapitalized_pass, different_ending_pass=True, is_lemma=is_lemma)
                    restored_token = nominative_token[:-2] + token[-1]

                # oxytone dative
                elif token[-1] == 'ῷ' and 'Dat' in morph.get("Case"):
                    nominative_token = token[:-1] + 'ός'
                    nominative_token = macronization_modules(nominative_token, lemma, pos, morph, recursion_depth, oxytonized_pass=oxytonized_pass, capitalized_pass=capitalized_pass, decapitalized_pass=decapitalized_pass, different_ending_pass=True, is_lemma=is_lemma)
                    restored_token = nominative_token[:-2] + token[-1]

                # non-oxytone gen plur
                elif token[-2:] == 'ων' and 'Gen' in morph.get("Case"):
                    nominative_token = token[:-2] + 'ος'
                    nominative_token = macronization_modules(nominative_token, lemma, pos, morph, recursion_depth, oxytonized_pass=oxytonized_pass, capitalized_pass=capitalized_pass, decapitalized_pass=decapitalized_pass, different_ending_pass=True, is_lemma=is_lemma)
                    restored_token = nominative_token[:-2] + token[-2:]
                
                # oxytone gen plur
                elif token[-2:] == 'ῶν' and 'Gen' in morph.get("Case"):
                    nominative_token = token[:-2] + 'ός'
                    nominative_token = macronization_modules(nominative_token, lemma, pos, morph, recursion_depth, oxytonized_pass=oxytonized_pass, capitalized_pass=capitalized_pass, decapitalized_pass=decapitalized_pass, different_ending_pass=True, is_lemma=is_lemma)
                    restored_token = nominative_token[:-2] + token[-2:]

                # non-oxytone dat plur
                elif token[-3:] == 'οις' and 'Dat' in morph.get("Case"):
                    nominative_token = token[:-3] + 'ος'
                    nominative_token = macronization_modules(nominative_token, lemma, pos, morph, recursion_depth, oxytonized_pass=oxytonized_pass, capitalized_pass=capitalized_pass, decapitalized_pass=decapitalized_pass, different_ending_pass=True, is_lemma=is_lemma)
                    restored_token = nominative_token[:-2] + token[-3:]

                # oxytone dat plur
                elif token[-3:] == 'οῖς' and 'Dat' in morph.get("Case"):
                    nominative_token = token[:-3] + 'ός'
                    nominative_token = macronization_modules(nominative_token, lemma, pos, morph, recursion_depth, oxytonized_pass=oxytonized_pass, capitalized_pass=capitalized_pass, decapitalized_pass=decapitalized_pass, different_ending_pass=True, is_lemma=is_lemma)
                    restored_token = nominative_token[:-2] + token[-3:]
                
                # non-oxytone acc plur
                elif token[-3:] == 'ους' and 'Acc' in morph.get("Case"):
                    nominative_token = token[:-3] + 'ος'
                    nominative_token = macronization_modules(nominative_token, lemma, pos, morph, recursion_depth, oxytonized_pass=oxytonized_pass, capitalized_pass=capitalized_pass, decapitalized_pass=decapitalized_pass, different_ending_pass=True, is_lemma=is_lemma)
                    restored_token = nominative_token[:-2] + token[-3:]

                # oxytone acc plur
                elif token[-3:] == 'ούς' and 'Acc' in morph.get("Case"):
                    nominative_token = token[:-3] + 'ος'
                    nominative_token = macronization_modules(nominative_token, lemma, pos, morph, recursion_depth, oxytonized_pass=oxytonized_pass, capitalized_pass=capitalized_pass, decapitalized_pass=decapitalized_pass, different_ending_pass=True, is_lemma=is_lemma)
                    restored_token = nominative_token[:-2] + token[-3:]

                macronized_token = merge_or_overwrite_markup(restored_token, macronized_token)

                if self.debug and count_dichrona_in_open_syllables(macronized_token) < count_dichrona_in_open_syllables(old_macronized_token):
                    case_ending_recursion_results.append(macronized_token)
                    logging.debug(f'\t✅ Wrong-case-ending helped: {count_dichrona_in_open_syllables(macronized_token)} left')
                else:
                    logging.debug(f'\t❌ Wrong-case-ending did not help')
            
            # 1st declension
            if not different_ending_pass and len(token) > 2 and (only_bases(lemma[-1]) == 'α' or only_bases(lemma[-1]) == 'η') and "Fem" in morph.get("Gender"):
                logging.debug(f'\t Testing for 1D wrong-case-ending recursion: {macronized_token} ({lemma})')
                old_macronized_token = macronized_token
                restored_token = ''

                # gen sing
                if (only_bases(token)[-2:] == 'ης' or only_bases(token)[-2:] == 'ας') and 'Gen' in morph.get("Case"):
                    nominative_token = token[:-2] + lemma[-1]
                    nominative_token = macronization_modules(nominative_token, lemma, pos, morph, recursion_depth, oxytonized_pass=oxytonized_pass, capitalized_pass=capitalized_pass, decapitalized_pass=decapitalized_pass, different_ending_pass=True, is_lemma=is_lemma)
                    if nominative_token[-1] == '^' or nominative_token[-1] == '_':
                        nominative_token = nominative_token[:-1] + lemma[-1]
                    restored_token = nominative_token[:-1] + token[-2:]

                # dat sing
                if (token[-1] == 'ῃ' or token[-1] == 'ῇ' or token[-1] == 'ᾳ' or token[-1] == 'ᾷ') and 'Dat' in morph.get("Case"):
                    nominative_token = macronized_token[:-1] + lemma[-1]

                # acc sing
                if (only_bases(token)[-2:] == 'ην' or only_bases(token)[-2:] == 'αν') and 'Acc' in morph.get("Case"):
                    nominative_token = macronized_token[:-2] + lemma[-1]
            
            ### OXYTONIZING RECURSION ###
            if not oxytonized_pass and macronized_token[-1] in GRAVES or macronized_token[-2] in GRAVES: # e.g. στρατηγὸν
                old_macronized_token = macronized_token
                oxytonized_token = replace_grave_with_acute(macronized_token)
                rebarytonized_token = replace_acute_with_grave(macronization_modules(oxytonized_token, lemma, pos, morph, recursion_depth, oxytonized_pass=True, capitalized_pass=capitalized_pass, decapitalized_pass=decapitalized_pass, is_lemma=is_lemma))
                macronized_token = merge_or_overwrite_markup(rebarytonized_token, macronized_token)
                if self.debug and count_dichrona_in_open_syllables(macronized_token) < count_dichrona_in_open_syllables(old_macronized_token):
                    logging.debug(f'\t✅ Oxytonizing helped: : {count_dichrona_in_open_syllables(macronized_token)} left')
                else:
                    logging.debug(f'\t❌ Oxytonizing did not help')

            if count_dichrona_in_open_syllables(macronized_token) == 0:
                if macronized_token.replace('^', '').replace('_', '') == 'Διὰ':
                    logging.debug(f'FOUND A Διὰ: {macronized_token}, {token} {lemma}, {pos}, {morph}')
                return macronized_token

            ### CAPITALIZING RECURSION ###
            # if not capitalized_pass and not decapitalized_pass and pos == "PROPN" and macronized_token[0] in VOWELS_LOWER_TO_UPPER.keys():
            #     capitalized_token = upper_grc(macronized_token[0]) + macronized_token[1:]
            #     if self.debug:
            #         logging.debug(f'\t \033Capitalizing {macronized_token} as {capitalized_token}')
            #     old_macronized_token = macronized_token
            #     capitalized_token = macronization_modules(capitalized_token, lemma, pos, morph, recursion_depth, oxytonized_pass=oxytonized_pass, capitalized_pass=True, decapitalized_pass=decapitalized_pass, is_lemma=is_lemma)
            #     restored_token = old_macronized_token[0] + capitalized_token[1:] # restore the original first character
            #     logging.debug(f'\t Restoring capitalized token: {capitalized_token} => {restored_token}')

            #     macronized_token = merge_or_overwrite_markup(restored_token, macronized_token)
            #     if self.debug and count_dichrona_in_open_syllables(macronized_token) != count_dichrona_in_open_syllables(old_macronized_token):
            #         logging.debug(f'\t✅ Capitalization helped: {count_dichrona_in_open_syllables(macronized_token)} left')
            #     else:
            #         logging.debug(f'\t❌ Capitalization did not help')

            ### DECAPITALIZING RECURSION ### Useful because many editions capitalize the first word of a sentence or section!
            if count_dichrona_in_open_syllables(macronized_token) > 0:
                old_macronized_token = macronized_token
                decapitalized_token = lower_grc(token[0]) + token[1:]
                if not capitalized_pass and not decapitalized_pass and macronized_token != decapitalized_token: # without the capitalized_pass check, we get infinite recursion for capitalized tokens
                    if self.debug:
                        logging.debug(f'\t Decapitalizing {macronized_token} as {decapitalized_token}')
                    
                    decapitalized_token = macronization_modules(decapitalized_token, lemma, pos, morph, recursion_depth, oxytonized_pass=oxytonized_pass, capitalized_pass=capitalized_pass,  decapitalized_pass=True, is_lemma=is_lemma)
                    recapitalized_token = token[0] + decapitalized_token[1:] # restore the original first character

                    macronized_token = merge_or_overwrite_markup(recapitalized_token, macronized_token)

                    if count_dichrona_in_open_syllables(macronized_token) < count_dichrona_in_open_syllables(old_macronized_token):
                        if self.debug:
                            logging.debug(f'\t✅ Decapitalization helped: {count_dichrona_in_open_syllables(macronized_token)} left')
                    elif self.debug:
                        logging.debug(f'\t❌ Decapitalization did not help')

            # ### LEMMA-BASED GENERALIZATION RECURSION ###
            # if count_dichrona_in_open_syllables(macronized_token) > 0:
            #     decapitalized_token = lower_grc(token.replace('^', ''))
            #     if not is_lemma and not decapitalized_token == lemma: # if the token is capitalized and is the lemma itself, we get infinite recursion
            #         lemma_token = macronization_modules(macronized_token, lemma, pos, morph, recursion_depth, oxytonized_pass=oxytonized_pass, capitalized_pass=capitalized_pass, decapitalized_pass=decapitalized_pass, is_lemma=True)
            #         macronized_token = self.lemma_generalization(macronized_token, lemma_token)
            #         if self.debug:
            #             logging.debug(f'\t✅ Lemma generalization (placeholder): {count_dichrona_in_open_syllables(macronized_token)} left')

            assert not macronized_diphthong(macronized_token), f"Watch out! We just macronized a diphthong: {macronized_token}"
            assert normalize_word(macronized_token.replace("^", "").replace("_", "")) == normalize_word(token.replace("^", "").replace("_", "")), f"Watch out! We just accidentally perverted a token: {token} has become {macronized_token}"

            return macronized_token

        macronized_tokens = []
        still_ambiguous = []
        for token, lemma, pos, morph in tqdm(token_lemma_pos_morph, desc="Macronizing tokens", leave=True):
            logging.debug(f'Sending to macronization_modules: {token} ({lemma}, {pos}, {morph})')
            result = macronization_modules(token, lemma, pos, morph)
            if count_dichrona_in_open_syllables(result) > 0:
                still_ambiguous.append(result)
            macronized_tokens.append(result)

        text_object.macronized_words = macronized_tokens
        text_object.integrate() # creates the final .macronized_text

        if stats:
            self.macronization_ratio(text, text_object.macronized_text, count_all_dichrona=True, count_proper_names=True)
        
        # MODULE EFFICACY LISTS

        with open('diagnostics/modules/case_recursion.txt', 'w', encoding='utf-8') as f:
            for word in case_ending_recursion_results:
                f.write(f'{word}\n')

        # STILL_AMBIGUOUS

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

        logging.debug(f'\n\n ### END OF MACRONIZATION ###\n\n')

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

        print("### STATS ###")

        count_before = 0
        count_after = 0

        if not count_all_dichrona:
            count_before = count_ambiguous_dichrona_in_open_syllables(text)
            count_after = count_ambiguous_dichrona_in_open_syllables(macronized_text)
            print(f"Dichrona in open syllables not covered by accent rules before: \t{count_before}")
            print(f"Dichrona in open syllables not covered by accent rules after: \t{count_after}")
        else:
            count_before = count_dichrona_in_open_syllables(text)
            count_after = count_dichrona_in_open_syllables(macronized_text)
            print(f"Dichrona in open syllables before: \t{count_before}")
            print(f"Unmacronized dichrona in open syllables left: \t{count_after}")
            
        difference = count_before - count_after

        print(f"\033[31m{difference}\033[0m dichrona macronized.")

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
    
    def lemma_generalization(self, macronized_token, lemma):
        """
        Take a deep breath and focus. 
        This is probably the one module with the greatest potential for optimization, given enough ingenuity.
        """
        return macronized_token