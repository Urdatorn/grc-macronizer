from concurrent.futures import ProcessPoolExecutor
import re
import sqlite3
import time

from barytone import grave_to_acute, replace_grave_with_acute, replace_acute_with_grave
from format_macrons import macron_unicode_to_markup
from grc_utils import count_ambiguous_dichrona_in_open_syllables, has_ambiguous_dichrona_in_open_syllables, no_macrons, normalize_word, vowel
from hypotactic import hypotactic
from proper_names import proper_names

def check_word(word):
    return not has_ambiguous_dichrona_in_open_syllables(word)

def get_words(text):
            text = normalize_word(text) # combining diacritics will cause splits without this
            words = re.findall(r'[\w^_]+', text) # remember that we are now acting on integrated markup with carets and underscores
            return [word for word in words if any(vowel(char) for char in word)] # extra precaution: all grc words have vowels

class Macronizer:
    """A class to handle macronization of Greek text using databases."""
    
    def __init__(self, 
                 macronize_everything=True,
                 unicode=False,
                 ifeellucky=True,
                 wiktionary_db_file='/Users/albin/git/grc-wiktionary/grc_macrons.db', 
                 hypotactic_db_file='db/hypotactic.db', 
                 aristophanes_db_file=None, 
                 custom_db_file=None):

        
        self.macronize_everything = macronize_everything
        self.unicode = unicode
        self.ifeellucky = ifeellucky
        self.wiktionary_db_file = wiktionary_db_file
        self.hypotactic_db_file = hypotactic_db_file
        self.aristophanes_db_file = aristophanes_db_file
        self.custom_db_file = custom_db_file

        # We could load the database into memory here if we wanted to,
        # but for now we'll connect each time to keep memory usage lower

    def macronize(self, words):
        """
        Takes a list of words and returns a dictionary mapping each original word
        to its macronized form(s). If no matches are found, returns the original word.
        If no match is found and the input ends with a grave accent, tries with acute.
        
        Args:
            words (list): List of words to macronize
            ifeellucky (bool): If True, return first match when multiple exist
        
        Returns:
            dict: Mapping of original words to their macronized forms
        """
        # Normalize and strip macrons from input words once for efficiency
        normalized_input_words = [normalize_word(no_macrons(w)) for w in words]

        # Connect to the SQLite database and fetch all words
        conn = sqlite3.connect(self.wiktionary_db_file)
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT word FROM macrons")
        rows = cursor.fetchall()
        conn.close()

        # Build lookup dictionary
        normalized_map = {}
        for row in rows:
            db_word = row[0]
            nw = normalize_word(no_macrons(db_word))
            normalized_map.setdefault(nw, []).append(db_word)

        # Process each input word
        results = {}
        for original_word, nw in zip(words, normalized_input_words):
            matches = normalized_map.get(nw, [])
            if len(matches) == 1:
                results[original_word] = matches[0]
            elif len(matches) > 1:
                if self.ifeellucky:
                    results[original_word] = matches[0]
                else:
                    results[original_word] = matches # work in progress; this should pipe to a POS disambiguator
            else:
                # Try replacing grave with acute if no matches
                if original_word and any(char in grave_to_acute for char in original_word):
                    modified_word = replace_grave_with_acute(original_word)
                    nw_modified = normalize_word(no_macrons(modified_word))
                    matches = normalized_map.get(nw_modified, [])
                    if matches:
                        results[original_word] = (replace_acute_with_grave(matches[0]) 
                                               if self.ifeellucky 
                                               else [replace_acute_with_grave(word) for word in matches]) # work in progress; this should pipe to a POS disambiguator
                        continue
                # Try hypotactic db if grave-acute doesn't help
                elif hypotactic(original_word) != original_word:
                    results[original_word] = hypotactic(original_word)
                    continue
                # If still no matches, return original word
                else:
                    results[original_word] = original_word

        if self.unicode:
            return results

        results.update((k, macron_unicode_to_markup(v)) for k, v in results.items())
        return results

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
            return single_result[text]
        
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
        print(f"Elapsed time: {end_time - start_time:.2f} seconds")

        return "".join(tokens)
    
    def macronization_ratio(self, text, count_proper_names=True):
        def remove_proper_names(text):
            # Build a regex pattern that matches whole words from the set
            pattern = r'\b(?:' + '|'.join(re.escape(name) for name in proper_names) + r')\b'

            # Remove names, handling extra spaces that might appear
            cleaned_text = re.sub(pattern, '', text).strip()
            cleaned_text = re.sub(r'\s+', ' ', cleaned_text)

            return cleaned_text
        
        text = normalize_word(text)
        if not count_proper_names:
            text = remove_proper_names(text)

        ambiguous_dichrona_in_open_syllables_before = count_ambiguous_dichrona_in_open_syllables(text)
        ambiguous_dichrona_in_open_syllables_after = count_ambiguous_dichrona_in_open_syllables(self.macronize_text(text))
        difference = ambiguous_dichrona_in_open_syllables_before - ambiguous_dichrona_in_open_syllables_after

        ratio = difference / ambiguous_dichrona_in_open_syllables_before
        return ratio
    
    def print_evaluation(self, text):
        pass

