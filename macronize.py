import re
import sqlite3
import time
from grc_utils import no_macrons, normalize_word

# Database file path
DB_FILE = '/Users/albin/git/grc-wiktionary/grc_macrons.db'

def macronize(words):
    """
    Takes a list of words and returns a dictionary mapping each original word
    to its macronized form(s). If no matches are found, it returns the original
    input word.
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
            # If no matches, return the original input word
            results[original_word] = original_word

    end_time = time.perf_counter()
    print(f"Elapsed time: {end_time - start_time:.2f} seconds")
    return results

def macronize_text(text):
    """
    Takes a string. If it contains no whitespace, macronize it directly.
    If it contains whitespace, split it into tokens (words, punctuation, whitespace),
    macronize the words only, and then reassemble everything with punctuation
    and whitespace in their original places.
    """
    # Check if there's whitespace in the text
    if not re.search(r'\s', text):
        # No whitespace: treat as a single word
        single_result = macronize([text])
        return single_result[text]
    else:
        # There's whitespace: split into tokens
        # Tokens: 
        # - \w+ matches words
        # - [^\w\s]+ matches punctuation
        # - \s+ matches whitespace
        tokens = re.findall(r'\w+|[^\w\s]+|\s+', text)

        # Extract just the words to macronize
        words = [t for t in tokens if re.match(r'^\w+$', t)]

        # Macronize the words
        macronized_map = macronize(words)

        # Replace original words with their macronized versions
        word_iter = iter(words)
        for i, token in enumerate(tokens):
            if re.match(r'^\w+$', token):
                original_word = next(word_iter)
                tokens[i] = macronized_map[original_word]

        # Join tokens back together to preserve punctuation and whitespace
        return "".join(tokens)

### TEST ###
test_words = ['ἀσφαλής', 'λύω', 'ὕδασιν', 'ὕδωρ']
batch_results = macronize(test_words)
for w in test_words:
    print(f"{w} -> {batch_results[w]}")

sentence = 'Δαρείου καὶ Παρυσάτιδος γίγνονται παῖδες δύο, πρεσβύτερος μὲν Ἀρταξέρξης, νεώτερος δὲ Κῦρος· ἐπεὶ δὲ ἠσθένει Δαρεῖος καὶ ὑπώπτευε τελευτὴν τοῦ βίου, ἐβούλετο τὼ παῖδε ἀμφοτέρω παρεῖναι. ὁ μὲν οὖν πρεσβύτερος παρὼν ἐτύγχανε· Κῦρον δὲ μεταπέμπεται ἀπὸ τῆς ἀρχῆς ἧς αὐτὸν σατράπην ἐποίησε, καὶ στρατηγὸν δὲ αὐτὸν ἀπέδειξε πάντων ὅσοι ἐς Καστωλοῦ πεδίον ἁθροίζονται. ἀναβαίνει οὖν ὁ Κῦρος λαβὼν Τισσαφέρνην ὡς φίλον, καὶ τῶν Ἑλλήνων ἔχων ὁπλίτας ἀνέβη τριακοσίους, ἄρχοντα δὲ αὐτῶν Ξενίαν Παρράσιον.'

print(macronize_text(sentence))