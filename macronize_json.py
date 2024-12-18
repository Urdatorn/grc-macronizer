import json
import time
from grc_utils import no_macrons, normalize_word

# Load the macronized Wiktionary dictionary
with open('/Users/albin/git/grc-wiktionary/grc_macrons.json', 'r', encoding='utf-8') as f:
    grc_dict = json.load(f)

def macronize(word):
    """
    Searches the keys of grc_final.json for matches, disregarding macrons.
    If there is exactly one match, returns the macronized key.
    If there is more than one match, returns a list of macronized keys.
    If no matches are found, returns None.

    Args:
        word (str): The Ancient Greek word to macronize.

    Returns:
        str | list | None: The macronized word(s) or None if no match is found.
    """
    start_time = time.perf_counter()

    macronisandum = normalize_word(no_macrons(word))
    matches = []

    for key in grc_dict.keys():
        normalized_key = normalize_word(no_macrons(key))
        if normalized_key == macronisandum:
            matches.append(key)

    end_time = time.perf_counter()
    print(f"Elapsed time: {end_time - start_time:.2f} seconds")

    if len(matches) == 1:
        return matches[0]  # Single match found
    elif len(matches) > 1:
        return matches  # Multiple matches found
    else:
        return None  # No match found

# Test Cases (with limited output)
test_words = ['ἀσφαλής']
for word in test_words:
    result = macronize(word)
    print(f"{word} -> {result}")