import sys

from grc_macronizer import Macronizer

macronizer = Macronizer(make_prints=True)

input_file = sys.argv[1]
output_file = sys.argv[2]

try:
    with open(input_file, 'r', encoding='utf-8') as f:
        text = f.read()
except FileNotFoundError:
    print(f"File '{input}' not found.")

output = macronizer.macronize(text)

with open(output_file, 'w', encoding='utf-8') as f:
    f.write(output)

print(f"Macronized text written to '{output_file}'.")