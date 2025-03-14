import re
import sqlite3
import time
from tqdm import tqdm

from barytone import grave_to_acute, replace_grave_with_acute, replace_acute_with_grave
from epic_stop_words import epic_stop_words
from format_macrons import macron_integrate_markup, macron_markup_to_unicode, macron_unicode_to_markup, merge_or_overwrite_markup
from grc_utils import count_ambiguous_dichrona_in_open_syllables, count_dichrona_in_open_syllables, DICHRONA, has_ambiguous_dichrona_in_open_syllables, long_acute, no_macrons, normalize_word, paroxytone, proparoxytone, properispomenon, short_vowel, syllabifier, vowel
from greek_proper_names_cltk.proper_names import proper_names

def check_word(word):
    return not has_ambiguous_dichrona_in_open_syllables(word)

def get_words(text):
            text = normalize_word(text) # combining diacritics will cause splits without this
            words = re.findall(r'[\w^_]+', text) # remember that we are now acting on integrated markup with carets and underscores
            return [word for word in words if any(vowel(char) for char in word)] # extra precaution: all grc words have vowels

class Macronizer:
    """A class to handle macronization of Greek text using databases."""
    
    def __init__(self, 
                 genre='prose',
                 macronize_everything=True,
                 unicode=False,
                 ifeellucky=True,
                 wiktionary_db_file='db/grc_macrons.db', 
                 hypotactic_db_file='db/hypotactic.db', 
                 aristophanes_db_file=None, 
                 custom_db_file=None):

        self.genre = genre
        self.macronize_everything = macronize_everything
        self.unicode = unicode
        self.ifeellucky = ifeellucky
        self.wiktionary_db_file = wiktionary_db_file
        self.hypotactic_db_file = hypotactic_db_file
        self.aristophanes_db_file = aristophanes_db_file
        self.custom_db_file = custom_db_file

        self.wiktionary_map = {}
        try:
            conn = sqlite3.connect(self.wiktionary_db_file)
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT word FROM macrons")
            rows = cursor.fetchall()
            conn.close()

            for row in rows:
                db_word = row[0]
                normalized_word = normalize_word(no_macrons(db_word))
                self.wiktionary_map.setdefault(normalized_word, []).append(db_word)
        except sqlite3.Error as e:
            print(f"Warning: Could not load wiktionary database: {e}")

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
        Looks up a word in the Wiktionary database and returns its macronized form(s).
        
        Args:
            word (str): Word to look up
            
        Returns:
            str or list: Macronized form(s) of the word if found, None if not found
        """
        nw = normalize_word(no_macrons(word))
        
        # Look up the word in the pre-loaded map
        matches = self.wiktionary_map.get(nw, [])
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

    def macronize(self, words):
        """
        Takes a list of words and returns a dictionary mapping each original word
        to its macronized form(s). If no matches are found, returns the original word.
        If no match is found and the input ends with a grave accent, tries with acute.
        
        Args:
            words (list): List of words to macronize
            
        Returns:
            dict: Mapping of original words to their macronized forms
        """
        results = {}

        if self.genre == 'epic':
            for word in words:
                if word in epic_stop_words:
                    results[word] = word
        for original_word in tqdm(words, desc="Querying Wiktionary", unit="word", leave=False):
            # Try Wiktionary lookup first
            wikt_result = self.wiktionary(original_word)
            if wikt_result is not None:
                results[original_word] = wikt_result
                continue
                
            # Try replacing grave with acute if no matches
            if original_word and any(char in grave_to_acute for char in original_word):
                modified_word = replace_grave_with_acute(original_word)
                wikt_result = self.wiktionary(modified_word)
                if wikt_result is not None:
                    if isinstance(wikt_result, list):
                        results[original_word] = [replace_acute_with_grave(word) for word in wikt_result] # work in progress; this should pipe to a POS disambiguator
                    else:
                        results[original_word] = replace_acute_with_grave(wikt_result)
                    continue
            # Try hypotactic db if grave-acute doesn't help
            elif self.hypotactic(original_word) != original_word:
                results[original_word] = self.hypotactic(original_word)
                continue
            # If still no matches, return original word
            else:
                results[original_word] = original_word
        
        # Finally, apply accent rules
        if self.macronize_everything:
            results = {k: self.apply_accentuation_rules(v) for k, v in results.items()} # applied to v to make use of disambiguated dichronic ultima and penultima

        if self.unicode:
            # Optional: convert to Unicode format
            return {k: macron_markup_to_unicode(v) for k, v in results.items()}
        
        # Normalize to markup format
        return {k: macron_unicode_to_markup(v) for k, v in results.items()}

    def macronize_text(self, text):
        """
        Takes a string and macronizes words while preserving punctuation and whitespace.
        
        Args:
            text (str): Input text to macronize
        
        Returns:
            str: Macronized text with original formatting preserved
        """
        start_time = time.perf_counter()

        # Check if there's whitespace in the text
        if not re.search(r'\s', text):
            single_result = self.macronize([text])
            if single_result and text in single_result:
                return single_result[text]
            return text
        
        # Split into tokens
        tokens = re.findall(r'\w+|[^\w\s]+|\s+', text)
        words = [t for t in tokens if re.match(r'^\w+$', t)]

        # Macronize the words
        macronized_map = self.macronize(words)

        # Replace original words with macronized versions
        word_iter = iter(words)
        for i, token in enumerate(tokens):
            if re.match(r'^\w+$', token):
                original_word = next(word_iter)
                tokens[i] = macronized_map.get(original_word, original_word)

        end_time = time.perf_counter()
        print(f"\nMacronization took {end_time - start_time:.2f} seconds")

        return "".join(tokens)
    
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

