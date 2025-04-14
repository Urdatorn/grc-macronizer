import json
from tqdm import tqdm

from class_macronizer import Macronizer
from grc_utils import colour_dichrona_in_open_syllables

macronizer = Macronizer()

# here I need to get all the verse_text entries from tests/unified_simplified.json
# and then run them through the macronizer

input_json = 'tests/unified_simplified.json'
output_json = 'tests/unified_simplified_macronized.json'

verse_texts = []
with open(input_json, 'r') as f:
    data = json.load(f)
    # Extract the 'verse_text' entries
    verse_texts = [entry['verse_text'] for entry in data]
    print(len(verse_texts))

verse_list = []
for verse_text in tqdm(verse_texts):
    verse_list.append(verse_text)

input = '\n'.join(verse_list)

output = macronizer.macronize(input)

with open('tests/unified_simplified_macronized.txt', 'w') as f:
    f.write(output)

# I now need to open 'tests/unified_simplified_macronized.json', which 
# is a duplicate of the input json, and replace the 'verse_text' entries with the macronized ones
# without touching the rest of the json

# with open(output_json, "r") as f:
#     out_data = json.load(f)

# for i, entry in enumerate(out_data):
#     entry["verse_text"] = output_list[i]

# with open(output_json, "w") as f:
#     json.dump(out_data, f, ensure_ascii=False, indent=4)

