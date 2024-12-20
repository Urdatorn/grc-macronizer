import re
import sqlite3
import time

from grc_utils import no_macrons, normalize_word

DB_FILE = '/Users/albin/git/grc-wiktionary/grc_macrons.db'

sentence = 'Δαρείου καὶ Παρυσάτιδος γίγνονται παῖδες δύο, πρεσβύτερος μὲν Ἀρταξέρξης, νεώτερος δὲ Κῦρος· ἐπεὶ δὲ ἠσθένει Δαρεῖος καὶ ὑπώπτευε τελευτὴν τοῦ βίου, ἐβούλετο τὼ παῖδε ἀμφοτέρω παρεῖναι. ὁ μὲν οὖν πρεσβύτερος παρὼν ἐτύγχανε· Κῦρον δὲ μεταπέμπεται ἀπὸ τῆς ἀρχῆς ἧς αὐτὸν σατράπην ἐποίησε, καὶ στρατηγὸν δὲ αὐτὸν ἀπέδειξε πάντων ὅσοι ἐς Καστωλοῦ πεδίον ἁθροίζονται. ἀναβαίνει οὖν ὁ Κῦρος λαβὼν Τισσαφέρνην ὡς φίλον, καὶ τῶν Ἑλλήνων ἔχων ὁπλίτας ἀνέβη τριακοσίους, ἄρχοντα δὲ αὐτῶν Ξενίαν Παρράσιον.'

# Optimized macronize function using batch queries
def macronize_batch(normalized_words):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Use batch query with placeholders
    placeholders = ', '.join(['?'] * len(normalized_words))
    query = f"SELECT word FROM macrons WHERE word IN ({placeholders})"

    print(f"\n[DEBUG] Querying words: {normalized_words}\n")

    # Execute the query
    cursor.execute(query, tuple(normalized_words))
    results = {normalize_word(no_macrons(row[0])): row[0] for row in cursor.fetchall()}

    print(f"[DEBUG] Found macronized words: {results}\n")

    conn.close()
    return results

# Efficient sentence macronization
def macronize_sentence(sentence):
    words = re.findall(r'\w+|\W+', sentence)  # Extract words while keeping punctuation
    word_tokens = [normalize_word(no_macrons(w)) for w in words if re.match(r'\w+', w)]

    start_time = time.perf_counter()

    # Perform a batch SQL query
    macronized_map = macronize_batch(word_tokens)

    # Reconstruct the sentence
    macronized_words = []
    macronized_count = 0

    for word in words:
        if re.match(r'\w+', word):  # Process words only
            normalized_word = normalize_word(no_macrons(word))
            if normalized_word in macronized_map:
                macronized_words.append(macronized_map[normalized_word])
                macronized_count += 1
            else:
                macronized_words.append(word)
        else:
            macronized_words.append(word)

    # Calculate stats
    total_words = len([w for w in words if re.match(r'\w+', w)])
    macronized_percentage = (macronized_count / total_words) * 100
    elapsed_time = time.perf_counter() - start_time

    reconstructed_sentence = ''.join(macronized_words)
    return macronized_percentage, reconstructed_sentence, elapsed_time

# Test the function
sentence = 'Δαρείου καὶ Παρυσάτιδος γίγνονται παῖδες δύο, πρεσβύτερος μὲν Ἀρταξέρξης, νεώτερος δὲ Κῦρος· ἐπεὶ δὲ ἠσθένει Δαρεῖος καὶ ὑπώπτευε τελευτὴν τοῦ βίου, ἐβούλετο τὼ παῖδε ἀμφοτέρω παρεῖναι.'
percent, macronized_text, elapsed = macronize_sentence(sentence)
print(f"Macronized Percentage: {percent:.2f}%")
print(f"Elapsed Time: {elapsed:.4f} seconds")
print(f"Macronized Text:\n{macronized_text}")