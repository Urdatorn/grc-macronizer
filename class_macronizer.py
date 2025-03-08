import re
import sqlite3
import time

from barytone import grave_to_acute, replace_grave_with_acute, replace_acute_with_grave
from format_macrons import macron_unicode_to_markup, merge_or_overwrite_markup
from grc_utils import count_ambiguous_dichrona_in_open_syllables, has_ambiguous_dichrona_in_open_syllables, long_acute, no_macrons, normalize_word, paroxytone, proparoxytone, properispomenon, short_vowel, syllabifier, vowel
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
                 wiktionary_db_file='db/grc_macrons.db', 
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
        print(f"\nMacronization took {end_time - start_time:.2f} seconds")

        return "".join(tokens)
    
    def macronization_ratio(self, text, macronized_text, count_proper_names=True):
        def remove_proper_names(text):
            # Build a regex pattern that matches whole words from the set
            pattern = r'\b(?:' + '|'.join(re.escape(name) for name in proper_names) + r')\b'

            # Remove names, handling extra spaces that might appear
            cleaned_text = re.sub(pattern, '', text).strip()
            cleaned_text = re.sub(r'\s+', ' ', cleaned_text)

            return cleaned_text
        start_time = time.perf_counter()

        text = normalize_word(text)
        if not count_proper_names:
            text = remove_proper_names(text)

        ambiguous_dichrona_in_open_syllables_before = count_ambiguous_dichrona_in_open_syllables(text)
        ambiguous_dichrona_in_open_syllables_after = count_ambiguous_dichrona_in_open_syllables(macronized_text)
        difference = ambiguous_dichrona_in_open_syllables_before - ambiguous_dichrona_in_open_syllables_after

        end_time = time.perf_counter()
        print(f"\nEvaluation took {end_time - start_time:.2f} seconds")

        print(f"Dichrona in open syllables not covered by accent rules before: {ambiguous_dichrona_in_open_syllables_before}")
        print(f"Dichrona in open syllables not covered by accent rules after: {ambiguous_dichrona_in_open_syllables_after}")
        print(f"Difference: {difference}")

        ratio = difference / ambiguous_dichrona_in_open_syllables_before
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
        print(syllable_positions) # debugging
        
        ultima = list_of_syllables[-1] # note that these may contain markup
        penultima = list_of_syllables[-2]

        modified_syllable_positions = []
        for position, syllable in syllable_positions:
            modified_syllable = syllable.replace('_', '').replace('^', '')  # Create a new variable to store modifications
            if position == -2 and paroxytone(new_version) and short_vowel(ultima):
                print(f'{syllable}: paroxytone, short ultima')
                # Find the last vowel in syllable and append '^' after it
                for i in range(len(syllable)-1, -1, -1): # NB: len(syllable)-1 is the index of the last character (0-indexed); -1 is to go backwards
                    if vowel(syllable[i]):
                        modified_syllable = syllable[:i+1] + '^' + syllable[i+1:]
                        break
            elif position == -1 and paroxytone(new_version) and long_acute(penultima):
                print(f'{syllable}: paroxytone with long acute')
                # Find the last vowel in syllable and append '_' after it
                for i in range(len(syllable)-1, -1, -1):
                    if vowel(syllable[i]):
                        modified_syllable = syllable[:i+1] + '_' + syllable[i+1:]
                        break
            elif position == -1 and (properispomenon(new_version) or proparoxytone(new_version)):
                if properispomenon(new_version):
                    print(f'{syllable}: properispomenon')
                elif proparoxytone(new_version):
                    print(f'{syllable}: proparoxytone')
                # Find the last vowel in syllable and append '^' after it
                for i in range(len(syllable)-1, -1, -1):
                    if vowel(syllable[i]):
                        modified_syllable = syllable[:i+1] + '^' + syllable[i+1:]
                        break
            modified_syllable_positions.append((position, modified_syllable))
            
        print("Modified syllable positions:", modified_syllable_positions) # new debug print
        new_version = ''.join(syllable for _, syllable in modified_syllable_positions)
        print("New version:", new_version) # debugging

        merged = merge_or_overwrite_markup(new_version, old_version)
        return merged

