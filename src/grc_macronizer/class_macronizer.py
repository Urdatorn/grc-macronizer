from collections import Counter
from datetime import datetime
from importlib.resources import files
import logging
import os
from pathlib import Path
import pickle
import re

from tqdm import tqdm

from grc_utils import ACCENTS, only_bases, CONSONANTS_LOWER_TO_UPPER, count_ambiguous_dichrona_in_open_syllables, count_dichrona_in_open_syllables, GRAVES, long_acute, lower_grc, no_macrons, normalize_word, paroxytone, patterns, proparoxytone, properispomenon, short_vowel, syllabifier, upper_grc, vowel, VOWELS_LOWER_TO_UPPER, word_with_real_dichrona

from .ascii import ascii_macronizer
from .barytone import replace_grave_with_acute, replace_acute_with_grave
from .class_text import Text
from .db.custom import custom_macronizer
from .db.lsj import lsj
from .db.proper_names import proper_names
from .db.wiktionary_ambiguous import wiktionary_ambiguous_map
from .db.wiktionary_singletons import wiktionary_singletons_map
from .format_macrons import macron_unicode_to_markup, merge_or_overwrite_markup
from .morph_disambiguator import morph_disambiguator
from .nominal_forms import macronize_nominal_forms
from .sanity_check import demacronize_diphthong, macronized_diphthong
from .verbal_forms import macronize_verbal_forms

####################
# --- Preamble --- #
####################

# Logging setup

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_dir = Path("diagnostics") / "logs"  # relative to working directory!
log_filename = log_dir / f"macronizer_{timestamp}.log"

os.makedirs(log_dir, exist_ok=True)

logging.basicConfig(
    level=logging.DEBUG,
    filename=log_filename,
    format="%(asctime)s - %(message)s"
)

logging.info("Starting new log...")
for line in ascii_macronizer:
    logging.info(line)

###########################
# Load pickled databases  #
###########################

lsj_keys_path = files("grc_macronizer.db").joinpath("lsj_keys.pkl")
with lsj_keys_path.open("rb") as f:
    lsj_keys = pickle.load(f)

# Convert lsj_keys to a set for faster lookups
lsj_keys_set = {only_bases(key) for key in lsj_keys}

hypotactic_path = files("grc_macronizer.db").joinpath("hypotactic.pkl")
with hypotactic_path.open("rb") as f:
    hypotactic = pickle.load(f)

#######################
# --- Main class ---  #
#######################

