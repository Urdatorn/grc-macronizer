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

    Args:
        word (str): The Ancient Greek word to macronize.

    Returns:
        str | list | None: The macronized word(s) or None if no match is found.
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

### TEST ###
test_words = ['ἀσφαλής']
for word in test_words:
    result = macronize(word)
    print(f"{word} -> {result}")