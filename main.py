import sys

from class_macronizer import Macronizer
from grc_utils import colour_dichrona_in_open_syllables

macronizer = Macronizer(debug=False)

input_file = sys.argv[1]
output_file = sys.argv[2]

try:
    with open(input_file, 'r', encoding='utf-8') as f:
        text = f.read()
except FileNotFoundError:
    print(f"File '{input}' not found.")

output = macronizer.macronize(text, genre="prose", stats=True)

with open(output_file, 'w', encoding='utf-8') as f:
    f.write(output)
print(f"Macronized text written to '{output_file}'.")