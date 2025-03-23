import sqlite3
from grc_utils import normalize_word, no_macrons, ACUTES, CIRCUMFLEXES, vowel

def load_wiktionary_map(wiktionary_db_file):
    wiktionary_map = {}

    try:
        conn = sqlite3.connect(wiktionary_db_file)
        cursor = conn.cursor()
        cursor.execute("SELECT word, table_name, row_header_1, row_header_2, column_header_1, column_header_2 FROM macrons")
        rows = cursor.fetchall()
        conn.close()

        for row in rows:
            db_word, table_name, row_header_1, row_header_2, column_header_1, column_header_2 = row
            normalized_word = normalize_word(no_macrons(db_word))

            # Get or create the entry for this normalized word
            if normalized_word not in wiktionary_map:
                wiktionary_map[normalized_word] = [[], [], [], [], [], []]
            entry = wiktionary_map[normalized_word]

            # Only add if db_word is not already in the list
            if db_word not in entry[0]:  # Check against the unnormalized word list
                entry[0].append(db_word)          # Unnormalized word
                entry[1].append(table_name)       # Table name
                entry[2].append(row_header_1)     # Row header 1
                entry[3].append(row_header_2)     # Row header 2
                entry[4].append(column_header_1)  # Column header 1
                entry[5].append(column_header_2)  # Column header 2

    except sqlite3.Error as e:
        print(f"Warning: Could not load wiktionary database: {e}")
        return None  # Exit if there's an error

    # Calculate stats for sublist lengths
    length_counts = {}
    for entry in wiktionary_map.values():
        sublist_length = len(entry[0])  # All sublists are the same length, so use entry[0]
        length_counts[sublist_length] = length_counts.get(sublist_length, 0) + 1

    # Count keys without acute or circumflex accents
    no_accents_count = 0
    for word in wiktionary_map.keys():
        has_accent = any(char in ACUTES or char in CIRCUMFLEXES for char in word)
        if not has_accent:
            no_accents_count += 1

    # Print stats
    print("Sublist length distribution:")
    for length in sorted(length_counts.keys()):
        print(f"  Length {length}: {length_counts[length]} keys")
    print(f"Keys without acute or circumflex accents: {no_accents_count}")

    # Debug: Print confirmation before writing main file
    print(f"Writing {len(wiktionary_map)} entries to wiktionary.py...")

    # **WRITE MAIN FILE (wiktionary.py)**
    try:
        with open('db/wiktionary.py', 'w', encoding='utf-8') as file:
            file.write("wiktionary_map = {\n")
            for word, data in wiktionary_map.items():
                file.write(f"    {repr(word)}: {repr(data)},\n")
            file.write("}\n")
        print("File wiktionary.py successfully written.")
    except Exception as e:
        print(f"Error writing wiktionary.py: {e}")

    # **WRITE AMBIGUOUS FILE (wiktionary_ambiguous.py)**
    ambiguous_entries = {word: data for word, data in wiktionary_map.items() if len(data[0]) > 1}
    if ambiguous_entries:
        # Sort entries by sublist length
        sorted_entries = sorted(ambiguous_entries.items(), key=lambda x: len(x[1][0]))
        print(f"Writing {len(ambiguous_entries)} ambiguous entries to wiktionary_ambiguous.py...")

        try:
            with open('db/wiktionary_ambiguous.py', 'w', encoding='utf-8') as file:
                file.write("wiktionary_ambiguous_map = {\n")
                first_len_2 = True
                first_len_3 = True
                first_len_4 = True
                for word, data in sorted_entries:
                    sublist_length = len(data[0])
                    if sublist_length == 2 and first_len_2:
                        file.write("    # First entry with length 2\n")
                        first_len_2 = False
                    elif sublist_length == 3 and first_len_3:
                        file.write("    # First entry with length 3\n")
                        first_len_3 = False
                    elif sublist_length == 4 and first_len_4:
                        file.write("    # First entry with length 4\n")
                        first_len_4 = False
                    file.write(f"    {repr(word)}: {repr(data)},\n")
                file.write("}\n")
            print("File wiktionary_ambiguous.py successfully written.")
        except Exception as e:
            print(f"Error writing wiktionary_ambiguous.py: {e}")
    else:
        print("No ambiguous entries (length > 1) found.")

    return wiktionary_map  # Return dict for further use

if __name__ == "__main__":
    wiktionary_db_file = 'db/grc_macrons.db'
    load_wiktionary_map(wiktionary_db_file)