class Macronizer:
    def __init__(self, 
                 macronize_everything=True,
                 make_prints=True,
                 unicode=False,
                 debug=False,
                 doc_from_file=True,
                 no_hypotactic=False,
                 custom_doc="",
                 lowercase=False):

        self.macronize_everything = macronize_everything
        self.make_prints = make_prints
        self.unicode = unicode
        self.debug = debug
        self.doc_from_file = doc_from_file
        self.no_hypotactic = no_hypotactic
        self.custom_doc = custom_doc
        self.lowercase = lowercase
            
    def wiktionary(self, word, lemma, pos, morph):
        """
        Should return with macron_unicode_to_markup
        """
        word = normalize_word(no_macrons(word.replace('^', '').replace('_', '')))
        word_lower = lower_grc(word[0]) + word[1:]
        
        if word in wiktionary_singletons_map:
            disambiguated = wiktionary_singletons_map[word][0][0] # get the db_word singleton content
            return macron_unicode_to_markup(disambiguated)
        elif word_lower in wiktionary_singletons_map:
            disambiguated = wiktionary_singletons_map[word_lower][0][0]
            word_recapitalized = upper_grc(disambiguated[0]) + disambiguated[1:]
            return macron_unicode_to_markup(word_recapitalized)
        elif word in wiktionary_ambiguous_map: # format: [[unnormalized tokens with macrons], [table names], [row headers 1], row headers 2], [column header 1], [column header 2]]
            match = wiktionary_ambiguous_map[word]
            print(match)
            disambiguated = morph_disambiguator(word, lemma, pos, morph, token=match[0], tense=match[1], case_voice=match[2], mode=match[3], person=match[4], number=match[5])
            return macron_unicode_to_markup(disambiguated)
        elif word_lower in wiktionary_ambiguous_map: # format: [[unnormalized tokens with macrons], [table names], [row headers 1], row headers 2], [column header 1], [column header 2]]
            match = wiktionary_ambiguous_map[word]
            disambiguated = morph_disambiguator(word, lemma, pos, morph, token=match[0], tense=match[1], case_voice=match[2], mode=match[3], person=match[4], number=match[5])
            word_recapitalized = upper_grc(disambiguated[0]) + disambiguated[1:]
            return macron_unicode_to_markup(word_recapitalized)
        else:
            return word
    
    def hypotactic(self, word):
        '''
        >>> hypotactic('ἀγαθῆς')
        >>> ἀ^γα^θῆς
        '''
        if self.no_hypotactic:
            return word

        word = word.replace('^', '').replace('_', '')
        word = normalize_word(word)

        macronized = hypotactic.get(word)
        
        if macronized:
            macronized = demacronize_diphthong(macronized)

        return macronized

    def macronize(self, text, genre='prose'):
        """
        Macronization is a modular and recursive process comprised of the following operations, 
        where later entries are considered more reliable and thus overwrite earlier ones in case of disagreement:
            [wiktionary]
            [hypotactic]
            [lsj]
            [nominal forms] # needs to be moved here from Text
            [verbal forms]
            [accent rules]
            [lemma-based generalization]
            [custom] # finally, hardcode whatever macronizations you want to overwrite every other module
        Accent rules and (naturally) lemma-based generalization are the only modules that rely on the output of the other modules for optimal performance.
        My design goal is that it should be easy for the "power user" to change the order of the other modules, and to graft in new ones.
        """

        text_object = Text(text, genre, doc_from_file=self.doc_from_file, debug=self.debug, custom_doc=self.custom_doc, lowercase=self.lowercase)
        token_lemma_pos_morph = text_object.token_lemma_pos_morph # format: [[orth, token.lemma_, token.pos_, token.morph], ...]

        # lists to keep track of module efficacy
        wiktionary_results = []
        hypotactic_results = []
        lsj_results = []
        nominal_forms_results = []
        verbal_forms_results = []
        accent_rules_results = []
        prefix_results = []
        lemma_generalization_results = []
        custom_results = []
        double_accent_recursion_results = []
        case_ending_recursion_results = []
        reversed_elision_recursion_results = []
        decapitalization_results = []
            
        def macronization_modules(token, lemma, pos, morph, recursion_depth=0, oxytonized_pass=False, capitalized_pass=False, decapitalized_pass=False, different_ending_pass=False, is_lemma=False, double_accent_pass=False, reversed_elision_pass=False):
            '''
            NOTE it is possible to change the order of modules without having to rewrite too many lines. 
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
            elif reversed_elision_pass:
                logging.debug(f'🔄 Macronizing (reversed elision): {token} ({lemma}, {pos}, {morph})')
            else:
                logging.debug(f'🔄 Macronizing: {token} ({lemma}, {pos}, {morph})')

            macronized_token = token

            ### CUSTOM OVERRIDING ###

            # Minimal pairs requiring special disambiguation

            if token == 'ἄλλα':
                if 'Fem' in morph.get("Gender"):
                    logging.debug(f'\t✅ Macronized feminine {token}')
                    return 'ἄλλα_'
                else:
                    logging.debug(f'\t✅ Macronized neutre {token}')
                    return 'ἄλλα^' # neutre plural

            custom_token = custom_macronizer(macronized_token)
            if self.debug and custom_token != macronized_token:
                logging.debug(f'\t✅ Custom: {macronized_token} => {merge_or_overwrite_markup(custom_token, macronized_token)}, with {count_dichrona_in_open_syllables(merge_or_overwrite_markup(custom_token, macronized_token))} left')
            elif self.debug:
                logging.debug(f'\t❌ Custom did not help')
            macronized_token = merge_or_overwrite_markup(custom_token, macronized_token)

            if count_dichrona_in_open_syllables(macronized_token) == 0:
                custom_results.append(macronized_token)
                return macronized_token

            ### DB MODULES ####

            # WIKTIONARY

            old_macronized_token = macronized_token
            wiktionary_token = self.wiktionary(macronized_token, lemma, pos, morph)
            macronized_token = merge_or_overwrite_markup(wiktionary_token, macronized_token)
            if count_dichrona_in_open_syllables(macronized_token) < count_dichrona_in_open_syllables(old_macronized_token):
                wiktionary_results.append(macronized_token)
                logging.debug(f'\t✅ Wiktionary: {token} => {wiktionary_token}, with {count_dichrona_in_open_syllables(wiktionary_token)} left')
            else:
                logging.debug(f'\t❌ Wiktionary did not help')
            
            if count_dichrona_in_open_syllables(macronized_token) == 0:
                return macronized_token

            # LSJ
            
            old_macronized_token = macronized_token
            lsj_token = lsj.get(token, token)
            if normalize_word(lsj_token.replace('^', '').replace('_', '')) == normalize_word(token.replace('^', '').replace('_', '')): # There are some accent bugs in the lsj db. Better safe than sorry
                macronized_token = merge_or_overwrite_markup(lsj_token, macronized_token)
                if count_dichrona_in_open_syllables(macronized_token) < count_dichrona_in_open_syllables(old_macronized_token):
                    lsj_results.append(macronized_token)
                    logging.debug(f'\t✅ LSJ helped: {old_macronized_token} => {macronized_token}, with {count_dichrona_in_open_syllables(macronized_token)} left')
                else:
                    logging.debug(f'\t❌ LSJ did not help')

            if count_dichrona_in_open_syllables(macronized_token) == 0:
                return macronized_token

            ### ALGORITHMIC MODULES ###

            old_macronized_token = macronized_token
            nominal_forms_token = macronize_nominal_forms(token, lemma, pos, morph, debug=self.debug)
            macronized_token = merge_or_overwrite_markup(nominal_forms_token, macronized_token)
            if count_dichrona_in_open_syllables(macronized_token) < count_dichrona_in_open_syllables(old_macronized_token):
                nominal_forms_results.append(macronized_token)
                logging.debug(f'\t✅ Nominal forms helped: {old_macronized_token} => {macronized_token}, with {count_dichrona_in_open_syllables(macronized_token)} left')
            else:
                logging.debug(f'\t❌ Nominal forms did not help')


            old_macronized_token = macronized_token
            verbal_forms_token = macronize_verbal_forms(token, lemma, pos, morph, debug=self.debug)
            macronized_token = merge_or_overwrite_markup(verbal_forms_token, macronized_token)
            if count_dichrona_in_open_syllables(macronized_token) < count_dichrona_in_open_syllables(old_macronized_token):
                verbal_forms_results.append(macronized_token)
                logging.debug(f'\t✅ Verbal forms helped: {old_macronized_token} => {macronized_token}, with {count_dichrona_in_open_syllables(macronized_token)} left')
            else:
                logging.debug(f'\t❌ Verbal forms did not help')
            
            if count_dichrona_in_open_syllables(macronized_token) == 0:
                return macronized_token

            old_macronized_token = macronized_token
            accent_rules_token = self.apply_accentuation_rules(macronized_token) # accent rules benefit from earlier macronization
            macronized_token = merge_or_overwrite_markup(accent_rules_token, macronized_token)
            if count_dichrona_in_open_syllables(macronized_token) < count_dichrona_in_open_syllables(old_macronized_token):
                accent_rules_results.append(macronized_token)
                logging.debug(f'\t✅ Accent rules helped: {old_macronized_token} => {macronized_token}, with {count_dichrona_in_open_syllables(macronized_token)} left')
            else:
                logging.debug(f'\t❌ Accent rules did not help')

            if count_dichrona_in_open_syllables(macronized_token) == 0:
                return macronized_token
            
            ### PREFIXES ###
            '''
            If the word's lemma minus a prefix string is still an LSJ entry, then we macronize the prefix.
            Example: ἀφίκοντο can be macronized to ἀ^φίκοντο because ικνεομαι is in LSJ
            '''
            dichronic_prefixes = {
                                'ἀνα': 'ἀ^να^', 
                                'ἀντι': 'ἀντι^',
                                'ἀπο': 'ἀ^πο',
                                'ἀφ': 'ἀ^φ',
                                'δια': 'δι^α^',
                                'ἐπι': 'ἐπι^',
                                'κατα': 'κα^τα^',
                                'καθ': 'κα^θ',
                                'μετα': 'μετα^',
                                'παρα': 'πα^ρα^',
                                'περι': 'περι^',
                                'συν': 'συ^ν',
                                'ξυν': 'ξυ^ν',
                                'συμ': 'συ^μ',
                                'ὑπερ': 'ὑ^περ',
                                'ὑπο': 'ὑ^πο',
                                'ὑφ': 'ὑ^φ',
            }

            dichronic_prefixes_unaspirated_elision = { # these need to be checked after the above since they are substrings of some of them
                                'ἀν': 'ἀ^ν', # e.g. ἀν-ειλέω 
                                'ἀπ': 'ἀ^π',
                                'δι': 'δι^', # e.g. δι-έχω
                                'κατ': 'κα^τ',
                                'παρ': 'πα^ρ',
                                'ὑπ': 'ὑ^π'
            }

            prefix_match = ''
            macronized_prefix_match = ''
            unprefixed_lemma = ''
            old_macronized_token = macronized_token
            for prefix, macronized_prefix in dichronic_prefixes.items():
                if token.startswith(prefix) and lemma.startswith(prefix):
                    prefix_match = prefix
                    macronized_prefix_match = macronized_prefix

                    unprefixed_lemma = lemma.removeprefix(prefix) # cool python 3.9 method!
                    unprefixed_lemma = only_bases(unprefixed_lemma)
                    logging.debug(f'\t Unprefixed lemma for {token}: {unprefixed_lemma}')
                    break
                
            for prefix, macronized_prefix in dichronic_prefixes_unaspirated_elision.items():
                if token.startswith(prefix) and lemma.startswith(prefix):
                    prefix_match = prefix
                    macronized_prefix_match = macronized_prefix

                    unprefixed_lemma = lemma.removeprefix(prefix) # cool python 3.9 method!
                    unprefixed_lemma = only_bases(unprefixed_lemma)
                    logging.debug(f'\t Unprefixed lemma for {token}: {unprefixed_lemma}')
                    break

            if unprefixed_lemma in lsj_keys_set:
                prefix_token = token.removeprefix(prefix_match)
                prefix_token = macronized_prefix_match + prefix_token
                prefix_token = normalize_word(prefix_token)
                logging.debug(f'\t Prefix token for {token}: {prefix_token}')

                macronized_token = merge_or_overwrite_markup(prefix_token, macronized_token)
                if self.debug and count_dichrona_in_open_syllables(macronized_token) < count_dichrona_in_open_syllables(old_macronized_token):
                    prefix_results.append(macronized_token)
                    logging.debug(f'\t✅ Prefix macronization helped: {count_dichrona_in_open_syllables(macronized_token)} left')
                else:
                    logging.debug(f'\t❌ Prefix macronization did not help')

            if count_dichrona_in_open_syllables(macronized_token) == 0:
                return macronized_token

            #################
            ### RECURSION ###
            #################

            '''
            # Example of working two-level recursion:
                # 2025-03-30 11:39:44,565 - 🔄 Macronizing: Διὰ (διά, ADP, )
                # 2025-03-30 11:39:44,565 - 🔄 Macronizing (oxytonized): Διά (διά, ADP, )
                # 2025-03-30 11:39:44,566 - 	 Decapitalizing Διά as διά
                # 2025-03-30 11:39:44,566 - 🔄 Macronizing (oxytonized): διά (διά, ADP, )
                # 2025-03-30 11:39:44,566 - 	✅ Custom: διά => δι^ά^, with 0 left
                # 2025-03-30 11:39:44,566 - 	✅ Decapitalization helped: 0 left
                # 2025-03-30 11:39:44,567 - 	✅ Oxytonizing helped: : 0 left
            '''

            ### DOUBLE-ACCENT RECURSION ###

            '''
            Recursively handle paroxytone or properispomenon tokens with >1 accent, like Καλλίμαχός or οἷός or πράγματά.
            # NOTE that if follows that such tokens cannot have final long, and so no risk of loosing iota subscript.
            Hence we should be able to safely use only_bases().
            # NOTE that what we need to handle is just that final accent can be on *the last or next to last syllable*. 
            '''

            if not double_accent_pass and len(normalize_word(token)) > 1:
                accents = [char for char in token if char in ACCENTS]
                if len(accents) > 1:
                    one_accent_token_last = ''
                    one_accent_token_next_to_last = ''
                    reconstituted_token = ''
                    old_macronized_token = macronized_token

                    if token[-1] in ACCENTS:
                        one_accent_token_last = token[:-1] + only_bases(token[-1])
                    if token[-2] in ACCENTS:
                        one_accent_token_next_to_last = token[:-2] + only_bases(token[-2:])
                    
                    if one_accent_token_last:
                        one_accent_token_last = macronization_modules(one_accent_token_last, lemma, pos, morph, recursion_depth, oxytonized_pass=oxytonized_pass, capitalized_pass=capitalized_pass, decapitalized_pass=decapitalized_pass, different_ending_pass=different_ending_pass, is_lemma=is_lemma, double_accent_pass=True)
                        logging.debug(f'\t One-accent token macronized (last): {one_accent_token_last}')
                        if one_accent_token_last[-1] == '_' or not one_accent_token_last: # no words with 2 accents have final long (they are either proparoxytone or properispomenon)
                            pass
                        elif one_accent_token_last[-1] == '^':
                            reconstituted_token = one_accent_token_last[:-2] + token[-1] + one_accent_token_last[-1]
                        else:
                            reconstituted_token = one_accent_token_last[:-1] + token[-1]
                    
                    if one_accent_token_next_to_last:
                        one_accent_token_next_to_last = macronization_modules(one_accent_token_next_to_last, lemma, pos, morph, recursion_depth, oxytonized_pass=oxytonized_pass, capitalized_pass=capitalized_pass, decapitalized_pass=decapitalized_pass, different_ending_pass=different_ending_pass, is_lemma=is_lemma, double_accent_pass=True)
                        logging.debug(f'\t One-accent token macronized (next to last): {one_accent_token_next_to_last}')
                        if one_accent_token_next_to_last[-2] == '_' or not one_accent_token_next_to_last: # no words with 2 accents have final long (they are either proparoxytone or properispomenon)
                            pass
                        elif one_accent_token_next_to_last[-2] == '^':
                            reconstituted_token = one_accent_token_next_to_last[:-3] + token[-2] + one_accent_token_next_to_last[-2] + token[-1]
                        else:
                            reconstituted_token = one_accent_token_next_to_last[:-2] + token[-2:]
                    if reconstituted_token:    
                        macronized_token = merge_or_overwrite_markup(reconstituted_token, macronized_token)
                    if count_dichrona_in_open_syllables(macronized_token) < count_dichrona_in_open_syllables(old_macronized_token):
                        double_accent_recursion_results.append(macronized_token)
                        logging.debug(f'\t✅ Double accent macronization helped: {count_dichrona_in_open_syllables(macronized_token)} left')
                    else:
                        logging.debug(f'\t❌ Double accent macronization did not help')
                    
            if count_dichrona_in_open_syllables(macronized_token) == 0:
                return macronized_token

            ### REVERSED-ELISION RECURSION ###

            '''
            Handle elided words like παρ'
            Elided final vowels: {"α^", "ε", "ι^"}. 
                - Example of elided alpha: διωλόμεσθ' (Sophocles)
            
            NOTE: When sent to full recursion, a reversed non-existent token like *διωλόμεσθι will get macronized by the proparoxytone rule
            and merged, introducing an error. Hence the extra check for ^ in the newly macronized token before re-elision.
            '''

            elided_vowels = ["ε", "ι", "α"]
            reversed_worked = False
            old_macronized_token = macronized_token
            if not reversed_elision_pass and token[-1] == "'":
                reversed_elision_token = token[:-1] + elided_vowels[0] # remove the apostrophe and add a vowel
                reversed_elision_token = macronization_modules(reversed_elision_token, lemma, pos, morph, recursion_depth, oxytonized_pass=oxytonized_pass, capitalized_pass=capitalized_pass, decapitalized_pass=decapitalized_pass, different_ending_pass=different_ending_pass, is_lemma=is_lemma, double_accent_pass=double_accent_pass, reversed_elision_pass=True)
                logging.debug(f'\t Reversed elision token: {reversed_elision_token}')
                restored_token = reversed_elision_token[:-1] + "'"
                macronized_token = merge_or_overwrite_markup(restored_token, macronized_token)
                if count_dichrona_in_open_syllables(macronized_token) < count_dichrona_in_open_syllables(old_macronized_token):
                    reversed_worked = True
                    reversed_elision_recursion_results.append(macronized_token)
                    logging.debug(f'\t✅ Reversed elision with iota macronization helped: {count_dichrona_in_open_syllables(macronized_token)} left')
                else:
                    logging.debug(f'\t❌ Reversed elision with epsilon macronization did not help')

            if not reversed_worked and not reversed_elision_pass and token[-1] == "'":
                reversed_elision_token = token[:-1] + elided_vowels[1] # remove the apostrophe and add a vowel
                reversed_elision_token = macronization_modules(reversed_elision_token, lemma, pos, morph, recursion_depth, oxytonized_pass=oxytonized_pass, capitalized_pass=capitalized_pass, decapitalized_pass=decapitalized_pass, different_ending_pass=different_ending_pass, is_lemma=is_lemma, double_accent_pass=double_accent_pass, reversed_elision_pass=True)
                logging.debug(f'\t Reversed elision token: {reversed_elision_token}')
                if reversed_elision_token[-1] == '^' or reversed_elision_token[-1] == '_': # I have encountered pathological cases with long ultima
                    restored_token = reversed_elision_token[:-2] + "'"
                else:
                    restored_token = reversed_elision_token[:-1] + "'"
                macronized_token = merge_or_overwrite_markup(restored_token, macronized_token)
                if count_dichrona_in_open_syllables(macronized_token) < count_dichrona_in_open_syllables(old_macronized_token):
                    reversed_elision_recursion_results.append(macronized_token)
                    logging.debug(f'\t✅ Reversed elision with iota macronization helped: {count_dichrona_in_open_syllables(macronized_token)} left')
                else:
                    logging.debug(f'\t❌ Reversed elision with iota macronization did not help either')

            ### WRONG-CASE-ENDING RECURSION ### 

            '''
            e.g. πόλιν should go through πόλις
            '''

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
            if (
                not oxytonized_pass and (
                    macronized_token[-1] in GRAVES or
                    (len(macronized_token) > 1 and macronized_token[-2] in GRAVES)
                )
            ): # e.g. στρατηγὸν
                old_macronized_token = macronized_token
                oxytonized_token = old_macronized_token[:-2] + replace_grave_with_acute(old_macronized_token[-2:])
                oxytonized_token = macronization_modules(oxytonized_token, lemma, pos, morph, recursion_depth, oxytonized_pass=True, capitalized_pass=capitalized_pass, decapitalized_pass=decapitalized_pass, is_lemma=is_lemma)
                rebarytonized_token = ''
                if len(oxytonized_token) > 2:
                    rebarytonized_token = oxytonized_token[:-3] + replace_acute_with_grave(oxytonized_token[-3:])
                else:
                    rebarytonized_token = oxytonized_token[:-2] + replace_acute_with_grave(oxytonized_token[-2:])
                macronized_token = merge_or_overwrite_markup(rebarytonized_token, macronized_token)
                if self.debug and count_dichrona_in_open_syllables(macronized_token) < count_dichrona_in_open_syllables(old_macronized_token):
                    logging.debug(f'\t✅ Oxytonizing helped: : {count_dichrona_in_open_syllables(macronized_token)} left')
                else:
                    logging.debug(f'\t❌ Oxytonizing did not help')

            if count_dichrona_in_open_syllables(macronized_token) == 0:
                if macronized_token.replace('^', '').replace('_', '') == 'Διὰ':
                    logging.debug(f'FOUND A Διὰ: {macronized_token}, {token} {lemma}, {pos}, {morph}')
                return macronized_token

            ### DECAPITALIZING RECURSION ###
            
            '''Useful because many editions capitalize the first word of a sentence or section! '''

            if count_dichrona_in_open_syllables(macronized_token) > 0 and (token[0] in VOWELS_LOWER_TO_UPPER.values() or token[0] in CONSONANTS_LOWER_TO_UPPER.values()):
                old_macronized_token = macronized_token
                decapitalized_token = lower_grc(token[0]) + token[1:]
                if not decapitalized_pass and macronized_token != decapitalized_token: # without the capitalized_pass check, we get infinite recursion for capitalized tokens
                    if self.debug:
                        logging.debug(f'\t Decapitalizing {macronized_token} as {decapitalized_token}')
                    
                    decapitalized_token = macronization_modules(decapitalized_token, lemma, pos, morph, recursion_depth, oxytonized_pass=oxytonized_pass, capitalized_pass=capitalized_pass,  decapitalized_pass=True, different_ending_pass=different_ending_pass, is_lemma=is_lemma, double_accent_pass=double_accent_pass, reversed_elision_pass=reversed_elision_pass)
                    recapitalized_token = token[0] + decapitalized_token[1:] # restore the original first character

                    macronized_token = merge_or_overwrite_markup(recapitalized_token, macronized_token)

                    if count_dichrona_in_open_syllables(macronized_token) < count_dichrona_in_open_syllables(old_macronized_token):
                        decapitalization_results.append(macronized_token)
                        if self.debug:
                            logging.debug(f'\t✅ Decapitalization helped: {count_dichrona_in_open_syllables(macronized_token)} left')
                    elif self.debug:
                        logging.debug(f'\t❌ Decapitalization did not help')

            ###############################
            # HYPOTACTIC (SPECIAL SAFETY) #
            ###############################

            '''
            Hypotactic is the wildest of the databases, because it is culled directly from verse. 
            To minimize bugs, the safety-net idea here is 
                1) that hypotactic is last in priority and 
                2) that bugs like θύ^ελλα_ν should be allowed to be corrected by the extra final accent rule call.
            '''

            old_macronized_token = macronized_token
            hypotactic_token = self.hypotactic(macronized_token)
            macronized_token = merge_or_overwrite_markup(hypotactic_token, macronized_token)
            if count_dichrona_in_open_syllables(macronized_token) < count_dichrona_in_open_syllables(old_macronized_token):
                hypotactic_results.append(macronized_token)
                logging.debug(f'\t✅ Hypotactic helped: {old_macronized_token} => {macronized_token}, with {count_dichrona_in_open_syllables(macronized_token)} left')
            else:
                logging.debug(f'\t❌ Hypotactic did not help')

            old_macronized_token = macronized_token
            accent_rules_token = self.apply_accentuation_rules(macronized_token) # accent rules benefit from earlier macronization
            print(accent_rules_token)
            macronized_token = merge_or_overwrite_markup(accent_rules_token, macronized_token)
            print(macronized_token)
            if count_dichrona_in_open_syllables(macronized_token) < count_dichrona_in_open_syllables(old_macronized_token):
                accent_rules_results.append(macronized_token)
                logging.debug(f'\t✅ Accent rules helped: {old_macronized_token} => {macronized_token}, with {count_dichrona_in_open_syllables(macronized_token)} left')
            else:
                logging.debug(f'\t❌ Accent rules did not help')
    
            ################
            # SANITY CHECK #
            ################

            macronized_normalized_for_checking = normalize_word(macronized_token.replace("^", "").replace("_", ""))
            token_normalized_for_checking = normalize_word(token.replace("^", "").replace("_", ""))
            if macronized_normalized_for_checking != token_normalized_for_checking: 
                logging.DEBUG(f"Watch out! We just accidentally perverted a token: {token} has become {macronized_token.replace('^', '').replace('_', '')}")

            macronized_token = demacronize_diphthong(macronized_token)

            return macronized_token

        macronized_tokens = []
        still_ambiguous = []
        for token, lemma, pos, morph in tqdm(token_lemma_pos_morph, desc="Macronizing tokens ☕️", leave=self.make_prints):
            logging.debug(f'Sending to macronization_modules: {token} ({lemma}, {pos}, {morph})')
            result = macronization_modules(token, lemma, pos, morph)
            if count_dichrona_in_open_syllables(result) > 0:
                still_ambiguous.append((result, lemma, pos, morph))
            macronized_tokens.append(result)

        logging.info(f'\n\n### END OF MACRONIZATION ###\n\n')

        text_object.macronized_words = macronized_tokens
        text_object.integrate() # creates the final .macronized_text

        if self.make_prints:
            the_ratio = self.macronization_ratio(text, text_object.macronized_text, count_all_dichrona=True, count_proper_names=True)
        
        # MODULE EFFICACY LISTS

        results_dict = {
            "wiktionary_results": wiktionary_results,
            "hypotactic_results": hypotactic_results,
            "lsj_results": lsj_results,
            "nominal_forms_results": nominal_forms_results,
            "verbal_forms_results": verbal_forms_results,
            "accent_rules_results": accent_rules_results,
            "prefix_results": prefix_results,
            "lemma_generalization_results": lemma_generalization_results,
            "custom_results": custom_results,
            "double_accent_recursion_results": double_accent_recursion_results,
            "case_ending_recursion_results": case_ending_recursion_results,
            "reversed_elision_recursion_results": reversed_elision_recursion_results,
            "decapitalization_results": decapitalization_results,
        }

        module_dir = Path("diagnostics") / "modules"
        module_dir.mkdir(parents=True, exist_ok=True)  # better than os.makedirs

        for name, result_list in results_dict.items():
            logging.debug(f'RESULT LIST: Found {len(result_list)} results in {name}')

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            out_path = module_dir / f"{timestamp}_{name}.txt"
            with out_path.open("w", encoding="utf-8") as f:
                for word in result_list:
                    f.write(f"{word}\n")

        # STILL_AMBIGUOUS

        def sort_by_occurrences(lst):
            count = Counter(x[0] for x in lst)
            sorted_lst = sorted(lst, key=lambda x: (-count[x[0]], x[0]))  # Sort by frequency (desc), then by value (asc)
            return sorted_lst, count  # Return sorted list + count dictionary

        sorted_list, counts = sort_by_occurrences(still_ambiguous)  # Preserve order
        # Remove duplicates while preserving order (based on first element of quadruple)
        seen = set()
        unique_sorted_list = []
        for item in sorted_list:
            key = item[0]
            if key not in seen:
                seen.add(key)
                unique_sorted_list.append(item)

        file_version = 1
        file_stub = ''
        file_name = ''

        still_ambiguous_dir = Path("diagnostics") / "still_ambiguous"
        still_ambiguous_dir.mkdir(parents=True, exist_ok=True)  # Create directory if it doesn't exist

        if len(macronized_tokens) > 0:
            if macronized_tokens[0]:
                file_stub = still_ambiguous_dir / f'still_ambiguous_{macronized_tokens[0].replace("^", "").replace("_", "")}'
            else:
                file_stub = still_ambiguous_dir / 'still_ambiguous'

            while True:
                file_name = file_stub.with_name(f'{file_stub.stem}_{file_version}.tsv')  # Output TSV now
                if not file_name.exists():
                    break
                file_version += 1

            with file_name.open('w', encoding='utf-8') as f:
                for item in unique_sorted_list:
                    count = counts[item[0]]
                    f.write(f"{count}\t{item[0]}\t{item[1]}\t{item[2]}\t{item[3]}\n")

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

        print("###### STATS ######")

        count_before = 0
        count_after = 0

        if not count_all_dichrona:
            count_before = count_ambiguous_dichrona_in_open_syllables(text)
            count_after = count_ambiguous_dichrona_in_open_syllables(macronized_text)
            print(f"Dichrona in open syllables not covered by accent rules before: \t\t\t{count_before}")
            print(f"Dichrona in open syllables not covered by accent rules after: \t{count_after}")
        else:
            count_before = count_dichrona_in_open_syllables(text)
            count_after = count_dichrona_in_open_syllables(macronized_text)
            print(f"Dichrona in open syllables before:            {count_before}")
            print(f"Unmacronized dichrona in open syllables left: {count_after}")
            
        difference = count_before - count_after

        print(f"\n\033[32m{difference}\033[0m dichrona macronized.")

        ratio = difference / count_before if count_before > 0 else 0

        print(f"\nMacronization ratio: \033[32m{ratio:.2%}\033[0m")

        return ratio
    
    def apply_accentuation_rules(self, old_version):
        if "'" in old_version:
            return old_version

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
                        modified_syllable = syllable[:i+1] + '^' + syllable[i+1:].replace("^", "").replace("_", "")
                        break
            elif position == -1 and paroxytone(new_version) and long_acute(penultima):
                # Find the last vowel in syllable and append '_' after it
                for i in range(len(syllable)-1, -1, -1):
                    if vowel(syllable[i]) and word_with_real_dichrona(syllable):
                        modified_syllable = syllable[:i+1] + '_' + syllable[i+1:].replace("^", "").replace("_", "")
                        break
            elif position == -1 and (properispomenon(new_version) or proparoxytone(new_version)):
                # Find the last vowel in syllable and append '^' after it
                for i in range(len(syllable)-1, -1, -1):
                    if vowel(syllable[i]) and word_with_real_dichrona(syllable):
                        modified_syllable = syllable[:i+1] + '^' + syllable[i+1:].replace("^", "").replace("_", "")
                        break
            modified_syllable_positions.append((position, modified_syllable))
            
        #print("Modified syllable positions:", modified_syllable_positions) # new debug print
        new_version = ''.join(syllable for _, syllable in modified_syllable_positions)
        print("New version:", new_version) # debugging

        merged = merge_or_overwrite_markup(new_version, old_version)

        if macronized_diphthong(merged):
            logging.debug(f"apply_accentuation_rules just macronized a diphthong, so we returned the old version: {merged}")
            return old_version
        return merged
