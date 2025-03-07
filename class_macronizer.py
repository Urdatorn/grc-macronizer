import re
import sqlite3
import time

from barytone import grave_to_acute, replace_grave_with_acute, replace_acute_with_grave
from format_macrons import macron_unicode_to_markup
from grc_utils import has_ambiguous_dichrona_in_open_syllables, no_macrons, normalize_word
from proper_names import proper_names

class Macronizer:
    """A class to handle macronization of Greek text using a SQLite database."""
    
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
                    results[original_word] = matches
            else:
                # Try replacing grave with acute if no matches
                if original_word and any(char in grave_to_acute for char in original_word):
                    modified_word = replace_grave_with_acute(original_word)
                    nw_modified = normalize_word(no_macrons(modified_word))
                    matches = normalized_map.get(nw_modified, [])
                    if matches:
                        results[original_word] = (replace_acute_with_grave(matches[0]) 
                                               if self.ifeellucky 
                                               else [replace_acute_with_grave(word) for word in matches])
                        continue
                # If still no matches, return original word
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
                tokens[i] = macronized_map[original_word]

        end_time = time.perf_counter()
        print(f"Elapsed time: {end_time - start_time:.2f} seconds")

        return "".join(tokens)
    
    def macronization_ratio_words(self, text, count_proper_names=True):
        def get_words(text):
            return re.findall(r'\w+', text)

        def remove_proper_names(text):
            # Build a regex pattern that matches whole words from the set
            pattern = r'\b(?:' + '|'.join(re.escape(name) for name in proper_names) + r')\b'

            # Remove names, handling extra spaces that might appear
            cleaned_text = re.sub(pattern, '', text).strip()
            cleaned_text = re.sub(r'\s+', ' ', cleaned_text)

            return cleaned_text

        if not count_proper_names:
            text = remove_proper_names(text)

        words = get_words(text)

        fully_disambiguated = 0
        for word in words:
            if has_ambiguous_dichrona_in_open_syllables(word):
                continue
            fully_disambiguated += 1

        print_statement = f'\nDisambiguated {fully_disambiguated} words out of {len(words)} (including proper names)'
        if not count_proper_names:
            print_statement = f'\nDisambiguated {fully_disambiguated} words out of {len(words)} (excluding proper names)'
        print(print_statement)

        ratio = fully_disambiguated / len(words)
        return ratio
    
    def print_evaluation(self, text):
        print(f'\nEVALUATION')
        print('******************')
        print(f"\nInput text:\n{text[:30]}...")
        macronized_text = self.macronize_text(text)
        print(f"\nMacronized text:\n{macronized_text[:30]}...")
        ratio = self.macronization_ratio_words(macronized_text)
        print(f"\nMacronization ratio: {ratio:.2f}")
        ratio = self.macronization_ratio_words(macronized_text, count_proper_names=False)
        print(f"\nMacronization ratio (no proper names): {ratio:.2f}")

