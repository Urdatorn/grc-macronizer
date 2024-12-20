import sqlite3
import time
from grc_utils import no_macrons, normalize_word

# Database file path
DB_FILE = '/Users/albin/git/grc-wiktionary/grc_macrons.db'

def macronize(word):
    """
    Searches the SQLite database for matches, disregarding macrons.
    If there is exactly one match, returns the macronized key.
    If there is more than one match, returns a list of macronized keys.
    If no matches are found, returns None.
    """
    start_time = time.perf_counter()
    
    macronisandum = normalize_word(no_macrons(word))
    matches = []

    # Connect to the SQLite database
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Query the database: Retrieve all words
    cursor.execute("SELECT DISTINCT word FROM macrons")
    rows = cursor.fetchall()

    # Compare normalized values
    for row in rows:
        db_word = row[0]
        normalized_db_word = normalize_word(no_macrons(db_word))

        if normalized_db_word == macronisandum:
            matches.append(db_word)

    # Close the database connection
    conn.close()

    # Return the appropriate result
    end_time = time.perf_counter()
    print(f"Elapsed time: {end_time - start_time:.2f} seconds")

    if len(matches) == 1:
        return matches[0]  # Single match found
    elif len(matches) > 1:
        return matches  # Multiple matches found
    else:
        return None  # No match found


def macronize_batch(words):
    """
    Takes a list of words and returns a dictionary mapping each original word to 
    its macronized form(s) or None, by loading all words once from the database.
    """
    start_time = time.perf_counter()
    
    # Normalize and strip macrons from input words once for efficiency
    normalized_input_words = [normalize_word(no_macrons(w)) for w in words]

    # Connect to the SQLite database and fetch all words once
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT word FROM macrons")
    rows = cursor.fetchall()
    conn.close()

    # Build a lookup dictionary:
    # key = normalized macron-stripped word, value = list of macronized candidates
    normalized_map = {}
    for row in rows:
        db_word = row[0]
        nw = normalize_word(no_macrons(db_word))
        normalized_map.setdefault(nw, []).append(db_word)

    # For each input word, fetch matches from the lookup map
    results = {}
    for original_word, nw in zip(words, normalized_input_words):
        matches = normalized_map.get(nw, [])
        if len(matches) == 1:
            results[original_word] = matches[0]
        elif len(matches) > 1:
            results[original_word] = matches
        else:
            results[original_word] = None

    end_time = time.perf_counter()
    print(f"Elapsed time: {end_time - start_time:.2f} seconds")
    return results

### TEST ###
test_words = ['ἀσφαλής', 'λύω', 'ὕδασιν']
batch_results = macronize_batch(test_words)
for w in test_words:
    print(f"{w} -> {batch_results[w]}")