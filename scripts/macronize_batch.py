'''
The Macronizer is very CPU intensive. On a system with multiple cores, ProcessPoolExecutor can speed up the process.
Assuming a quadcore system as per default, I divide the input text into four parts and set max_workers=4.
The Macronizer is faster if left to do its own sentence splitting, whence I will feed it four maximally long batches of texts.

'''

import sys

from grc_macronizer import Macronizer

macronizer = Macronizer(make_prints=False)

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