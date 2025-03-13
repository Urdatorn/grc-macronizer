import json
from tqdm import tqdm

from grc_utils import no_macrons, normalize_word, make_only_greek
from greek_accentuation.syllabify import add_necessary_breathing

def extract_lsj_keys():
    # Read the JSON file
    print("Reading lsj.json...")
    with open('lsj.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Extract top-level keys
    print("Extracting keys...")
    keys = list(data.keys())
    
    # Sort keys alphabetically
    keys.sort()
    
    # Process keys into a set
    print("Processing keys...")
    processed_words = set()
    for key in tqdm(keys, desc="Processing keys"):
        try:
            # Apply transformations in sequence
            processed_key = no_macrons(key)
            processed_key = normalize_word(processed_key)
            processed_key = make_only_greek(processed_key)
            processed_key = add_necessary_breathing(processed_key)
            processed_words.add(processed_key)
        except Exception:
            continue
    
    # Write set to Python file
    print("Writing to lsj.py...")
    with open('lsj.py', 'w', encoding='utf-8') as f:
        f.write("lsj = {\n")
        for word in tqdm(sorted(processed_words), desc="Writing words"):
            f.write(f"    '{word}',\n")
        f.write("}\n")
    
    print(f"\nDone! Wrote {len(processed_words)} unique words to lsj.py")

if __name__ == "__main__":
    extract_lsj_keys() 